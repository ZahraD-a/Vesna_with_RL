"""
MiniGrid-style visualization of the VEsNA office map.

One unified grid — all corridors connected by visible hallway cells.
Colored cells for rooms, dark walls, openings for doors/passages.

Usage:
    python visualize_grid_map.py
    python visualize_grid_map.py --map path/to/map.asl
"""

import argparse, os, re
from collections import defaultdict
from typing import Dict, List, Set, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ================================================================
#  Parsing
# ================================================================
def parse_map(filepath):
    rooms, furniture, ec, po = set(), {}, [], []
    ntpp_re = re.compile(r"map_ntpp\(\s*(\w+)\s*,\s*(\w+)\s*\)")
    ec_re   = re.compile(r"map_ec\(\s*(\w+)\s*,\s*(\w+)\s*\)")
    po_re   = re.compile(r"map_po\(\s*(\w+)\s*,\s*(\w+)\s*\)")
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line.startswith("//") or not line: continue
            m = ntpp_re.search(line)
            if m:
                if m.group(2) == "office": rooms.add(m.group(1))
                else: furniture[m.group(1)] = m.group(2)
                continue
            m = ec_re.search(line)
            if m: ec.append((m.group(1), m.group(2))); continue
            m = po_re.search(line)
            if m: po.append((m.group(1), m.group(2)))
    return rooms, furniture, ec, po

def derive_door_edges(po_pairs, rooms):
    po_link = defaultdict(set)
    for a, b in po_pairs: po_link[a].add(b); po_link[b].add(a)
    ents = set()
    for a, b in po_pairs: ents.update([a, b])
    edges = []
    for door in ents - rooms:
        conn = [r for r in po_link[door] if r in rooms]
        for i in range(len(conn)):
            for j in range(i+1, len(conn)):
                edges.append((conn[i], conn[j], door))
    return edges

# ================================================================
#  Categories & colors
# ================================================================
def classify(name):
    if name.startswith("_hall"): return "corridor"
    if "corridor" in name: return "corridor"
    if any(k in name for k in ("office","senior","boss","executive")): return "office"
    if name in ("common","kitchen","cafeteria"): return "common"
    if any(k in name for k in ("meeting","conference","training")): return "meeting"
    if name in ("lab_1","lab_2","server_room"): return "technical"
    if name in ("outside","terrace","parking"): return "outdoor"
    if name in ("lobby","reception"): return "entrance"
    if name in ("restroom_1","restroom_2","storage_1","supply_closet",
                "archive","mail_room","print_room","security_desk"): return "utility"
    if name in ("gym","lounge","wellness_room","phone_booth_1",
                "phone_booth_2","library"): return "amenity"
    return "other"

RGB = {
    "corridor":(245,210,80),"office":(110,190,230),"common":(120,200,120),
    "meeting":(195,150,220),"technical":(235,155,70),"outdoor":(80,195,115),
    "entrance":(240,140,100),"utility":(180,180,180),"amenity":(235,145,175),
    "other":(210,210,210),
}
WALL_C    = np.array([45,55,70], dtype=np.uint8)
FLOOR_C   = np.array([245,242,220], dtype=np.uint8)
PASSAGE_C = np.array([40,155,55], dtype=np.uint8)
DOOR_C    = np.array([150,95,55], dtype=np.uint8)

LABELS = {
    "corridor_north":"Corr N","corridor_south":"Corr S","corridor":"Corridor",
    "senior_office_1":"Sr.Of1","senior_office_2":"Sr.Of2",
    "senior_office_3":"Sr.Of3","boss_office_1":"Boss1",
    "boss_office_2":"Boss2","meeting_room":"Meet",
    "meeting_room_2":"Meet2","meeting_room_3":"Meet3",
    "conference_room":"Conf","executive_suite":"ExSuite",
    "phone_booth_1":"Ph1","phone_booth_2":"Ph2",
    "supply_closet":"Supply","training_room":"Train",
    "wellness_room":"Wellns","security_desk":"Secur",
    "open_office":"OpenOff","print_room":"Print",
    "mail_room":"Mail","restroom_1":"WC1","restroom_2":"WC2",
    "storage_1":"Store","server_room":"Server",
}
def lbl(n):
    if n.startswith("_hall"): return ""
    return LABELS.get(n, n.replace("_"," ").title())

