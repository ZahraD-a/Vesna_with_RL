// ============================================================
//              SYMBOLIC EXECUTION ENGINE
// ============================================================
// Shared RL infrastructure for all learning agents.
//
// This engine handles:
//   - Region ID encoding (domain knowledge)
//   - State vector building (one-hot observation)
//   - Valid action computation from RCC adjacency
//   - Reward computation (reward machine)
//   - RL service communication
//
// Architecture:
//   Jason (this engine) KNOWS the map and computes rewards.
//   Python RL service LEARNS the policy, knows nothing about domain.
//
// Agents include this file and define their own goals/starting positions.

// ============================================================
//              REGION ID ENCODING (Domain Knowledge)
// ============================================================
// Maps region names to integer IDs for the RL service.
// This is the ONLY place where this mapping is defined.

region_id(reception,       0).
region_id(corridor,        1).
region_id(open_office,     2).
region_id(outside,         3).
region_id(common,          4).
region_id(meeting_room,    5).
region_id(senior_office_1, 6).
region_id(senior_office_2, 7).
region_id(senior_office_3, 8).
region_id(boss_office_1,   9).
region_id(boss_office_2,  10).

num_regions(11).

// Reverse lookup: ID -> Region
id_to_region(Id, Region) :- region_id(Region, Id).

// ============================================================
//              ADJACENCY (Door-Collapsed from RCC)
// ============================================================
// Derived from office_map.asl RCC relations:
//   ec(X, Y) -> neighbor
//   po(X, Door) & po(Door, Y) -> neighbor (through door)

neighbor(reception, corridor).
neighbor(corridor, reception).

neighbor(corridor, open_office).
neighbor(open_office, corridor).

neighbor(corridor, common).
neighbor(common, corridor).

neighbor(corridor, meeting_room).
neighbor(meeting_room, corridor).

neighbor(corridor, senior_office_1).
neighbor(senior_office_1, corridor).

neighbor(corridor, senior_office_2).
neighbor(senior_office_2, corridor).

neighbor(corridor, senior_office_3).
neighbor(senior_office_3, corridor).

neighbor(open_office, boss_office_1).
neighbor(boss_office_1, open_office).

neighbor(open_office, boss_office_2).
neighbor(boss_office_2, open_office).

neighbor(open_office, outside).
neighbor(outside, open_office).

// ============================================================
//              STATE VECTOR BUILDING
// ============================================================
// Build one-hot observation vector o_t from current region

+!build_state_vector(Region, StateVector)
    :   region_id(Region, RegionId) & num_regions(N)
    <-  !build_one_hot(RegionId, N, 0, [], StateVector).

// Goal-conditioned state: [current_one_hot(11) | goal_one_hot(11)] = 22-dim
+!build_goal_state_vector(CurrentRegion, GoalRegion, StateVector)
    :   region_id(CurrentRegion, CurrentId) & region_id(GoalRegion, GoalId) & num_regions(N)
    <-  !build_one_hot(CurrentId, N, 0, [], CurrentVec);
        !build_one_hot(GoalId, N, 0, [], GoalVec);
        .concat(CurrentVec, GoalVec, StateVector).

+!build_one_hot(TargetId, N, N, Acc, StateVector)
    <-  .reverse(Acc, StateVector).

+!build_one_hot(TargetId, N, I, Acc, StateVector)
    :   I < N
    <-  if (I == TargetId) {
            NewAcc = [1 | Acc];
        } else {
            NewAcc = [0 | Acc];
        }
        !build_one_hot(TargetId, N, I + 1, NewAcc, StateVector).

// ============================================================
//              VALID ACTION COMPUTATION
// ============================================================
// Get valid action IDs A(o_t) from RCC adjacency

+!get_valid_action_ids(Region, ActionIds)
    <-  .findall(N, neighbor(Region, N), Neighbors);
        !regions_to_ids(Neighbors, ActionIds).

+!regions_to_ids([], []).
+!regions_to_ids([R | Rs], [Id | Ids])
    :   region_id(R, Id)
    <-  !regions_to_ids(Rs, Ids).

// ============================================================
//              RL SERVICE WRAPPER
// ============================================================
// High-level wrapper that handles encoding/decoding
// Calls: rl.select_action(StateVector, ValidActionIds, Reward, Done, ActionId)

+!rl_select_action(CurrentRegion, GoalRegion, Reward, Done, TargetRegion)
    <-  // Build goal-conditioned observation o_t (22-dim: current | goal)
        !build_goal_state_vector(CurrentRegion, GoalRegion, StateVector);
        // Compute valid actions A(o_t) from adjacency
        !get_valid_action_ids(CurrentRegion, ValidActionIds);
        // Call RL service (domain-agnostic HTTP client)
        rl.select_action(StateVector, ValidActionIds, Reward, Done, ActionId);
        // Convert action ID back to region name
        ?id_to_region(ActionId, TargetRegion).

// ============================================================
//              EMBODIED SPATIAL PERCEPTION
// ============================================================
// When the body enters a region, Godot sends a region_entered signal.
// This trigger updates beliefs automatically — the body informs the mind.

+region_entered(Region, _)
    :   .my_name(Me)
    <-  -current_region(_);
        +current_region(Region);
        -ntpp(Me, _);
        +ntpp(Me, Region).

// ============================================================
//              SINGLE ROOM HOP (One RL step = one hop)
// ============================================================
// Execute exactly one room transition (via door if needed)
// Beliefs are updated automatically by +region_entered perception.

+!hop_to(TargetRegion)
    :   .my_name(Me) & current_region(CurrentRegion) & neighbor(CurrentRegion, TargetRegion)
    <-  // Find if there's a door between regions
        if (po(CurrentRegion, Door) & po(Door, TargetRegion)) {
            // Go through door
            vesna.walk(Door);
            .wait({+movement(completed, destination_reached)});
            vesna.walk(TargetRegion);
            .wait({+movement(completed, destination_reached)});
        } else {
            // Direct connection (ec)
            vesna.walk(TargetRegion);
            .wait({+movement(completed, destination_reached)});
        }
        // Update beliefs (fallback — +region_entered may also fire from body)
        -current_region(_);
        +current_region(TargetRegion);
        -ntpp(Me, _);
        +ntpp(Me, TargetRegion).

-!hop_to(TargetRegion)
    <-  .print("ERROR: Cannot hop to ", TargetRegion).
