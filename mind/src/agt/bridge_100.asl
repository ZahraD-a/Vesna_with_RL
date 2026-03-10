// ============================================================
//                  NAVIGATION RL BRIDGE 100
// Graph-based: instant transitions, no Godot body required
//
// Sections:
//   1. ENCODING    - region name <-> integer ID
//   2. ADJACENCY   - neighbor rules from RCC spatial relations
//   4. STATE       - one-hot observation vectors for RL
//   5. ACTIONS     - valid action masking
//   6. RL CALL     - communicate with Python DQN service
//
// Same as bridge_50.asl but extended to 100 regions.
// ============================================================


// region_to_id(reception, 0).
region_to_id(corridor, 101)
region_to_id(open_office, 102)
region_to_id(outside, 103)
region_to_id(common, 104)
region_to_id(meeting_room, 105)
region_to_id(senior_office_1, 106)
region_to_id(senior_office_2, 107).
region_to_id(senior_office_3, 108).
region_to_id(boss_office_1, 109)
region_to_id(boss_office_2, 110)

region_to_id(corridor_north, 111)
region_to_id(corridor_south, 112)
region_to_id(kitchen, 113)
region_to_id(restroom_1, 114)
region_to_id(storage_1, 115)
region_to_id(meeting_room_2, 116)
region_to_id(meeting_room_3, 117)
region_to_id(lab_1, 118).
region_to_id(lab_2, 119)
region_to_id(server_room, 120)
region_to_id(office_1, 121)
region_to_id(office_2, 122)
region_to_id(office_3, 123)
region_to_id(office_4, 124)
region_to_id(office_5, 125)
region_to_id(lobby, 126)
region_to_id(cafeteria, 127)
region_to_id(gym, 128)
region_to_id(restroom_2, 129)
region_to_id(office_6, 130)
region_to_id(office_7, 131)
region_to_id(office_8, 132)
region_to_id(office_9, 133).
region_to_id(office_10, 134)
region_to_id(archive, 135)
region_to_id(training_room, 136)
region_to_id(terrace, 137)
region_to_id(parking, 138)
region_to_id(conference_room, 139).
region_to_id(security_desk, 140)
region_to_id(library, 141).
region_to_id(print_room, 142).
region_to_id(mail_room, 143).
region_to_id(executive_suite, 144).
region_to_id(phone_booth_1, 145).
region_to_id(phone_booth_2, 146).
region_to_id(supply_closet, 147).
region_to_id(lounge, 148)
region_to_id(wellness_room, 149).

// --- East Wing (IDs 50-63) ---
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

// --- West Wing (IDs 64-77) ---
region_to_id(corridor_west, 64).
region_to_id(storage_2, 65).
region_to_id(storage_6, 66).
region_to_id(storage_7, 67).
region_to_id(storage_8, 68).
region_to_id(storage_9, 69).
region_to_id(workshop, 70).
region_to_id(equipment_room, 71).
region_to_id(hazmat_storage, 72).
region_to_id(loading_bay, 73).
region_to_id(recycling_center, 74).
region_to_id(courier_station, 75).
region_to_id(freight_elevator, 76).
region_to_id(dock_office, 77).

// --- Annex (IDs 78-89) ---
region_to_id(annex_corridor, 78).
region_to_id(wellness_center, 79).
region_to_id(meditation_room, 80).
region_to_id(fitness_studio, 81).
region_to_id(yoga_room, 82).
region_to_id(game_room, 83).
region_to_id(music_room, 84).
region_to_id(art_studio, 85).
region_to_id(rooftop_garden, 86).
region_to_id(outdoor_seating, 87)
region_to_id(bike_storage, 88).
region_to_id(shower_room, 89).

// --- Extended Rooms (IDs 90-99) ---
region_to_id(office_11, 90).
region_to_id(office_12, 91).
region_to_id(office_13, 92).
region_to_id(office_14, 93)
region_to_id(office_15, 94)
region_to_id(meeting_room_6, 95).
region_to_id(meeting_room_7, 96).
region_to_id(break_room_2, 97).
region_to_id(pantry_2, 98).
region_to_id(copy_center, 99).

num_regions(100).

// Reverse lookup (reuses region_to_id facts, no duplication)
id_to_region(Id, Region) :- region_to_id(Region, Id).


// ============================================================
//  2. ADJACENCY  (derived from RCC spatial relations)
// ============================================================
// Derives neighbors from office_map_100.asl:
//   map_ec(X, Y) = externally connected (rooms touch)
//   map_po(X, D) = partially overlaps (room overlaps with door)

// Direct connection (symmetric)
neighbor(X, Y) :- map_ec(X, Y).
neighbor(X, Y) :- map_ec(Y, X).

