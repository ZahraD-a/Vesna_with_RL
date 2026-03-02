"""
VEsNA Office -- MiniGrid-style Gymnasium Environment.

Grid-world environment for the 50-room VEsNA office building.
Agent navigates between rooms (colored cells) connected by
passages (EC, green) and doors (PO, brown).

Usage:
    # View the map only
    python vesna_minigrid_env.py --view

    # Interactive navigation (number keys pick valid move)
    python vesna_minigrid_env.py

    # Replay trained DQN policy (original 11 rooms)
    python vesna_minigrid_env.py --checkpoint ../../checkpoints/alice.pt --original-11

    # Replay on full 50-room map
    python vesna_minigrid_env.py --checkpoint ../../checkpoints/alice.pt

    # BDI Mission replay (uses trained policy for navigation sub-goals)
    python vesna_minigrid_env.py --mission delivery
    python vesna_minigrid_env.py --mission patrol --delay 0.3
    python vesna_minigrid_env.py --mission multi_delivery --start lobby
"""

import argparse
import math
import os
import re
import sys
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

import gymnasium
import numpy as np
from gymnasium import spaces

try:
    import pygame

    _HAS_PYGAME = True
except ImportError:
    _HAS_PYGAME = False


# ==================================================================
#  ASL Map Parsing
# ==================================================================

def parse_map(filepath: str):
    """Parse an ASL map file -> rooms, furniture, EC edges, PO pairs."""
    rooms: Set[str] = set()
    furniture: Dict[str, str] = {}
    ec: List[Tuple[str, str]] = []
    po: List[Tuple[str, str]] = []
    ntpp_re = re.compile(r"map_ntpp\(\s*(\w+)\s*,\s*(\w+)\s*\)")
    ec_re = re.compile(r"map_ec\(\s*(\w+)\s*,\s*(\w+)\s*\)")
    po_re = re.compile(r"map_po\(\s*(\w+)\s*,\s*(\w+)\s*\)")
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line.startswith("//") or not line:
                continue
            m = ntpp_re.search(line)
            if m:
                if m.group(2) == "office":
                    rooms.add(m.group(1))
                else:
                    furniture[m.group(1)] = m.group(2)
                continue
            m = ec_re.search(line)
            if m:
                ec.append((m.group(1), m.group(2)))
                continue
            m = po_re.search(line)
            if m:
                po.append((m.group(1), m.group(2)))
    return rooms, furniture, ec, po


def derive_door_edges(po_pairs, rooms):
    """Derive room-to-room connections through shared doors."""
    po_link: Dict[str, Set[str]] = defaultdict(set)
    for a, b in po_pairs:
        po_link[a].add(b)
        po_link[b].add(a)
    ents: Set[str] = set()
    for a, b in po_pairs:
        ents.update([a, b])
    edges = []
    for door in ents - rooms:
        conn = [r for r in po_link[door] if r in rooms]
        for i in range(len(conn)):
            for j in range(i + 1, len(conn)):
                edges.append((conn[i], conn[j], door))
    return edges


# ==================================================================
#  Grid Layout  (unified -- hallways physically connect all wings)
# ==================================================================
#
#  Right hallway (col 7): corridor_north <-> corridor
#  Left  hallway (col 0): corridor <-> corridor_south <-> lobby

GRID: Dict[str, List[Tuple[int, int]]] = {
    # --- NORTH WING (rows 0-2) ---
    "office_1": [(2, 0)], "office_2": [(3, 0)], "office_3": [(4, 0)],
    "office_4": [(5, 0)], "office_5": [(6, 0)],
    "corridor_north": [(2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1)],
    "meeting_room_2": [(2, 2)], "meeting_room_3": [(3, 2)],
    "lab_1": [(4, 2)], "lab_2": [(5, 2)], "server_room": [(6, 2)],
    # right hallway connectors
    "_hall_r1": [(7, 2)], "_hall_r2": [(7, 3)],

    # --- MAIN FLOOR (rows 3-7) ---
    "mail_room": [(1, 3)], "reception": [(2, 3)],
    "corridor": [
        (0, 4), (1, 4), (2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4),
        (8, 4), (9, 4), (10, 4), (11, 4), (12, 4),
    ],
    "common": [(13, 4)], "kitchen": [(14, 4)],
    "open_office": [(3, 5), (4, 5), (5, 5), (6, 5)],
    "meeting_room": [(7, 5)], "senior_office_1": [(8, 5)],
    "senior_office_2": [(9, 5)], "senior_office_3": [(10, 5)],
    "restroom_1": [(11, 5)], "storage_1": [(12, 5)],
    "library": [(13, 5)], "phone_booth_1": [(14, 5)],
    "print_room": [(3, 6)], "outside": [(4, 6)],
    "boss_office_1": [(5, 6)], "boss_office_2": [(6, 6)],
    "supply_closet": [(12, 6)],
    "executive_suite": [(5, 7)],
    # left hallway connectors
    "_hall_l1": [(0, 5)], "_hall_l2": [(0, 6)], "_hall_l3": [(0, 7)],
    "_hall_l4": [(0, 8)], "_hall_l5": [(0, 9)],

    # --- SOUTH WING (rows 9-13) ---
    "office_6": [(1, 9)], "office_7": [(2, 9)], "office_8": [(3, 9)],
    "office_9": [(4, 9)], "office_10": [(5, 9)],
    "corridor_south": [
        (0, 10), (1, 10), (2, 10), (3, 10), (4, 10), (5, 10), (6, 10),
    ],
    "cafeteria": [(1, 11)], "gym": [(2, 11), (3, 11)],
    "restroom_2": [(4, 11)], "archive": [(5, 11)], "training_room": [(6, 11)],
    "terrace": [(1, 12)], "lounge": [(2, 12)], "wellness_room": [(3, 12)],
    "phone_booth_2": [(2, 13)],
    # left hallway connectors (south -> lobby)
    "_hall_l6": [(0, 11)], "_hall_l7": [(0, 12)],
    "_hall_l8": [(0, 13)], "_hall_l9": [(0, 14)],

    # --- LOBBY (rows 15-16) ---
    "lobby": [(0, 15), (1, 15), (2, 15), (3, 15)],
    "security_desk": [(1, 16)], "conference_room": [(4, 15)],
    "parking": [(2, 16)],
}

# Hallway EC connections (wall removal between hallway cells).
HALL_EC = [
    ("corridor_north", "_hall_r1"), ("_hall_r1", "_hall_r2"),
    ("_hall_r2", "corridor"),
    ("corridor", "_hall_l1"), ("_hall_l1", "_hall_l2"),
    ("_hall_l2", "_hall_l3"), ("_hall_l3", "_hall_l4"),
    ("_hall_l4", "_hall_l5"), ("_hall_l5", "corridor_south"),
    ("corridor_south", "_hall_l6"), ("_hall_l6", "_hall_l7"),
    ("_hall_l7", "_hall_l8"), ("_hall_l8", "_hall_l9"),
    ("_hall_l9", "lobby"),
]

# Pseudo-rooms used only as hallway connectors
HALL_ROOMS = {name for name in GRID if name.startswith("_hall_")}

# Ordered hallway waypoints between navigable rooms (for trail & animation).
# Each entry maps (src, dst) -> list of _hall_* rooms the path passes through.
HALL_ROUTES: Dict[Tuple[str, str], List[str]] = {}
_RAW_ROUTES = [
    ("corridor_north", ["_hall_r1", "_hall_r2"], "corridor"),
    ("corridor", ["_hall_l1", "_hall_l2", "_hall_l3", "_hall_l4", "_hall_l5"], "corridor_south"),
    ("corridor_south", ["_hall_l6", "_hall_l7", "_hall_l8", "_hall_l9"], "lobby"),
]
for _src, _wps, _dst in _RAW_ROUTES:
    HALL_ROUTES[(_src, _dst)] = _wps
    HALL_ROUTES[(_dst, _src)] = list(reversed(_wps))

# Original 11 rooms (for testing existing checkpoints).
ORIGINAL_11_ROOMS = [
    "reception", "corridor", "open_office", "outside", "common",
    "meeting_room", "senior_office_1", "senior_office_2",
    "senior_office_3", "boss_office_1", "boss_office_2",
]

# Training order from navigation_rl_bridge.asl (must match checkpoint IDs)
TRAINING_50_ROOMS = [
    "reception", "corridor", "open_office", "outside", "common",
    "meeting_room", "senior_office_1", "senior_office_2",
    "senior_office_3", "boss_office_1", "boss_office_2",
    "corridor_north", "corridor_south",
    "kitchen", "restroom_1", "storage_1",
    "meeting_room_2", "meeting_room_3", "lab_1", "lab_2", "server_room",
    "office_1", "office_2", "office_3", "office_4", "office_5",
    "lobby", "cafeteria", "gym", "restroom_2",
    "office_6", "office_7", "office_8", "office_9", "office_10",
    "archive", "training_room",
    "terrace", "parking", "conference_room", "security_desk",
    "library", "print_room", "mail_room", "executive_suite",
    "phone_booth_1", "phone_booth_2", "supply_closet", "lounge",
    "wellness_room",
]