# ================================================================
#  UNIFIED grid layout — one contiguous grid, hallways connect wings
# ================================================================
#
#  Right hallway (col 7): corridor_north ↔ corridor
#  Left hallway  (col 0): corridor ↔ corridor_south ↔ lobby
#
GRID = {
    # === NORTH WING (rows 0-2) ===
    "office_1":[(2,0)],"office_2":[(3,0)],"office_3":[(4,0)],
    "office_4":[(5,0)],"office_5":[(6,0)],
    "corridor_north":[(2,1),(3,1),(4,1),(5,1),(6,1),(7,1)],
    "meeting_room_2":[(2,2)],"meeting_room_3":[(3,2)],
    "lab_1":[(4,2)],"lab_2":[(5,2)],"server_room":[(6,2)],

    # Right hallway: CN(7,1) → hall(7,2) → hall(7,3) → C(7,4)
    "_hall_r1":[(7,2)], "_hall_r2":[(7,3)],

    # === MAIN FLOOR (rows 3-7) ===
    "mail_room":[(1,3)],"reception":[(2,3)],
    "corridor":[(0,4),(1,4),(2,4),(3,4),(4,4),(5,4),(6,4),(7,4),
                (8,4),(9,4),(10,4),(11,4),(12,4)],
    "common":[(13,4)],"kitchen":[(14,4)],
    "open_office":[(3,5),(4,5),(5,5),(6,5)],
    "meeting_room":[(7,5)],"senior_office_1":[(8,5)],
    "senior_office_2":[(9,5)],"senior_office_3":[(10,5)],
    "restroom_1":[(11,5)],"storage_1":[(12,5)],
    "library":[(13,5)],"phone_booth_1":[(14,5)],
    "print_room":[(3,6)],"outside":[(4,6)],
    "boss_office_1":[(5,6)],"boss_office_2":[(6,6)],
    "supply_closet":[(12,6)],
    "executive_suite":[(5,7)],

    # Left hallway: C(0,4) → hall(0,5..0,9) → CS(0,10)
    "_hall_l1":[(0,5)],"_hall_l2":[(0,6)],"_hall_l3":[(0,7)],
    "_hall_l4":[(0,8)],"_hall_l5":[(0,9)],

    # === SOUTH WING (rows 9-13) ===
    "office_6":[(1,9)],"office_7":[(2,9)],"office_8":[(3,9)],
    "office_9":[(4,9)],"office_10":[(5,9)],
    "corridor_south":[(0,10),(1,10),(2,10),(3,10),(4,10),(5,10),(6,10)],
    "cafeteria":[(1,11)],"gym":[(2,11),(3,11)],
    "restroom_2":[(4,11)],"archive":[(5,11)],"training_room":[(6,11)],
    "terrace":[(1,12)],"lounge":[(2,12)],"wellness_room":[(3,12)],
    "phone_booth_2":[(2,13)],

    # Left hallway: CS(0,10) → hall(0,11..0,14) → Lobby(0,15)
    "_hall_l6":[(0,11)],"_hall_l7":[(0,12)],
    "_hall_l8":[(0,13)],"_hall_l9":[(0,14)],

    # === LOBBY (rows 15-16) ===
    "lobby":[(0,15),(1,15),(2,15),(3,15)],
    "security_desk":[(1,16)],
    "conference_room":[(4,15)],
    "parking":[(2,16)],
}

