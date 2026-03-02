"""
Visualize the VEsNA office environment for RL agent training.

Generates two views:
  1. Floor plan  — architectural layout with rooms, doors, and passages
  2. Nav graph   — topology of the state space the RL agent trains on

Usage:
    python visualize_map.py                          # default paths
    python visualize_map.py --map path/to/map.asl    # custom map
    python visualize_map.py --output my_map.png      # custom output name
"""

import argparse
import math
import os
import re
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.patches import FancyBboxPatch

# ================================================================
#  Parsing
# ================================================================

def parse_map(filepath: str):
    """Parse the ASL map and return rooms, furniture, ec-edges, po-pairs."""
    rooms: Set[str] = set()
    furniture: Dict[str, str] = {}
    ec_edges: List[Tuple[str, str]] = []
    po_pairs: List[Tuple[str, str]] = []

    ntpp_re = re.compile(r"map_ntpp\(\s*(\w+)\s*,\s*(\w+)\s*\)")
    ec_re   = re.compile(r"map_ec\(\s*(\w+)\s*,\s*(\w+)\s*\)")
    po_re   = re.compile(r"map_po\(\s*(\w+)\s*,\s*(\w+)\s*\)")

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("//") or not line:
                continue
            m = ntpp_re.search(line)
            if m:
                child, parent = m.group(1), m.group(2)
                if parent == "office":
                    rooms.add(child)
                else:
                    furniture[child] = parent
                continue
            m = ec_re.search(line)
            if m:
                ec_edges.append((m.group(1), m.group(2)))
                continue
            m = po_re.search(line)
            if m:
                po_pairs.append((m.group(1), m.group(2)))

    return rooms, furniture, ec_edges, po_pairs


def derive_door_edges(po_pairs, rooms):
    po_link: Dict[str, Set[str]] = defaultdict(set)
    for a, b in po_pairs:
        po_link[a].add(b)
        po_link[b].add(a)

    all_entities = set()
    for a, b in po_pairs:
        all_entities.update([a, b])
    doors = all_entities - rooms

    door_edges = []
    for door in doors:
        connected = [r for r in po_link[door] if r in rooms]
        for i in range(len(connected)):
            for j in range(i + 1, len(connected)):
                door_edges.append((connected[i], connected[j], door))
    return door_edges, doors


def build_adjacency(rooms, ec_edges, door_edges):
    adj: Dict[str, Set[str]] = defaultdict(set)
    for a, b in ec_edges:
        if a in rooms and b in rooms:
            adj[a].add(b)
            adj[b].add(a)
    for a, b, _ in door_edges:
        if a in rooms and b in rooms:
            adj[a].add(b)
            adj[b].add(a)
    return adj


def compute_bfs_depth(adj, start="corridor"):
    depth = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nb in adj[node]:
            if nb not in depth:
                depth[nb] = depth[node] + 1
                queue.append(nb)
    return depth


# ================================================================
#  Style constants
# ================================================================

# Professional muted palette
PALETTE = {
    "corridor":    "#F5C542",   # warm gold
    "office":      "#7EB5D6",   # steel blue
    "common_area": "#8BC78B",   # sage green
    "meeting":     "#C49DD8",   # soft purple
    "technical":   "#E8985E",   # warm orange
    "outdoor":     "#6BBF8A",   # leaf green
    "entrance":    "#E88E6E",   # coral
    "utility":     "#B8B8B8",   # neutral gray
    "amenity":     "#E8879E",   # rose
    "other":       "#D4D4D4",
}

EDGE_PALETTE = {
    "corridor":    "#D4A420",
    "office":      "#5A94B5",
    "common_area": "#5FA05F",
    "meeting":     "#9E72B0",
    "technical":   "#C07030",
    "outdoor":     "#3E9E5E",
    "entrance":    "#C06040",
    "utility":     "#888888",
    "amenity":     "#C05070",
    "other":       "#999999",
}

BG_COLOR   = "#FAFAFA"
WALL_COLOR = "#3A3A3A"
TEXT_COLOR = "#2A2A2A"
LIGHT_TEXT = "#666666"
PASSAGE_COLOR = "#2E7D32"
DOOR_COLOR    = "#78909C"


def classify_room(name: str) -> str:
    if "corridor" in name:
        return "corridor"
    if any(k in name for k in ("office", "senior", "boss", "executive")):
        return "office"
    if name in ("common", "kitchen", "cafeteria"):
        return "common_area"
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


# ================================================================
#  Manual floor-plan layout  (y increases downward)
# ================================================================

