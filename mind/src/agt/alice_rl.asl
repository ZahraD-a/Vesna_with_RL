{ include("vesna.asl") }
{ include("playgrounds/office/office_map.asl") }
{ include("symbolic_execution_engine.asl") }

// ============================================================
//                    ALICE RL - Learning Agent
// ============================================================
// Agent-specific configuration for Alice.
// All RL infrastructure is in symbolic_execution_engine.asl

// ============================================================
//              AGENT-SPECIFIC CONFIGURATION
// ============================================================
goal_region(meeting_room).
start_position(110.3, 4.2, -20.0).
max_steps(50).

// ============================================================
//                    AGENT START
// ============================================================
+!start
    :   goal_region(GoalRegion)
    <-  // Teleport body to start position (coordinates)
        ?start_position(X, Y, Z);
        vesna.teleport(X, Y, Z);
        .wait({+movement(completed, destination_reached)});
        // Beliefs auto-set by +region_entered perception from body
        ?current_region(ActualRegion);
        .print("");
        .print("============================================");
        .print("ALICE RL - Learning Agent Started");
        .print("Location: ", ActualRegion);
        .print("Goal: Reach ", GoalRegion);
        .print("============================================");
        .print("");
        !run_episodes.

// ============================================================
//                    EPISODE LOOP
// ============================================================
+!run_episodes
    <-  +episode(0);
        !run_episode.

+!run_episode
    :   episode(Ep)
    <-  .print("");
        .print("========== EPISODE ", Ep, " ==========");
        +step(0);
        +episode_reward(0);
        // Reset to start position
        !reset_position;
        // Run the episode
        !rl_loop.

+!reset_position
    <-  ?start_position(X, Y, Z);
        vesna.teleport(X, Y, Z);
        .wait({+movement(completed, destination_reached)}).
        // Beliefs auto-set by +region_entered perception from body

// ============================================================
//                    RL TRAINING LOOP
// ============================================================
+!rl_loop
    :   current_region(Region) & goal_region(Region)
    <-  // Goal reached!
        ?step(S);
        ?episode(Ep);
        .print("*** GOAL REACHED in ", S, " steps! ***");
        // Final call to RL service with done=true and reward=+100
        !rl_select_action(Region, Region, 100.0, true, _);
        // Update stats
        ?episode_reward(ER);
        NewER = ER + 100;
        -episode_reward(_);
        +episode_reward(NewER);
        .print("Episode ", Ep, " total reward: ", NewER);
        // Next episode
        !next_episode.

+!rl_loop
    :   step(S) & max_steps(MaxS) & S >= MaxS
    <-  // Timeout
        ?episode(Ep);
        ?current_region(Region);
        ?goal_region(GoalRegion);
        .print("*** TIMEOUT at step ", S, " ***");
        // Final call with done=true and timeout penalty
        !rl_select_action(Region, GoalRegion, -10.0, true, _);
        ?episode_reward(ER);
        NewER = ER - 10;
        -episode_reward(_);
        +episode_reward(NewER);
        .print("Episode ", Ep, " total reward: ", NewER);
        !next_episode.

+!rl_loop
    :   current_region(Region) & step(S)
    <-  // Normal step
        ?goal_region(GoalRegion);
        .print("Step ", S, ": at ", Region, " (goal: ", GoalRegion, ")");
        // Get action from RL service (reward = -1 per step)
        !rl_select_action(Region, GoalRegion, -1.0, false, TargetRegion);
        .print("  -> RL selected: ", TargetRegion);
        // Execute single room hop
        !hop_to(TargetRegion);
        // Update step counter
        -step(_);
        +step(S + 1);
        ?episode_reward(ER);
        -episode_reward(_);
        +episode_reward(ER - 1);
        // Continue loop
        !rl_loop.

// ============================================================
//                    EPISODE MANAGEMENT
// ============================================================
+!next_episode
    :   episode(Ep)
    <-  NewEp = Ep + 1;
        -episode(_);
        +episode(NewEp);
        -step(_);
        -episode_reward(_);
        .wait(1000);
        !run_episode.

// Note: outside-cartago.asl and outside-moise.asl are already included via vesna.asl
