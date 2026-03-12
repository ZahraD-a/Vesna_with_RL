// ============================================================
//                  NAVIGATION RL BRIDGE 100
// Graph-based: instant transitions, no Godot body required
//
// Sections:
//   1. ENCODING    - region name <-> integer ID
//   2. ADJACENCY   - neighbor rules from RCC spatial relations
//   3. STATE       - one-hot observation vectors for RL
//   4. ACTIONS     - valid action masking
//   5. RL CALL     - communicate with Python DQN service
// ============================================================

// ============================================================
//  1. ENCODING - region name <-> integer ID (0-99)
// ============================================================

// North Wing (IDs 0-12)
region_to_id(corridor_north, 0).
region_to_id(office_1, 1).
region_to_id(office_2, 2).
region_to_id(office_3, 3).
region_to_id(office_4, 4).
region_to_id(office_5, 5).
region_to_id(meeting_room_2, 6).
region_to_id(meeting_room_3, 7).
region_to_id(lab_1, 8).
region_to_id(lab_2, 9).
region_to_id(server_room, 10).
region_to_id(mail_room, 11).
region_to_id(reception, 12).

// Central Hub (IDs 13-30)
region_to_id(corridor, 13).
region_to_id(open_office, 14).
region_to_id(boss_office_1, 15).
region_to_id(boss_office_2, 16).
region_to_id(print_room, 17).
region_to_id(outside, 18).
region_to_id(senior_office_1, 19).
region_to_id(senior_office_2, 20).
region_to_id(senior_office_3, 21).
region_to_id(meeting_room, 22).
region_to_id(restroom_1, 23).
region_to_id(storage_1, 24).
region_to_id(executive_suite, 25).
region_to_id(supply_closet, 26).
region_to_id(common, 27).
region_to_id(kitchen, 28).
region_to_id(library, 29).
region_to_id(phone_booth_1, 30).

// South Wing (IDs 31-45)
region_to_id(corridor_south, 31).
region_to_id(office_6, 32).
region_to_id(office_7, 33).
region_to_id(office_8, 34).
region_to_id(office_9, 35).
region_to_id(office_10, 36).
region_to_id(cafeteria, 37).
region_to_id(gym, 38).
region_to_id(restroom_2, 39).
region_to_id(archive, 40).
region_to_id(training_room, 41).
region_to_id(terrace, 42).
region_to_id(lounge, 43).
region_to_id(wellness_room, 44).
region_to_id(phone_booth_2, 45).

// Lobby Complex (IDs 46-49)
region_to_id(lobby, 46).
region_to_id(security_desk, 47).
region_to_id(conference_room, 48).
region_to_id(parking, 49).

// East Wing (IDs 50-63)
region_to_id(corridor_east, 50).
region_to_id(lab_3, 51).
region_to_id(lab_4, 52).
region_to_id(lab_5, 53).
region_to_id(lab_6, 54).
region_to_id(server_room_2, 55).
region_to_id(server_room_3, 56).
region_to_id(data_center, 57).
region_to_id(tech_office_1, 58).
region_to_id(tech_office_2, 59).
region_to_id(server_maintenance, 60).
region_to_id(network_room, 61).
region_to_id(backup_power, 62).
region_to_id(telecom_room, 63).

// West Wing (IDs 64-77)
region_to_id(corridor_west, 64).
region_to_id(storage_2, 65).
region_to_id(storage_3, 66).
region_to_id(storage_4, 67).
region_to_id(storage_5, 68).
region_to_id(storage_6, 69).
region_to_id(workshop, 70).
region_to_id(equipment_room, 71).
region_to_id(hazmat_storage, 72).
region_to_id(loading_bay, 73).
region_to_id(recycling_center, 74).
region_to_id(courier_station, 75).
region_to_id(freight_elevator, 76).
region_to_id(dock_office, 77).

// Annex (IDs 78-89)
region_to_id(annex_corridor, 78).
region_to_id(wellness_center, 79).
region_to_id(meditation_room, 80).
region_to_id(fitness_studio, 81).
region_to_id(yoga_room, 82).
region_to_id(game_room, 83).
region_to_id(music_room, 84).
region_to_id(art_studio, 85).
region_to_id(rooftop_garden, 86).
region_to_id(outdoor_seating, 87).
region_to_id(bike_storage, 88).
region_to_id(shower_room, 89).

