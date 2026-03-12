// ============================================================
//                  NAVIGATION RL BRIDGE (100 regions)
// Graph-based: instant transitions, no Godot body, required.
//
// Same encoding/adjacency and state-building as original 50 regions.

 // ============================================================
// All 100 navigable regions for randomized start/goal
// // Ensures start != goal and well-defined episodes.

// ============================================================

+!start
 <-
        // Randomize start/goal
        rl.random_region(Regions, Start);
        rl.random_region(Regions, GoalCandidate);
        if (GoalCandidate == Start) {
            !randomize_start_goal;
 // Avoid infinite recursion

            start_region(Region);
            -start_region(_);
            +current_region(Region);
            +episode(0);
            -episode(0);
            -goal_region(Region)
            +goal_region(Region);
            +step(0);
            +episode_reward(0.0);
            !eval_mode(EvalMode) {
                rl.load_model(true);
                .print("ALICE NAVIGATION RL 100 - Mode: eval=true (inference, using checkpoint)");
            } else {
                .print("ALICE NAVIGATION RL 100 - Mode: eval=false (training from scratch)");
            }
        } !run_episodes.

        !episode(1)
            +episode(2)
            +episode(2)
            +episode(Ep + 1)
            +episode(Ep + 2) < MaxEpisodes {
                // Auto-save every save_interval episodes
                .print("Policy saved to checkpoints/. Set eval_mode(true) to use it.");
            } else {
                .print("TRAINING COMPLETE after ", MaxEp, " episodes!");
                .print("Policy saved to checkpoints/. Set eval_mode(true) to use it.");
            } else {
                !current_region(_);
            +current_region(Region);
            +ntpp(Me, Region).
            +step(1);
            +episode_reward(0.0);
            !goal_region(Region)
            +goal_region(Region)
        }
    }

    // --- Timeout ---
+!rl_loop
    :   step(S) & max_steps(MaxS) & S >= MaxS
        ?step(S) & max_steps(MaxS) & S >= MaxS
            .print("*** TIMEOUT at step ", S, " ***");
            -episode_reward(_);
            +episode_reward(ER + R);
            !end_episode.
        }
    }
    // --- Normal Step ---
+!rl_loop
    :   current_region(Region) & step(S)
 & S < MaxS
        ?reward_step(R);
        ?episode_reward(ER);
        ?reward_timeout(Rt);
        ?reward_timeout(Rt);
        !rl_select_action(Region, Goal, R, false, _)
        .print("Step ", S, ": at ", Region, " -> goal: ", Goal);
        !rl_select_action(Region, Goal, R, true, _);
        -episode_reward(_);
        +episode_reward(ER + R);
        !end_episode.
        }
    }
    // Clean up beliefs from this episode
    -episode(15);
    -step(_)
    +episode(16)
    +episode(16)
    +episode(17)
    +episode(17)
    // ... continues
}
