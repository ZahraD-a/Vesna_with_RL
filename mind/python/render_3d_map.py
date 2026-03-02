"""Generate a 3D image of the VEsNA office map showing all 50 rooms."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

GRID = {
    "office_1": [(2,0)], "office_2": [(3,0)], "office_3": [(4,0)],
    "office_4": [(5,0)], "office_5": [(6,0)],
    "corridor_north": [(2,1),(3,1),(4,1),(5,1),(6,1),(7,1)],
    "meeting_room_2": [(2,2)], "meeting_room_3": [(3,2)],
    "lab_1": [(4,2)], "lab_2": [(5,2)], "server_room": [(6,2)],
    "mail_room": [(1,3)], "reception": [(2,3)],
    "corridor": [(0,4),(1,4),(2,4),(3,4),(4,4),(5,4),(6,4),(7,4),
                  (8,4),(9,4),(10,4),(11,4),(12,4)],
    "common": [(13,4)], "kitchen": [(14,4)],
    "open_office": [(3,5),(4,5),(5,5),(6,5)],
    "meeting_room": [(7,5)], "senior_office_1": [(8,5)],
    "senior_office_2": [(9,5)], "senior_office_3": [(10,5)],
    "restroom_1": [(11,5)], "storage_1": [(12,5)],
    "library": [(13,5)], "phone_booth_1": [(14,5)],
    "print_room": [(3,6)], "outside": [(4,6)],
    "boss_office_1": [(5,6)], "boss_office_2": [(6,6)],
    "supply_closet": [(12,6)],
    "executive_suite": [(5,7)],
    "office_6": [(1,9)], "office_7": [(2,9)], "office_8": [(3,9)],
    "office_9": [(4,9)], "office_10": [(5,9)],
    "corridor_south": [(0,10),(1,10),(2,10),(3,10),(4,10),(5,10),(6,10)],
    "cafeteria": [(1,11)], "gym": [(2,11),(3,11)],
    "restroom_2": [(4,11)], "archive": [(5,11)], "training_room": [(6,11)],
    "terrace": [(1,12)], "lounge": [(2,12)], "wellness_room": [(3,12)],
    "phone_booth_2": [(2,13)],
    "lobby": [(0,15),(1,15),(2,15),(3,15)],
    "security_desk": [(1,16)], "conference_room": [(4,15)],
    "parking": [(2,16)],
}

EC_CONNS = [
    ("corridor", "reception"),
    ("corridor", "open_office"),
    ("corridor", "corridor_north"),
    ("corridor", "corridor_south"),
    ("corridor_south", "lobby"),
]

DOOR_CONNS = [
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
    ("cafeteria", "terrace"), ("reception", "mail_room"),
    ("boss_office_1", "executive_suite"),
    ("library", "phone_booth_1"),
    ("gym", "lounge"), ("gym", "wellness_room"),
    ("lounge", "phone_booth_2"),
    ("storage_1", "supply_closet"),
]

BRIDGES = [
    ("corridor_north", "corridor",       7, 1, 7, 4),
    ("corridor",       "corridor_south", 0, 4, 0, 10),
    ("corridor_south", "lobby",          0, 10, 0, 15),
]

def classify(name):
    if "corridor" in name: return "corridor"
    for k in ("office", "senior", "boss", "executive"):
        if k in name: return "office"
    if name in ("common", "kitchen", "cafeteria"): return "common"
    for k in ("meeting", "conference", "training"):
        if k in name: return "meeting"
    if name in ("lab_1", "lab_2", "server_room"): return "technical"
    if name in ("outside", "terrace", "parking"): return "outdoor"
    if name in ("lobby", "reception"): return "entrance"
    if name in ("restroom_1", "restroom_2", "storage_1", "supply_closet",
                "archive", "mail_room", "print_room", "security_desk"):
        return "utility"
    if name in ("gym", "lounge", "wellness_room", "phone_booth_1",
                "phone_booth_2", "library"):
        return "amenity"
    return "other"

CAT_CLR = {
    "corridor": "#F0DA73", "office": "#8CC6E1", "common": "#91D291",
    "meeting": "#C3A5DA", "technical": "#E4AA64", "outdoor": "#73C88C",
    "entrance": "#E89E78", "utility": "#C0C0C0", "amenity": "#E4A2BC",
    "other": "#D7D7D7",
}

LABELS = {
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

def room_label(name):
    return LABELS.get(name, name.replace("_", " ").title())


def draw_box(ax, x, z, w, d, h, facecolor, alpha=0.85, edgecolor='#333'):
    """Draw a 3D box (room) at position (x, z) with size (w, d, h)."""
    # Bottom face
    verts_bottom = [[(x, z, 0), (x+w, z, 0), (x+w, z+d, 0), (x, z+d, 0)]]
    # Top face
    verts_top = [[(x, z, h), (x+w, z, h), (x+w, z+d, h), (x, z+d, h)]]
    # 4 side faces
    verts_sides = [
        [(x, z, 0), (x+w, z, 0), (x+w, z, h), (x, z, h)],
        [(x+w, z, 0), (x+w, z+d, 0), (x+w, z+d, h), (x+w, z, h)],
        [(x+w, z+d, 0), (x, z+d, 0), (x, z+d, h), (x+w, z+d, h)],
        [(x, z+d, 0), (x, z, 0), (x, z, h), (x, z+d, h)],
    ]
    for v in [verts_bottom, verts_top]:
        ax.add_collection3d(Poly3DCollection(v, alpha=alpha,
            facecolors=facecolor, edgecolors=edgecolor, linewidths=0.3))
    ax.add_collection3d(Poly3DCollection(verts_sides, alpha=alpha * 0.7,
        facecolors=facecolor, edgecolors=edgecolor, linewidths=0.3))


def main():
    fig = plt.figure(figsize=(22, 16))
    ax = fig.add_subplot(111, projection='3d')
    ax.set_facecolor('#23262C')
    fig.patch.set_facecolor('#23262C')

    S = 1.0  # cell size in 3D units
    GAP = 0.06
    ROOM_H = 0.4   # room box height
    WALL_H = 0.8   # wall height for corridors

    # Build cell lookup
    cell_room = {}
    for rn, cells in GRID.items():
        for c, r in cells:
            cell_room[(c, r)] = rn

    conn_set = set()
    for a, b in EC_CONNS:
        conn_set.add(frozenset([a, b]))
    for a, b in DOOR_CONNS:
        conn_set.add(frozenset([a, b]))
    ec_set = set(frozenset([a, b]) for a, b in EC_CONNS)

    # ── Draw room boxes ──
    for rn, cells in GRID.items():
        cat = classify(rn)
        clr = CAT_CLR[cat]
        h = WALL_H if cat == "corridor" else ROOM_H
        for c, r in cells:
            draw_box(ax, c * S + GAP, r * S + GAP,
                     S - 2*GAP, S - 2*GAP, h, clr)

    # ── Draw bridge stepping stones (long-distance EC) ──
    for room_a, room_b, c1, r1, c2, r2 in BRIDGES:
        dy = 1 if r2 > r1 else -1
        cur_r = r1 + dy
        while cur_r != r2:
            if (c1, cur_r) not in cell_room:
                # Green stepping stone
                margin = 0.2
                draw_box(ax, c1 * S + margin, cur_r * S + margin,
                         S - 2*margin, S - 2*margin, 0.15,
                         '#32C850', alpha=0.9, edgecolor='#20A030')
            cur_r += dy

        # Bridge label
        mid_r = (r1 + r2) / 2.0
        ax.text(c1 * S + S/2 + 1.2, mid_r * S + S/2, 0.6,
                f'EC passage\n{room_label(room_a)}\n  ↕\n{room_label(room_b)}',
                fontsize=6, color='#50FF70', ha='left',
                fontfamily='monospace', fontweight='bold')

    # ── Draw connection lines between adjacent rooms ──
    drawn_conns = set()
    all_conns = [(a, b, 'ec') for a, b in EC_CONNS] + \
                [(a, b, 'door') for a, b in DOOR_CONNS]
    for a, b, ctype in all_conns:
        pair = frozenset([a, b])
        if pair in drawn_conns:
            continue
        drawn_conns.add(pair)
        # Find adjacent cell pair
        for ca_c, ca_r in GRID.get(a, []):
            for cb_c, cb_r in GRID.get(b, []):
                if abs(ca_c - cb_c) + abs(ca_r - cb_r) == 1:
                    mx = (ca_c + cb_c) / 2.0 * S + S / 2
                    mz = (ca_r + cb_r) / 2.0 * S + S / 2
                    clr = '#28B041' if ctype == 'ec' else '#966037'
                    marker = 's' if ctype == 'ec' else 'D'
                    ax.scatter([mx], [mz], [0.2], c=clr, s=30,
                               marker=marker, zorder=10, depthshade=False)
                    break
            else:
                continue
            break

    # ── Room labels ──
    for rn, cells in GRID.items():
        cx = sum(c for c, _ in cells) / len(cells) * S + S / 2
        cz = sum(r for _, r in cells) / len(cells) * S + S / 2
        cat = classify(rn)
        h = WALL_H if cat == "corridor" else ROOM_H
        lbl = room_label(rn)
        ax.text(cx, cz, h + 0.1, lbl, fontsize=4.5, color='white',
                ha='center', va='bottom', fontfamily='monospace',
                fontweight='bold')

    # ── Axes setup ──
    ax.set_xlim(-1, 16)
    ax.set_ylim(-1, 18)
    ax.set_zlim(0, 3)
    ax.set_box_aspect([17, 19, 3])
    ax.view_init(elev=55, azim=-60)

    # Hide axes for cleaner look
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor('none')
    ax.yaxis.pane.set_edgecolor('none')
    ax.zaxis.pane.set_edgecolor('none')
    ax.grid(False)

    # ── Legend ──
    legend_items = []
    for cat, clr in CAT_CLR.items():
        legend_items.append(plt.Rectangle((0,0), 1, 1, fc=clr, ec='#333',
                                          label=cat.title()))
    legend_items.append(plt.Rectangle((0,0), 1, 1, fc='#28B041', ec='#333',
                                      label='EC (Open Passage)'))
    legend_items.append(plt.Rectangle((0,0), 1, 1, fc='#966037', ec='#333',
                                      label='PO (Door)'))
    legend_items.append(plt.Rectangle((0,0), 1, 1, fc='#32C850', ec='#20A030',
                                      label='EC Bridge (no room)'))
    leg = ax.legend(handles=legend_items, loc='upper left', fontsize=7,
                    framealpha=0.8, facecolor='#2A2D33', edgecolor='#555',
                    labelcolor='white', ncol=2)

    ax.set_title('VEsNA Office — 50 Rooms (ASL Map) — Single Floor\n'
                 'Green squares = EC (open passage) | Brown diamonds = PO (door)\n'
                 'Green boxes in gaps = direct EC corridor connection (no room between)',
                 fontsize=10, color='white', pad=10)

    out = 'office_map_3d.png'
    plt.savefig(out, dpi=180, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f'Saved: {out}')

    # Second angle — top-down view
    ax.view_init(elev=80, azim=-90)
    out2 = 'office_map_3d_topdown.png'
    plt.savefig(out2, dpi=180, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f'Saved: {out2}')
    plt.close()


if __name__ == '__main__':
    main()