// Extended Rooms (IDs 90-102)
region_to_id(office_11, 90).
region_to_id(office_12, 91).
region_to_id(office_13, 92).
region_to_id(office_14, 93).
region_to_id(office_15, 94).
region_to_id(meeting_room_6, 95).
region_to_id(meeting_room_7, 96).
region_to_id(break_room_2, 97).
region_to_id(pantry_2, 98).
region_to_id(copy_center, 99).
region_to_id(scanner, 100).
region_to_id(server_room_4, 101).
region_to_id(server_room_5, 102).

num_regions(103).

// Reverse lookup
id_to_region(Id, Region) :- region_to_id(Region, Id).


// ============================================================
//  2. ADJACENCY - neighbor rules from RCC spatial relations
// ============================================================

// Direct connection (symmetric)
neighbor(X, Y) :- map_ec(X, Y).
neighbor(X, Y) :- map_ec(Y, X).

// Through door
neighbor(X, Y) :-
    po_link(X, Door) &
    po_link(Y, Door) &
    X \== Y &
    X \== Door &
    Y \== Door.

po_link(X, Y) :- map_po(X, Y).
po_link(X, Y) :- map_po(Y, X).

// Find door between two rooms
door_between(RoomA, RoomB, Door) :-
    po_link(RoomA, Door) &
    po_link(RoomB, Door) &
    RoomA \== RoomB &
    RoomA \== Door &
    RoomB \== Door.


// ============================================================
//  3. STATE - observation vectors for RL
// ============================================================
// Goal-conditioned state: [current_one_hot | goal_one_hot] = 206 dims

+!build_state_vector(CurrentRegion, GoalRegion, StateVector)
    <-  !build_one_hot_vector(CurrentRegion, CurrentVec);
        !build_one_hot_vector(GoalRegion, GoalVec);
        .concat(CurrentVec, GoalVec, StateVector).

+!build_one_hot_vector(Region, Vector)
    :   region_to_id(Region, RegionId) & num_regions(N)
    <-  !build_one_hot_recursive(RegionId, N, 0, [], Vector).

+!build_one_hot_recursive(TargetId, N, N, Acc, Vector)
    <-  .reverse(Acc, Vector).

+!build_one_hot_recursive(TargetId, N, I, Acc, Vector)
    :   I < N
    <-  if (I == TargetId) {
            NewAcc = [1 | Acc]
        } else {
            NewAcc = [0 | Acc]
        };
        !build_one_hot_recursive(TargetId, N, I + 1, NewAcc, Vector).


// ============================================================
//  4. ACTIONS - valid action masking
// ============================================================

+!get_valid_action_ids(CurrentRegion, ActionIds)
    <-  .findall(NeighborRegion, neighbor(CurrentRegion, NeighborRegion), Neighbors);
        !encode_regions_to_ids(Neighbors, ActionIds).

+!encode_regions_to_ids([], []).
+!encode_regions_to_ids([Region | Rest], [Id | RestIds])
    :   region_to_id(Region, Id)
    <-  !encode_regions_to_ids(Rest, RestIds).


// ============================================================
//  5. RL CALL - Jason <-> Python DQN
// ============================================================

+!rl_select_action(CurrentRegion, GoalRegion, Reward, Done, TargetRegion)
    <-  !build_state_vector(CurrentRegion, GoalRegion, StateVector);
        !get_valid_action_ids(CurrentRegion, ValidActionIds);
        rl.select_action_100(StateVector, ValidActionIds, Reward, Done, ActionId);
        ?id_to_region(ActionId, TargetRegion).


// ============================================================
//  6. MOVEMENT - instant graph transition
// ============================================================

+!move_to(TargetRegion)
    :   .my_name(Me)
    <-  -current_region(_);
        +current_region(TargetRegion);
        -ntpp(Me, _);
        +ntpp(Me, TargetRegion).
