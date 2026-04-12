// ============================================================
//  BRIDGE 50 — encoding, adjacency, state, actions, RL call
//  For: navigation_rl_50.asl (50 regions)
//  Checkpoint: alice50.pt
//  Java action: rl.select_action_50 (select_action_50.java)
// ============================================================


// ============================================================
//  1. ENCODING — 50 rooms (IDs 0-49)
// ============================================================

// --- Original 11 rooms (IDs 0-10) ---
region_to_id(reception,        0).
region_to_id(corridor,         1).
region_to_id(open_office,      2).
region_to_id(outside,          3).
region_to_id(common,           4).
region_to_id(meeting_room,     5).
region_to_id(senior_office_1,  6).
region_to_id(senior_office_2,  7).
region_to_id(senior_office_3,  8).
region_to_id(boss_office_1,    9).
region_to_id(boss_office_2,   10).

// --- Hub corridors (IDs 11-12) ---
region_to_id(corridor_north,  11).
region_to_id(corridor_south,  12).

// --- Rooms off corridor (IDs 13-15) ---
region_to_id(kitchen,         13).
region_to_id(restroom_1,      14).
region_to_id(storage_1,       15).

// --- Rooms off corridor_north (IDs 16-25) ---
region_to_id(meeting_room_2,  16).
region_to_id(meeting_room_3,  17).
region_to_id(lab_1,           18).
region_to_id(lab_2,           19).
region_to_id(server_room,     20).
region_to_id(office_1,        21).
region_to_id(office_2,        22).
region_to_id(office_3,        23).
region_to_id(office_4,        24).
region_to_id(office_5,        25).

// --- Rooms off corridor_south (IDs 26-36) ---
region_to_id(lobby,           26).
region_to_id(cafeteria,       27).
region_to_id(gym,             28).
region_to_id(restroom_2,      29).
region_to_id(office_6,        30).
region_to_id(office_7,        31).
region_to_id(office_8,        32).
region_to_id(office_9,        33).
region_to_id(office_10,       34).
region_to_id(archive,         35).
region_to_id(training_room,   36).

// --- Rooms off lobby (IDs 37-40) ---
region_to_id(terrace,         37).
region_to_id(parking,         38).
region_to_id(conference_room, 39).
region_to_id(security_desk,   40).

// --- Rooms off other rooms (IDs 41-49) ---
region_to_id(library,         41).
region_to_id(print_room,      42).
region_to_id(mail_room,       43).
region_to_id(executive_suite, 44).
region_to_id(phone_booth_1,   45).
region_to_id(phone_booth_2,   46).
region_to_id(supply_closet,   47).
region_to_id(lounge,          48).
region_to_id(wellness_room,   49).

num_regions(50).

id_to_region(Id, Region) :- region_to_id(Region, Id).


// ============================================================
//  2. ADJACENCY — neighbor rules from RCC spatial relations
// ============================================================

neighbor(X, Y) :- map_ec(X, Y).
neighbor(X, Y) :- map_ec(Y, X).

neighbor(X, Y) :-
    po_link(X, Door) &
    po_link(Y, Door) &
    X \== Y &
    X \== Door &
    Y \== Door.

po_link(X, Y) :- map_po(X, Y).
po_link(X, Y) :- map_po(Y, X).

door_between(RoomA, RoomB, Door) :-
    po_link(RoomA, Door) &
    po_link(RoomB, Door) &
    RoomA \== RoomB &
    RoomA \== Door &
    RoomB \== Door.


// ============================================================
//  3. STATE — one-hot observation vectors (100 dims: 50+50)
// ============================================================

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
//  4. ACTIONS — valid action masking
// ============================================================

+!get_valid_action_ids(CurrentRegion, ActionIds)
    <-  .findall(NeighborRegion, neighbor(CurrentRegion, NeighborRegion), Neighbors);
        !encode_regions_to_ids(Neighbors, ActionIds).

+!encode_regions_to_ids([], []).
+!encode_regions_to_ids([Region | Rest], [Id | RestIds])
    :   region_to_id(Region, Id)
    <-  !encode_regions_to_ids(Rest, RestIds).


// ============================================================
//  5. RL CALL — HTTP to Python DQN service
// ============================================================

+!rl_select_action(CurrentRegion, GoalRegion, Reward, Done, TargetRegion)
    <-  !build_state_vector(CurrentRegion, GoalRegion, StateVector);
        !get_valid_action_ids(CurrentRegion, ValidActionIds);
        rl.select_action_50(StateVector, ValidActionIds, Reward, Done, ActionId);
        ?id_to_region(ActionId, TargetRegion).


// ============================================================
//  6. MOVEMENT — instant graph transition
// ============================================================

+!hop_to(TargetRegion)
    :   .my_name(Me) &
        current_region(CurrentRegion) &
        neighbor(CurrentRegion, TargetRegion)
    <-
        -current_region(_);
        +current_region(TargetRegion);
        -ntpp(Me, _);
        +ntpp(Me, TargetRegion).

-!hop_to(TargetRegion)
    :   current_region(CurrentRegion)
    <-  .print("ERROR: Cannot hop from ", CurrentRegion, " to ", TargetRegion).

-!hop_to(TargetRegion)
    <-  .print("ERROR: Cannot hop to ", TargetRegion).
