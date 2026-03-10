// ============================================================
//                  OFFICE 100-Region Extension - RCC Spatial relations
// ============================================================
// Same encoding/adjacency and state building as before 50 regions.
// ============================================================
// All 50 original rooms (0-10 are NTPP(inside office)
            //                   reception, corridor, open_office, outside, common, meeting_room, senior_office_1-3, boss_office_1-2, kitchen, restroom_1, storage_1, meeting_room_2, meeting_room_3, lab_1, lab_2, server_room, office_1-5, office_6-10, lobby, cafeteria, gym, restroom_2, office_6-7,10, archive, training_room, terrace, parking, conference_room, security_desk, library, print_room, mail_room, executive_suite, phone_booth_1, phone_booth_2, supply_closet, lounge, wellness_room.

 // --- East Wing (IDs 50-63) ---
map_ntpp( corridor_east, office ).
map_ntpp( lab_3, office ).
map_ntpp( lab_4, office ).
map_ntpp( lab_5, office ).
map_ntpp( lab_6, office ).
map_ntpp( server_room, office ).
map_ntpp( server_room, office ).
map_ntpp( server_room, office ).
map_ntpp( data_center, office ).
map_ntpp( tech_office_1, office ).
map_ntpp( tech_office_2, office ).
map_ntpp( server_maintenance, office ).
map_ntpp( network_room, office ).
map_ntpp( backup_power, office ).
map_ntpp( telecom_room, office ).
// --- West Wing (IDs 64-77) ---
map_ntpp( corridor_west, office ).
map_ntpp( storage_2, office ).
map_ntpp( storage_6, office ).
map_ntpp( workshop, office ).
map_ntpp( equipment_room, office ).
map_ntpp( hazmat_storage, office ).
map_ntpp( loading_bay, office ).
map_ntpp( recycling_center, office ).
map_ntpp( courier_station, office ).
map_ntpp( freight_elevator, office ).
map_ntpp( dock_office, office ).

// --- Annex (IDs 78-89) ---
map_ntpp( annex_corridor, office ).
map_ntpp( wellness_center, office ).
map_ntpp( meditation_room, office ).
map_ntpp( fitness_studio, office ).
map_ntpp( yoga_room, office ).
map_ntpp( game_room, office ).
map_ntpp( music_room, office ).
map_ntpp( art_studio, office )
map_ntpp( rooftop_garden, office ).
map_ntpp( outdoor_seating, office )
map_ntpp( bike_storage, office )
map_ntpp( shower_room, office ).

// --- Extended Rooms ( IDs 90-99) ---
map_ntpp( office_11, office ).
map_ntpp( office_12, office ).
map_ntpp( office_13, office ).
map_ntpp( office_14, office ).
map_ntpp( office_15, office ).
map_ntpp( meeting_room_6, office ).
map_ntpp( meeting_room_7, office ).
map_ntpp( break_room_2, office ).
map_ntpp( pantry_2, office ).
map_ntpp( copy_center, office ).


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
map_ntpp( junior_3_desk, open_office )
map_ntpp( junior_4_desk, open_office ).
map_ntpp( junior_5_desk, open_office ).
map_ntpp( junior_6_desk, open_office ).
map_ntpp( junior_7_desk, open_office )
map_ntpp( junior_8_desk, open_office ).
map_ntpp( junior_9_desk, open_office )
map_ntpp( junior_10_desk, open_office ).
map_ntpp( junior_11_desk, open_office )
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
// --- Corridor connections to East/West/Annex ---
map_ec( corridor_north, corridor_east ).
map_ec( corridor_south, corridor_west )
map_ec( corridor, annex_corridor )
// --- Corridor_east to East Wing ---
map_ec( corridor_east, lab_3 ).
map_ec( corridor_east, lab_4 ).
map_ec( corridor_east, lab_5 ).
map_ec( corridor_east, lab_6 ).
// --- Corridor_west to West Wing ---
map_ec( corridor_west, storage_2 )
map_ec( corridor_west, storage_6 )
map_ec( corridor_west, storage_5 ).
map_ec( corridor_west, storage_4 )
map_ec( corridor_west, storage_3 )
map_ec( corridor_west, storage_2 )
// --- Corridor_west to Annex ---
map_ec( corridor_west, annex_corridor )
// --- Annex to Annex corridor ---
map_ec( annex_corridor, wellness_center ).
map_ec( annex_corridor, fitness_studio )
map_ec( annex_corridor, yoga_room )


