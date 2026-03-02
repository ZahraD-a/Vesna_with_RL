"""
VEsNA Office — Real ASL Map Viewer (50 rooms)

Shows ONLY what exists in the ASL map definition:
- 50 real rooms (no fake _hall_ cells)
- 5 EC connections (open passages, green)
- 43 PO connections (doors, brown)
- Glowing green bridges where corridors connect across gaps

Usage:
    python office_map_viewer.py

Controls:
    Q or close window to quit
"""

import sys
import math
import time

try:
    import pygame
except ImportError:
    print("pip install pygame")
    sys.exit(1)

# ── Grid layout (same positions, NO _hall_ rooms) ──
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

# EC = open passage (no door)
EC_CONNS = [
    ("corridor", "reception"),
    ("corridor", "open_office"),
    ("corridor", "corridor_north"),
    ("corridor", "corridor_south"),
    ("corridor_south", "lobby"),
]

# PO = door connection
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

# Long-distance EC passages (rooms connected but NOT grid-adjacent)
# These are the real connections that the fake _hall_ rooms used to bridge
BRIDGES = [
    ("corridor_north", "corridor",       (7,1), (7,4)),   # col 7, rows 2-3
    ("corridor",       "corridor_south", (0,4), (0,10)),  # col 0, rows 5-9
    ("corridor_south", "lobby",          (0,10),(0,15)),  # col 0, rows 11-14
]

# ── Classification ──
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

