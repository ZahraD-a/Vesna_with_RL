
// Learns to find path from any start to any goal region
// Graph-based training: no Godot body, instant transitions
// 100-region version
// ============================================================

{ include("playgrounds/office/office_map_100.asl") }
{ include("bridge_100.asl") }


//------------------------------CONFIGURATION (100 regions)-------------

max_steps(200).                 // max steps before timeout (reduced for faster episodes)
max_episodes(100000).           // 100K episodes for comprehensive training
eval_mode(false).               // false = train from scratch
save_interval(10000).           // auto-save every 10K episodes (10 checkpoints)

// All 103 navigable regions
all_regions([corridor_north, office_1, office_2, office_3, office_4, office_5,
            meeting_room_2, meeting_room_3, lab_1, lab_2, server_room, mail_room, reception,
            corridor, open_office, boss_office_1, boss_office_2, print_room, outside,
            senior_office_1, senior_office_2, senior_office_3, meeting_room, restroom_1, storage_1,
            executive_suite, supply_closet, common, kitchen, library, phone_booth_1,
            corridor_south, office_6, office_7, office_8, office_9, office_10,
            cafeteria, gym, restroom_2, archive, training_room,
            terrace, lounge, wellness_room, phone_booth_2,
            lobby, security_desk, conference_room, parking,
            corridor_east, lab_3, lab_4, lab_5, lab_6,
            server_room_2, server_room_3, data_center, tech_office_1, tech_office_2,
            server_maintenance, network_room, backup_power, telecom_room,
            corridor_west, storage_2, storage_3, storage_4, storage_5, storage_6,
            workshop, equipment_room, hazmat_storage, loading_bay,
            recycling_center, courier_station, freight_elevator, dock_office,
            annex_corridor, wellness_center, meditation_room, fitness_studio, yoga_room,
            game_room, music_room, art_studio, rooftop_garden, outdoor_seating,
            bike_storage, shower_room,
            office_11, office_12, office_13, office_14, office_15,
            meeting_room_6, meeting_room_7, break_room_2, pantry_2,
            copy_center, scanner, server_room_4, server_room_5]).


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
            .print("ALICE NAVIGATION RL 100 - Mode: eval=true (inference)");
        } else {
            .print("ALICE NAVIGATION RL 100 - Mode: eval=false (training)");
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
            rl.save_model;
            .print("Policy saved. Set eval_mode(true) to use it.");
        };
        .print("============================================").


// --- Normal end (continue) ---
+!end_episode
    :   episode(Ep) & episode_reward(TotalReward) & save_interval(SaveN)
    <-
        ?step(Steps);
        ?start_region(S);
        ?goal_region(G);

        if (TotalReward > 0) { Outcome = success } else { Outcome = timeout };
        rl.log_episode(Ep, S, G, Steps, TotalReward, Outcome);

        .print("Episode ", Ep, " total reward: ", TotalReward);

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

        !end_episode.

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

        !end_episode.

// --- Normal Step ---
+!rl_loop
    :   current_region(Region) & step(S)
    <-
        ?goal_region(Goal);
        ?reward_step(R);
        ?episode_reward(ER);

        !rl_select_action(Region, Goal, R, false, TargetRegion);

        !move_to(TargetRegion);

        -step(_);
        +step(S + 1);

        -episode_reward(_);
        +episode_reward(ER + R);

        !rl_loop.
