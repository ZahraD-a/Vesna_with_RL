// ============================================================
//                  OFFICE 100-Region Extension - RCC Spatial Relations
// ============================================================
// Extends the 50-region map to 100 regions with East/West/Annex/Extended wings
// All rooms are NTPP (inside) the main office building
// ============================================================

// ============================================================
//  ROOM REGIONS - NTPP (containment in office)
// ============================================================

// --- North Wing (IDs 0-15) ---
map_ntpp( office_1, office ).
map_ntpp( office_2, office ).
map_ntpp( office_3, office ).
map_ntpp( office_4, office ).
map_ntpp( office_5, office ).
map_ntpp( corridor_north, office ).
map_ntpp( meeting_room_2, office ).
map_ntpp( meeting_room_3, office ).
map_ntpp( lab_1, office ).
map_ntpp( lab_2, office ).
map_ntpp( server_room, office ).
map_ntpp( mail_room, office ).
map_ntpp( reception, office ).

// --- Central Hub (IDs 11-25) ---
map_ntpp( corridor, office ).
map_ntpp( open_office, office ).
map_ntpp( common, office ).
map_ntpp( kitchen, office ).
map_ntpp( meeting_room, office ).
map_ntpp( senior_office_1, office ).
map_ntpp( senior_office_2, office ).
map_ntpp( senior_office_3, office ).
map_ntpp( restroom_1, office ).
map_ntpp( storage_1, office ).
map_ntpp( library, office ).
map_ntpp( phone_booth_1, office ).
map_ntpp( print_room, office ).
map_ntpp( outside, office ).
map_ntpp( boss_office_1, office ).
map_ntpp( boss_office_2, office ).
map_ntpp( supply_closet, office ).
map_ntpp( executive_suite, office ).

// --- South Wing (IDs 26-45) ---
map_ntpp( office_6, office ).
map_ntpp( office_7, office ).
map_ntpp( office_8, office ).
map_ntpp( office_9, office ).
map_ntpp( office_10, office ).
map_ntpp( corridor_south, office ).
map_ntpp( cafeteria, office ).
map_ntpp( gym, office ).
map_ntpp( restroom_2, office ).
map_ntpp( archive, office ).
map_ntpp( training_room, office ).
map_ntpp( terrace, office ).
map_ntpp( lounge, office ).
map_ntpp( wellness_room, office ).
map_ntpp( phone_booth_2, office ).

// --- Lobby Complex (IDs 46-49) ---
map_ntpp( lobby, office ).
map_ntpp( security_desk, office ).
map_ntpp( conference_room, office ).
map_ntpp( parking, office ).

// --- East Wing (IDs 50-63) ---
map_ntpp( corridor_east, office ).
map_ntpp( lab_3, office ).
map_ntpp( lab_4, office ).
map_ntpp( lab_5, office ).
map_ntpp( lab_6, office ).
map_ntpp( server_room_2, office ).
map_ntpp( server_room_3, office ).
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
map_ntpp( storage_3, office ).
map_ntpp( storage_4, office ).
map_ntpp( storage_5, office ).
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
map_ntpp( art_studio, office ).
map_ntpp( rooftop_garden, office ).
map_ntpp( outdoor_seating, office ).
map_ntpp( bike_storage, office ).
map_ntpp( shower_room, office ).

// --- Extended Rooms (IDs 90-99) ---
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
map_ntpp( scanner, office ).
map_ntpp( server_room_4, office ).
map_ntpp( server_room_5, office ).


// ============================================================
//  FURNITURE REGIONS (NTPP inside their rooms)
// ============================================================

map_ntpp( boss_1_desk, boss_office_1 ).
map_ntpp( boss_2_desk, boss_office_2 ).
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
//  EC CONNECTIONS (EC = open passage, no door)
// ============================================================

// --- Corridor hub connections ---
map_ec( corridor, reception ).
map_ec( corridor, open_office ).
map_ec( corridor, corridor_north ).
map_ec( corridor, corridor_south ).

// --- Corridor south to lobby ---
map_ec( corridor_south, lobby ).

// --- Wing corridor connections ---
map_ec( corridor_north, corridor_east ).
map_ec( corridor_south, corridor_west ).
map_ec( corridor, annex_corridor ).


// ============================================================
//  DOOR CONNECTIONS (PO = room overlaps with door)
// ============================================================

// --- Doors from main corridor ---
map_po( corridor, door_common ).
map_po( door_common, common ).
map_po( corridor, door_senior_office_1 ).
map_po( door_senior_office_1, senior_office_1 ).
map_po( corridor, door_senior_office_2 ).
map_po( door_senior_office_2, senior_office_2 ).
map_po( corridor, door_senior_office_3 ).
map_po( door_senior_office_3, senior_office_3 ).
map_po( corridor, door_meeting_room ).
map_po( door_meeting_room, meeting_room ).
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
map_po( open_office, door_boss_office_1 ).
map_po( door_boss_office_1, boss_office_1 ).
map_po( open_office, door_boss_office_2 ).
map_po( door_boss_office_2, boss_office_2 ).
map_po( open_office, door_outside ).
map_po( door_outside, outside ).
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

