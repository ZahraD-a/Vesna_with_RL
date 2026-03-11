"""
VEsNA Office 100 - Real ASL Map Viewer (100 rooms)

Shows ONLY what exists in the ASL map definition (NO fake cells)
- All 100 real rooms with corridors, labs, server rooms, etc.
- All connections properly defined via RCC relations
- Interactive Pygame visualization

Controls:
    Q or ESC - quit
    H - toggle help text
    G - toggle grid visibility
    C or SPACE - toggle connection visibility
    L - toggle legend
    Arrow keys - pan view
    +/- - zoom in/out
    R - reset view
    Scroll wheel - zoom
"""

import sys
from collections import deque
from typing import Dict, List, Set, Tuple, Optional

import pygame

# Initialize Pygame
pygame.init()

# ── Color Scheme ───────────────────────────────────────────────────────────
WING_COLORS = {
    "north":     (255, 220, 100),   # Warm yellow
    "east":      (100, 200, 220),   # Cool cyan
    "west":      (180, 100, 220),   # Rich purple
    "annex":     (100, 200, 100),   # Fresh green
    "south":     (200, 100, 100),   # Coral red
    "lobby":     (100, 150, 200),   # Steel blue
    "central":   (100, 180, 180),   # Teal
    "extended":  (255, 180, 100),   # Warm orange
}

ROOM_COLORS = {
    "corridor":   (240, 218, 115),
    "office":     (140, 198, 225),
    "common":     (145, 210, 145),
    "meeting":    (195, 165, 218),
    "technical":  (228, 170, 100),
    "outdoor":    (115, 200, 140),
    "entrance":   (232, 158, 120),
    "utility":    (192, 192, 192),
    "amenity":    (228, 162, 188),
    "other":      (215, 215, 215),
}

CONNECTION_COLORS = {
    "ec":      (40, 175, 65),    # Green - open passage
    "po":      (150, 95, 55),    # Brown - door
    "bridge":  (50, 200, 80),    # Glowing green - bridge
}

BG_COLOR = (35, 38, 44)
TEXT_COLOR = (220, 220, 220)
PAD = 50

# Cell dimensions - larger for better readability
CELL_SIZE = 60
WALL_THICKNESS = 2

# ── 100-ROOM Grid Layout (8 wings) ──────────────────────────────────────────
# Compact layout: All rooms visible on single floor
# Grid: 20 columns x 15 rows
#
#   NORTH WING (row 0-2)     |  EAST WING (row 0-4, col 11-14)
#   CENTRAL HUB (row 3-6)    |  ANNEX (row 5-8, col 11-14)
#   SOUTH WING (row 7-9)     |  EXTENDED (row 10-12, col 11-14)
#   LOBBY (row 10-11)        |  WEST WING (row 0-4, col 16-19)