W  = 2.8
H  = 1.6
G  = 0.15
WG = 1.6
_step = W + G

_5w = 5 * W + 4 * G
_6w = 6 * W + 5 * G


# --- NORTH WING ---
_y = 0.0
_north_y = _y
_north_top = {n: (i * _step, _y, W, H)
              for i, n in enumerate(["office_1", "office_2", "office_3",
                                      "office_4", "office_5"])}
_y += H + G
_corridor_north = {"corridor_north": (0, _y, _5w, 0.9)}
_y += 0.9 + G
_north_bot = {n: (i * _step, _y, W, H)
              for i, n in enumerate(["meeting_room_2", "meeting_room_3",
                                      "lab_1", "lab_2", "server_room"])}

# --- MAIN FLOOR ---
_y += H + WG
_main_y = _y
_main_r1 = {
    "mail_room":  (0,            _y, W, H),
    "reception":  (1 * _step,    _y, W, H),
    "corridor":   (2 * _step,    _y, 3 * W + 2 * G, 0.9),
    "common":     (5 * _step,    _y, W, H),
    "kitchen":    (6 * _step,    _y, W, H),
}
_y += H + G
_main_r2 = {n: (i * _step, _y, W, H)
            for i, n in enumerate(["open_office", "meeting_room",
                                    "senior_office_1", "senior_office_2",
                                    "senior_office_3", "restroom_1",
                                    "storage_1"])}
_y += H + G
_main_r3 = {
    "print_room":    (0 * _step, _y, W, H),
    "outside":       (1 * _step, _y, W, H),
    "boss_office_1": (2 * _step, _y, W, H),
    "boss_office_2": (3 * _step, _y, W, H),
    "supply_closet": (4 * _step, _y, W, H),
    "library":       (5 * _step, _y, W, H),
    "phone_booth_1": (6 * _step, _y, W, H),
}
_y += H + G
_main_r4 = {"executive_suite": (2 * _step, _y, W, H)}

# --- SOUTH WING ---
_y += H + WG
_south_y = _y
_south_top = {n: (i * _step, _y, W, H)
              for i, n in enumerate(["office_6", "office_7", "office_8",
                                      "office_9", "office_10"])}
_y += H + G
_corridor_south = {"corridor_south": (0, _y, _5w, 0.9)}
_y += 0.9 + G
_south_r1 = {n: (i * _step, _y, W, H)
             for i, n in enumerate(["cafeteria", "gym", "restroom_2",
                                     "archive", "training_room"])}
_y += H + G
_south_r2 = {
    "terrace":       (0 * _step, _y, W, H),
    "lounge":        (1 * _step, _y, W, H),
    "wellness_room": (2 * _step, _y, W, H),
}
_y += H + G
_south_r3 = {"phone_booth_2": (1 * _step, _y, W, H)}

# --- LOBBY WING ---
_y += H + WG * 0.6
_lobby_y = _y
_lobby_r1 = {
    "security_desk":   (0 * _step, _y, W, H),
    "lobby":           (1 * _step, _y, 3 * W + 2 * G, 0.9),
    "conference_room": (4 * _step, _y, W, H),
}
_y += H + G
_lobby_r2 = {"parking": (1 * _step, _y, W, H)}


def get_all_room_positions() -> Dict[str, Tuple[float, float, float, float]]:
    pos = {}
    for d in [_north_top, _corridor_north, _north_bot,
              _main_r1, _main_r2, _main_r3, _main_r4,
              _south_top, _corridor_south, _south_r1, _south_r2, _south_r3,
              _lobby_r1, _lobby_r2]:
        pos.update(d)
    return pos


# ================================================================
#  Drawing helpers
# ================================================================

SHORT_LABELS = {
    "senior_office_1": "Sr. Office 1", "senior_office_2": "Sr. Office 2",
    "senior_office_3": "Sr. Office 3", "boss_office_1": "Boss 1",
    "boss_office_2": "Boss 2", "corridor_north": "CORRIDOR N",
    "corridor_south": "CORRIDOR S", "corridor": "CORRIDOR",
    "meeting_room": "Meeting Rm", "meeting_room_2": "Meeting 2",
    "meeting_room_3": "Meeting 3", "conference_room": "Conference",
    "executive_suite": "Exec Suite", "phone_booth_1": "Phone 1",
    "phone_booth_2": "Phone 2", "supply_closet": "Supply",
    "training_room": "Training", "wellness_room": "Wellness",
    "security_desk": "Security", "open_office": "Open Office",
    "print_room": "Print Rm", "mail_room": "Mail Rm",
    "restroom_1": "Restroom 1", "restroom_2": "Restroom 2",
    "storage_1": "Storage", "server_room": "Server Rm",
}


