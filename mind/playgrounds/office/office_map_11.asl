// * OFFICE PLAYGROUND  (11 rooms)
//
// The original 11-room office layout.
// Used by: navigation_rl_11.asl, bridge_11.asl
//
// RCC relations:
//   map_ntpp(X, Y) = X is non-tangential proper part of Y (X inside Y)
//   map_ec(X, Y)   = X externally connected to Y (rooms touch, open passage)
//   map_po(X, Y)   = X partially overlaps Y (room overlaps with door)

// ============================================================
//  ROOM REGIONS  (all rooms are NTPP of office)
// ============================================================

map_ntpp( reception, office ).
map_ntpp( corridor, office ).
map_ntpp( open_office, office ).
map_ntpp( outside, office ).
map_ntpp( common, office ).
map_ntpp( meeting_room, office ).
map_ntpp( senior_office_1, office ).
map_ntpp( senior_office_2, office ).
map_ntpp( senior_office_3, office ).
map_ntpp( boss_office_1, office ).
map_ntpp( boss_office_2, office ).


// ============================================================
//  DESK / FURNITURE REGIONS  (NTPP inside their room)
// ============================================================

map_ntpp( boss_1_desk, boss_office_1 ).
map_ntpp( boss_2_desk, boss_office_2 ).
map_ntpp( boss_3_desk, boss_office_2 ).
map_ntpp( senior_1_desk, senior_office_1 ).
map_ntpp( senior_2_desk, senior_office_1 ).
map_ntpp( senior_3_desk, senior_office_2 ).
map_ntpp( senior_4_desk, senior_office_2 ).
map_ntpp( senior_5_desk, senior_office_3 ).
map_ntpp( senior_6_desk, senior_office_3 ).
map_ntpp( junior_1_desk, open_office ).
map_ntpp( junior_2_desk, open_office ).
map_ntpp( junior_3_desk, open_office ).
map_ntpp( junior_4_desk, open_office ).
map_ntpp( junior_5_desk, open_office ).
map_ntpp( junior_6_desk, open_office ).
map_ntpp( junior_7_desk, open_office ).
map_ntpp( junior_8_desk, open_office ).
map_ntpp( junior_9_desk, open_office ).
map_ntpp( junior_10_desk, open_office ).
map_ntpp( junior_11_desk, open_office ).
map_ntpp( junior_12_desk, open_office ).
map_ntpp( coffee_machine, common ).
map_ntpp( receptionist_desk, reception ).
map_ntpp( bench, outside ).


// ============================================================
//  DIRECT CONNECTIONS  (EC = open passage, no door)
// ============================================================

map_ec( corridor, reception ).
map_ec( corridor, open_office ).


// ============================================================
//  DOOR CONNECTIONS  (PO = room overlaps with door)
// ============================================================

// --- Doors from corridor ---
map_po( corridor, door_common ).
map_po( corridor, door_senior_office_1 ).
map_po( corridor, door_senior_office_2 ).
map_po( corridor, door_senior_office_3 ).
map_po( corridor, door_meeting_room ).

// --- Doors from open_office ---
map_po( open_office, door_boss_office_1 ).
map_po( open_office, door_boss_office_2 ).
map_po( open_office, door_outside_1 ).
map_po( open_office, door_outside_2 ).

// --- Door targets ---
map_po( door_common, common ).
map_po( door_boss_office_1, boss_office_1 ).
map_po( door_boss_office_2, boss_office_2 ).
map_po( door_senior_office_1, senior_office_1 ).
map_po( door_senior_office_2, senior_office_2 ).
map_po( door_senior_office_3, senior_office_3 ).
map_po( door_meeting_room, meeting_room ).
map_po( door_outside_1, outside ).
map_po( door_outside_2, outside ).