# ==================================================================
#  Room Classification & Colors
# ==================================================================

def classify(name: str) -> str:
    if name.startswith("_hall"):
        return "corridor"
    if "corridor" in name:
        return "corridor"
    if any(k in name for k in ("office", "senior", "boss", "executive")):
        return "office"
    if name in ("common", "kitchen", "cafeteria"):
        return "common"
    if any(k in name for k in ("meeting", "conference", "training")):
        return "meeting"
    if name in ("lab_1", "lab_2", "server_room"):
        return "technical"
    if name in ("outside", "terrace", "parking"):
        return "outdoor"
    if name in ("lobby", "reception"):
        return "entrance"
    if name in ("restroom_1", "restroom_2", "storage_1", "supply_closet",
                "archive", "mail_room", "print_room", "security_desk"):
        return "utility"
    if name in ("gym", "lounge", "wellness_room", "phone_booth_1",
                "phone_booth_2", "library"):
        return "amenity"
    return "other"


# -- Softer architectural color scheme --
CATEGORY_RGB = {
    "corridor":  (240, 218, 115),
    "office":    (140, 198, 225),
    "common":    (145, 210, 145),
    "meeting":   (195, 165, 218),
    "technical": (228, 170, 100),
    "outdoor":   (115, 200, 140),
    "entrance":  (232, 158, 120),
    "utility":   (192, 192, 192),
    "amenity":   (228, 162, 188),
    "other":     (215, 215, 215),
}

WALL_CLR = (90, 95, 105)
WALL_LIGHT = (130, 135, 145)  # top/left bevel highlight
WALL_DARK = (60, 65, 75)      # bottom/right bevel shadow
BG_CLR = (235, 235, 230)
PASSAGE_CLR = (40, 155, 55)
DOOR_CLR = (150, 95, 55)
AGENT_CLR = (255, 70, 70)
GOAL_CLR = (40, 240, 40)
VALID_CLR = (255, 255, 90)
TRAIL_CLR = (220, 100, 60)

# --- RPG floor tile palettes (light, dark) per category ---
FLOOR_TILES = {
    "office":    ((170, 210, 235), (140, 185, 215)),
    "corridor":  ((225, 205, 165), (210, 190, 148)),
    "common":    ((160, 215, 160), (130, 195, 130)),
    "meeting":   ((195, 170, 215), (175, 148, 198)),
    "technical": ((185, 185, 190), (165, 165, 172)),
    "outdoor":   ((125, 195, 120), (105, 175, 100)),
    "entrance":  ((240, 225, 210), (218, 200, 185)),
    "utility":   ((195, 195, 195), (178, 178, 178)),
    "amenity":   ((200, 160, 130), (182, 140, 108)),
    "other":     ((215, 215, 215), (195, 195, 195)),
}

# --- Furniture layout: room_name -> [(type, x_off, y_off, *extra), ...] ---
# Offsets are relative to room's top-left pixel (or bounding box for multi-cell).
# Extra params: (w, h) for desks/tables, orientation char for chairs.
FURNITURE_LAYOUT = {
    "boss_office_1": [
        ("desk", 10, 8, 32, 18), ("chair", 24, 30), ("bookshelf", 4, 38),
    ],
    "boss_office_2": [
        ("desk", 10, 8, 32, 18), ("chair", 24, 30), ("desk", 10, 34, 22, 14),
    ],
    "senior_office_1": [
        ("desk", 4, 6, 22, 14), ("chair", 14, 24),
        ("desk", 30, 6, 22, 14), ("chair", 40, 24),
    ],
    "senior_office_2": [
        ("desk", 4, 6, 22, 14), ("chair", 14, 24),
        ("desk", 30, 6, 22, 14), ("chair", 40, 24),
    ],
    "senior_office_3": [
        ("desk", 4, 6, 22, 14), ("chair", 14, 24),
        ("desk", 30, 6, 22, 14), ("chair", 40, 24),
    ],
    "open_office": [
        # Row 1 (top) - 6 desks + chairs
        ("desk", 8, 10, 18, 12), ("chair", 16, 26),
        ("desk", 36, 10, 18, 12), ("chair", 44, 26),
        ("desk", 64, 10, 18, 12), ("chair", 72, 26),
        ("desk", 92, 10, 18, 12), ("chair", 100, 26),
        ("desk", 120, 10, 18, 12), ("chair", 128, 26),
        ("desk", 148, 10, 18, 12), ("chair", 156, 26),
        # Row 2 (bottom) - 6 desks + chairs
        ("desk", 8, 38, 18, 12), ("chair", 16, 34),
        ("desk", 36, 38, 18, 12), ("chair", 44, 34),
        ("desk", 64, 38, 18, 12), ("chair", 72, 34),
        ("desk", 92, 38, 18, 12), ("chair", 100, 34),
        ("desk", 120, 38, 18, 12), ("chair", 128, 34),
        ("desk", 148, 38, 18, 12), ("chair", 156, 34),
    ],
    "common": [
        ("coffee_machine", 6, 6), ("table_round", 28, 26),
        ("chair", 18, 22), ("chair", 38, 22), ("chair", 28, 40),
    ],
    "reception": [
        ("desk", 8, 10, 36, 16), ("chair", 24, 32),
    ],
    "outside": [
        ("bench", 10, 18), ("bench", 10, 38),
    ],
    "meeting_room": [
        ("table_rect", 14, 16, 28, 20),
        ("chair", 10, 14), ("chair", 44, 14), ("chair", 10, 38), ("chair", 44, 38),
    ],
    "meeting_room_2": [
        ("table_rect", 14, 16, 28, 20),
        ("chair", 10, 14), ("chair", 44, 14), ("chair", 10, 38), ("chair", 44, 38),
    ],
    "meeting_room_3": [
        ("table_rect", 14, 16, 28, 20),
        ("chair", 10, 14), ("chair", 44, 14), ("chair", 10, 38), ("chair", 44, 38),
    ],
    "kitchen": [
        ("table_rect", 12, 18, 30, 16), ("chair", 10, 38), ("chair", 36, 38),
        ("coffee_machine", 40, 4),
    ],
    "library": [
        ("bookshelf", 6, 4), ("bookshelf", 6, 22), ("bookshelf", 6, 40),
        ("desk", 30, 20, 20, 14), ("chair", 38, 38),
    ],
    "gym": [
        ("bench", 16, 14), ("bench", 16, 38),
        ("bench", 72, 14), ("bench", 72, 38),
    ],
    "lobby": [
        ("bench", 20, 10), ("bench", 80, 10),
        ("desk", 40, 30, 30, 16), ("chair", 54, 50),
    ],
    "conference_room": [
        ("table_rect", 10, 12, 34, 28),
        ("chair", 6, 10), ("chair", 46, 10), ("chair", 6, 38), ("chair", 46, 38),
    ],
    "executive_suite": [
        ("desk", 10, 8, 34, 18), ("chair", 26, 30), ("bookshelf", 4, 38),
    ],
    "cafeteria": [
        ("table_round", 16, 16), ("table_round", 36, 36),
        ("chair", 8, 12), ("chair", 24, 12), ("chair", 28, 32), ("chair", 44, 32),
    ],
    "training_room": [
        ("table_rect", 12, 14, 30, 24),
        ("chair", 8, 10), ("chair", 44, 10), ("chair", 8, 38), ("chair", 44, 38),
    ],
    "lounge": [
        ("bench", 10, 14), ("table_round", 28, 30), ("bench", 10, 38),
    ],
}

_LABELS = {
    "corridor_north": "CorrN", "corridor_south": "CorrS",
    "corridor": "Corridor", "senior_office_1": "Sr.Of1",
    "senior_office_2": "Sr.Of2", "senior_office_3": "Sr.Of3",
    "boss_office_1": "Boss1", "boss_office_2": "Boss2",
    "meeting_room": "Meet", "meeting_room_2": "Meet2",
    "meeting_room_3": "Meet3", "conference_room": "Conf",
    "executive_suite": "ExSuite", "phone_booth_1": "Ph1",
    "phone_booth_2": "Ph2", "supply_closet": "Supply",
    "training_room": "Train", "wellness_room": "Wellns",
    "security_desk": "Secur", "open_office": "OpenOff",
    "print_room": "Print", "mail_room": "Mail",
    "restroom_1": "WC1", "restroom_2": "WC2",
    "storage_1": "Store", "server_room": "Server",
}


def room_label(name: str) -> str:
    if name.startswith("_hall"):
        return ""
    return _LABELS.get(name, name.replace("_", " ").title())


# ==================================================================
#  Gymnasium Environment
# ==================================================================

