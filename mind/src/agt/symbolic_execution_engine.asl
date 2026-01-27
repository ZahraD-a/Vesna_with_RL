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
//              GOAL-CONDITIONED STATE VECTOR
// ============================================================
// Build combined state: [current_one_hot | goal_one_hot] = 22 dims
// This enables the agent to learn general navigation (any start -> any goal)

+!build_goal_conditioned_state(CurrentRegion, GoalRegion, StateVector)
    <-  !build_state_vector(CurrentRegion, CurrentVec);
        !build_state_vector(GoalRegion, GoalVec);
        .concat(CurrentVec, GoalVec, StateVector).

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

// Goal-conditioned version: state includes both current position and goal
+!rl_select_action(CurrentRegion, GoalRegion, Reward, Done, TargetRegion)
    <-  // Build goal-conditioned state [current_one_hot | goal_one_hot] = 22 dims
        !build_goal_conditioned_state(CurrentRegion, GoalRegion, StateVector);
        // Compute valid actions A(o_t) from adjacency
        !get_valid_action_ids(CurrentRegion, ValidActionIds);
        // Call RL service (domain-agnostic HTTP client)
        rl.select_action(StateVector, ValidActionIds, Reward, Done, ActionId);
        // Convert action ID back to region name
        ?id_to_region(ActionId, TargetRegion).

// ============================================================
//              SINGLE ROOM HOP (One RL step = one hop)
// ============================================================
// Execute exactly one room transition (via door if needed)

// Training mode: use vesna.run with timeout to catch permanently stuck agents.
// Clear stale movement beliefs before each wait to prevent signal race conditions.
// Godot-side cooldown (_walk_cooldown) prevents premature signaling.
+!hop_to(TargetRegion)
    :   .my_name(Me) & current_region(CurrentRegion) & neighbor(CurrentRegion, TargetRegion) & training_mode(true)
    <-  if (po(CurrentRegion, Door) & po(Door, TargetRegion)) {
            -movement(_, _);
            vesna.run(Door);
            .wait({+movement(completed, destination_reached)}, 30000);
            -movement(_, _);
            vesna.run(TargetRegion);
            .wait({+movement(completed, destination_reached)}, 30000);
        } else {
            -movement(_, _);
            vesna.run(TargetRegion);
            .wait({+movement(completed, destination_reached)}, 30000);
        }
        -movement(_, _);
        -current_region(_);
        +current_region(TargetRegion);
        -ntpp(Me, _);
        +ntpp(Me, TargetRegion).

// Inference mode: use vesna.walk (normal speed)
+!hop_to(TargetRegion)
    :   .my_name(Me) & current_region(CurrentRegion) & neighbor(CurrentRegion, TargetRegion)
    <-  if (po(CurrentRegion, Door) & po(Door, TargetRegion)) {
            vesna.walk(Door);
            .wait({+movement(completed, destination_reached)});
            vesna.walk(TargetRegion);
            .wait({+movement(completed, destination_reached)});
        } else {
            vesna.walk(TargetRegion);
            .wait({+movement(completed, destination_reached)});
        }
        -current_region(_);
        +current_region(TargetRegion);
        -ntpp(Me, _);
        +ntpp(Me, TargetRegion).

-!hop_to(TargetRegion)
    <-  .print("ERROR: Cannot hop to ", TargetRegion).
