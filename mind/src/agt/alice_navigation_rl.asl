
// Learns to find path from any start to any goal region (room).
// Graph-based training: no Godot body, instant transitions.
// Same reward logic and RL loop as alice_rl.asl.
// ============================================================

{ include("playgrounds/office/office_map.asl") }
{ include("navigation_rl_bridge.asl") }


//------------------------------CONFIGURATION-------------

max_steps(150).                 // max steps before timeout (diameter=7, 150 is plenty)
max_episodes(100000).           // 100K episodes for full convergence across all 2500 pairs
eval_mode(true).                // true = use trained policy, false = learning
save_interval(5000).            // auto-save checkpoint every 5K episodes

// All 50 navigable regions for randomized start/goal
all_regions([reception, corridor, open_office, outside, common,
             meeting_room, senior_office_1, senior_office_2,
             senior_office_3, boss_office_1, boss_office_2,
             corridor_north, corridor_south,
             kitchen, restroom_1, storage_1,
             meeting_room_2, meeting_room_3, lab_1, lab_2, server_room,
             office_1, office_2, office_3, office_4, office_5,
             lobby, cafeteria, gym, restroom_2,
             office_6, office_7, office_8, office_9, office_10,
             archive, training_room,
             terrace, parking, conference_room, security_desk,
             library, print_room, mail_room, executive_suite,
             phone_booth_1, phone_booth_2, supply_closet,
             lounge, wellness_room]).


//--------------------------------REWARD MACHINE-----------------
// Immediate rewards sent to Python RL.
// Python uses these in Bellman equation: Q = r + gamma * max(Q_next)

reward_goal(100.0).       // given when agent reaches goal_region
reward_step(-1.0).        // given each step (encourages short paths)
reward_timeout(-10.0).    // given when step >= max_steps


//---------------------------START AGENT------------------------------------
+!start
    :   eval_mode(EvalMode)
    <-
        if (EvalMode) {
            rl.load_model(true);
            .print("ALICE NAVIGATION RL - Mode: eval=true (inference, using checkpoint)");
        } else {
            .print("ALICE NAVIGATION RL - Mode: eval=false (training from scratch)");
        };

        !run_episodes.

// ============================================================
//                    RANDOMIZE START / GOAL
// ============================================================
// Picks a random start and goal region each episode.
// Ensures start != goal for meaningful episodes.

+!randomize_start_goal
    :   all_regions(Regions)
    <-
        rl.random_region(Regions, Start);
        rl.random_region(Regions, GoalCandidate);
        if (GoalCandidate == Start) {
            !randomize_start_goal;  // retry
        } else {
            -start_region(_);
            -goal_region(_);
            +start_region(Start);
            +goal_region(GoalCandidate);
        }.

// ============================================================
//                    GO TO START
// ============================================================
// Instant belief update (no Godot teleport, no waiting).

+!go_to_start
    :   .my_name(Me)
    <-
        ?start_region(Region);

        // Instant position reset via belief update
        -current_region(_);
        +current_region(Region);
        -ntpp(Me, _);
        +ntpp(Me, Region).


// ============================================================
//                    EPISODE MANAGEMENT
// ============================================================

+!run_episodes
    <-
        +episode(0);
        !run_episode.

+!run_episode
    :   episode(Ep)
    <-
        !randomize_start_goal;

        ?start_region(S);
        ?goal_region(G);
        .print("========== EPISODE ", Ep, " (", S, " -> ", G, ") ==========");

        +step(0);
        +episode_reward(0);
        !go_to_start;
        !rl_loop.              // start RL loop immediately (no perception delay)

// --- Training/Inference complete ---
+!end_episode
    :   episode(Ep) & max_episodes(MaxEp) & Ep + 1 >= MaxEp
    <-
        ?episode_reward(TotalReward);
        ?step(Steps);
        ?start_region(S);
        ?goal_region(G);
        ?eval_mode(EvalMode);

        if (TotalReward > 0) { Outcome = success } else { Outcome = timeout };
        rl.log_episode(Ep, S, G, Steps, TotalReward, Outcome);

        .print("Episode ", Ep, " total reward: ", TotalReward);
        .print("============================================");
        if (EvalMode) {
            .print("INFERENCE COMPLETE after ", Ep + 1, " episodes.");
        } else {
            .print("TRAINING COMPLETE after ", Ep + 1, " episodes!");
            .print("Saving final policy...");
            rl.save_model;
            .print("Policy saved to checkpoints/. Set eval_mode(true) to use it.");
        };
        .print("============================================").

// --- Normal end (continue to next episode) ---
+!end_episode
    :   episode(Ep) & episode_reward(TotalReward) & save_interval(SaveN)
    <-
        ?step(Steps);
        ?start_region(S);
        ?goal_region(G);

        if (TotalReward > 0) { Outcome = success } else { Outcome = timeout };
        rl.log_episode(Ep, S, G, Steps, TotalReward, Outcome);

        .print("Episode ", Ep, " total reward: ", TotalReward);

        // Auto-save every save_interval episodes
        if ((Ep + 1) mod SaveN == 0) {
            .print("Auto-saving checkpoint at episode ", Ep + 1, "...");
            rl.save_model;
        };

        // Clean up beliefs from this episode
        -episode(_);
        -step(_);
        -episode_reward(_);

        // Start new episode in a NEW intention (!! instead of !)
        // This frees the old intention stack and prevents memory buildup.
        +episode(Ep + 1);
        .wait(10);
        !!run_episode.


//-------------------------RL LOOP----------------------------------

// --- CASE 0: Wait for perception (should not happen in graph mode) ---
+!rl_loop
    :   not current_region(_)
    <-  .print("WARNING: current_region not set, retrying...");
        .wait(10);
        !rl_loop.

// --- CASE 1: Goal Reached ---
+!rl_loop
    :   current_region(Region) & goal_region(Region)
    <-
        ?step(S);
        ?reward_goal(R);
        ?episode_reward(ER);

        .print("*** GOAL REACHED in ", S, " steps! ***");

        !rl_select_action(Region, Region, R, true, _);

        -episode_reward(_);
        +episode_reward(ER + R);

        !end_episode.

// --- CASE 2: Timeout ---
+!rl_loop
    :   step(S) & max_steps(MaxS) & S >= MaxS
    <-
        ?current_region(Region);
        ?goal_region(Goal);
        ?reward_timeout(R);
        ?episode_reward(ER);

        .print("*** TIMEOUT at step ", S, " ***");

        !rl_select_action(Region, Goal, R, true, _);

        -episode_reward(_);
        +episode_reward(ER + R);

        !end_episode.

// --- CASE 3: Normal Step ---
+!rl_loop
    :   current_region(Region) & step(S)
    <-
        ?goal_region(Goal);
        ?reward_step(R);
        ?episode_reward(ER);

        .print("Step ", S, ": at ", Region, " -> goal: ", Goal);

        !rl_select_action(Region, Goal, R, false, TargetRegion);

        .print("  -> RL selected: ", TargetRegion);

        !hop_to(TargetRegion);

        -step(_);
        +step(S + 1);

        -episode_reward(_);
        +episode_reward(ER + R);

        // Use !! to start a new intention (prevents stack buildup over 100 steps)
        !!rl_loop.
