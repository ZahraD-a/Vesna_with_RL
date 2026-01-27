{ include("vesna.asl") }
{ include("playgrounds/office/office_map.asl") }
{ include("symbolic_execution_engine.asl") }

// ============================================================
//                    ALICE RL - Learning Agent
// ============================================================
// Goal-Conditioned RL: Agent learns to navigate from ANY start to ANY goal.
// Each episode randomizes both start and goal positions.
// All RL infrastructure is in symbolic_execution_engine.asl

// ============================================================
//              AGENT-SPECIFIC CONFIGURATION
// ============================================================
// All navigable regions (for random start/goal selection)
possible_regions([reception, corridor, open_office, outside, common,
                  meeting_room, senior_office_1, senior_office_2,
                  senior_office_3, boss_office_1, boss_office_2]).

max_steps(50).
max_episodes(100).  // Set to 100 for testing, 5000 for full training

// Training mode: use vesna.run (2x speed) instead of vesna.walk
// Set to false for inference with normal walking speed
training_mode(true).

// ============================================================
//                    AGENT START
// ============================================================
+!start
    :   .my_name(Me)
    <-  .print("");
        .print("============================================");
        .print("ALICE RL - Goal-Conditioned Learning Agent");
        .print("Training: Random start -> Random goal");
        .print("============================================");
        .print("");
        !run_episodes.

// ============================================================
//              RANDOM START/GOAL SELECTION
// ============================================================
// Select random start and goal (ensuring they are different)
+!select_random_start_goal(Start, Goal)
    :   possible_regions(Regions)
    <-  .shuffle(Regions, Shuffled);
        .nth(0, Shuffled, Start);
        .nth(1, Shuffled, Goal).

// ============================================================
//                    EPISODE LOOP
// ============================================================
+!run_episodes
    <-  +episode(0);
        !run_episode.

+!run_episode
    :   episode(Ep) & .my_name(Me)
    <-  // Select random start and goal for this episode
        !select_random_start_goal(StartRegion, GoalRegion);
        // Log episode info
        .print("");
        .print("========== EPISODE ", Ep, " ==========");
        .print("Start: ", StartRegion, " -> Goal: ", GoalRegion);
        // Teleport agent to start position in Godot
        vesna.teleport(StartRegion);
        .wait({+teleport(completed, _)});
        .wait(500);  // Let physics settle after teleport
        // Update beliefs after teleport
        -current_region(_);
        +current_region(StartRegion);
        -goal_region(_);
        +goal_region(GoalRegion);
        -ntpp(Me, _);
        +ntpp(Me, StartRegion);
        +step(0);
        +episode_reward(0);
        // Run the episode
        !rl_loop.

// ============================================================
//                    RL TRAINING LOOP
// ============================================================
+!rl_loop
    :   current_region(Region) & goal_region(Region)
    <-  // Goal reached! (current == goal)
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
    :   step(S) & max_steps(MaxS) & S >= MaxS & current_region(Region) & goal_region(Goal)
    <-  // Timeout
        ?episode(Ep);
        .print("*** TIMEOUT at step ", S, " ***");
        // Final call with done=true and timeout penalty
        !rl_select_action(Region, Goal, -10.0, true, _);
        ?episode_reward(ER);
        NewER = ER - 10;
        -episode_reward(_);
        +episode_reward(NewER);
        .print("Episode ", Ep, " total reward: ", NewER);
        !next_episode.

+!rl_loop
    :   current_region(Region) & goal_region(Goal) & step(S) & episode_reward(ER)
    <-  .print("Step ", S, ": at ", Region, " (goal: ", Goal, ")");
        !rl_select_action(Region, Goal, -1.0, false, TargetRegion);
        .print("  -> RL selected: ", TargetRegion);
        !hop_to(TargetRegion);
        -step(_); +step(S + 1);
        -episode_reward(_); +episode_reward(ER - 1);
        !rl_loop.

// ============================================================
//                    EPISODE MANAGEMENT
// ============================================================
// Training complete - save and stop
+!next_episode
    :   episode(Ep) & max_episodes(Max) & Ep >= Max
    <-  .print("");
        .print("========================================");
        .print("TRAINING COMPLETE - ", Ep, " episodes");
        .print("Saving policy...");
        .print("========================================");
        rl.save;
        .print("Policy saved. Training finished.").

// Continue training
+!next_episode
    :   episode(Ep)
    <-  -episode(_); +episode(Ep + 1);
        -step(_); -episode_reward(_);
        .wait(500);
        !run_episode.