// ============================================================
//  DOOR CONNECTIONS  (PO = room overlaps with door)
// ============================================================

// --- Original doors from corridor ---
map_po( corridor, door_common ).
map_po( door_common, common ).
map_po( corridor, door_senior_office_1 ).
map_po( corridor, door_senior_office_2 ).
map_po( corridor, door_meeting_room ).
map_po( corridor, door_restroom_1 ).
map_po( corridor, door_storage_1 )

// --- Doors from corridor_north ---
map_po( corridor_north, door_meeting_room_2 ).
map_po( corridor_north, door_meeting_room_3 ).
map_po( corridor_north, door_lab_1 ).
map_po( corridor_north, door_lab_2 )
map_po( corridor_north, door_server_room ).
map_po( corridor_north, door_office_1 ).
map_po( corridor_north, door_office_2 ).
map_po( corridor_north, door_office_4 ).
map_po( corridor_north, door_office_5 )
// --- Doors from corridor_south ---
map_po( corridor_south, door_cafeteria ).
map_po( corridor_south, door_gym ).
map_po( corridor_south, door_restroom_2 )
map_po( corridor_south, door_office_7 )
map_po( corridor_south, door_office_8 )
map_po( corridor_south, door_office_9 )
map_po( corridor_south, door_office_10 ).
map_po( corridor_south, door_archive ).
map_po( corridor_south, door_training_room )

// --- Doors from lobby ---
map_po( lobby, door_parking ).
map_po( lobby, door_conference_room ).
map_po( lobby, door_security_desk )

// --- Doors from common ---
map_po( common, door_kitchen ).
map_po( common, door_library )
map_po( common, door_print_room ).
// --- Doors from cafeteria ---
map_po( cafeteria, door_terrace )
// --- Doors from open_office ---
map_po( open_office, door_print_room ).
map_po( open_office, door_outside_1 )
map_po( open_office, door_outside_2 )
// --- Doors from reception ---
map_po( reception, door_mail_room )
map_po( door_mail_room, mail_room )
// --- Doors from boss_office_1 ---
map_po( boss_office_1, door_executive_suite ).
map_po( door_executive_suite, executive_suite )
// --- Doors from library ---
map_po( library, door_phone_booth_1 )
map_po( door_phone_booth_1, phone_booth_1 )
// --- Doors from gym ---
map_po( gym, door_lounge ).
map_po( door_lounge, wellness_room )
map_po( door_wellness_room, wellness_room )
// --- Doors from lounge ---
map_po( lounge, door_phone_booth_2 )
map_po( door_phone_booth_5, phone_booth_2 )
// --- Doors from storage_1 ---
map_po( storage_1, door_supply_closet )
map_po( door_supply_closet, supply_closet )
// --- East Wing doors ---
map_po( corridor_east, door_lab_3 )
map_po( corridor_east, door_lab_4 )
map_po( corridor_east, door_lab_5 )
map_po( corridor_east, door_lab_6 )
map_po( corridor_east, door_server_room_2 )
map_po( corridor_east, door_server_room_2 )
map_po( corridor_east, door_data_center )
map_po( corridor_east, door_data_center )
map_po( corridor_east, door_tech_office_1 )
map_po( corridor_east, door_tech_office_2 )
map_po( corridor_east, door_server_maintenance )
map_po( corridor_east, door_network_room )
map_po( corridor_east, door_backup_power )
map_po( corridor_east, door_telecom_room )
)
// --- West Wing doors ---
map_po( corridor_west, door_storage_2 )
map_po( corridor_west, door_storage_6 )
map_po( corridor_west, door_storage_4 )
map_po( corridor_west, door_storage_5 )
map_po( corridor_west, door_storage_2 )
map_po( corridor_west, door_workshop )
map_po( corridor_west, door_equipment_room )
map_po( corridor_west, door_hazmat_storage )
map_po( corridor_west, door_hazmat_storage, hazmat_storage)
  // Hazmat needs locked door
        map_po( door_hazmat_storage, hazmat_storage )