class VesnaOfficeEnv(gymnasium.Env):
    """
    MiniGrid-style Gymnasium environment for the VEsNA office.

    Observation : float32 [current_one_hot | goal_one_hot]  (2*N)
    Action      : int room index (0..N-1), must be adjacent
    Reward      : +10 goal, -0.1/step, -0.5 invalid move
    Terminated  : agent reaches goal room
    Truncated   : steps >= max_steps
    """

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 4}

    CELL = 56   # pixels per macro-cell interior
    WALL = 4    # wall thickness
    STEP = 60   # CELL + WALL
    PAD = 20    # canvas padding
    BAR_H = 90  # status-bar height

    def __init__(
        self,
        render_mode: Optional[str] = None,
        map_path: Optional[str] = None,
        rooms: Optional[List[str]] = None,
        max_steps: int = 100,
    ):
        super().__init__()
        self.render_mode = render_mode
        self.max_steps = max_steps

        # --- Parse ASL map ---
        default_map = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "playgrounds", "office", "office_map.asl",
        )
        self._all_rooms, self._furniture, self._ec_raw, self._po_raw = parse_map(
            map_path or default_map
        )
        self._door_edges = derive_door_edges(self._po_raw, self._all_rooms)

        # --- Adjacency graph ---
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        for a, b in self._ec_raw:
            if a in self._all_rooms and b in self._all_rooms:
                self.adjacency[a].add(b)
                self.adjacency[b].add(a)
        for a, b, _ in self._door_edges:
            self.adjacency[a].add(b)
            self.adjacency[b].add(a)

        # --- Navigable room list (RL state/action space) ---
        # Preserve caller's order if provided (critical for checkpoint compatibility)
        self.nav_rooms: List[str] = list(rooms) if rooms else sorted(self._all_rooms)
        self.n: int = len(self.nav_rooms)
        self.r2i: Dict[str, int] = {r: i for i, r in enumerate(self.nav_rooms)}
        self.i2r: Dict[int, str] = {i: r for r, i in self.r2i.items()}

        # --- Gymnasium spaces ---
        self.observation_space = spaces.Box(0, 1, (self.n * 2,), np.float32)
        self.action_space = spaces.Discrete(self.n)

        # --- Episode state ---
        self.agent_room: Optional[str] = None
        self.goal_room: Optional[str] = None
        self.steps: int = 0
        self.episode_count: int = 0
        self.total_reward: float = 0.0
        self.trajectory: List[str] = []

        # --- Trail visualization ---
        # _trail holds every pixel waypoint (including hallway intermediates).
        # _trail_step_num maps each _trail index to its step number (0=start),
        # or -1 for hallway-only waypoints (no label drawn).
        self._trail: List[Tuple[int, int]] = []
        self._trail_step_num: List[int] = []

        # --- Animation state (multi-waypoint path) ---
        self._anim_path: List[Tuple[int, int]] = []
        self._anim_t: float = 1.0  # 1.0 = animation complete
        self._agent_direction: str = "down"  # RPG facing: up/down/left/right

        # --- Precompute pixel grid data ---
        self._c2r: Dict[Tuple[int, int], str] = {}
        for rname, cells in GRID.items():
            for c, r in cells:
                self._c2r[(c, r)] = rname
        all_c = [c for c, _ in self._c2r]
        all_r = [r for _, r in self._c2r]
        self._mc, self._mr = min(all_c), min(all_r)
        ncols = max(all_c) - self._mc + 1
        nrows = max(all_r) - self._mr + 1
        self._gw = self.WALL + ncols * self.STEP
        self._gh = self.WALL + nrows * self.STEP
        self._ww = self._gw + 2 * self.PAD
        self._wh = self._gh + 2 * self.PAD + self.BAR_H

        # connection sets
        self._ec_set: Set[frozenset] = set()
        for a, b in self._ec_raw:
            self._ec_set.add(frozenset([a, b]))
        for a, b in HALL_EC:
            self._ec_set.add(frozenset([a, b]))
        self._door_set: Set[frozenset] = set()
        for a, b, _ in self._door_edges:
            self._door_set.add(frozenset([a, b]))

        # --- Precompute room bounding boxes for outline borders ---
        self._room_bounds: Dict[str, Tuple[int, int, int, int]] = {}
        for rn, cells in GRID.items():
            xs = [self._px(c) for c, _ in cells]
            ys = [self._py(r) for _, r in cells]
            self._room_bounds[rn] = (
                min(xs) - 1, min(ys) - 1,
                max(xs) + self.CELL + 1, max(ys) + self.CELL + 1,
            )

        # --- Mission overlay state (set externally by mission replay) ---
        self.mission_name: Optional[str] = None
        self.mission_step_text: Optional[str] = None
        self.mission_carrying: List[str] = []

        # --- Pygame state (lazy init) ---
        self._win = None
        self._clk = None
        self._fnt = None
        self._fnt_sm = None
        self._fnt_bar = None

    # ---- Pixel helpers ----

    def _px(self, c: int) -> int:
        return self.PAD + self.WALL + (c - self._mc) * self.STEP

    def _py(self, r: int) -> int:
        return self.PAD + self.WALL + (r - self._mr) * self.STEP

    def _room_center(self, room: str) -> Tuple[int, int]:
        cells = GRID.get(room, [])
        if not cells:
            return self._ww // 2, self._gh // 2
        xs = [self._px(c) + self.CELL // 2 for c, r in cells]
        ys = [self._py(r) + self.CELL // 2 for c, r in cells]
        return int(sum(xs) / len(xs)), int(sum(ys) / len(ys))

    # ---- Doorway & routing helpers ----

    def _shared_edge_center(self, room_a: str, room_b: str) -> Optional[Tuple[int, int]]:
        """Pixel midpoint of the shared wall between two grid-adjacent rooms."""
        cells_a = set(GRID.get(room_a, []))
        cells_b = set(GRID.get(room_b, []))
        pts: List[Tuple[int, int]] = []
        for c, r in cells_a:
            if (c + 1, r) in cells_b:
                pts.append((self._px(c) + self.CELL + self.WALL // 2,
                            self._py(r) + self.CELL // 2))
            if (c - 1, r) in cells_b:
                pts.append((self._px(c) - self.WALL // 2,
                            self._py(r) + self.CELL // 2))
            if (c, r + 1) in cells_b:
                pts.append((self._px(c) + self.CELL // 2,
                            self._py(r) + self.CELL + self.WALL // 2))
            if (c, r - 1) in cells_b:
                pts.append((self._px(c) + self.CELL // 2,
                            self._py(r) - self.WALL // 2))
        if not pts:
            return None
        return (sum(x for x, _ in pts) // len(pts),
                sum(y for _, y in pts) // len(pts))

    def _step_waypoints(self, from_room: str, to_room: str) -> List[Tuple[int, int]]:
        """Intermediate pixel waypoints between two rooms (doorways + hallways).

        Does NOT include from_room center or to_room center -- only the
        points in between so the trail hugs walls and walks through doors.
        """
        route = HALL_ROUTES.get((from_room, to_room))
        if route:
            pts: List[Tuple[int, int]] = []
            prev = from_room
            for hall in route:
                edge = self._shared_edge_center(prev, hall)
                if edge:
                    pts.append(edge)
                pts.append(self._room_center(hall))
                prev = hall
            edge = self._shared_edge_center(prev, to_room)
            if edge:
                pts.append(edge)
            return pts

        # Direct adjacency -- insert the doorway point
        edge = self._shared_edge_center(from_room, to_room)
        if edge:
            return [edge]
        return []

    # ---- Animation helpers ----

    def _start_animation(self, from_room: str, to_room: str):
        """Begin smooth slide through doorways and hallways."""
        path = [self._room_center(from_room)]
        path.extend(self._step_waypoints(from_room, to_room))
        path.append(self._room_center(to_room))
        self._anim_path = path
        self._anim_t = 0.0
        # Set agent facing direction from movement vector
        sx, sy = path[0]
        ex, ey = path[-1]
        dx, dy = ex - sx, ey - sy
        if abs(dx) > abs(dy):
            self._agent_direction = "right" if dx > 0 else "left"
        else:
            self._agent_direction = "down" if dy > 0 else "up"

    def _animate_step(self, dt: float) -> bool:
        """Advance animation by dt seconds. Returns True while animating."""
        if self._anim_t >= 1.0:
            return False
        n_segs = max(1, len(self._anim_path) - 1)
        duration = n_segs * 0.12  # 0.12s per segment
        self._anim_t = min(1.0, self._anim_t + dt / duration)
        return self._anim_t < 1.0

    def _agent_draw_pos(self) -> Tuple[int, int]:
        """Current visual position of the agent (possibly mid-animation)."""
        if self._anim_t >= 1.0 or len(self._anim_path) < 2:
            if self.agent_room and self.agent_room in GRID:
                return self._room_center(self.agent_room)
            return self._ww // 2, self._gh // 2
        # smoothstep on total progress
        t = self._anim_t
        t = t * t * (3 - 2 * t)
        # map onto path segments
        n_segs = len(self._anim_path) - 1
        seg_f = t * n_segs
        seg_i = min(int(seg_f), n_segs - 1)
        seg_t = seg_f - seg_i
        sx, sy = self._anim_path[seg_i]
        ex, ey = self._anim_path[seg_i + 1]
        return int(sx + (ex - sx) * seg_t), int(sy + (ey - sy) * seg_t)

    def _run_animation(self):
        """Run the animation sub-loop until complete (call after step)."""
        if self._anim_t >= 1.0 or self._win is None:
            return
        clock = pygame.time.Clock()
        while self._anim_t < 1.0:
            dt = clock.tick(60) / 1000.0
            self._animate_step(dt)
            self._render_frame(pump_events=False)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.close()
                    sys.exit(0)

    # ---- Observation / valid actions ----

    def _obs(self) -> np.ndarray:
        o = np.zeros(self.n * 2, dtype=np.float32)
        if self.agent_room and self.agent_room in self.r2i:
            o[self.r2i[self.agent_room]] = 1.0
        if self.goal_room and self.goal_room in self.r2i:
            o[self.n + self.r2i[self.goal_room]] = 1.0
        return o

    def get_valid_actions(self) -> List[int]:
        """Return sorted list of valid action indices (neighbor rooms)."""
        if not self.agent_room:
            return []
        nbrs = self.adjacency.get(self.agent_room, set())
        return sorted(self.r2i[r] for r in nbrs if r in self.r2i)

    # ---- Gymnasium API ----

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        opt = options or {}

        self.agent_room = opt.get(
            "start_room", self.np_random.choice(self.nav_rooms)
        )
        cands = [r for r in self.nav_rooms if r != self.agent_room]
        self.goal_room = opt.get(
            "goal_room", self.np_random.choice(cands)
        )

        self.steps = 0
        self.total_reward = 0.0
        self.episode_count += 1
        self.trajectory = [self.agent_room]

        # Reset trail & animation
        self._trail = [self._room_center(self.agent_room)]
        self._trail_step_num = [0]
        self._anim_path = []
        self._anim_t = 1.0

        info = {
            "agent_room": self.agent_room,
            "goal_room": self.goal_room,
            "valid_actions": self.get_valid_actions(),
            "room_names": list(self.nav_rooms),
        }
        if self.render_mode == "human":
            self._render_frame()
        return self._obs(), info

    def step(self, action):
        action = int(action)
        target = self.i2r.get(action)
        valid = self.get_valid_actions()
        self.steps += 1

        prev_room = self.agent_room

        if action in valid and target:
            self.agent_room = target
            self.trajectory.append(self.agent_room)
            # Update trail (route through doorways & hallway waypoints)
            for wp in self._step_waypoints(prev_room, self.agent_room):
                self._trail.append(wp)
                self._trail_step_num.append(-1)
            self._trail.append(self._room_center(self.agent_room))
            self._trail_step_num.append(self.steps)
            # Start animation
            if prev_room and prev_room in GRID and self.agent_room in GRID:
                self._start_animation(prev_room, self.agent_room)
            if self.agent_room == self.goal_room:
                reward = 10.0
                terminated = True
            else:
                reward = -0.1
                terminated = False
        else:
            reward = -0.5
            terminated = False

        truncated = self.steps >= self.max_steps
        self.total_reward += reward

        info = {
            "agent_room": self.agent_room,
            "goal_room": self.goal_room,
            "valid_actions": self.get_valid_actions(),
            "steps": self.steps,
            "total_reward": self.total_reward,
        }
        if self.render_mode == "human":
            self._run_animation()
            self._render_frame()
        return self._obs(), reward, terminated, truncated, info

    # ---- Rendering ----

    def _init_pygame(self):
        if not _HAS_PYGAME:
            raise ImportError("pygame is required: pip install pygame")
        if self._win is None:
            pygame.init()
            pygame.display.set_caption("VEsNA Office - MiniGrid Environment")
            self._win = pygame.display.set_mode((self._ww, self._wh))
            self._clk = pygame.time.Clock()
            self._fnt_bar = pygame.font.SysFont("consolas,courier,monospace", 15)
            self._fnt = pygame.font.SysFont("consolas,courier,monospace", 11)
            self._fnt_sm = pygame.font.SysFont("consolas,courier,monospace", 11)

    # ---- RPG drawing helpers ----

    def _draw_floor_tiles(self, surf, px, py, col, row, room_name):
        """Draw 4x4 grid of 14px tiles with category-specific pattern."""
        C = self.CELL
        cat = classify(room_name)
        lt, dk = FLOOR_TILES.get(cat, ((215, 215, 215), (195, 195, 195)))
        ts = C // 4  # 14px tile size

        if cat == "office":
            # Checkerboard light/dark blue
            for ty in range(4):
                for tx in range(4):
                    clr = lt if (tx + ty) % 2 == 0 else dk
                    pygame.draw.rect(surf, clr, (px + tx * ts, py + ty * ts, ts, ts))
        elif cat == "corridor":
            # Stone tiles with 1px grout lines
            grout = (190, 172, 130)
            for ty in range(4):
                for tx in range(4):
                    x0, y0 = px + tx * ts, py + ty * ts
                    clr = lt if (tx + ty) % 2 == 0 else dk
                    pygame.draw.rect(surf, clr, (x0, y0, ts, ts))
                    pygame.draw.rect(surf, grout, (x0, y0, ts, ts), 1)
        elif cat == "common":
            # Green checkerboard
            for ty in range(4):
                for tx in range(4):
                    clr = lt if (tx + ty) % 2 == 0 else dk
                    pygame.draw.rect(surf, clr, (px + tx * ts, py + ty * ts, ts, ts))
        elif cat == "meeting":
            # Subtle carpet grid (purple tones)
            surf_rect = pygame.Surface((C, C))
            surf_rect.fill(lt)
            for ty in range(4):
                pygame.draw.line(surf_rect, dk, (0, ty * ts), (C, ty * ts), 1)
            for tx in range(4):
                pygame.draw.line(surf_rect, dk, (tx * ts, 0), (tx * ts, C), 1)
            surf.blit(surf_rect, (px, py))
        elif cat == "technical":
            # Metal plate with raised edges
            for ty in range(4):
                for tx in range(4):
                    x0, y0 = px + tx * ts, py + ty * ts
                    pygame.draw.rect(surf, dk, (x0, y0, ts, ts))
                    pygame.draw.rect(surf, lt, (x0 + 1, y0 + 1, ts - 2, ts - 2))
        elif cat == "outdoor":
            # Green grass base with scattered tan patches
            pygame.draw.rect(surf, lt, (px, py, C, C))
            for ty in range(4):
                for tx in range(4):
                    if (tx * 3 + ty * 7 + col + row) % 5 == 0:
                        x0, y0 = px + tx * ts + 2, py + ty * ts + 2
                        pygame.draw.rect(surf, (185, 170, 130), (x0, y0, ts - 4, ts - 4))
                    if (tx * 5 + ty * 3 + col) % 7 == 0:
                        cx = px + tx * ts + ts // 2
                        cy = py + ty * ts + ts // 2
                        pygame.draw.circle(surf, dk, (cx, cy), 2)
        elif cat == "entrance":
            # Marble diagonal checkerboard (white/beige)
            for ty in range(4):
                for tx in range(4):
                    clr = lt if (tx + ty) % 2 == 0 else dk
                    x0, y0 = px + tx * ts, py + ty * ts
                    pygame.draw.rect(surf, clr, (x0, y0, ts, ts))
                    # Diagonal line for marble veining
                    vein = (min(clr[0] + 12, 255), min(clr[1] + 8, 255), min(clr[2] + 5, 255))
                    pygame.draw.line(surf, vein, (x0, y0 + ts), (x0 + ts, y0), 1)
        elif cat == "utility":
            # Concrete speckle: flat gray with noise dots
            pygame.draw.rect(surf, lt, (px, py, C, C))
            for ty in range(4):
                for tx in range(4):
                    if (tx * 7 + ty * 11 + col * 3 + row * 5) % 4 == 0:
                        cx = px + tx * ts + ts // 2
                        cy = py + ty * ts + ts // 2
                        pygame.draw.circle(surf, dk, (cx, cy), 1)
        elif cat == "amenity":
            # Wood planks: horizontal brown stripes
            for ty in range(4):
                y0 = py + ty * ts
                clr = lt if ty % 2 == 0 else dk
                pygame.draw.rect(surf, clr, (px, y0, C, ts))
                # Plank separator line
                sep = (max(clr[0] - 20, 0), max(clr[1] - 18, 0), max(clr[2] - 15, 0))
                pygame.draw.line(surf, sep, (px, y0), (px + C, y0), 1)
        else:
            # Fallback: plain fill
            pygame.draw.rect(surf, lt, (px, py, C, C))

    def _draw_floor_shadows(self, surf):
        """Draw 4px dark strips along inner edges of floor cells that border walls."""
        C, W = self.CELL, self.WALL
        shadow = pygame.Surface((C, 4), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 35))
        shadow_v = pygame.Surface((4, C), pygame.SRCALPHA)
        shadow_v.fill((0, 0, 0, 35))
        for (c, r), rn in self._c2r.items():
            px, py = self._px(c), self._py(r)
            # Top edge shadow if no room cell above
            if (c, r - 1) not in self._c2r:
                surf.blit(shadow, (px, py))
            # Left edge shadow if no room cell to the left
            if (c - 1, r) not in self._c2r:
                surf.blit(shadow_v, (px, py))

    def _draw_carpet_runners(self, surf):
        """Draw deep red carpet runner strip on corridor rooms."""
        C = self.CELL
        runner_clr = (140, 45, 35)
        gold = (185, 150, 50)
        diamond_clr = (160, 60, 45)
        for (c, r), rn in self._c2r.items():
            if classify(rn) != "corridor":
                continue
            px, py = self._px(c), self._py(r)
            if rn in HALL_ROOMS:
                # Full-width vertical corridor runner (same width as horizontal)
                rw = 30
                rx = px + (C - rw) // 2
                pygame.draw.rect(surf, runner_clr, (rx, py, rw, C))
                pygame.draw.line(surf, gold, (rx, py), (rx, py + C - 1), 1)
                pygame.draw.line(surf, gold, (rx + rw - 1, py), (rx + rw - 1, py + C - 1), 1)
                # Diamond pattern
                dcx = px + C // 2
                dcy = py + C // 2
                dsz = 4
                pts = [(dcx, dcy - dsz), (dcx + dsz, dcy), (dcx, dcy + dsz), (dcx - dsz, dcy)]
                pygame.draw.polygon(surf, diamond_clr, pts)
            else:
                # Horizontal corridor runner
                rw = 30
                ry = py + (C - rw) // 2
                pygame.draw.rect(surf, runner_clr, (px, ry, C, rw))
                pygame.draw.line(surf, gold, (px, ry), (px + C - 1, ry), 1)
                pygame.draw.line(surf, gold, (px, ry + rw - 1), (px + C - 1, ry + rw - 1), 1)
                # Diamond pattern
                dcx = px + C // 2
                dcy = py + C // 2
                dsz = 4
                pts = [(dcx, dcy - dsz), (dcx + dsz, dcy), (dcx, dcy + dsz), (dcx - dsz, dcy)]
                pygame.draw.polygon(surf, diamond_clr, pts)

    # ---- Carpet turn indicators at corridor/hall junctions ----

    # Maps grid cell -> direction hint for carpet turn through the wall gap.
    # "from_above" = horizontal runner turns down into vertical runner
    # "to_below"   = vertical runner turns into horizontal runner below
    HALL_TURNS = {
        (7, 2): "from_above",   # corridor_north(7,1) -> _hall_r1(7,2)
        (7, 3): "to_below",     # _hall_r2(7,3) -> corridor(7,4)
        (0, 5): "from_above",   # corridor(0,4) -> _hall_l1(0,5)
        (0, 9): "to_below",     # _hall_l5(0,9) -> corridor_south(0,10)
        (0, 11): "from_above",  # corridor_south(0,10) -> _hall_l6(0,11)
        (0, 14): "to_below",    # _hall_l9(0,14) -> lobby(0,15)
    }

    def _draw_carpet_turns(self, surf):
        """Draw carpet strips through wall gaps at corridor/hall junctions."""
        C, W = self.CELL, self.WALL
        runner_clr = (140, 45, 35)
        gold = (185, 150, 50)
        rw = 30  # runner width, matching both horizontal and vertical

        for (gc, gr), direction in self.HALL_TURNS.items():
            if (gc, gr) not in self._c2r:
                continue
            px, py = self._px(gc), self._py(gr)
            rx = px + (C - rw) // 2  # x position of vertical runner

            if direction == "from_above":
                # Fill the wall gap above this cell with runner
                gap_y = py - W
                pygame.draw.rect(surf, runner_clr, (rx, gap_y, rw, W))
                pygame.draw.line(surf, gold, (rx, gap_y), (rx, gap_y + W - 1), 1)
                pygame.draw.line(surf, gold, (rx + rw - 1, gap_y), (rx + rw - 1, gap_y + W - 1), 1)
                # Small chevron arrow pointing down
                cx = px + C // 2
                cy = gap_y + W // 2
                pygame.draw.line(surf, gold, (cx - 3, cy - 1), (cx, cy + 1), 1)
                pygame.draw.line(surf, gold, (cx + 3, cy - 1), (cx, cy + 1), 1)
            else:  # "to_below"
                # Fill the wall gap below this cell with runner
                gap_y = py + C
                pygame.draw.rect(surf, runner_clr, (rx, gap_y, rw, W))
                pygame.draw.line(surf, gold, (rx, gap_y), (rx, gap_y + W - 1), 1)
                pygame.draw.line(surf, gold, (rx + rw - 1, gap_y), (rx + rw - 1, gap_y + W - 1), 1)
                # Small chevron arrow pointing down
                cx = px + C // 2
                cy = gap_y + W // 2
                pygame.draw.line(surf, gold, (cx - 3, cy - 1), (cx, cy + 1), 1)
                pygame.draw.line(surf, gold, (cx + 3, cy - 1), (cx, cy + 1), 1)

    # ---- Furniture shape drawing ----

    def _draw_desk(self, surf, x, y, w, h):
        """Brown desk rectangle with a small monitor."""
        pygame.draw.rect(surf, (120, 80, 45), (x, y, w, h))
        pygame.draw.rect(surf, (90, 60, 35), (x, y, w, h), 1)
        # Monitor
        mw, mh = min(10, w - 4), min(7, h - 4)
        mx = x + w // 2 - mw // 2
        my = y + 2
        pygame.draw.rect(surf, (50, 50, 60), (mx, my, mw, mh))
        pygame.draw.rect(surf, (80, 180, 220), (mx + 1, my + 1, mw - 2, mh - 2))

    def _draw_chair(self, surf, x, y):
        """Small dark circle with backrest arc."""
        pygame.draw.circle(surf, (65, 55, 50), (x, y), 5)
        pygame.draw.circle(surf, (45, 38, 35), (x, y), 5, 1)

    def _draw_table_round(self, surf, x, y):
        """Brown circle table."""
        pygame.draw.circle(surf, (130, 90, 50), (x, y), 10)
        pygame.draw.circle(surf, (100, 65, 35), (x, y), 10, 1)

    def _draw_table_rect(self, surf, x, y, w, h):
        """Brown rectangular table."""
        pygame.draw.rect(surf, (130, 90, 50), (x, y, w, h))
        pygame.draw.rect(surf, (100, 65, 35), (x, y, w, h), 1)

    def _draw_bookshelf(self, surf, x, y):
        """Tall rectangle with shelf lines and colored book rects."""
        pygame.draw.rect(surf, (100, 70, 40), (x, y, 14, 16))
        pygame.draw.rect(surf, (80, 55, 30), (x, y, 14, 16), 1)
        # Shelf lines
        for sy in (y + 5, y + 10):
            pygame.draw.line(surf, (80, 55, 30), (x, sy), (x + 13, sy), 1)
        # Colored books
        colors = [(180, 50, 40), (40, 100, 180), (50, 150, 60), (180, 150, 40)]
        for i, bc in enumerate(colors):
            bx = x + 1 + i * 3
            pygame.draw.rect(surf, bc, (bx, y + 1, 2, 4))

    def _draw_bench(self, surf, x, y):
        """Light brown bench rectangle with leg marks."""
        pygame.draw.rect(surf, (170, 140, 95), (x, y, 28, 10))
        pygame.draw.rect(surf, (130, 105, 70), (x, y, 28, 10), 1)
        # Legs
        pygame.draw.rect(surf, (100, 80, 50), (x + 2, y + 10, 3, 3))
        pygame.draw.rect(surf, (100, 80, 50), (x + 23, y + 10, 3, 3))

    def _draw_coffee_machine(self, surf, x, y):
        """Gray rectangle with indicator light."""
        pygame.draw.rect(surf, (140, 140, 145), (x, y, 12, 14))
        pygame.draw.rect(surf, (110, 110, 115), (x, y, 12, 14), 1)
        # Indicator light
        pygame.draw.circle(surf, (60, 220, 60), (x + 6, y + 4), 2)

    def _draw_all_furniture(self, surf):
        """Draw furniture for all rooms that have layout definitions."""
        for rn, items in FURNITURE_LAYOUT.items():
            cells = GRID.get(rn)
            if not cells:
                continue
            # Bounding box top-left in pixels
            xs = [self._px(c) for c, _ in cells]
            ys = [self._py(r) for _, r in cells]
            bx, by = min(xs), min(ys)
            for item in items:
                kind = item[0]
                ox, oy = item[1], item[2]
                x, y = bx + ox, by + oy
                if kind == "desk":
                    self._draw_desk(surf, x, y, item[3], item[4])
                elif kind == "chair":
                    self._draw_chair(surf, x, y)
                elif kind == "table_round":
                    self._draw_table_round(surf, x, y)
                elif kind == "table_rect":
                    self._draw_table_rect(surf, x, y, item[3], item[4])
                elif kind == "bookshelf":
                    self._draw_bookshelf(surf, x, y)
                elif kind == "bench":
                    self._draw_bench(surf, x, y)
                elif kind == "coffee_machine":
                    self._draw_coffee_machine(surf, x, y)

    # ---- RPG agent character ----

    def _draw_agent_character(self, surf, cx, cy, direction):
        """Draw a ~20x26px top-down RPG person at (cx, cy)."""
        # Drop shadow
        shadow = pygame.Surface((20, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 50), (0, 0, 20, 8))
        surf.blit(shadow, (cx - 10, cy + 8))

        # Body (red shirt)
        pygame.draw.rect(surf, (210, 55, 45), (cx - 6, cy - 2, 12, 12))
        pygame.draw.rect(surf, (180, 40, 35), (cx - 6, cy - 2, 12, 12), 1)

        # Arms
        pygame.draw.rect(surf, (210, 55, 45), (cx - 9, cy, 4, 8))
        pygame.draw.rect(surf, (210, 55, 45), (cx + 5, cy, 4, 8))
        # Hands (skin)
        pygame.draw.circle(surf, (220, 180, 140), (cx - 7, cy + 9), 2)
        pygame.draw.circle(surf, (220, 180, 140), (cx + 7, cy + 9), 2)

        # Legs
        pygame.draw.rect(surf, (60, 60, 120), (cx - 5, cy + 10, 4, 6))
        pygame.draw.rect(surf, (60, 60, 120), (cx + 1, cy + 10, 4, 6))
        # Shoes
        pygame.draw.rect(surf, (50, 40, 30), (cx - 5, cy + 15, 5, 2))
        pygame.draw.rect(surf, (50, 40, 30), (cx + 1, cy + 15, 5, 2))

        # Head
        pygame.draw.circle(surf, (220, 180, 140), (cx, cy - 6), 7)
        # Hair
        pygame.draw.arc(surf, (60, 40, 25), (cx - 7, cy - 14, 14, 12), 0, 3.14, 3)

        # Eyes (direction-aware)
        if direction == "left":
            ex1, ex2 = cx - 3, cx + 1
        elif direction == "right":
            ex1, ex2 = cx - 1, cx + 3
        else:
            ex1, ex2 = cx - 3, cx + 3
        ey = cy - 7 if direction == "up" else cy - 5
        pygame.draw.circle(surf, (255, 255, 255), (ex1, ey), 2)
        pygame.draw.circle(surf, (255, 255, 255), (ex2, ey), 2)
        # Pupils
        if direction == "up":
            pygame.draw.circle(surf, (30, 30, 30), (ex1, ey - 1), 1)
            pygame.draw.circle(surf, (30, 30, 30), (ex2, ey - 1), 1)
        elif direction == "down":
            pygame.draw.circle(surf, (30, 30, 30), (ex1, ey + 1), 1)
            pygame.draw.circle(surf, (30, 30, 30), (ex2, ey + 1), 1)
        elif direction == "left":
            pygame.draw.circle(surf, (30, 30, 30), (ex1 - 1, ey), 1)
            pygame.draw.circle(surf, (30, 30, 30), (ex2 - 1, ey), 1)
        else:
            pygame.draw.circle(surf, (30, 30, 30), (ex1 + 1, ey), 1)
            pygame.draw.circle(surf, (30, 30, 30), (ex2 + 1, ey), 1)

    def _render_frame(self, pump_events: bool = True):
        self._init_pygame()
        s = self._win
        C, W = self.CELL, self.WALL

        # 1) Background
        s.fill(BG_CLR)

        # 2) Wall blocks with 3D bevel around occupied cells
        for (c, r) in self._c2r:
            bx = self.PAD + (c - self._mc) * self.STEP
            by = self.PAD + (r - self._mr) * self.STEP
            bw, bh = self.STEP + W, self.STEP + W
            pygame.draw.rect(s, WALL_CLR, (bx, by, bw, bh))
            # Bevel highlight (top + left)
            pygame.draw.rect(s, WALL_LIGHT, (bx, by, bw, 2))
            pygame.draw.rect(s, WALL_LIGHT, (bx, by, 2, bh))
            # Bevel shadow (bottom + right)
            pygame.draw.rect(s, WALL_DARK, (bx, by + bh - 2, bw, 2))
            pygame.draw.rect(s, WALL_DARK, (bx + bw - 2, by, 2, bh))

        # 3) Room interiors (tiled floors)
        for (c, r), rn in self._c2r.items():
            self._draw_floor_tiles(s, self._px(c), self._py(r), c, r, rn)

        # 3b) Floor shadows along inner wall edges
        self._draw_floor_shadows(s)

        # 4) Remove internal walls within multi-cell rooms
        for rn, cells in GRID.items():
            cs = set(cells)
            cat = classify(rn)
            lt = FLOOR_TILES.get(cat, ((215, 215, 215), (195, 195, 195)))[0]
            for c, r in cells:
                if (c + 1, r) in cs:
                    pygame.draw.rect(s, lt, (self._px(c) + C, self._py(r), W, C))
                if (c, r + 1) in cs:
                    pygame.draw.rect(s, lt, (self._px(c), self._py(r) + C, C, W))

        # 4b) Carpet runners on corridors
        self._draw_carpet_runners(s)
        self._draw_carpet_turns(s)

        # 4c) Furniture
        self._draw_all_furniture(s)

        # 5) Openings (passages & doors) between different rooms
        for (c, r), rn in self._c2r.items():
            for dc, dr in [(1, 0), (0, 1)]:
                nc, nr = c + dc, r + dr
                if (nc, nr) not in self._c2r:
                    continue
                nn = self._c2r[(nc, nr)]
                if nn == rn:
                    continue
                pair = frozenset([rn, nn])
                is_hall_pair = rn in HALL_ROOMS or nn in HALL_ROOMS
                if pair in self._ec_set:
                    if is_hall_pair:
                        # Full-width corridor-colored openings for hall connections
                        conn_clr = CATEGORY_RGB.get("corridor", (240, 218, 115))
                        if dc == 1:
                            pygame.draw.rect(
                                s, conn_clr,
                                (self._px(c) + C, self._py(r) + 2, W, C - 4),
                            )
                        else:
                            pygame.draw.rect(
                                s, conn_clr,
                                (self._px(c) + 2, self._py(r) + C, C - 4, W),
                            )
                    else:
                        if dc == 1:
                            pygame.draw.rect(
                                s, PASSAGE_CLR,
                                (self._px(c) + C, self._py(r) + 2, W, C - 4),
                            )
                        else:
                            pygame.draw.rect(
                                s, PASSAGE_CLR,
                                (self._px(c) + 2, self._py(r) + C, C - 4, W),
                            )
                elif pair in self._door_set:
                    span = max(6, C // 3)
                    if dc == 1:
                        mid = self._py(r) + C // 2
                        pygame.draw.rect(
                            s, DOOR_CLR,
                            (self._px(c) + C, mid - span // 2, W, span),
                        )
                    else:
                        mid = self._px(c) + C // 2
                        pygame.draw.rect(
                            s, DOOR_CLR,
                            (mid - span // 2, self._py(r) + C, span, W),
                        )

        # 5b) Room outline borders
        for rn, (x0, y0, x1, y1) in self._room_bounds.items():
            pygame.draw.rect(s, (80, 90, 105), (x0, y0, x1 - x0, y1 - y0), 1)

        # 6) Highlight valid moves (yellow border)
        if self.agent_room:
            for a_idx in self.get_valid_actions():
                tgt = self.i2r[a_idx]
                for gc, gr in GRID.get(tgt, []):
                    pygame.draw.rect(
                        s, VALID_CLR,
                        (self._px(gc) - 1, self._py(gr) - 1, C + 2, C + 2), 2,
                    )

        # 6b) Path trail
        if len(self._trail) >= 2:
            pygame.draw.lines(s, TRAIL_CLR, False, self._trail, 2)
        for i, (tx, ty) in enumerate(self._trail):
            step_num = self._trail_step_num[i] if i < len(self._trail_step_num) else -1
            if step_num >= 0:
                # Real room stop: bigger dot + step number label
                pygame.draw.circle(s, TRAIL_CLR, (tx, ty), 5)
                if step_num > 0:
                    lbl = self._fnt_sm.render(str(step_num), True, (255, 220, 180))
                    s.blit(lbl, (tx + 6, ty - 11))
            else:
                # Hallway waypoint: small dot, no label
                pygame.draw.circle(s, TRAIL_CLR, (tx, ty), 3)

        # 7) Goal marker (pulsing green diamond)
        if self.goal_room and self.goal_room in GRID:
            gx, gy = self._room_center(self.goal_room)
            pulse = 2.0 * math.sin(time.time() * 4.0 * 2.0 * math.pi)
            sz = int(14 + pulse)
            pts = [(gx, gy - sz), (gx + sz, gy), (gx, gy + sz), (gx - sz, gy)]
            pygame.draw.polygon(s, GOAL_CLR, pts)
            pygame.draw.polygon(s, (0, 160, 0), pts, 2)
            # Inner sparkle
            inner = max(3, sz // 3)
            pts2 = [(gx, gy - inner), (gx + inner, gy), (gx, gy + inner), (gx - inner, gy)]
            pygame.draw.polygon(s, (180, 255, 180), pts2)

        # 8) Agent character (RPG sprite)
        ax, ay = self._agent_draw_pos()
        self._draw_agent_character(s, ax, ay, self._agent_direction)

        # 9) Room labels (text over cells)
        for rn, cells in GRID.items():
            txt = room_label(rn)
            if not txt:
                continue
            cx, cy = self._room_center(rn)
            ncells = len(cells)
            offy = 18 if ncells > 1 else 16
            ts = self._fnt_sm.render(txt, True, (15, 15, 15))
            tr = ts.get_rect(center=(cx, cy + offy))
            bg = pygame.Surface((tr.width + 4, tr.height + 2), pygame.SRCALPHA)
            clr = CATEGORY_RGB.get(classify(rn), (215, 215, 215))
            bg.fill((*clr, 180))
            s.blit(bg, (tr.x - 2, tr.y - 1))
            s.blit(ts, tr)

        # 10) Enhanced status bar
        bar_y = self._gh + 2 * self.PAD
        # Dark panel background
        pygame.draw.rect(s, (240, 240, 240), (0, bar_y, self._ww, self.BAR_H))
        pygame.draw.line(s, (180, 180, 180), (0, bar_y), (self._ww, bar_y), 1)
        text_y = bar_y + 8
        if self.mission_name:
            # --- Mission mode status bar ---
            mission_label = f"MISSION: {self.mission_name}"
            if self.mission_carrying:
                mission_label += f"   Carrying: {', '.join(self.mission_carrying)}"
            ts = self._fnt_bar.render(mission_label, True, (0, 120, 0))
            s.blit(ts, (self.PAD, text_y))
            step_text = self.mission_step_text or ""
            ts2 = self._fnt_bar.render(step_text, True, (160, 120, 0))
            s.blit(ts2, (self.PAD, text_y + 20))
            room_info = f"Room: {self.agent_room}"
            if self.goal_room:
                room_info += f"   Nav goal: {self.goal_room}   Step: {self.steps}"
            ts3 = self._fnt_bar.render(room_info, True, (60, 60, 60))
            s.blit(ts3, (self.PAD, text_y + 40))
        elif self.agent_room:
            line1 = (
                f"Room: {self.agent_room}   Goal: {self.goal_room}"
                f"   Step: {self.steps}/{self.max_steps}"
                f"   R: {self.total_reward:.1f}"
                f"   Ep: {self.episode_count}"
            )
            ts = self._fnt_bar.render(line1, True, (30, 30, 30))
            s.blit(ts, (self.PAD, text_y))
            moves_str = ", ".join(self.i2r[a] for a in self.get_valid_actions())
            line2 = f"Moves: {moves_str}"
            ts2 = self._fnt_bar.render(line2, True, (60, 60, 60))
            s.blit(ts2, (self.PAD, text_y + 22))
        else:
            ts = self._fnt_bar.render("Press R to start | Q to quit", True, (80, 80, 80))
            s.blit(ts, (self.PAD, text_y))

        # 11) Legend (compact, top-right)
        lx = self._ww - 130
        ly = self.PAD + 2
        for cat in ("corridor", "office", "common", "meeting", "technical",
                     "outdoor", "entrance", "utility", "amenity"):
            clr = CATEGORY_RGB[cat]
            pygame.draw.rect(s, clr, (lx, ly, 12, 12))
            pygame.draw.rect(s, (120, 120, 120), (lx, ly, 12, 12), 1)
            ts = self._fnt_sm.render(cat.title(), True, (40, 40, 40))
            s.blit(ts, (lx + 16, ly - 1))
            ly += 16
        # passage / door legend
        pygame.draw.rect(s, PASSAGE_CLR, (lx, ly, 12, 4))
        ts = self._fnt_sm.render("Passage", True, (40, 40, 40))
        s.blit(ts, (lx + 16, ly - 3))
        ly += 16
        pygame.draw.rect(s, DOOR_CLR, (lx, ly, 12, 4))
        ts = self._fnt_sm.render("Door", True, (40, 40, 40))
        s.blit(ts, (lx + 16, ly - 3))

        pygame.display.flip()
        self._clk.tick(self.metadata["render_fps"])

        # pump events so window stays responsive
        if pump_events:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.close()
                    sys.exit(0)

    def render(self):
        if self.render_mode == "rgb_array":
            self._init_pygame()
            self._render_frame()
            return pygame.surfarray.array3d(self._win).transpose(1, 0, 2)
        if self.render_mode == "human":
            self._render_frame()

    def close(self):
        if self._win is not None:
            pygame.quit()
            self._win = None


# ==================================================================
#  Interactive Demo
# ==================================================================

def _interactive(env: VesnaOfficeEnv, reset_options: Optional[dict] = None):
    """Navigate with number keys. R = reset, Q = quit."""
    obs, info = env.reset(options=reset_options)
    print(f"\n=== VEsNA Office Navigation ===")
    print(f"Goal: {env.goal_room}")
    print("Press 1-9 to pick a valid move, R to reset, Q to quit.\n")

    running = True
    while running:
        valid = env.get_valid_actions()
        vr = [(a, env.i2r[a]) for a in valid]
        print(f"  [{env.agent_room}] -> Goal: {env.goal_room}")
        for i, (_, rn) in enumerate(vr):
            print(f"    [{i + 1}] {rn}")

        action = None
        while action is None:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return
                if ev.type != pygame.KEYDOWN:
                    continue
                if ev.key == pygame.K_q:
                    return
                if ev.key == pygame.K_r:
                    obs, info = env.reset()
                    print(f"\n--- Reset! Goal: {env.goal_room} ---")
                    action = -2
                    break
                num = ev.key - pygame.K_1
                if 0 <= num < len(vr):
                    action = vr[num][0]
                    break
            time.sleep(0.01)

        if action == -2:
            continue

        obs, reward, term, trunc, info = env.step(action)
        print(f"  -> {env.agent_room}  (r={reward:.1f}  total={env.total_reward:.1f})")

        if term:
            print(f"\n  GOAL in {env.steps} steps! ({' -> '.join(env.trajectory)})")
            time.sleep(1.5)
            obs, info = env.reset()
            print(f"\n--- New episode! Goal: {env.goal_room} ---")
        elif trunc:
            print(f"\n  Max steps. Resetting...")
            time.sleep(0.8)
            obs, info = env.reset()
            print(f"\n--- New episode! Goal: {env.goal_room} ---")


# ==================================================================
#  Policy Replay
# ==================================================================

def _replay(env: VesnaOfficeEnv, ckpt: str, episodes: int, delay: float,
            reset_options: Optional[dict] = None):
    """Load a DQN checkpoint and replay its policy visually."""
    try:
        from dqn_agent import DQNAgent
        import torch
    except ImportError:
        print("ERROR: cannot import dqn_agent/torch. Run from mind/python/.")
        return

    # Load checkpoint to get hidden size
    ckpt_data = torch.load(ckpt, map_location='cpu')
    if 'policy_net' in ckpt_data:
        hidden_size = ckpt_data['policy_net']['fc1.weight'].shape[0]
    else:
        hidden_size = 64  # default

    agent = DQNAgent(state_size=env.n * 2, action_size=env.n, hidden_size=hidden_size)
    agent.load(ckpt)
    agent.set_eval_mode(True)
    print(f"Loaded: {ckpt}  ({env.n} rooms, hidden={hidden_size})")

    for ep in range(episodes):
        obs, info = env.reset(options=reset_options)
        print(f"\n=== Ep {ep + 1} === {env.agent_room} -> {env.goal_room}")
        done = False
        while not done:
            va = info["valid_actions"]
            act, qv, expl = agent.step_with_explanation(
                state=obs, valid_actions=va, reward=0.0, done=False,
            )
            obs, rew, term, trunc, info = env.step(act)
            done = term or trunc
            print(f"  step {env.steps}: -> {env.agent_room} (r={rew:.1f} {expl})")
            time.sleep(delay)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (
                    ev.type == pygame.KEYDOWN and ev.key == pygame.K_q
                ):
                    env.close()
                    return
        tag = "GOAL!" if term else "truncated"
        print(f"  {tag}  ({' -> '.join(env.trajectory)})")
        time.sleep(1)


# ==================================================================
#  Mission Replay  (BDI + trained RL policy)
# ==================================================================

# Missions: list of (action, argument) tuples
# Actions: "go" = navigate using RL, "pickup"/"drop"/"inspect" = BDI-only
MISSIONS = {
    "delivery": [
        ("go",      "mail_room"),
        ("pickup",  "package"),
        ("go",      "boss_office_1"),
        ("drop",    "package"),
    ],
    "patrol": [
        ("go",      "server_room"),
        ("inspect", "servers"),
        ("go",      "lab_1"),
        ("inspect", "lab_equipment"),
        ("go",      "lobby"),
        ("inspect", "entrance"),
        ("go",      "reception"),
    ],
    "multi_delivery": [
        ("go",      "mail_room"),
        ("pickup",  "package_a"),
        ("go",      "office_1"),
        ("drop",    "package_a"),
        ("go",      "mail_room"),
        ("pickup",  "package_b"),
        ("go",      "lab_2"),
        ("drop",    "package_b"),
        ("go",      "reception"),
    ],
}


def _mission_replay(env: VesnaOfficeEnv, ckpt: str, mission_name: str,
                    delay: float, start_room: str = "reception"):
    """Execute a BDI mission using the trained RL policy, visualized on the grid."""
    try:
        from dqn_agent import DQNAgent
        import torch
    except ImportError:
        print("ERROR: cannot import dqn_agent/torch. Run from mind/python/.")
        return

    if mission_name not in MISSIONS:
        print(f"ERROR: unknown mission '{mission_name}'")
        print(f"Available: {list(MISSIONS.keys())}")
        return

    subgoals = MISSIONS[mission_name]

    # Load trained policy
    ckpt_data = torch.load(ckpt, map_location='cpu', weights_only=False)
    if 'policy_net' in ckpt_data:
        hidden_size = ckpt_data['policy_net']['fc1.weight'].shape[0]
    else:
        hidden_size = 128
    agent = DQNAgent(state_size=env.n * 2, action_size=env.n, hidden_size=hidden_size)
    agent.load(ckpt)
    agent.set_eval_mode(True)
    print(f"Loaded policy: {ckpt}  ({env.n} rooms, hidden={hidden_size})")

    # Setup initial state
    env.mission_name = mission_name
    env.mission_carrying = []
    env.agent_room = start_room
    env.goal_room = None
    env.steps = 0
    env.trajectory = [start_room]
    env._trail = [env._room_center(start_room)]
    env._trail_step_num = [0]

    print(f"\n{'='*50}")
    print(f"  MISSION: {mission_name.upper()}")
    print(f"  Start: {start_room}")
    print(f"  Sub-goals: {subgoals}")
    print(f"{'='*50}\n")

    # Show initial state
    env.mission_step_text = f"Starting mission at {start_room}..."
    env._render_frame()
    time.sleep(1.0)

    def check_quit():
        """Returns True if user wants to quit."""
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return True
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_q:
                return True
        return False

    # Execute each sub-goal
    for i, (action, arg) in enumerate(subgoals):
        step_num = i + 1

        if check_quit():
            env.close()
            return

        if action == "go":
            # ---- NAVIGATE using trained RL policy ----
            target_room = arg
            env.mission_step_text = f"Step {step_num}/{len(subgoals)}: Navigate to {target_room}"
            env.goal_room = target_room
            print(f"--- Step {step_num}: go({target_room}) ---")

            if env.agent_room == target_room:
                print(f"  Already at {target_room}!")
                env.mission_step_text = f"Step {step_num}: Already at {target_room}!"
                env._render_frame()
                time.sleep(delay)
                continue

            # Reset trail for this navigation sub-goal
            env._trail = [env._room_center(env.agent_room)]
            env._trail_step_num = [0]
            env.steps = 0

            print(f"  Navigating: {env.agent_room} -> {target_room}")
            env._render_frame()
            time.sleep(delay * 0.5)

            # RL navigation loop
            nav_steps = 0
            max_nav = 150
            while env.agent_room != target_room and nav_steps < max_nav:
                if check_quit():
                    env.close()
                    return

                # Build observation
                obs = env._obs()
                # Set goal in observation
                obs = np.zeros(env.n * 2, dtype=np.float32)
                obs[env.r2i[env.agent_room]] = 1.0
                obs[env.n + env.r2i[target_room]] = 1.0

                valid_actions = env.get_valid_actions()
                act, qv, expl = agent.step_with_explanation(
                    state=obs, valid_actions=valid_actions, reward=0.0, done=False,
                )

                next_room = env.i2r[act]
                prev_room = env.agent_room

                # Update trail
                for wp in env._step_waypoints(prev_room, next_room):
                    env._trail.append(wp)
                    env._trail_step_num.append(-1)
                env._trail.append(env._room_center(next_room))
                nav_steps += 1
                env._trail_step_num.append(nav_steps)

                # Animate movement
                if prev_room in GRID and next_room in GRID:
                    env._start_animation(prev_room, next_room)

                env.agent_room = next_room
                env.steps = nav_steps
                env.trajectory.append(next_room)

                q_str = ""
                if qv is not None:
                    q_str = f" Q={qv[act]:.2f}"
                print(f"    Step {nav_steps}: {prev_room} -> {next_room}{q_str} ({expl})")

                env.mission_step_text = (
                    f"Step {step_num}/{len(subgoals)}: "
                    f"{prev_room} -> {next_room}  (nav step {nav_steps})"
                )

                # Run animation then render
                env._run_animation()
                env._render_frame()
                time.sleep(delay)

            if env.agent_room == target_room:
                print(f"  Arrived at {target_room} in {nav_steps} steps!")
                env.mission_step_text = (
                    f"Step {step_num}: Arrived at {target_room} in {nav_steps} steps!"
                )
            else:
                print(f"  TIMEOUT navigating to {target_room}")
                env.mission_step_text = f"Step {step_num}: TIMEOUT reaching {target_room}"
            env.goal_room = None
            env._render_frame()
            time.sleep(delay)

        elif action == "pickup":
            # ---- BDI ACTION: pickup ----
            env.mission_carrying.append(arg)
            env.mission_step_text = (
                f"Step {step_num}/{len(subgoals)}: Picked up {arg} at {env.agent_room}"
            )
            print(f"--- Step {step_num}: pickup({arg}) at {env.agent_room} ---")
            env._render_frame()
            time.sleep(delay * 1.5)

        elif action == "drop":
            # ---- BDI ACTION: drop ----
            if arg in env.mission_carrying:
                env.mission_carrying.remove(arg)
            env.mission_step_text = (
                f"Step {step_num}/{len(subgoals)}: Delivered {arg} to {env.agent_room}"
            )
            print(f"--- Step {step_num}: drop({arg}) at {env.agent_room} ---")
            env._render_frame()
            time.sleep(delay * 1.5)

        elif action == "inspect":
            # ---- BDI ACTION: inspect ----
            env.mission_step_text = (
                f"Step {step_num}/{len(subgoals)}: Inspecting {arg} at {env.agent_room}"
            )
            print(f"--- Step {step_num}: inspect({arg}) at {env.agent_room} ---")
            env._render_frame()
            time.sleep(delay * 1.5)

    # Mission complete!
    print(f"\n{'='*50}")
    print(f"  MISSION COMPLETE: {mission_name.upper()}")
    print(f"{'='*50}")
    env.mission_step_text = "MISSION COMPLETE!"
    env.goal_room = None
    env._render_frame()

    # Wait for user to close
    print("\nPress Q or close window to exit.")
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                env.close()
                return
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_q:
                env.close()
                return
        time.sleep(0.05)


# ==================================================================
#  Main
# ==================================================================

def main():
    ap = argparse.ArgumentParser(description="VEsNA Office MiniGrid Environment")
    ap.add_argument("--view", action="store_true", help="View map only")
    ap.add_argument("--checkpoint", type=str, help="DQN checkpoint for replay")
    ap.add_argument("--mission", type=str, default=None,
                    choices=list(MISSIONS.keys()),
                    help="Run a BDI mission (delivery, patrol, multi_delivery)")
    ap.add_argument("--original-11", action="store_true",
                    help="Use only the original 11 rooms")
    ap.add_argument("--episodes", type=int, default=5)
    ap.add_argument("--delay", type=float, default=0.5)
    ap.add_argument("--max-steps", type=int, default=100)
    ap.add_argument("--map", type=str, default=None)
    ap.add_argument("--start", type=str, default=None,
                    help="Start room name (e.g. reception)")
    ap.add_argument("--goal", type=str, default=None,
                    help="Goal room name (e.g. boss_office_1)")
    args = ap.parse_args()

    if args.original_11:
        rooms = ORIGINAL_11_ROOMS
    elif args.checkpoint or args.mission:
        # Use training order so room IDs match the checkpoint
        rooms = TRAINING_50_ROOMS
    else:
        rooms = None
    env = VesnaOfficeEnv(
        render_mode="human", map_path=args.map,
        rooms=rooms, max_steps=args.max_steps,
    )

    # Build reset options from --start / --goal
    reset_opts = {}
    all_room_names = set(GRID.keys()) - HALL_ROOMS
    if args.start:
        if args.start not in all_room_names:
            print(f"ERROR: unknown start room '{args.start}'")
            print(f"Available: {sorted(all_room_names)}")
            return
        reset_opts["start_room"] = args.start
    if args.goal:
        if args.goal not in all_room_names:
            print(f"ERROR: unknown goal room '{args.goal}'")
            print(f"Available: {sorted(all_room_names)}")
            return
        reset_opts["goal_room"] = args.goal
    reset_opts = reset_opts or None

    if args.view:
        start = args.start or "corridor"
        goal = args.goal or "boss_office_1"
        env.agent_room = start
        env.goal_room = goal
        env._trail = [env._room_center(start)]
        env._trail_step_num = [0]
        env._render_frame()
        print(f"Viewing map: {start} -> {goal}. Press Q or close window to exit.")
        while True:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    env.close()
                    return
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_q:
                    env.close()
                    return
            time.sleep(0.05)
    elif args.mission:
        ckpt = args.checkpoint
        if not ckpt:
            # Default checkpoint path
            default_ckpt = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "..", "checkpoints", "alice.pt",
            )
            if os.path.exists(default_ckpt):
                ckpt = default_ckpt
            else:
                print("ERROR: No checkpoint found. Provide --checkpoint or train first.")
                print(f"  Looked at: {default_ckpt}")
                return
        start = args.start or "reception"
        _mission_replay(env, ckpt, args.mission, args.delay, start_room=start)
    elif args.checkpoint:
        _replay(env, args.checkpoint, args.episodes, args.delay,
                reset_options=reset_opts)
    else:
        _interactive(env, reset_options=reset_opts)

    env.close()


if __name__ == "__main__":
    main()
