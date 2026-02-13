// ============================================================
//                       RL BRIDGE
// ============================================================
// Bridge between Jason (symbolic) and Python RL (numerical).
//
// Jason KNOWS the map  -> region names, spatial relations
// Python LEARNS policy -> integer IDs, float vectors
// This bridge TRANSLATES between them.
//
// Sections:
//   1. ENCODING    - region name <-> integer ID
//   2. ADJACENCY   - neighbor rules from RCC spatial relations
//   3. STATE       - one-hot observation vectors for RL
//   4. ACTIONS     - valid action masking
//   5. RL CALL     - communicate with Python DQN service
//   6. PERCEPTION  - handle Godot body signals
//   7. MOVEMENT    - control body navigation
// ============================================================


// ============================================================
//  1. ENCODING  (Jason <-> Python)
// ============================================================
//   Encode: ?region_to_id(meeting_room, Id)  -> Id = 5
//   Decode: ?id_to_region(5, Region)         -> Region = meeting_room

region_to_id(reception,       0).
region_to_id(corridor,        1).
region_to_id(open_office,     2).
region_to_id(outside,         3).
region_to_id(common,          4).
region_to_id(meeting_room,    5).
region_to_id(senior_office_1, 6).
region_to_id(senior_office_2, 7).
region_to_id(senior_office_3, 8).
region_to_id(boss_office_1,   9).
region_to_id(boss_office_2,  10).

num_regions(11).

// ---------------DECODER ------------------is reverse lookup of encoder
// Reverse lookup (reuses region_to_id facts, no duplication) 
id_to_region(Id, Region) :- region_to_id(Region, Id).


// ============================================================
//  2. ADJACENCY  (derived from RCC spatial relations)
// ============================================================
// Derives neighbors from office_map.asl:
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
//  3. STATE  (observation vectors for RL)
// ============================================================
// Goal-conditioned state: [current_one_hot | goal_one_hot] = 22 dims
// Example: agent at boss_office_1(9), goal meeting_room(5)
//   -> [0,0,0,0,0,0,0,0,0,1,0, 0,0,0,0,0,1,0,0,0,0,0]

+!build_state_vector(CurrentRegion, GoalRegion, StateVector)
    <-  !build_one_hot_vector(CurrentRegion, CurrentVec);
        !build_one_hot_vector(GoalRegion, GoalVec);
        .concat(CurrentVec, GoalVec, StateVector).

// One-hot vector: meeting_room(ID=5) -> [0,0,0,0,0,1,0,0,0,0,0]
+!build_one_hot_vector(Region, Vector)
    :   region_to_id(Region, RegionId) & num_regions(N)
    <-  !build_one_hot_recursive(RegionId, N, 0, [], Vector).

// Base case: I == N, reverse accumulated list
+!build_one_hot_recursive(TargetId, N, N, Acc, Vector)
    <-  .reverse(Acc, Vector).

// Recursive case: append 1 at target index, 0 elsewhere
+!build_one_hot_recursive(TargetId, N, I, Acc, Vector)
    :   I < N
    <-  if (I == TargetId) {
            NewAcc = [1 | Acc];
        } else {
            NewAcc = [0 | Acc];
        }
        !build_one_hot_recursive(TargetId, N, I + 1, NewAcc, Vector).


// ============================================================
//  4. ACTIONS  (valid action masking)
// ============================================================
// Returns IDs of neighbor regions the agent can move to.
// RL masks invalid actions with -infinity so they're never chosen.

+!get_valid_action_ids(CurrentRegion, ActionIds)
    <-  .findall(NeighborRegion, neighbor(CurrentRegion, NeighborRegion), Neighbors);
        !encode_regions_to_ids(Neighbors, ActionIds).

+!encode_regions_to_ids([], []).
+!encode_regions_to_ids([Region | Rest], [Id | RestIds])
    :   region_to_id(Region, Id)
    <-  !encode_regions_to_ids(Rest, RestIds).


// ============================================================
//  5. RL CALL  (Jason <-> Python DQN)
// ============================================================
// Main interface agents call:
//   !rl_select_action(Current, Goal, Reward, Done, NextRegion)
//
// Flow: ENCODE state+actions -> CALL Python -> DECODE action ID

+!rl_select_action(CurrentRegion, GoalRegion, Reward, Done, TargetRegion)
    <-
        // Encode: region names -> state vector + valid action IDs
        !build_state_vector(CurrentRegion, GoalRegion, StateVector);
        !get_valid_action_ids(CurrentRegion, ValidActionIds);

        // Call Python DQN (HTTP POST via rl/select_action.java)
        rl.select_action(StateVector, ValidActionIds, Reward, Done, ActionId);

        // Decode: action ID -> region name
        ?id_to_region(ActionId, TargetRegion).


// ============================================================
//  6. PERCEPTION  (Godot body signals)
// ============================================================
// Auto-triggered when body enters a region (from Godot WebSocket).
// Updates current_region and ntpp beliefs.

+region_entered(Region, _)
    :   .my_name(Me)
    <-
        -current_region(_);
        -ntpp(Me, _);
        +current_region(Region);
        +ntpp(Me, Region).


// ============================================================
//  7. MOVEMENT  (body navigation)
// ============================================================
// One RL step = one room hop.
// Through door: walk to door -> wait -> walk to room -> wait
// Direct (ec):  walk to room -> wait

+!hop_to(TargetRegion)
    :   .my_name(Me) &
        current_region(CurrentRegion) &
        neighbor(CurrentRegion, TargetRegion)
    <-
        if (door_between(CurrentRegion, TargetRegion, Door)) {
            -movement(_, _);     // clear stale signal
            vesna.walk(Door);
            .wait({+movement(completed, destination_reached)});
            -movement(_, _);     // clear before next walk
            vesna.walk(TargetRegion);
            .wait({+movement(completed, destination_reached)});
        } else {
            -movement(_, _);     // clear stale signal
            vesna.walk(TargetRegion);
            .wait({+movement(completed, destination_reached)});
        }

        -current_region(_);
        +current_region(TargetRegion);
        -ntpp(Me, _);
        +ntpp(Me, TargetRegion).

-!hop_to(TargetRegion)
    :   current_region(CurrentRegion)
    <-  .print("ERROR: Cannot hop from ", CurrentRegion, " to ", TargetRegion);
        .print("       These regions are not neighbors.").

-!hop_to(TargetRegion)
    <-  .print("ERROR: Cannot hop to ", TargetRegion);
        .print("       Current region unknown.").