def _label(name: str) -> str:
    return SHORT_LABELS.get(name, name.replace("_", " ").title())


def _rect_edge_point(rect, target_cx, target_cy):
    """Point on rectangle border closest to target center."""
    x, y, w, h = rect
    cx, cy = x + w / 2, y + h / 2
    dx, dy = target_cx - cx, target_cy - cy
    if dx == 0 and dy == 0:
        return cx, cy
    # Scale to hit rectangle edge
    sx = abs((w / 2) / dx) if dx != 0 else float("inf")
    sy = abs((h / 2) / dy) if dy != 0 else float("inf")
    s = min(sx, sy)
    return cx + dx * s, cy + dy * s


# ================================================================
#  Figure 1: Architectural floor plan
# ================================================================

def render_floor_plan(rooms, furniture, ec_edges, door_edges, output_path):
    positions = get_all_room_positions()
    adj = build_adjacency(rooms, ec_edges, door_edges)
    depth = compute_bfs_depth(adj, "corridor")
    max_depth = max(depth.values()) if depth else 1

    fig, ax = plt.subplots(figsize=(22, 28))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.set_aspect("equal")
    ax.invert_yaxis()

    # --- Wing background panels ---
    wing_info = [
        (_north_y - 0.5, "NORTH WING", 4.3,  "#FFF8E1"),
        (_main_y  - 0.5, "MAIN FLOOR", 7.3,  "#E8F5E9"),
        (_south_y - 0.5, "SOUTH WING", 8.7,  "#E3F2FD"),
        (_lobby_y - 0.5, "LOBBY",      3.4,  "#FBE9E7"),
    ]
    for wy, wlabel, wh, wcolor in wing_info:
        bg = FancyBboxPatch(
            (-1.2, wy), _5w + 7 * _step + 1.5, wh,
            boxstyle="round,pad=0.3",
            facecolor=wcolor, edgecolor="none", alpha=0.45, zorder=-2)
        ax.add_patch(bg)
        ax.text(-0.9, wy + 0.15, wlabel, fontsize=11, fontweight="bold",
                color="#555555", ha="left", va="top",
                fontstyle="italic",
                path_effects=[pe.withStroke(linewidth=2, foreground="white")])

    # --- Draw connections ---
    # Build lookup for edge type
    ec_set = set()
    for a, b in ec_edges:
        ec_set.add((a, b))
        ec_set.add((b, a))

    all_edges = []
    for a, b in ec_edges:
        if a in positions and b in positions:
            all_edges.append((a, b, "passage"))
    for a, b, door in door_edges:
        if a in positions and b in positions:
            all_edges.append((a, b, "door"))

    for a, b, ctype in all_edges:
        ra, rb = positions[a], positions[b]
        acx, acy = ra[0] + ra[2] / 2, ra[1] + ra[3] / 2
        bcx, bcy = rb[0] + rb[2] / 2, rb[1] + rb[3] / 2

        # Get edge points on rectangle borders
        px1, py1 = _rect_edge_point(ra, bcx, bcy)
        px2, py2 = _rect_edge_point(rb, acx, acy)

        if ctype == "passage":
            ax.plot([px1, px2], [py1, py2], "-",
                    color=PASSAGE_COLOR, linewidth=2.5, alpha=0.7, zorder=0,
                    solid_capstyle="round")
            # Small open-circle marker at midpoint
            mx, my = (px1 + px2) / 2, (py1 + py2) / 2
            ax.plot(mx, my, "o", color=PASSAGE_COLOR, markersize=5,
                    markerfacecolor="white", markeredgewidth=1.5, zorder=3)
        else:
            ax.plot([px1, px2], [py1, py2], "-",
                    color=DOOR_COLOR, linewidth=1.2, alpha=0.55, zorder=0)
            # Small door marker (square) at midpoint
            mx, my = (px1 + px2) / 2, (py1 + py2) / 2
            ax.plot(mx, my, "s", color=DOOR_COLOR, markersize=3.5,
                    markerfacecolor=DOOR_COLOR, markeredgewidth=0, alpha=0.7, zorder=3)

    # --- Draw rooms ---
    for name, (x, y, w, h) in positions.items():
        cat = classify_room(name)
        color = PALETTE.get(cat, "#D4D4D4")
        edge_color = EDGE_PALETTE.get(cat, "#999999")

        # Shadow
        shadow = FancyBboxPatch(
            (x + 0.05, y + 0.05), w, h,
            boxstyle="round,pad=0.05",
            facecolor="#00000015", edgecolor="none", zorder=0)
        ax.add_patch(shadow)

        # Room box
        rect = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.05",
            facecolor=color, edgecolor=edge_color, linewidth=1.4, zorder=1)
        ax.add_patch(rect)

        label = _label(name)
        is_corridor = "CORRIDOR" in label
        fontsize = 8.0 if is_corridor else 6.2
        fontweight = "bold" if is_corridor else "medium"

        # Room label
        ax.text(x + w / 2, y + h / 2 - 0.08, label,
                ha="center", va="center", fontsize=fontsize,
                fontweight=fontweight, color=TEXT_COLOR, zorder=2,
                path_effects=[pe.withStroke(linewidth=1.5, foreground=color)])

        # Depth badge (small number showing BFS distance from corridor)
        d = depth.get(name, "?")
        if name != "corridor":
            badge_x = x + w - 0.25
            badge_y = y + 0.25
            ax.add_patch(plt.Circle((badge_x, badge_y), 0.18,
                         facecolor="white", edgecolor=edge_color,
                         linewidth=0.8, zorder=3, alpha=0.9))
            ax.text(badge_x, badge_y, str(d),
                    ha="center", va="center", fontsize=4.5,
                    fontweight="bold", color=LIGHT_TEXT, zorder=4)

        # Furniture count
        furn_count = sum(1 for f, r in furniture.items() if r == name)
        if furn_count > 0:
            ax.text(x + w / 2, y + h / 2 + 0.28,
                    f"{furn_count} item{'s' if furn_count > 1 else ''}",
                    ha="center", va="center", fontsize=4.0,
                    color=LIGHT_TEXT, fontstyle="italic", zorder=2)

    # --- Legend ---
    handles = []
    used_cats = {classify_room(n) for n in positions}
    for cat, color in PALETTE.items():
        if cat in used_cats:
            handles.append(mpatches.Patch(
                facecolor=color, edgecolor=EDGE_PALETTE[cat], linewidth=1.2,
                label=cat.replace("_", " ").title()))
    handles.append(plt.Line2D([0], [0], marker="o", color=PASSAGE_COLOR, lw=2.5,
                   markerfacecolor="white", markeredgecolor=PASSAGE_COLOR,
                   markersize=6, label="Open Passage (EC)"))
    handles.append(plt.Line2D([0], [0], marker="s", color=DOOR_COLOR, lw=1.2,
                   markerfacecolor=DOOR_COLOR, markersize=4,
                   label="Door Connection (PO)"))
    handles.append(plt.Line2D([0], [0], marker="o", color="white",
                   markeredgecolor="#888", markersize=8,
                   markeredgewidth=1, lw=0,
                   label="Depth from Corridor (badge)"))

    leg = ax.legend(handles=handles, loc="upper right", fontsize=7.5,
                    framealpha=0.95, title="Legend", title_fontsize=9,
                    edgecolor="#CCCCCC", fancybox=True, shadow=True)

    ax.set_title(
        f"VEsNA Office — Floor Plan    [{len(positions)} rooms, "
        f"{len(ec_edges)} passages, {len(door_edges)} doors]",
        fontsize=16, fontweight="bold", pad=16, color=TEXT_COLOR)

    ax.autoscale()
    ax.margins(0.04)
    ax.axis("off")
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=160, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close()
    print(f"  Floor plan saved -> {output_path}")