# Extra EC connections for hallway adjacency (these let the renderer
# remove walls between hallway cells and their corridor neighbors).
HALL_EC = [
    ("corridor_north","_hall_r1"),("_hall_r1","_hall_r2"),("_hall_r2","corridor"),
    ("corridor","_hall_l1"),("_hall_l1","_hall_l2"),("_hall_l2","_hall_l3"),
    ("_hall_l3","_hall_l4"),("_hall_l4","_hall_l5"),("_hall_l5","corridor_south"),
    ("corridor_south","_hall_l6"),("_hall_l6","_hall_l7"),("_hall_l7","_hall_l8"),
    ("_hall_l8","_hall_l9"),("_hall_l9","lobby"),
]

# ================================================================
#  Pixel rendering
# ================================================================
CELL = 7
W    = 2
STEP = CELL + W

def render(rooms_parsed, ec_edges, door_edges, furniture, output_path):
    # Build connection sets
    ec_set = set()
    for a, b in ec_edges:
        ec_set.add(frozenset([a, b]))
    for a, b in HALL_EC:
        ec_set.add(frozenset([a, b]))
    door_set = set()
    for a, b, _ in door_edges:
        door_set.add(frozenset([a, b]))

    # Cell lookup
    cell_to_room = {}
    for rname, cells in GRID.items():
        for c, r in cells:
            cell_to_room[(c, r)] = rname

    all_c = [c for c, r in cell_to_room]
    all_r = [r for c, r in cell_to_room]
    min_c, max_c = min(all_c), max(all_c)
    min_r, max_r = min(all_r), max(all_r)
    cols = max_c - min_c + 1
    rows = max_r - min_r + 1

    pw = W + cols * STEP
    ph = W + rows * STEP
    img = np.tile(FLOOR_C, (ph, pw, 1))

    def px(c): return W + (c - min_c) * STEP
    def py(r): return W + (r - min_r) * STEP

    # Draw walls only around room cells
    for (c, r) in cell_to_room:
        bx = (c - min_c) * STEP
        by = (r - min_r) * STEP
        x0, y0 = max(bx, 0), max(by, 0)
        x1 = min(bx + STEP + W, pw)
        y1 = min(by + STEP + W, ph)
        img[y0:y1, x0:x1] = WALL_C

    # Paint interiors
    for (c, r), rname in cell_to_room.items():
        rgb = np.array(RGB.get(classify(rname), (210,210,210)), dtype=np.uint8)
        img[py(r):py(r)+CELL, px(c):px(c)+CELL] = rgb

    # Remove internal walls (same room)
    for rname, cells in GRID.items():
        cset = set(cells)
        rgb = np.array(RGB.get(classify(rname), (210,210,210)), dtype=np.uint8)
        for c, r in cells:
            if (c+1, r) in cset:
                img[py(r):py(r)+CELL, px(c)+CELL:px(c)+CELL+W] = rgb
            if (c, r+1) in cset:
                img[py(r)+CELL:py(r)+CELL+W, px(c):px(c)+CELL] = rgb

    # Openings for connections
    for (c, r), rname in cell_to_room.items():
        for dc, dr in [(1,0),(0,1)]:
            nc, nr = c+dc, r+dr
            if (nc, nr) not in cell_to_room: continue
            nname = cell_to_room[(nc, nr)]
            if nname == rname: continue
            pair = frozenset([rname, nname])

            if pair in ec_set:
                # Passage — wide green opening
                if dc == 1:
                    wx = px(c) + CELL
                    wy = py(r) + 1
                    img[wy:wy+CELL-2, wx:wx+W] = PASSAGE_C
                else:
                    wx = px(c) + 1
                    wy = py(r) + CELL
                    img[wy:wy+W, wx:wx+CELL-2] = PASSAGE_C
            elif pair in door_set:
                # Door — narrow brown opening
                span = max(2, CELL // 3)
                if dc == 1:
                    wx = px(c) + CELL
                    mid = py(r) + CELL // 2
                    img[mid-span//2:mid-span//2+span, wx:wx+W] = DOOR_C
                else:
                    wy = py(r) + CELL
                    mid = px(c) + CELL // 2
                    img[wy:wy+W, mid-span//2:mid-span//2+span] = DOOR_C

    # --- Matplotlib figure ---
    scale = 5.5
    fig_w = pw * scale / 20
    fig_h = ph * scale / 20
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor("#F5F2DC")
    ax.imshow(img, interpolation="nearest", aspect="equal")
    ax.axis("off")

    # Room labels
    for rname, cells in GRID.items():
        txt = lbl(rname)
        if not txt: continue
        cxs = [px(c) + CELL/2 for c, r in cells]
        cys = [py(r) + CELL/2 for c, r in cells]
        cx = sum(cxs) / len(cxs)
        cy = sum(cys) / len(cys)
        cat = classify(rname)
        bg = RGB.get(cat, (210,210,210))
        bg_hex = "#{:02x}{:02x}{:02x}".format(*bg)
        fs = 5.5 if len(cells) > 3 else (4.5 if len(cells) > 1 else 3.5)
        fw = "bold" if "corridor" in rname or rname == "lobby" else "medium"
        ax.text(cx, cy, txt, ha="center", va="center",
                fontsize=fs, fontweight=fw, color="#1a1a1a",
                bbox=dict(boxstyle="round,pad=0.08", facecolor=bg_hex,
                          edgecolor="none", alpha=0.7))

    # Wing labels
    wing_labels = [
        (2, -0.8, "NORTH WING"), (1, 2.5, "MAIN FLOOR"),
        (1, 8.5, "SOUTH WING"), (0, 14.5, "LOBBY"),
    ]
    for wc, wr, wt in wing_labels:
        ax.text(px(wc)-2, py(int(wr)) if wr == int(wr) else py(int(wr))+CELL*0.5,
                wt, fontsize=6, fontweight="bold", color="#555",
                fontstyle="italic", va="bottom")

    # Legend
    handles = []
    for cat in ["corridor","office","common","meeting","technical",
                "outdoor","entrance","utility","amenity"]:
        r,g,b = RGB[cat]
        handles.append(mpatches.Patch(facecolor=(r/255,g/255,b/255),
                       edgecolor="#444",linewidth=0.8,
                       label=cat.replace("_"," ").title()))
    handles.append(plt.Line2D([0],[0],color=(40/255,155/255,55/255),
                   lw=4,label="Passage (EC)"))
    handles.append(plt.Line2D([0],[0],color=(150/255,95/255,55/255),
                   lw=4,label="Door (PO)"))
    handles.append(mpatches.Patch(facecolor=(45/255,55/255,70/255),
                   edgecolor="none",label="Wall"))
    ax.legend(handles=handles, loc="upper right", fontsize=5,
              framealpha=0.95, title="Legend", title_fontsize=6,
              edgecolor="#CCC", fancybox=True)

    total = len(ec_edges) + len(door_edges)
    ax.set_title(
        f"VEsNA Office — Grid Map   "
        f"[{len(rooms_parsed)} rooms | {len(ec_edges)} passages | {len(door_edges)} doors]",
        fontsize=10, fontweight="bold", pad=10, color="#333")

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plt.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="#F5F2DC")
    plt.close()
    print(f"  Grid map saved -> {output_path}")

# ================================================================
def main():
    parser = argparse.ArgumentParser()
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    parser.add_argument("--map", default=os.path.join(root,"mind","playgrounds","office","office_map.asl"))
    parser.add_argument("--output", default=os.path.join(root,"logs","office_grid_map.png"))
    args = parser.parse_args()
    print(f"Parsing: {args.map}")
    rooms, furniture, ec_edges, po_pairs = parse_map(args.map)
    door_edges = derive_door_edges(po_pairs, rooms)
    print(f"  {len(rooms)} rooms, {len(ec_edges)} passages, {len(door_edges)} doors")
    render(rooms, ec_edges, door_edges, furniture, args.output)
    print("Done.")

if __name__ == "__main__":
    main()