GRID: Dict[str, List[Tuple[int, int]]] = {
    # ══════════════════════════════════════════════════════════════════════════
    # NORTH WING (IDs 0-12) - Top row, offices and labs
    # ══════════════════════════════════════════════════════════════════════════
    "corridor_north": [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0), (9, 0)],
    "office_1": [(0, 1)], "office_2": [(1, 1)], "office_3": [(2, 1)],
    "office_4": [(3, 1)], "office_5": [(4, 1)],
    "meeting_room_2": [(6, 1)], "meeting_room_3": [(7, 1)],
    "lab_1": [(8, 1)], "lab_2": [(9, 1)],
    "server_room": [(0, 2)], "mail_room": [(1, 2)], "reception": [(2, 2)],

    # ══════════════════════════════════════════════════════════════════════════
    # CENTRAL HUB (IDs 13-30) - Main corridor and offices
    # ══════════════════════════════════════════════════════════════════════════
    "corridor": [(0, 3), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3), (8, 3), (9, 3)],
    "open_office": [(0, 4), (1, 4), (2, 4), (3, 4)],
    "boss_office_1": [(4, 4)], "boss_office_2": [(5, 4)],
    "print_room": [(6, 4)], "outside": [(7, 4)],
    "senior_office_1": [(0, 5)], "senior_office_2": [(1, 5)], "senior_office_3": [(2, 5)],
    "meeting_room": [(3, 5)], "restroom_1": [(4, 5)], "storage_1": [(5, 5)],
    "executive_suite": [(6, 5)], "supply_closet": [(7, 5)],
    "common": [(0, 6)], "kitchen": [(1, 6)], "library": [(2, 6)],
    "phone_booth_1": [(3, 6)],

    # ══════════════════════════════════════════════════════════════════════════
    # SOUTH WING (IDs 31-45) - Cafeteria, gym, offices
    # ══════════════════════════════════════════════════════════════════════════
    "corridor_south": [(0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (5, 7), (6, 7), (7, 7), (8, 7), (9, 7)],
    "office_6": [(0, 8)], "office_7": [(1, 8)], "office_8": [(2, 8)],
    "office_9": [(3, 8)], "office_10": [(4, 8)],
    "cafeteria": [(5, 8)], "gym": [(6, 8), (7, 8)],
    "restroom_2": [(8, 8)], "archive": [(9, 8)],
    "training_room": [(0, 9)], "terrace": [(1, 9)], "lounge": [(2, 9)],
    "wellness_room": [(3, 9)], "phone_booth_2": [(4, 9)],

    # ══════════════════════════════════════════════════════════════════════════
    # LOBBY COMPLEX (IDs 46-49) - Entrance area
    # ══════════════════════════════════════════════════════════════════════════
    "lobby": [(0, 10), (1, 10), (2, 10), (3, 10)],
    "security_desk": [(4, 10)], "conference_room": [(5, 10)],
    "parking": [(6, 10)],

    # ══════════════════════════════════════════════════════════════════════════
    # EAST WING (IDs 50-63) - Labs and server rooms (col 11-14, row 0-4)
    # ══════════════════════════════════════════════════════════════════════════
    "corridor_east": [(11, 0), (11, 1), (11, 2), (11, 3), (11, 4)],
    "lab_3": [(12, 0)], "lab_4": [(13, 0)], "lab_5": [(14, 0)],
    "lab_6": [(12, 1)], "server_room_2": [(13, 1)], "server_room_3": [(14, 1)],
    "data_center": [(12, 2)], "tech_office_1": [(13, 2)], "tech_office_2": [(14, 2)],
    "server_maintenance": [(12, 3)], "network_room": [(13, 3)], "backup_power": [(14, 3)],
    "telecom_room": [(12, 4)],

    # ══════════════════════════════════════════════════════════════════════════
    # WEST WING (IDs 64-77) - Storage and utilities (col 16-19, row 0-4)
    # ══════════════════════════════════════════════════════════════════════════
    "corridor_west": [(16, 0), (16, 1), (16, 2), (16, 3), (16, 4)],
    "storage_2": [(17, 0)], "storage_3": [(18, 0)], "storage_4": [(19, 0)],
    "storage_5": [(17, 1)], "storage_6": [(18, 1)], "workshop": [(19, 1)],
    "equipment_room": [(17, 2)], "hazmat_storage": [(18, 2)], "loading_bay": [(19, 2)],
    "recycling_center": [(17, 3)], "courier_station": [(18, 3)], "freight_elevator": [(19, 3)],
    "dock_office": [(17, 4)],

    # ══════════════════════════════════════════════════════════════════════════
    # ANNEX (IDs 78-89) - Wellness and amenities (col 11-14, row 5-8)
    # ══════════════════════════════════════════════════════════════════════════
    "annex_corridor": [(11, 5), (11, 6), (11, 7), (11, 8)],
    "wellness_center": [(12, 5)], "meditation_room": [(13, 5)], "fitness_studio": [(14, 5)],
    "yoga_room": [(12, 6)], "game_room": [(13, 6)], "music_room": [(14, 6)],
    "art_studio": [(12, 7)], "rooftop_garden": [(13, 7)], "outdoor_seating": [(14, 7)],
    "bike_storage": [(12, 8)], "shower_room": [(13, 8)],

    # ══════════════════════════════════════════════════════════════════════════
    # EXTENDED ROOMS (IDs 90-102) - Additional offices (col 11-14, row 10-12)
    # ══════════════════════════════════════════════════════════════════════════
    "office_11": [(11, 10)], "office_12": [(12, 10)], "office_13": [(13, 10)],
    "office_14": [(14, 10)], "office_15": [(15, 10)],
    "meeting_room_6": [(11, 11)], "meeting_room_7": [(12, 11)],
    "break_room_2": [(13, 11)], "pantry_2": [(14, 11)],
    "copy_center": [(11, 12)], "scanner": [(12, 12)],
    "server_room_4": [(13, 12)], "server_room_5": [(14, 12)],
}