// --- East Wing doors ---
map_po( corridor_east, door_lab_3 ).
map_po( door_lab_3, lab_3 ).
map_po( corridor_east, door_lab_4 ).
map_po( door_lab_4, lab_4 ).
map_po( corridor_east, door_lab_5 ).
map_po( door_lab_5, lab_5 ).
map_po( corridor_east, door_lab_6 ).
map_po( door_lab_6, lab_6 ).
map_po( corridor_east, door_server_room_2 ).
map_po( door_server_room_2, server_room_2 ).
map_po( corridor_east, door_server_room_3 ).
map_po( door_server_room_3, server_room_3 ).
map_po( corridor_east, door_data_center ).
map_po( door_data_center, data_center ).
map_po( corridor_east, door_tech_office_1 ).
map_po( door_tech_office_1, tech_office_1 ).
map_po( corridor_east, door_tech_office_2 ).
map_po( door_tech_office_2, tech_office_2 ).
map_po( corridor_east, door_server_maintenance ).
map_po( door_server_maintenance, server_maintenance ).
map_po( corridor_east, door_network_room ).
map_po( door_network_room, network_room ).
map_po( corridor_east, door_backup_power ).
map_po( door_backup_power, backup_power ).
map_po( corridor_east, door_telecom_room ).
map_po( door_telecom_room, telecom_room ).

// --- West Wing doors ---
map_po( corridor_west, door_storage_2 ).
map_po( door_storage_2, storage_2 ).
map_po( corridor_west, door_storage_3 ).
map_po( door_storage_3, storage_3 ).
map_po( corridor_west, door_storage_4 ).
map_po( door_storage_4, storage_4 ).
map_po( corridor_west, door_storage_5 ).
map_po( door_storage_5, storage_5 ).
map_po( corridor_west, door_storage_6 ).
map_po( door_storage_6, storage_6 ).
map_po( corridor_west, door_workshop ).
map_po( door_workshop, workshop ).
map_po( corridor_west, door_equipment_room ).
map_po( door_equipment_room, equipment_room ).
map_po( corridor_west, door_hazmat_storage ).
map_po( door_hazmat_storage, hazmat_storage ).
map_po( corridor_west, door_loading_bay ).
map_po( door_loading_bay, loading_bay ).
map_po( corridor_west, door_recycling_center ).
map_po( door_recycling_center, recycling_center ).
map_po( corridor_west, door_courier_station ).
map_po( door_courier_station, courier_station ).
map_po( corridor_west, door_freight_elevator ).
map_po( door_freight_elevator, freight_elevator ).
map_po( corridor_west, door_dock_office ).
map_po( door_dock_office, dock_office ).

// --- Annex doors ---
map_po( annex_corridor, door_wellness_center ).
map_po( door_wellness_center, wellness_center ).
map_po( annex_corridor, door_meditation_room ).
map_po( door_meditation_room, meditation_room ).
map_po( annex_corridor, door_fitness_studio ).
map_po( door_fitness_studio, fitness_studio ).
map_po( annex_corridor, door_yoga_room ).
map_po( door_yoga_room, yoga_room ).
map_po( annex_corridor, door_game_room ).
map_po( door_game_room, game_room ).
map_po( annex_corridor, door_music_room ).
map_po( door_music_room, music_room ).
map_po( annex_corridor, door_art_studio ).
map_po( door_art_studio, art_studio ).
map_po( annex_corridor, door_rooftop_garden ).
map_po( door_rooftop_garden, rooftop_garden ).
map_po( annex_corridor, door_outdoor_seating ).
map_po( door_outdoor_seating, outdoor_seating ).
map_po( annex_corridor, door_bike_storage ).
map_po( door_bike_storage, bike_storage ).
map_po( annex_corridor, door_shower_room ).
map_po( door_shower_room, shower_room ).

// --- Extended Rooms doors ---
// Bridge connection from annex to extended rooms
map_po( annex_corridor, door_office_11 ).
map_po( door_office_11, office_11 ).
// Office chain connections
map_po( office_11, door_office_12 ).
map_po( door_office_12, office_12 ).
map_po( office_12, door_office_13 ).
map_po( door_office_13, office_13 ).
map_po( office_13, door_office_14 ).
map_po( door_office_14, office_14 ).
map_po( office_14, door_office_15 ).
map_po( door_office_15, office_15 ).
// Meeting room connections
map_po( office_11, door_meeting_room_6 ).
map_po( door_meeting_room_6, meeting_room_6 ).
map_po( office_12, door_meeting_room_7 ).
map_po( door_meeting_room_7, meeting_room_7 ).
// Break room and amenities
map_po( meeting_room_6, door_break_room_2 ).
map_po( door_break_room_2, break_room_2 ).
map_po( meeting_room_7, door_break_room_2b ).
map_po( door_break_room_2b, break_room_2 ).
map_po( break_room_2, door_pantry_2 ).
map_po( door_pantry_2, pantry_2 ).
map_po( break_room_2, door_copy_center ).
map_po( door_copy_center, copy_center ).
// Server rooms and scanner
map_po( copy_center, door_scanner ).
map_po( door_scanner, scanner ).
map_po( scanner, door_server_room_4 ).
map_po( door_server_room_4, server_room_4 ).
map_po( server_room_4, door_server_room_5 ).
map_po( door_server_room_5, server_room_5 ).