# ================================================================
#  Figure 2: Navigation graph (agent's state space)
# ================================================================

def _hierarchical_layout(adj, rooms, start="corridor"):
    """Layered layout grouped by parent hub for clarity."""
    depth = compute_bfs_depth(adj, start)
    max_d = max(depth.values()) if depth else 0

    # Group rooms by depth
    layers: Dict[int, List[str]] = defaultdict(list)
    for r in rooms:
        d = depth.get(r, max_d + 1)
        layers[d].append(r)

    # Within each layer, sort by category then name for visual grouping
    cat_order = ["corridor", "entrance", "common_area", "office", "meeting",
                 "technical", "utility", "amenity", "outdoor", "other"]

    def sort_key(name):
        cat = classify_room(name)
        ci = cat_order.index(cat) if cat in cat_order else 99
        return (ci, name)

    for d in layers:
        layers[d].sort(key=sort_key)

    # For wide layers, use a 2-row staggered sub-layout
    MAX_PER_ROW = 12
    pos = {}
    y_spacing = 3.0
    x_spacing = 2.4

    for d in range(max_d + 1):
        nodes = layers[d]
        n = len(nodes)
        if n <= MAX_PER_ROW:
            total_w = (n - 1) * x_spacing
            x0 = -total_w / 2
            for i, node in enumerate(nodes):
                pos[node] = (x0 + i * x_spacing, -d * y_spacing)
        else:
            # Split into two sub-rows
            mid = (n + 1) // 2
            row1 = nodes[:mid]
            row2 = nodes[mid:]
            sub_y_offset = 0.9
            for ri, row in enumerate([row1, row2]):
                nr = len(row)
                total_w = (nr - 1) * x_spacing
                x0 = -total_w / 2
                y_off = -sub_y_offset if ri == 0 else sub_y_offset
                for i, node in enumerate(row):
                    pos[node] = (x0 + i * x_spacing, -d * y_spacing + y_off)

    # Place unreachable rooms
    unreachable = [r for r in rooms if r not in depth]
    if unreachable:
        n = len(unreachable)
        total_w = (n - 1) * x_spacing
        x0 = -total_w / 2
        y = -(max_d + 2) * y_spacing
        for i, node in enumerate(unreachable):
            pos[node] = (x0 + i * x_spacing, y)

    return pos, depth