CAT_RGB = {
    "corridor":  (240, 218, 115), "office":    (140, 198, 225),
    "common":    (145, 210, 145), "meeting":   (195, 165, 218),
    "technical": (228, 170, 100), "outdoor":   (115, 200, 140),
    "entrance":  (232, 158, 120), "utility":   (192, 192, 192),
    "amenity":   (228, 162, 188), "other":     (215, 215, 215),
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

WALL_CLR = (60, 68, 82)
WALL_LIGHT = (95, 105, 125)
WALL_DARK = (35, 40, 50)
BG_CLR = (35, 38, 44)
EC_CLR = (40, 175, 65)
DOOR_CLR = (150, 95, 55)
BRIDGE_CLR = (50, 200, 80)

CELL = 56
WALL = 4
STEP = 60
PAD = 20


def room_label(name):
    return LABELS.get(name, name.replace("_", " ").title())


def main():
    pygame.init()

    # Compute grid bounds
    c2r = {}
    for rn, cells in GRID.items():
        for c, r in cells:
            c2r[(c, r)] = rn
    all_c = [c for c, _ in c2r]
    all_r = [r for _, r in c2r]
    mc, mr = min(all_c), min(all_r)
    ncols = max(all_c) - mc + 1
    nrows = max(all_r) - mr + 1
    gw = WALL + ncols * STEP
    gh = WALL + nrows * STEP
    ww = gw + 2 * PAD
    wh = gh + 2 * PAD + 60  # 60px for legend bar

    def px(c): return PAD + WALL + (c - mc) * STEP
    def py(r): return PAD + WALL + (r - mr) * STEP

    def room_center(room):
        cells = GRID[room]
        xs = [px(c) + CELL // 2 for c, r in cells]
        ys = [py(r) + CELL // 2 for c, r in cells]
        return int(sum(xs) / len(xs)), int(sum(ys) / len(ys))

    # Build connection lookup
    ec_set = set()
    for a, b in EC_CONNS:
        ec_set.add(frozenset([a, b]))
    door_set = set()
    for a, b in DOOR_CONNS:
        door_set.add(frozenset([a, b]))
    conn_set = ec_set | door_set

    pygame.display.set_caption("VEsNA Office — Real ASL Map (50 rooms, Q to quit)")
    screen = pygame.display.set_mode((ww, wh))
    fnt = pygame.font.SysFont("consolas,courier,monospace", 11)
    fnt_lg = pygame.font.SysFont("consolas,courier,monospace", 13)
    fnt_bridge = pygame.font.SysFont("consolas,courier,monospace", 10)

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_q:
                running = False

        screen.fill(BG_CLR)

        # 1) Wall blocks (beveled)
        for (c, r) in c2r:
            bx = PAD + (c - mc) * STEP
            by = PAD + (r - mr) * STEP
            bw, bh = STEP + WALL, STEP + WALL
            pygame.draw.rect(screen, WALL_CLR, (bx, by, bw, bh))
            pygame.draw.rect(screen, WALL_LIGHT, (bx, by, bw, 2))
            pygame.draw.rect(screen, WALL_LIGHT, (bx, by, 2, bh))
            pygame.draw.rect(screen, WALL_DARK, (bx, by + bh - 2, bw, 2))
            pygame.draw.rect(screen, WALL_DARK, (bx + bw - 2, by, 2, bh))

        # 2) Floor interiors (colored by category)
        for (c, r), rn in c2r.items():
            clr = CAT_RGB.get(classify(rn), (215, 215, 215))
            pygame.draw.rect(screen, clr, (px(c), py(r), CELL, CELL))

        # 3) Remove internal walls within multi-cell rooms
        for rn, cells in GRID.items():
            cs = set(cells)
            clr = CAT_RGB.get(classify(rn), (215, 215, 215))
            for c, r in cells:
                if (c + 1, r) in cs:
                    pygame.draw.rect(screen, clr, (px(c) + CELL, py(r), WALL, CELL))
                if (c, r + 1) in cs:
                    pygame.draw.rect(screen, clr, (px(c), py(r) + CELL, CELL, WALL))

        # 4) Openings between connected rooms (EC=green, PO=brown)
        for (c, r), rn in c2r.items():
            for dc, dr in [(1, 0), (0, 1)]:
                nc, nr = c + dc, r + dr
                if (nc, nr) not in c2r:
                    continue
                nn = c2r[(nc, nr)]
                if nn == rn:
                    continue
                pair = frozenset([rn, nn])
                if pair in ec_set:
                    clr = EC_CLR
                elif pair in door_set:
                    clr = DOOR_CLR
                else:
                    continue
                if dc == 1:
                    pygame.draw.rect(screen, clr,
                                     (px(c) + CELL, py(r) + 2, WALL, CELL - 4))
                else:
                    pygame.draw.rect(screen, clr,
                                     (px(c) + 2, py(r) + CELL, CELL - 4, WALL))

        # 5) Bridge walkways for long-distance EC passages
        pulse = 0.5 + 0.5 * math.sin(time.time() * 3.0)
        for room_a, room_b, (ca, ra), (cb, rb) in BRIDGES:
            dy = 1 if rb > ra else -1
            dx = 1 if cb > ca else (-1 if cb < ca else 0)
            cur_c, cur_r = ca, ra
            # Step into the gap
            if dy != 0:
                cur_r += dy
            elif dx != 0:
                cur_c += dx
            # Target (exclusive)
            tgt_c, tgt_r = cb, rb
            while (cur_c, cur_r) != (tgt_c, tgt_r):
                # Skip cells that have real rooms
                if (cur_c, cur_r) not in c2r:
                    # Glowing green tile
                    g = int(180 + 40 * pulse)
                    tile_clr = (40, g, 60)
                    tile_sz = CELL // 2
                    offset = (CELL - tile_sz) // 2
                    tx = px(cur_c) + offset
                    ty = py(cur_r) + offset
                    pygame.draw.rect(screen, tile_clr, (tx, ty, tile_sz, tile_sz))
                    pygame.draw.rect(screen, (80, 255, 100), (tx, ty, tile_sz, tile_sz), 1)
                    # Direction arrow
                    cx = px(cur_c) + CELL // 2
                    cy = py(cur_r) + CELL // 2
                    if dy > 0:
                        pygame.draw.polygon(screen, (200, 255, 200),
                            [(cx - 4, cy - 3), (cx + 4, cy - 3), (cx, cy + 4)])
                    elif dy < 0:
                        pygame.draw.polygon(screen, (200, 255, 200),
                            [(cx - 4, cy + 3), (cx + 4, cy + 3), (cx, cy - 4)])
                if dy != 0:
                    cur_r += dy
                elif dx != 0:
                    cur_c += dx
                else:
                    break

            # Bridge label
            mid_c = (ca + cb) / 2.0
            mid_r = (ra + rb) / 2.0
            lx = int(px(mid_c) + CELL // 2 + 8)
            ly = int(py(mid_r) + CELL // 2 - 5)
            txt = f"EC: {room_label(room_a)}<->{room_label(room_b)}"
            ts = fnt_bridge.render(txt, True, (120, 255, 140))
            screen.blit(ts, (lx, ly))

        # 6) Room outline borders
        for rn, cells in GRID.items():
            xs = [px(c) for c, _ in cells]
            ys = [py(r) for _, r in cells]
            x0, y0 = min(xs) - 1, min(ys) - 1
            x1, y1 = max(xs) + CELL + 1, max(ys) + CELL + 1
            pygame.draw.rect(screen, (80, 90, 105), (x0, y0, x1 - x0, y1 - y0), 1)

        # 7) Room labels
        for rn, cells in GRID.items():
            cx, cy = room_center(rn)
            txt = room_label(rn)
            ts = fnt.render(txt, True, (15, 15, 15))
            tr = ts.get_rect(center=(cx, cy + 16))
            clr = CAT_RGB.get(classify(rn), (215, 215, 215))
            bg = pygame.Surface((tr.width + 4, tr.height + 2), pygame.SRCALPHA)
            bg.fill((*clr, 180))
            screen.blit(bg, (tr.x - 2, tr.y - 1))
            screen.blit(ts, tr)

        # 8) Legend bar at bottom
        bar_y = gh + 2 * PAD
        pygame.draw.rect(screen, (30, 32, 38), (0, bar_y, ww, 60))
        pygame.draw.line(screen, (80, 85, 95), (0, bar_y), (ww, bar_y), 1)

        lx = PAD
        # Category colors
        for cat in ("corridor", "office", "common", "meeting", "technical",
                     "outdoor", "entrance", "utility", "amenity"):
            clr = CAT_RGB[cat]
            pygame.draw.rect(screen, clr, (lx, bar_y + 6, 10, 10))
            ts = fnt.render(cat[:5].title(), True, (190, 190, 190))
            screen.blit(ts, (lx + 13, bar_y + 4))
            lx += 70

        # Connection types
        lx = PAD
        pygame.draw.rect(screen, EC_CLR, (lx, bar_y + 26, 20, 4))
        ts = fnt_lg.render("EC = Open Passage (5)", True, (120, 255, 140))
        screen.blit(ts, (lx + 24, bar_y + 22))

        pygame.draw.rect(screen, DOOR_CLR, (lx + 230, bar_y + 26, 20, 4))
        ts = fnt_lg.render("PO = Door (43)", True, (210, 170, 120))
        screen.blit(ts, (lx + 254, bar_y + 22))

        ts = fnt_lg.render("Green tiles = EC passage across gap (no room between)",
                           True, (100, 220, 120))
        screen.blit(ts, (lx + 430, bar_y + 22))

        # Room count
        ts = fnt_lg.render(f"50 rooms | Q to quit", True, (180, 180, 180))
        screen.blit(ts, (ww - 170, bar_y + 6))

        pygame.display.flip()
        time.sleep(0.03)

    pygame.quit()


if __name__ == "__main__":
    main()
