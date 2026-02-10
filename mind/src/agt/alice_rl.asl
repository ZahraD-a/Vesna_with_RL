 
// Learns to find path from any start to any goal region(room).
// only step reward sent  to pyhton 
// Each transition only needs the immediate reward from that one step
// episode_reward is only for logging, not sent to Python. 
// The neural network learns to predict the total future reward by chaining steps together
// Python computes its own returns using Bellman equation.
// ============================================================

{ include("vesna.asl") }
{ include("playgrounds/office/office_map.asl") }
{ include("rl_bridge.asl") }

 
//------------------------------CONFIGURATION-------------

max_steps(50).                  // max steps before timeout
max_episodes(3000).              // stop training after N episodes
eval_mode(false).               // true = use trained policy, false = learning
save_interval(50).              // auto-save checkpoint every N episodes

// All navigable regions for randomized start/goal
all_regions([reception, corridor, open_office, outside, common,
             meeting_room, senior_office_1, senior_office_2,
             senior_office_3, boss_office_1, boss_office_2]).


//--------------------------------REWARD MACHINE-----------------
// Immediate rewards sent to Python RL.
// Python uses these in Bellman equation: Q = r + γ * max(Q_next)
// DQN learns to PREDICT the sum, not receive it directly.

reward_goal(100.0).       // given when agent reaches goal_region
reward_step(-1.0).        // given each step (encourages short paths)
reward_timeout(-10.0).    // given when step >= max_steps


//---------------------------START AGENT------------------------------------
+!start
    :   eval_mode(EvalMode)
    <-
        // Load neural network from checkpoint (in Python)
        // EvalMode=true means inference only, no training
        rl.load_model(EvalMode);  //call the load.model file in rl folder to loading the policy from the alice.pt checkpoint file
          .print("ALICE RL - Mode: eval=", EvalMode);
        
        // Begin running episodes
        !run_episodes.
 
// ============================================================
//                    RANDOMIZE START / GOAL-----
// Picks a random start and goal region each episode.
// Ensures start != goal for meaningful episodes.

+!randomize_start_goal
    :   all_regions(Regions)
    <-
        // Pick random start
        rl.random_region(Regions, Start);

        // Pick random goal (retry until different from start)
        rl.random_region(Regions, GoalCandidate);
        if (GoalCandidate == Start) {
            !randomize_start_goal;  // retry
        } else {
            // Remove old beliefs and set new ones
            -start_region(_);
            -goal_region(_);
            +start_region(Start);
            +goal_region(GoalCandidate);
        }.

// ============================================================
//                    GO TO START
// ============================================================
// Teleports agent to start_region.
// Uses vesna.teleport(region_name) from vesna.asl
// Waits for body to confirm arrival.

+!go_to_start
    <-
        ?start_region(Region);

        -movement(_, _);          // clear stale movement signal
        vesna.teleport(Region);
        .wait({+movement(completed, destination_reached)}).



// ============================================================
//                    EPISODE MANAGEMENT
// ============================================================
// Beliefs created per episode:
//   episode(N)        - current episode number
//   step(N)           - current step in episode
//   episode_reward(N) - sum of rewards (for logging only)

+!run_episodes
    <-
        +episode(0);     // start from episode 0
        !run_episode.

+!run_episode
    :   episode(Ep)
    <-
        // Randomize start/goal for each episode
        !randomize_start_goal;

        ?start_region(S);
        ?goal_region(G);
        .print("========== EPISODE ", Ep, " (", S, " -> ", G, ") ==========");

        +step(0);              // initialize step counter to 0
        +episode_reward(0);    // initialize episode reward for logging
        !go_to_start;          // reset position to start region
        .wait(100);            // wait for region_entered perception to be processed
        !rl_loop.              // start RL loop

// --- Training complete ---
+!end_episode
    :   episode(Ep) & max_episodes(MaxEp) & Ep + 1 >= MaxEp
    <-
        ?episode_reward(TotalReward);
        .print("Episode ", Ep, " total reward: ", TotalReward);
        .print("============================================");
        .print("TRAINING COMPLETE after ", Ep + 1, " episodes!");
        .print("Saving final policy...");
        rl.save_model;
        .print("Policy saved to checkpoints/. Set eval_mode(true) to use it.");
        .print("============================================").

// --- Normal end (continue training) ---
+!end_episode
    :   episode(Ep) & episode_reward(TotalReward) & save_interval(SaveN)
    <-
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

        // Start new episode
        +episode(Ep + 1);
        .wait(1000);
        !run_episode.


//-------------------------RL LOOP----------------------------------
// The decision logic IS the reward machine.
// Each case checks state and sends appropriate reward to Python.

// --- CASE 0: Wait for perception ---
// Guard: if current_region not yet set (race with region_entered handler), retry
+!rl_loop
    :   not current_region(_)
    <-  .wait(100);
        !rl_loop.

// --- CASE 1: Goal Reached ---
// When current_region == goal_region
+!rl_loop
    :   current_region(Region) & goal_region(Region)
    <-
        ?step(S);
        ?reward_goal(R);
        ?episode_reward(ER);

        .print("*** GOAL REACHED in ", S, " steps! ***");

        // Send to Python: reward=+100, done=true
        !rl_select_action(Region, Region, R, true, _);

        // Update episode reward for logging
        -episode_reward(_);
        +episode_reward(ER + R);

        !end_episode.

// --- CASE 2: Timeout ---
// When step >= max_steps
+!rl_loop
    :   step(S) & max_steps(MaxS) & S >= MaxS
    <-
        ?current_region(Region);
        ?goal_region(Goal);
        ?reward_timeout(R);
        ?episode_reward(ER);

        .print("*** TIMEOUT at step ", S, " ***");

        // Send to Python: reward=-10, done=true
        !rl_select_action(Region, Goal, R, true, _);

        // Update episode reward for logging
        -episode_reward(_);
        +episode_reward(ER + R);

        !end_episode.

// --- CASE 3: Normal Step ---
// Agent still trying to reach goal, step < max_steps
+!rl_loop
    :   current_region(Region) & step(S)
    <-
        ?goal_region(Goal);
        ?reward_step(R);
        ?episode_reward(ER);

        .print("Step ", S, ": at ", Region, " -> goal: ", Goal);

        // Send to Python: reward=-1, done=false
        // Python returns TargetRegion (next action)
        !rl_select_action(Region, Goal, R, false, TargetRegion);

        .print("  -> RL selected: ", TargetRegion);

        // Execute action (move body)
        !hop_to(TargetRegion);

        // Update step counter
        -step(_);
        +step(S + 1);

        // Update episode reward for logging
        -episode_reward(_);
        +episode_reward(ER + R);

        // Continue loop
        !rl_loop.