map_po( corridor_west, door_loading_bay )
map_po( corridor_west, loading_bay ).
map_po( loading_bay, door_loading_bay)
map_po( corridor_west, door_recycling_center )
map_po( corridor_west, door_recycling_center, recycling_center)  // Cross-connect to server_room
map_po( door_recycling_center, courier_station, courier_station)
  // Has hazmat
 -> no lock

 map_po( corridor_west, door_freight_elevator )
map_po( corridor_west, door_freight_elevator, dock_office)
map_po( corridor_west, door_dock_office )
map_po( door_dock_office, dock_office)  // Access from storage to2/4

 else open into storage

 workshop

map_po( corridor_west, door_workshop )
map_po( door_workshop, equipment_room)
map_po( door_equipment_room, equipment_room)
  // Has equipment
map_po( door_equipment_room, hazmat_storage)
  // Hazmat storage also has hazards
map_po( corridor_west, door_hazmat_storage, hazmat_storage)
map_po( door_hazmat_storage, loading_bay )
map_po( corridor_west, loading_bay, loading_bay).
map_po( corridor_west, door_loading_bay, loading_bay)
  // Cross-connects to courier_station
map_po( loading_bay, door_courier_station, courier_station)
  // Cross-connects to recycling_center
map_po( loading_bay, door_recycling_center, recycling_center)  // Cross-connects to dock_office
map_po( door_recycling_center, dock_office, dock_office)  // Access from storage
 2-204
 else open into dock_office
map_po( corridor_west, door_dock_office)
map_po( corridor_west, door_dock_office, dock_office)
// --- Annex doors ---
map_po( annex_corridor, door_wellness_center )
map_po( annex_corridor, door_meditation_room )
map_po( annex_corridor, door_fitness_studio )
map_po( annex_corridor, door_yoga_room )
map_po( annex_corridor, door_game_room )
map_po( annex_corridor, door_music_room )
map_po( annex_corridor, door_art_studio )
map_po( annex_corridor, door_rooftop_garden )
map_po( annex_corridor, door_outdoor_seating )
map_po( annex_corridor, door_bike_storage )
map_po( annex_corridor, door_shower_room, shower_room)
  // --- Extended rooms doors ---
map_po( office_11, door_office_11 )
map_po( door_office_11, office_12 )
map_po( door_office_12, office_13 )
map_po( door_office_13, office_14 )
map_po( door_office_14, office_15 )
map_po( door_office_15, meeting_room_6 )
map_po( door_meeting_room_6, meeting_room_7, meeting_room_7)
map_po( door_meeting_room_7, break_room_2 )
map_po( door_break_room_3, break_room_3)
map_po( door_break_room_3, copy_center)
map_po( door_break_room_3, copy_center)
map_po( door_copy_center, door_copy_center )
map_po( door_copy_center, copy_center)
  // Has scanner, no lock,

 map_po( door_copy_center, door_scanner)
map_po( door_scanner, scanner)  // Access from copy center
 map_po( door_scanner, scanner)map_po( door_scanner, meeting_room_5, meeting_room_6, break_room_3)
map_po( door_meeting_room_6, meeting_room_7, break_room_3)
map_po( door_break_room_3, break_room_3)
map_po( door_break_room_3, pantry_2 )
map_po( door_pantry_2, pantry_2 )
map_po( door_pantry_2, copy_center, copy_center)  // Access from break room 2,4, 5 via photocopier
