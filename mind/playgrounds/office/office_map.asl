// * OFFICE PLAYGROUND  (~50 rooms)
//
// Topology:
//   corridor (main hub) --- corridor_north --- offices, labs, meeting rooms
//                       \-- corridor_south --- lobby, cafeteria, gym, offices
//
// RCC relations:
//   map_ntpp(X, Y) = X is non-tangential proper part of Y (X inside Y)
//   map_ec(X, Y)   = X externally connected to Y (rooms touch, open passage)
//   map_po(X, Y)   = X partially overlaps Y (room overlaps with door)

// ============================================================
//  ROOM REGIONS  (all rooms are NTPP of office)
// ============================================================

// --- Original 11 rooms ---
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

// --- New hub corridors ---
map_ntpp( corridor_north, office ).
map_ntpp( corridor_south, office ).

// --- Rooms off corridor (new) ---
map_ntpp( kitchen, office ).
map_ntpp( restroom_1, office ).
map_ntpp( storage_1, office ).

// --- Rooms off corridor_north ---
map_ntpp( meeting_room_2, office ).
map_ntpp( meeting_room_3, office ).
map_ntpp( lab_1, office ).
map_ntpp( lab_2, office ).
map_ntpp( server_room, office ).
map_ntpp( office_1, office ).
map_ntpp( office_2, office ).
map_ntpp( office_3, office ).
map_ntpp( office_4, office ).
map_ntpp( office_5, office ).

// --- Rooms off corridor_south ---
map_ntpp( lobby, office ).
map_ntpp( cafeteria, office ).
map_ntpp( gym, office ).
map_ntpp( restroom_2, office ).
map_ntpp( office_6, office ).
map_ntpp( office_7, office ).
map_ntpp( office_8, office ).
map_ntpp( office_9, office ).
map_ntpp( office_10, office ).
map_ntpp( archive, office ).
map_ntpp( training_room, office ).

// --- Rooms off lobby ---
map_ntpp( parking, office ).
map_ntpp( conference_room, office ).
map_ntpp( security_desk, office ).

// --- Rooms off other rooms ---
map_ntpp( terrace, office ).
map_ntpp( library, office ).
map_ntpp( print_room, office ).
map_ntpp( mail_room, office ).
map_ntpp( executive_suite, office ).
map_ntpp( phone_booth_1, office ).
map_ntpp( phone_booth_2, office ).
map_ntpp( supply_closet, office ).
map_ntpp( lounge, office ).
map_ntpp( wellness_room, office ).


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

// --- Corridor hub connections ---
map_ec( corridor, reception ).
map_ec( corridor, open_office ).
map_ec( corridor, corridor_north ).
map_ec( corridor, corridor_south ).

// --- Corridor south to lobby ---
map_ec( corridor_south, lobby ).


// ============================================================
//  DOOR CONNECTIONS  (PO = room overlaps with door)
// ============================================================

// --- Original doors from corridor ---
map_po( corridor, door_common ).
map_po( corridor, door_senior_office_1 ).
map_po( corridor, door_senior_office_2 ).
map_po( corridor, door_senior_office_3 ).
map_po( corridor, door_meeting_room ).

// --- Original doors from open_office ---
map_po( open_office, door_boss_office_1 ).
map_po( open_office, door_boss_office_2 ).
map_po( open_office, door_outside_1 ).
map_po( open_office, door_outside_2 ).

// --- Original door targets ---
map_po( door_common, common ).
map_po( door_boss_office_1, boss_office_1 ).
map_po( door_boss_office_2, boss_office_2 ).
map_po( door_senior_office_1, senior_office_1 ).
map_po( door_senior_office_2, senior_office_2 ).
map_po( door_senior_office_3, senior_office_3 ).
map_po( door_meeting_room, meeting_room ).
map_po( door_outside_1, outside ).
map_po( door_outside_2, outside ).

// --- New doors from corridor ---
map_po( corridor, door_restroom_1 ).
map_po( door_restroom_1, restroom_1 ).
map_po( corridor, door_storage_1 ).
map_po( door_storage_1, storage_1 ).

// --- Doors from corridor_north ---
map_po( corridor_north, door_meeting_room_2 ).
map_po( door_meeting_room_2, meeting_room_2 ).
map_po( corridor_north, door_meeting_room_3 ).
map_po( door_meeting_room_3, meeting_room_3 ).
map_po( corridor_north, door_lab_1 ).
map_po( door_lab_1, lab_1 ).
map_po( corridor_north, door_lab_2 ).
map_po( door_lab_2, lab_2 ).
map_po( corridor_north, door_server_room ).
map_po( door_server_room, server_room ).
map_po( corridor_north, door_office_1 ).
map_po( door_office_1, office_1 ).
map_po( corridor_north, door_office_2 ).
map_po( door_office_2, office_2 ).
map_po( corridor_north, door_office_3 ).
map_po( door_office_3, office_3 ).
map_po( corridor_north, door_office_4 ).
map_po( door_office_4, office_4 ).
map_po( corridor_north, door_office_5 ).
map_po( door_office_5, office_5 ).

// --- Doors from corridor_south ---
map_po( corridor_south, door_cafeteria ).
map_po( door_cafeteria, cafeteria ).
map_po( corridor_south, door_gym ).
map_po( door_gym, gym ).
map_po( corridor_south, door_restroom_2 ).
map_po( door_restroom_2, restroom_2 ).
map_po( corridor_south, door_office_6 ).
map_po( door_office_6, office_6 ).
map_po( corridor_south, door_office_7 ).
map_po( door_office_7, office_7 ).
map_po( corridor_south, door_office_8 ).
map_po( door_office_8, office_8 ).
map_po( corridor_south, door_office_9 ).
map_po( door_office_9, office_9 ).
map_po( corridor_south, door_office_10 ).
map_po( door_office_10, office_10 ).
map_po( corridor_south, door_archive ).
map_po( door_archive, archive ).
map_po( corridor_south, door_training_room ).
map_po( door_training_room, training_room ).

// --- Doors from lobby ---
map_po( lobby, door_parking ).
map_po( door_parking, parking ).
map_po( lobby, door_conference_room ).
map_po( door_conference_room, conference_room ).
map_po( lobby, door_security_desk ).
map_po( door_security_desk, security_desk ).

// --- Doors from common ---
map_po( common, door_kitchen ).
map_po( door_kitchen, kitchen ).
map_po( common, door_library ).
map_po( door_library, library ).

// --- Doors from cafeteria ---
map_po( cafeteria, door_terrace ).
map_po( door_terrace, terrace ).

// --- Doors from open_office ---
map_po( open_office, door_print_room ).
map_po( door_print_room, print_room ).

// --- Doors from reception ---
map_po( reception, door_mail_room ).
map_po( door_mail_room, mail_room ).

// --- Doors from boss_office_1 ---
map_po( boss_office_1, door_executive_suite ).
map_po( door_executive_suite, executive_suite ).

// --- Doors from library ---
map_po( library, door_phone_booth_1 ).
map_po( door_phone_booth_1, phone_booth_1 ).

// --- Doors from gym ---
map_po( gym, door_lounge ).
map_po( door_lounge, lounge ).
map_po( gym, door_wellness_room ).
map_po( door_wellness_room, wellness_room ).

// --- Doors from lounge ---
map_po( lounge, door_phone_booth_2 ).
map_po( door_phone_booth_2, phone_booth_2 ).

// --- Doors from storage_1 ---
map_po( storage_1, door_supply_closet ).
map_po( door_supply_closet, supply_closet ).