# ── Connections (EC = open passages, PO = doors, Bridges) ───────────────────

EC_CONNS = [
    # Original EC connections
    ("corridor", "reception"),
    ("corridor", "open_office"),
    ("corridor", "corridor_north"),
    ("corridor", "corridor_south"),
    ("corridor_south", "lobby"),
    # New wing connections
    ("corridor_north", "corridor_east"),
    ("corridor_south", "corridor_west"),
    ("corridor", "annex_corridor"),
]

DOOR_CONNS = [
    # Original 50-room doors
    ("corridor", "common"), ("corridor", "senior_office_1"),
    ("corridor", "senior_office_2"), ("corridor", "senior_office_3"),
    ("corridor", "meeting_room"), ("corridor", "restroom_1"),
    ("corridor", "storage_1"),
    ("open_office", "boss_office_1"), ("open_office", "boss_office_2"),
    ("open_office", "outside"), ("open_office", "print_room"),
    ("corridor_north", "meeting_room_2"), ("corridor_north", "meeting_room_3"),
    ("corridor_north", "lab_1"), ("corridor_north", "lab_2"),
    ("corridor_north", "server_room"),
    ("corridor_north", "office_1"), ("corridor_north", "office_2"),
    ("corridor_north", "office_3"), ("corridor_north", "office_4"),
    ("corridor_north", "office_5"),
    ("corridor_south", "cafeteria"), ("corridor_south", "gym"),
    ("corridor_south", "restroom_2"),
    ("corridor_south", "office_6"), ("corridor_south", "office_7"),
    ("corridor_south", "office_8"), ("corridor_south", "office_9"),
    ("corridor_south", "office_10"),
    ("corridor_south", "archive"), ("corridor_south", "training_room"),
    ("lobby", "parking"), ("lobby", "conference_room"),
    ("lobby", "security_desk"),
    ("common", "kitchen"), ("common", "library"),
    ("cafeteria", "terrace"),
    ("reception", "mail_room"),
    ("boss_office_1", "executive_suite"),
    ("library", "phone_booth_1"),
    ("gym", "lounge"), ("gym", "wellness_room"),
    ("lounge", "phone_booth_2"),
    ("storage_1", "supply_closet"),
    # East Wing doors (IDs 50-63)
    ("corridor_east", "lab_3"), ("corridor_east", "lab_4"),
    ("corridor_east", "lab_5"), ("corridor_east", "lab_6"),
    ("corridor_east", "server_room_2"), ("corridor_east", "server_room_3"),
    ("corridor_east", "data_center"),
    ("corridor_east", "tech_office_1"), ("corridor_east", "tech_office_2"),
    ("corridor_east", "server_maintenance"),
    ("corridor_east", "network_room"),
    ("corridor_east", "backup_power"),
    ("corridor_east", "telecom_room"),
    # West Wing doors (IDs 64-77)
    ("corridor_west", "storage_2"), ("corridor_west", "storage_3"),
    ("corridor_west", "storage_4"), ("corridor_west", "storage_5"),
    ("corridor_west", "storage_6"),
    ("corridor_west", "workshop"),
    ("corridor_west", "equipment_room"),
    ("corridor_west", "hazmat_storage"),
    ("corridor_west", "loading_bay"),
    ("corridor_west", "recycling_center"),
    ("corridor_west", "courier_station"),
    ("corridor_west", "freight_elevator"),
    ("corridor_west", "dock_office"),
    # Annex doors (IDs 78-89)
    ("annex_corridor", "wellness_center"),
    ("annex_corridor", "meditation_room"),
    ("annex_corridor", "fitness_studio"),
    ("annex_corridor", "yoga_room"),
    ("annex_corridor", "game_room"),
    ("annex_corridor", "music_room"),
    ("annex_corridor", "art_studio"),
    ("annex_corridor", "rooftop_garden"),
    ("annex_corridor", "outdoor_seating"),
    ("annex_corridor", "bike_storage"),
    ("annex_corridor", "shower_room"),
    # Extended Rooms doors (IDs 90-99)
    ("office_11", "meeting_room_6"),
    ("office_12", "meeting_room_7"),
    ("meeting_room_6", "break_room_2"),
    ("meeting_room_7", "break_room_2"),
    ("break_room_2", "pantry_2"),
    ("break_room_2", "copy_center"),
    ("copy_center", "scanner"),
]