def render_nav_graph(rooms, ec_edges, door_edges, furniture, output_path):
    adj = build_adjacency(rooms, ec_edges, door_edges)
    pos, depth = _hierarchical_layout(adj, rooms, "corridor")
    max_depth = max(depth.values()) if depth else 1

    fig, ax = plt.subplots(figsize=(26, 22))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    # --- Draw edges ---
    # Door edges first (thinner, behind)
    for a, b, door in door_edges:
        if a in pos and b in pos:
            x1, y1 = pos[a]
            x2, y2 = pos[b]
            ax.plot([x1, x2], [y1, y2], "-", color=DOOR_COLOR,
                    linewidth=1.0, alpha=0.4, zorder=0)
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.plot(mx, my, "s", color=DOOR_COLOR, markersize=3,
                    alpha=0.6, zorder=1)

    # Passage edges (thicker, on top)
    for a, b in ec_edges:
        if a in pos and b in pos:
            x1, y1 = pos[a]
            x2, y2 = pos[b]
            ax.plot([x1, x2], [y1, y2], "-", color=PASSAGE_COLOR,
                    linewidth=2.5, alpha=0.6, zorder=1)
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.plot(mx, my, "o", color=PASSAGE_COLOR, markersize=5,
                    markerfacecolor="white", markeredgewidth=1.5, zorder=2)

    # --- Draw nodes ---
    for name in rooms:
        if name not in pos:
            continue
        x, y = pos[name]
        cat = classify_room(name)
        color = PALETTE.get(cat, "#D4D4D4")
        edge_color = EDGE_PALETTE.get(cat, "#999999")
        degree = len(adj.get(name, set()))
        d = depth.get(name, 0)

        # Node size proportional to degree
        node_r = 0.35 + degree * 0.06

        # Shadow
        shadow = plt.Circle((x + 0.04, y - 0.04), node_r,
                             facecolor="#00000018", edgecolor="none", zorder=2)
        ax.add_patch(shadow)

        # Node circle
        circle = plt.Circle((x, y), node_r,
                             facecolor=color, edgecolor=edge_color,
                             linewidth=2.0, zorder=3)
        ax.add_patch(circle)

        # Label
        label = _label(name)
        fontsize = 6.5 if len(label) > 10 else 7.5
        if "CORRIDOR" in label:
            fontsize = 8.5
        ax.text(x, y + 0.03, label, ha="center", va="center",
                fontsize=fontsize, fontweight="bold", color=TEXT_COLOR,
                zorder=4, path_effects=[
                    pe.withStroke(linewidth=2, foreground=color)])

        # Degree label below node
        ax.text(x, y - node_r - 0.18, f"d={d}  [{degree}]",
                ha="center", va="top", fontsize=4.5, color=LIGHT_TEXT,
                zorder=4)

    # --- Depth bands (subtle horizontal stripes) ---
    if pos:
        all_x = [p[0] for p in pos.values()]
        x_min, x_max = min(all_x) - 2, max(all_x) + 2
        for d_level in range(max_depth + 1):
            band_y = -d_level * 3.0
            band = mpatches.FancyBboxPatch(
                (x_min, band_y - 1.4), x_max - x_min, 2.8,
                boxstyle="round,pad=0.1",
                facecolor="#00000008" if d_level % 2 == 0 else "#00000003",
                edgecolor="none", zorder=-1)
            ax.add_patch(band)
            ax.text(x_max + 0.3, band_y, f"depth {d_level}",
                    ha="left", va="center", fontsize=7,
                    color="#AAAAAA", fontstyle="italic")

    # --- Legend ---
    handles = []
    used_cats = {classify_room(n) for n in rooms}
    for cat, color in PALETTE.items():
        if cat in used_cats:
            handles.append(plt.Line2D([0], [0], marker="o", color="none",
                           markerfacecolor=color, markeredgecolor=EDGE_PALETTE[cat],
                           markersize=10, markeredgewidth=1.5,
                           label=cat.replace("_", " ").title()))
    handles.append(plt.Line2D([0], [0], marker="o", color=PASSAGE_COLOR, lw=2.5,
                   markerfacecolor="white", markeredgecolor=PASSAGE_COLOR,
                   markersize=6, label="Open Passage"))
    handles.append(plt.Line2D([0], [0], marker="s", color=DOOR_COLOR, lw=1.0,
                   markerfacecolor=DOOR_COLOR, markersize=4,
                   label="Door Connection"))

    leg = ax.legend(handles=handles, loc="upper left", fontsize=7.5,
                    framealpha=0.95, title="Legend", title_fontsize=9,
                    edgecolor="#CCCCCC", fancybox=True, shadow=True)

    # Stats box
    total_edges = len(ec_edges) + len(door_edges)
    furn_rooms = len(set(furniture.values()))
    stats_text = (
        f"Rooms (states): {len(rooms)}\n"
        f"Connections (actions): {total_edges}\n"
        f"  Passages: {len(ec_edges)}\n"
        f"  Doors: {len(door_edges)}\n"
        f"Furniture items: {len(furniture)}\n"
        f"Max depth: {max_depth}\n"
        f"Avg degree: {sum(len(adj[r]) for r in rooms) / len(rooms):.1f}"
    )
    props = dict(boxstyle="round,pad=0.5", facecolor="white",
                 edgecolor="#CCCCCC", alpha=0.95)
    ax.text(0.99, 0.02, stats_text, transform=ax.transAxes,
            fontsize=7.5, verticalalignment="bottom", horizontalalignment="right",
            bbox=props, fontfamily="monospace", color=TEXT_COLOR)

    # Node size legend
    ax.text(0.01, 0.02,
            "Node label: d=BFS depth  [degree]\n"
            "Node size proportional to degree",
            transform=ax.transAxes, fontsize=6.5,
            verticalalignment="bottom", horizontalalignment="left",
            color=LIGHT_TEXT, fontstyle="italic")

    ax.set_title(
        "VEsNA Office — Navigation Graph  (RL Agent State Space)",
        fontsize=16, fontweight="bold", pad=16, color=TEXT_COLOR)

    ax.set_aspect("equal")
    ax.autoscale()
    ax.margins(0.06)
    ax.axis("off")
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=160, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close()
    print(f"  Nav graph  saved -> {output_path}")


# ================================================================
#  Main
# ================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Visualize the VEsNA office map for RL training")
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", ".."))
    default_map = os.path.join(
        project_root, "mind", "playgrounds", "office", "office_map.asl")
    default_out = os.path.join(project_root, "logs")

    parser.add_argument("--map", default=default_map,
                        help="Path to office_map.asl")
    parser.add_argument("--output", default=default_out,
                        help="Output directory for PNG files")
    args = parser.parse_args()

    print(f"Parsing: {args.map}")
    rooms, furniture, ec_edges, po_pairs = parse_map(args.map)
    door_edges, doors = derive_door_edges(po_pairs, rooms)
    print(f"  {len(rooms)} rooms, {len(furniture)} furniture items, "
          f"{len(ec_edges)} passages, {len(door_edges)} doors")

    out_dir = args.output
    os.makedirs(out_dir, exist_ok=True)

    render_floor_plan(
        rooms, furniture, ec_edges, door_edges,
        os.path.join(out_dir, "office_floorplan.png"))

    render_nav_graph(
        rooms, ec_edges, door_edges, furniture,
        os.path.join(out_dir, "office_nav_graph.png"))

    print("Done.")


if __name__ == "__main__":
    main()
