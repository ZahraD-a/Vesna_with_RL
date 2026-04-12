// 50-region graph-based RL navigation agent.
// Checkpoint: checkpoints/alice50.pt
// Config: vesna_navigation_rl_50.jcm (agent "alice50")
// Training: start_navigation_training.sh --medium
// Bridge: bridge_50.asl (encoding, adjacency, RL call)
// ============================================================

{ include("playgrounds/office/office_map_50.asl") }
{ include("bridge_50.asl") }


//------------------------------CONFIGURATION (50 regions)-------------

max_steps(150).                 // max steps before timeout
max_episodes(100000).           // 100K episodes
eval_mode(true).                // true = use trained policy, false = learning
save_interval(5000).            // auto-save checkpoint every 5K episodes

// All 50 navigable regions
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

reward_goal(100.0).
reward_step(-1.0).
reward_timeout(-10.0).


//---------------------------START AGENT------------------------------------

+!start
    :   eval_mode(EvalMode)
    <-

        if (EvalMode) {
            rl.load_model(true);
            .print("ALICE NAVIGATION RL 50 - Mode: eval=true (inference)");
        } else {
            .print("ALICE NAVIGATION RL 50 - Mode: eval=false (training)");
        };

        !run_episodes.


// ============================================================
//                    RANDOMIZE START / GOAL
// ============================================================

+!randomize_start_goal
    :   all_regions(Regions)
    <-
        rl.random_region(Regions, Start);
        rl.random_region(Regions, GoalCandidate);
        if (GoalCandidate == Start) {
            !randomize_start_goal;
        } else {
            -start_region(_);
            -goal_region(_);
            +start_region(Start);
            +goal_region(GoalCandidate);
        }.


// ============================================================
//                    GO TO START
// ============================================================

+!go_to_start
    :   .my_name(Me)
    <-
        ?start_region(Region);
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
        !rl_loop.


// --- Training complete ---
+!end_episode(Outcome)
    :   episode(Ep) & max_episodes(MaxEp) & Ep + 1 >= MaxEp
    <-
        ?episode_reward(TotalReward);
        ?step(Steps);
        ?start_region(S);
        ?goal_region(G);
        ?eval_mode(EvalMode);

        rl.log_episode(Ep, S, G, Steps, TotalReward, Outcome);

        .print("Episode ", Ep, " total reward: ", TotalReward, " (", Outcome, ")");
        .print("============================================");
        if (EvalMode) {
            .print("INFERENCE COMPLETE after ", Ep + 1, " episodes.");
        } else {
            .print("TRAINING COMPLETE after ", Ep + 1, " episodes!");
            rl.save_model;
            .print("Policy saved. Set eval_mode(true) to use it.");
        };
        .print("============================================").


// --- Normal end (continue) ---
+!end_episode(Outcome)
    :   episode(Ep) & episode_reward(TotalReward) & save_interval(SaveN)
    <-
        ?step(Steps);
        ?start_region(S);
        ?goal_region(G);

        rl.log_episode(Ep, S, G, Steps, TotalReward, Outcome);

        .print("Episode ", Ep, " total reward: ", TotalReward, " (", Outcome, ")");

        if ((Ep + 1) mod SaveN == 0) {
            .print("Auto-saving checkpoint at episode ", Ep + 1, "...");
            rl.save_model;
        };

        -episode(_);
        -step(_);
        -episode_reward(_);
        +episode(Ep + 1);
        .wait(10);
        !!run_episode.


//-------------------------RL LOOP----------------------------------

// --- Wait for perception ---
+!rl_loop
    :   not current_region(_)
    <-  .print("WARNING: current_region not set");
        .wait(10);
        !rl_loop.

// --- Goal Reached ---
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

        !end_episode(success).

// --- Timeout ---
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

        !end_episode(timeout).

// --- Normal Step ---
+!rl_loop
    :   current_region(Region) & step(S)
    <-
        ?goal_region(Goal);
        ?reward_step(R);
        ?episode_reward(ER);

        !rl_select_action(Region, Goal, R, false, TargetRegion);

        !hop_to(TargetRegion);

        -step(_);
        +step(S + 1);

        -episode_reward(_);
        +episode_reward(ER + R);

        !rl_loop.
