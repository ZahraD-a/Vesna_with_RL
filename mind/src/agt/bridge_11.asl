// ============================================================
//  BRIDGE 11 — encoding, adjacency, state, actions, RL call
//  For: navigation_rl_11.asl (11 regions)
//  Checkpoint: alice11.pt
//  Java action: rl.select_action_11 (select_action_11.java)
// ============================================================


// ============================================================
//  1. ENCODING — 11 original rooms (IDs 0-10)
// ============================================================

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

num_regions(11).

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
//  3. STATE — one-hot observation vectors (22 dims: 11+11)
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
        rl.select_action_11(StateVector, ValidActionIds, Reward, Done, ActionId);
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