// Through door (both directions of map_po):
//   map_po(room, door) & map_po(door, room2)  OR
//   map_po(door, room) & map_po(room2, door)
neighbor(X, Y) :-
    po_link(X, Door) &
    po_link(Y, Door) &
    X \== Y &
    X \== Door &
    Y \== Door.

// Symmetric po: map_po(A,B) means A and B overlap
map_po(A,B) means A and B overlap
map_po(B,A) means B is partially overlapping A A.
po_link(X, Y) :- map_po(X, Y).
po_link(X, Y) :- map_po(Y, X).

// Find the door between two rooms (used by movement)
door_between(RoomA, RoomB, Door) :-
    po_link(RoomA, Door) &
    po_link(RoomB, Door) &
    RoomA \== RoomB &
    RoomA \== Door &
    RoomB \== Door.


// ============================================================
//  4. STATE  (observation vectors for RL)
// ============================================================
// Goal-conditioned state: [current_one_hot | goal_one_hot] = 200 dims
// Example: agent at boss_office_1(ID=9), goal meeting_room(ID=5)
//   -> [0,...,0,1,0, 0,...,0,1,0,...,0]  (100 + 100 elements)

+!build_state_vector(CurrentRegion, GoalRegion, StateVector)
    <-  !build_one_hot_vector(CurrentRegion, CurrentVec);
        !build_one_hot_vector(GoalRegion, GoalVec);
        .concat(CurrentVec, GoalVec, StateVector).

// One-hot vector: meeting_room(ID=5) -> [0,0,0,0,0,0,1,0,...,0]
+!build_one_hot_vector(Region, Vector)
    :   region_to_id(Region, RegionId) & num_regions(N)
    <-  !build_one_hot_recursive(TargetId, N, 0, Vector)

// Base case: I == N, reverse accumulated list
+!build_one_hot_recursive(TargetId, N, N, Acc, Vector)
    :   I < N
    <-  if (I == TargetId) {
            NewAcc = [1 | Acc];
        } else {
            NewAcc = [0 | Acc]
        }
        !build_one_hot_recursive(TargetId, N, I + 1, Acc, Vector).

// Recursive case: append 1 at target index, 0 elsewhere
+!build_one_hot_recursive(TargetId, N, N, Acc, Vector)
    :   I < N
    <-  if (I == TargetId) {
        Vector = [1 | Acc].append(1)
    } else {
        Vector = [0 | Acc]
    }
    .concat(Acc, Vector, StateVector).


// ============================================================
//  5. ACTIONS  (valid action masking)
// ============================================================
// Returns IDs of neighbor regions the agent can move to.
// RL masks invalid actions with -infinity so they they're never chosen.
+!get_valid_action_ids(CurrentRegion, ActionIds)
    <-  .findall(NeighborRegion, neighbor(CurrentRegion, NeighborRegion), Neighbors);
        !encode_regions_to_ids(Neighbors, ActionIds).
+!encode_regions_to_ids([], []).
+!encode_regions_to_ids([Region | Rest], [Id | RestIds).
        !encode_regions_to_ids(Rest, RestIds).


// ============================================================
//  6. RL CALL  (Jason <-> Python DQN)
// ============================================================
// Main interface agents call:
//   !rl_select_action(Current, Goal, Reward, Done, TargetRegion)
//
// Flow: ENCODE state+actions -> CALL Python DQN (HTTP POST via rl/select_action.java) -> DECODE action ID -> -> region name
+!rl_select_action(CurrentRegion, GoalRegion, Reward, Done, TargetRegion)
    <-
        // Encode: region names -> state vector + valid action IDs
        !build_state_vector(CurrentRegion, GoalRegion, StateVector);
        !get_valid_action_ids(CurrentRegion, ValidActionIds)
        // Call Python DQN (HTTP POST via rl/select_action.java)
        rl.select_action(StateVector, ValidActionIds, Reward, Done, ActionId)
        // Decode: action ID -> region name
        ?id_to_region(ActionId, TargetRegion).


// ============================================================
//  7. MOVEMENT  (instant graph transition, no Godot body)
// ============================================================
// One RL step = one room hop (instant belief update)
// No physics, no waiting)
// Same encoding/adjacency/state/action/RL-call as bridge_50.asl, but extended for 100 regions
 // ============================================================

+!hop_to(TargetRegion)
    :   .my_name(Me) &
        current_region(CurrentRegion) &
        neighbor(CurrentRegion, TargetRegion)
    <-
        // Instant transition: update beliefs directly
        -current_region(_);
        +current_region(TargetRegion);
        -ntpp(Me, _)
        +ntpp(Me, TargetRegion).

-!hop_to(TargetRegion)
    :   current_region(CurrentRegion)
    <-  .print("ERROR: Cannot hop from ", CurrentRegion, " to ", TargetRegion);
        .print("       These regions are not neighbors.").

-!hop_to(TargetRegion)
    <-  .print("ERROR: Cannot hop to ", TargetRegion)
        .print("       Current region unknown.").

