// ============================================================
//                  NAVIGATION RL BRIDGE
// ============================================================
// Bridge between Jason (symbolic) and Python RL (numerical).
// Graph-based: instant transitions, no Godot body required.
//
// Same encoding/adjacency/state/action/RL-call as rl_bridge.asl,
// but movement is instant belief update (no physics, no waiting).
//
// Sections:
//   1. ENCODING    - region name <-> integer ID
//   2. ADJACENCY   - neighbor rules from RCC spatial relations
//   3. STATE       - one-hot observation vectors for RL
//   4. ACTIONS     - valid action masking
//   5. RL CALL     - communicate with Python DQN service
//   6. MOVEMENT    - instant graph transition (no Godot body)
// ============================================================


// ============================================================
//  1. ENCODING  (Jason <-> Python)
// ============================================================
//   Encode: ?region_to_id(meeting_room, Id)  -> Id = 5
//   Decode: ?id_to_region(5, Region)         -> Region = meeting_room

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

// --- New hub corridors (IDs 11-12) ---
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

// --- Rooms off lobby (IDs 37-39) ---
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
// Goal-conditioned state: [current_one_hot | goal_one_hot] = 100 dims
// Example: agent at boss_office_1(9), goal meeting_room(5)
//   -> [0,...,0,1,0, 0,...,0,1,0,...,0]  (50 + 50 = 100 elements)

+!build_state_vector(CurrentRegion, GoalRegion, StateVector)
    <-  !build_one_hot_vector(CurrentRegion, CurrentVec);
        !build_one_hot_vector(GoalRegion, GoalVec);
        .concat(CurrentVec, GoalVec, StateVector).

// One-hot vector: meeting_room(ID=5) -> [0,0,0,0,0,1,0,...,0]
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
//  6. MOVEMENT  (instant graph transition, no Godot body)
// ============================================================
// One RL step = one room hop (instant belief update).
// No vesna.walk(), no .wait() -- pure graph traversal.

+!hop_to(TargetRegion)
    :   .my_name(Me) &
        current_region(CurrentRegion) &
        neighbor(CurrentRegion, TargetRegion)
    <-
        // Instant transition: update beliefs directly
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