# Bridges (long-distance connections across gaps)
# Format: (room_a, room_b, start_cell, end_cell)
BRIDGES = [
    ("corridor_north", "corridor_east", (9, 0), (11, 0)),   # North to East
    ("corridor", "corridor_west", (0, 3), (16, 0)),          # Central to West
    ("corridor_south", "lobby", (0, 7), (0, 10)),            # South to Lobby
    ("corridor", "annex_corridor", (9, 3), (11, 5)),         # Central to Annex
    ("annex_corridor", "office_11", (11, 8), (11, 10)),      # Annex to Extended
]

# Additional door connections for extended rooms connectivity
EXTENDED_CONNS = [
    ("annex_corridor", "office_11"),  # Bridge connection
    ("office_11", "office_12"),       # Connect offices in extended wing
    ("office_12", "office_13"),
    ("office_13", "office_14"),
    ("office_14", "office_15"),
    ("scanner", "server_room_4"),     # Connect server rooms
    ("server_room_4", "server_room_5"),
]

# Add extended connections to door connections
DOOR_CONNS = DOOR_CONNS + EXTENDED_CONNS


# ── Room Classification ─────────────────────────────────────────────────────
def classify_room(room_name: str) -> str:
    """Classify room by type for coloring."""
    if "corridor" in room_name:
        return "corridor"
    if room_name.startswith(("office_", "senior_", "boss_", "executive")):
        return "office"
    if room_name in ("common", "kitchen", "cafeteria", "break_room"):
        return "common"
    if room_name.startswith(("meeting_room", "conference")):
        return "meeting"
    if room_name.startswith(("lab_", "server", "tech", "data", "network", "backup", "telecom", "scanner")):
        return "technical"
    if room_name in ("outside", "terrace", "parking", "rooftop_garden", "outdoor_seating"):
        return "outdoor"
    if room_name in ("lobby", "reception", "entrance"):
        return "entrance"
    if room_name.startswith(("restroom", "storage", "archive", "mail_room", "print", "supply", "security",
                             "workshop", "equipment", "hazmat", "loading", "recycling", "courier",
                             "freight", "dock", "pantry")):
        return "utility"
    if room_name in ("gym", "lounge", "wellness_room", "wellness_center", "meditation_room",
                     "fitness_studio", "yoga_room", "game_room", "music_room", "art_studio",
                     "shower_room", "bike_storage"):
        return "amenity"
    return "other"


def get_wing_name(room_name: str) -> str:
    """Get the wing assignment for a room based on grid position."""
    # Define wing boundaries based on new compact layout
    north_rooms = {"office_1", "office_2", "office_3", "office_4", "office_5",
                   "corridor_north", "meeting_room_2", "meeting_room_3",
                   "lab_1", "lab_2", "server_room", "mail_room", "reception"}
    central_rooms = {"corridor", "open_office", "common", "kitchen", "meeting_room",
                     "senior_office_1", "senior_office_2", "senior_office_3",
                     "restroom_1", "storage_1", "library", "phone_booth_1",
                     "print_room", "outside", "boss_office_1", "boss_office_2",
                     "supply_closet", "executive_suite"}
    south_rooms = {"office_6", "office_7", "office_8", "office_9", "office_10",
                   "corridor_south", "cafeteria", "gym", "restroom_2", "archive",
                   "training_room", "terrace", "lounge", "wellness_room", "phone_booth_2"}
    lobby_rooms = {"lobby", "security_desk", "conference_room", "parking"}
    east_rooms = {"corridor_east", "lab_3", "lab_4", "lab_5", "lab_6",
                  "server_room_2", "server_room_3", "data_center",
                  "tech_office_1", "tech_office_2", "server_maintenance",
                  "network_room", "backup_power", "telecom_room"}
    west_rooms = {"corridor_west", "storage_2", "storage_3", "storage_4", "storage_5",
                  "storage_6", "workshop", "equipment_room", "hazmat_storage",
                  "loading_bay", "recycling_center", "courier_station",
                  "freight_elevator", "dock_office"}
    annex_rooms = {"annex_corridor", "wellness_center", "meditation_room",
                   "fitness_studio", "yoga_room", "game_room", "music_room",
                   "art_studio", "rooftop_garden", "outdoor_seating",
                   "bike_storage", "shower_room"}
    extended_rooms = {"office_11", "office_12", "office_13", "office_14", "office_15",
                      "meeting_room_6", "meeting_room_7", "break_room_2",
                      "pantry_2", "copy_center", "scanner", "server_room_4", "server_room_5"}

    if room_name in north_rooms:
        return "north"
    if room_name in central_rooms:
        return "central"
    if room_name in south_rooms:
        return "south"
    if room_name in lobby_rooms:
        return "lobby"
    if room_name in east_rooms:
        return "east"
    if room_name in west_rooms:
        return "west"
    if room_name in annex_rooms:
        return "annex"
    if room_name in extended_rooms:
        return "extended"
    return "other"


class Viewer:
    def __init__(self):
        # Initialize display
        self.screen_width = 1400
        self.screen_height = 900
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("VEsNA Office 100 - Press Q to quit, H for help")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 12)
        self.font_small = pygame.font.SysFont("consolas", 10)
        self.font_large = pygame.font.SysFont("consolas", 16)

        self.running = True
        self.show_grid = True
        self.show_connections = True
        self.show_help = False
        self.legend_visible = True
        self.zoom = 1.0         # Start with full view
        self.pan_offset = [20, 20]
        self.tooltip_room = None
        self.tooltip_pos = (0, 0)

        # Calculate bounds
        self._calculate_bounds()
        self._build_room_rects()
        self._build_connection_lookup()

    def _calculate_bounds(self):
        """Calculate the bounding box for all rooms."""
        all_cells = [(c, r) for cells in GRID.values() for c, r in cells]
        self.min_col = min(c for c, r in all_cells)
        self.max_col = max(c for c, r in all_cells)
        self.min_row = min(r for c, r in all_cells)
        self.max_row = max(r for c, r in all_cells)

    def _build_room_rects(self):
        """Build rectangles for each room."""
        self.room_rects: Dict[str, pygame.Rect] = {}
        for room_name, cells in GRID.items():
            min_c = min(c for c, r in cells)
            max_c = max(c for c, r in cells)
            min_r = min(r for c, r in cells)
            max_r = max(r for c, r in cells)
            self.room_rects[room_name] = pygame.Rect(
                min_c * CELL_SIZE, min_r * CELL_SIZE,
                (max_c - min_c + 1) * CELL_SIZE - 2,
                (max_r - min_r + 1) * CELL_SIZE - 2
            )

    def _build_connection_lookup(self):
        """Build lookup for connections."""
        self.ec_connections: Set[frozenset] = set()
        self.door_connections: Set[frozenset] = set()
        for room_a, room_b in EC_CONNS:
            self.ec_connections.add(frozenset([room_a, room_b]))
        for room_a, room_b in DOOR_CONNS:
            self.door_connections.add(frozenset([room_a, room_b]))

    def get_room_color(self, room_name: str) -> Tuple[int, int, int]:
        """Get color for a room based on wing and category."""
        wing = get_wing_name(room_name)
        category = classify_room(room_name)
        wing_color = WING_COLORS.get(wing, (200, 200, 200))
        category_color = ROOM_COLORS.get(category, (200, 200, 200))
        # Blend wing and category colors
        r = int((wing_color[0] + category_color[0]) / 2)
        g = int((wing_color[1] + category_color[1]) / 2)
        b = int((wing_color[2] + category_color[2]) / 2)
        return (r, g, b)

    def _get_neighbors(self, room_name: str) -> List[str]:
        """Get all connected neighbors of a room."""
        neighbors = []
        for room_a, room_b in EC_CONNS + DOOR_CONNS:
            if room_a == room_name:
                neighbors.append(room_b)
            elif room_b == room_name:
                neighbors.append(room_a)
        return neighbors

    def _cell_to_screen(self, col: int, row: int) -> Tuple[int, int]:
        """Convert grid cell to screen coordinates."""
        x = int((col * CELL_SIZE + self.pan_offset[0]) * self.zoom)
        y = int((row * CELL_SIZE + self.pan_offset[1]) * self.zoom)
        return (x, y)

    def _rect_to_screen(self, rect: pygame.Rect) -> pygame.Rect:
        """Convert a grid rect to screen coordinates."""
        sx, sy = self._cell_to_screen(rect.x // CELL_SIZE, rect.y // CELL_SIZE)
        sw = int(rect.width * self.zoom)
        sh = int(rect.height * self.zoom)
        return pygame.Rect(sx, sy, sw, sh)

    def run(self):
        """Main game loop."""
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_key(event.key)
                elif event.type == pygame.MOUSEWHEEL:
                    self._handle_scroll(event.y)
                elif event.type == pygame.MOUSEMOTION:
                    self._handle_mouse(event.pos)

            self._draw()
            self.clock.tick(60)

        pygame.quit()
        print("Viewer closed.")

    def _handle_key(self, key):
        """Handle keyboard input."""
        if key == pygame.K_q or key == pygame.K_ESCAPE:
            self.running = False
        elif key == pygame.K_g:
            self.show_grid = not self.show_grid
        elif key == pygame.K_h:
            self.show_help = not self.show_help
        elif key == pygame.K_c or key == pygame.K_SPACE:
            self.show_connections = not self.show_connections
        elif key == pygame.K_l:
            self.legend_visible = not self.legend_visible
        elif key == pygame.K_r:
            # Reset view
            self.zoom = 0.8
            self.pan_offset = [100, 50]
        elif key == pygame.K_EQUALS or key == pygame.K_PLUS or key == pygame.K_KP_PLUS:
            self.zoom = min(self.zoom * 1.2, 3.0)
        elif key == pygame.K_MINUS or key == pygame.K_KP_MINUS:
            self.zoom = max(self.zoom / 1.2, 0.3)
        elif key == pygame.K_UP:
            self.pan_offset[1] += 30
        elif key == pygame.K_DOWN:
            self.pan_offset[1] -= 30
        elif key == pygame.K_LEFT:
            self.pan_offset[0] += 30
        elif key == pygame.K_RIGHT:
            self.pan_offset[0] -= 30

    def _handle_scroll(self, direction):
        """Handle scroll wheel for zoom."""
        if direction > 0:
            self.zoom = min(self.zoom * 1.1, 3.0)
        else:
            self.zoom = max(self.zoom / 1.1, 0.3)

    def _handle_mouse(self, pos):
        """Handle mouse movement for tooltips."""
        mx, my = pos
        self.tooltip_room = None

        for room_name, rect in self.room_rects.items():
            screen_rect = self._rect_to_screen(rect)
            if screen_rect.collidepoint(mx, my):
                self.tooltip_room = room_name
                self.tooltip_pos = (mx + 15, my + 15)
                break

    def _draw(self):
        """Draw the entire scene."""
        self.screen.fill(BG_COLOR)

        # Draw grid lines
        if self.show_grid:
            self._draw_grid_lines()

        # Draw rooms
        for room_name, rect in self.room_rects.items():
            self._draw_room(room_name, rect)

        # Draw connections
        if self.show_connections:
            self._draw_connections()
            self._draw_bridges()

        # Draw legend
        if self.legend_visible:
            self._draw_legend()

        # Draw help
        if self.show_help:
            self._draw_help()

        # Draw tooltip
        if self.tooltip_room:
            self._draw_tooltip()

        # Draw status bar
        self._draw_status_bar()

        pygame.display.flip()

    def _draw_grid_lines(self):
        """Draw background grid lines."""
        grid_color = (50, 55, 65)
        for col in range(self.min_col, self.max_col + 2):
            x1, y1 = self._cell_to_screen(col, self.min_row)
            x2, y2 = self._cell_to_screen(col, self.max_row + 1)
            pygame.draw.line(self.screen, grid_color, (x1, y1), (x2, y2), 1)
        for row in range(self.min_row, self.max_row + 2):
            x1, y1 = self._cell_to_screen(self.min_col, row)
            x2, y2 = self._cell_to_screen(self.max_col + 1, row)
            pygame.draw.line(self.screen, grid_color, (x1, y1), (x2, y2), 1)

    def _draw_room(self, room_name: str, rect: pygame.Rect):
        """Draw a single room."""
        screen_rect = self._rect_to_screen(rect)
        color = self.get_room_color(room_name)
        pygame.draw.rect(self.screen, color, screen_rect)
        pygame.draw.rect(self.screen, (80, 80, 80), screen_rect, 1)

        # Draw room label if big enough
        if screen_rect.width > 40 and screen_rect.height > 20:
            # Shorten name for display
            short_name = room_name.replace("_", " ").replace("room", "r").title()
            if len(short_name) > 12:
                short_name = short_name[:10] + ".."
            text = self.font_small.render(short_name, True, (40, 40, 40))
            text_rect = text.get_rect(center=screen_rect.center)
            self.screen.blit(text, text_rect)

    def _draw_connections(self):
        """Draw EC and PO connections."""
        for room_a, room_b in EC_CONNS:
            self._draw_connection_line(room_a, room_b, CONNECTION_COLORS["ec"])
        for room_a, room_b in DOOR_CONNS:
            self._draw_connection_line(room_a, room_b, CONNECTION_COLORS["po"])

    def _draw_connection_line(self, room_a: str, room_b: str, color: Tuple[int, int, int]):
        """Draw a line between two rooms."""
        if room_a not in self.room_rects or room_b not in self.room_rects:
            return

        rect_a = self._rect_to_screen(self.room_rects[room_a])
        rect_b = self._rect_to_screen(self.room_rects[room_b])

        center_a = rect_a.center
        center_b = rect_b.center

        pygame.draw.line(self.screen, color, center_a, center_b, 2)

    def _draw_bridges(self):
        """Draw bridge connections with arrows."""
        for room_a, room_b, start_cell, end_cell in BRIDGES:
            if room_a not in self.room_rects or room_b not in self.room_rects:
                continue

            color = CONNECTION_COLORS["bridge"]
            x1, y1 = self._cell_to_screen(start_cell[0], start_cell[1])
            x2, y2 = self._cell_to_screen(end_cell[0], end_cell[1])

            # Draw dashed line
            dx = x2 - x1
            dy = y2 - y1
            dist = (dx * dx + dy * dy) ** 0.5
            if dist > 0:
                steps = int(dist / 15)
                for i in range(0, steps, 2):
                    s = i / steps
                    e = min((i + 1) / steps, 1.0)
                    pygame.draw.line(self.screen, color,
                                     (int(x1 + dx * s), int(y1 + dy * s)),
                                     (int(x1 + dx * e), int(y1 + dy * e)), 3)

            # Draw arrow at end
            pygame.draw.circle(self.screen, color, (x2, y2), 5)

    def _draw_legend(self):
        """Draw the legend panel."""
        legend_x = 10
        legend_y = self.screen_height - 120
        legend_width = 500
        legend_height = 110

        # Background
        pygame.draw.rect(self.screen, (30, 35, 45),
                         (legend_x, legend_y, legend_width, legend_height))
        pygame.draw.rect(self.screen, (60, 65, 75),
                         (legend_x, legend_y, legend_width, legend_height), 1)

        # Wing colors
        y = legend_y + 5
        x = legend_x + 10
        text = self.font.render("Wings:", True, TEXT_COLOR)
        self.screen.blit(text, (x, y))
        x += 50

        for wing in ["north", "east", "west", "annex", "south", "lobby", "central", "extended"]:
            pygame.draw.rect(self.screen, WING_COLORS[wing], (x, y + 2, 10, 10))
            text = self.font_small.render(wing[:2], True, TEXT_COLOR)
            self.screen.blit(text, (x + 12, y + 1))
            x += 40

        # Room types
        y += 20
        x = legend_x + 10
        text = self.font.render("Types:", True, TEXT_COLOR)
        self.screen.blit(text, (x, y))
        x += 50

        for room_type in ["corridor", "office", "common", "meeting", "technical", "utility"]:
            pygame.draw.rect(self.screen, ROOM_COLORS[room_type], (x, y + 2, 10, 10))
            text = self.font_small.render(room_type[:3], True, TEXT_COLOR)
            self.screen.blit(text, (x + 12, y + 1))
            x += 50

        # Connection types
        y += 20
        x = legend_x + 10
        text = self.font.render("Conns:", True, TEXT_COLOR)
        self.screen.blit(text, (x, y))
        x += 50

        for conn_type, label in [("ec", "EC"), ("po", "PO"), ("bridge", "Bridge")]:
            pygame.draw.rect(self.screen, CONNECTION_COLORS[conn_type], (x, y + 2, 10, 10))
            text = self.font_small.render(label, True, TEXT_COLOR)
            self.screen.blit(text, (x + 12, y + 1))
            x += 50

        # Stats
        y += 25
        stats = f"Rooms: {len(GRID)} | EC: {len(EC_CONNS)} | PO: {len(DOOR_CONNS)} | Bridges: {len(BRIDGES)}"
        text = self.font.render(stats, True, (150, 200, 150))
        self.screen.blit(text, (legend_x + 10, y))

    def _draw_help(self):
        """Draw help overlay."""
        help_x = 10
        help_y = 10
        help_width = 300
        help_height = 180

        pygame.draw.rect(self.screen, (20, 25, 35),
                         (help_x, help_y, help_width, help_height))
        pygame.draw.rect(self.screen, (80, 85, 95),
                         (help_x, help_y, help_width, help_height), 1)

        lines = [
            "Controls:",
            "  Q/ESC - Quit",
            "  H - Toggle this help",
            "  G - Toggle grid",
            "  C/SPACE - Toggle connections",
            "  L - Toggle legend",
            "  R - Reset view",
            "  +/- - Zoom in/out",
            "  Arrow keys - Pan view",
            "  Scroll wheel - Zoom",
        ]

        for i, line in enumerate(lines):
            color = (200, 200, 100) if i == 0 else TEXT_COLOR
            text = self.font.render(line, True, color)
            self.screen.blit(text, (help_x + 10, help_y + 10 + i * 16))

    def _draw_tooltip(self):
        """Draw tooltip for hovered room."""
        if not self.tooltip_room:
            return

        room_name = self.tooltip_room
        wing = get_wing_name(room_name)
        category = classify_room(room_name)
        cells = GRID.get(room_name, [])

        lines = [
            f"Room: {room_name}",
            f"Wing: {wing}",
            f"Type: {category}",
            f"Cells: {len(cells)}",
        ]

        # Calculate tooltip size
        padding = 5
        line_height = 14
        max_width = max(self.font.size(line)[0] for line in lines) + padding * 2
        tooltip_height = len(lines) * line_height + padding * 2

        tx, ty = self.tooltip_pos

        # Keep tooltip on screen
        if tx + max_width > self.screen_width:
            tx = self.screen_width - max_width - 5
        if ty + tooltip_height > self.screen_height:
            ty = self.screen_height - tooltip_height - 5

        # Draw tooltip background
        pygame.draw.rect(self.screen, (40, 45, 55),
                         (tx, ty, max_width, tooltip_height))
        pygame.draw.rect(self.screen, (100, 105, 115),
                         (tx, ty, max_width, tooltip_height), 1)

        # Draw text
        for i, line in enumerate(lines):
            text = self.font.render(line, True, TEXT_COLOR)
            self.screen.blit(text, (tx + padding, ty + padding + i * line_height))

    def _draw_status_bar(self):
        """Draw status bar at top."""
        status = f"Zoom: {self.zoom:.1f}x | Rooms: {len(GRID)} | Press H for help | Q to quit"
        text = self.font.render(status, True, (150, 150, 150))
        self.screen.blit(text, (10, 10))


def check_connectivity():
    """Check if all rooms are connected via BFS."""
    print("Checking connectivity...")
    all_rooms = set(GRID.keys())
    start = list(all_rooms)[0]
    visited = {start}
    queue = deque([start])

    # Build adjacency from connections
    adjacency: Dict[str, Set[str]] = {room: set() for room in all_rooms}
    for a, b in EC_CONNS + DOOR_CONNS:
        if a in adjacency and b in adjacency:
            adjacency[a].add(b)
            adjacency[b].add(a)

    while queue:
        current = queue.popleft()
        for neighbor in adjacency.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    connected = len(visited)
    total = len(all_rooms)
    print(f"Connectivity: {connected}/{total} rooms reachable")
    if connected < total:
        unreachable = all_rooms - visited
        print(f"WARNING: Unreachable rooms: {unreachable}")
    else:
        print("All rooms are connected!")


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="VEsNA Office 100 Viewer")
    parser.add_argument("--check", action="store_true", help="Check connectivity only")
    args = parser.parse_args()

    if args.check:
        check_connectivity()
        return

    print("Starting VEsNA Office 100 Viewer...")
    print(f"Rooms: {len(GRID)}, EC connections: {len(EC_CONNS)}, PO connections: {len(DOOR_CONNS)}")
    print("Press H for help, Q to quit")
    print()

    viewer = Viewer()
    viewer.run()


if __name__ == "__main__":
    main()
