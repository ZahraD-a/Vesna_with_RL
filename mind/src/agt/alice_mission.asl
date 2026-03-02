// ============================================================
//  ALICE MISSION AGENT — BDI + Trained RL Policy
// ============================================================
//  Demonstrates hybrid BDI-RL:
//    - BDI layer (Jason) plans WHAT to do (pick up, deliver, patrol)
//    - RL policy (trained DQN) decides HOW to navigate (room-to-room)
//    - NO retraining needed! Uses the already trained checkpoint.
//
//  This is something pure RL CANNOT do:
//    RL learned ONE skill: navigate(A, B).
//    Jason COMPOSES that skill into multi-step missions.
// ============================================================

{ include("playgrounds/office/office_map.asl") }
{ include("navigation_rl_bridge.asl") }


// --------------------- CONFIGURATION -----------------------

max_nav_steps(150).       // max steps for each navigation sub-goal


// =====================================================
//  MISSION DEFINITIONS
// =====================================================
//  Each mission is a list of sub-goals.
//  You can easily add new missions here!

// Mission 1: Deliver a package from mail_room to boss_office_1
mission(delivery, [
    go(mail_room),          // walk to mail room
    pickup(package),        // pick up the package
    go(boss_office_1),      // walk to boss office
    drop(package)           // deliver the package
]).

// Mission 2: Patrol — check three rooms then return to reception
mission(patrol, [
    go(server_room),        // check server room
    inspect(servers),       // inspect servers
    go(lab_1),              // check lab
    inspect(lab_equipment), // inspect lab equipment
    go(lobby),              // check lobby
    inspect(entrance),      // inspect entrance
    go(reception)           // return to base
]).

// Mission 3: Multi-delivery — deliver to two offices
mission(multi_delivery, [
    go(mail_room),          // pick up first package
    pickup(package_a),
    go(office_1),           // deliver to office 1
    drop(package_a),
    go(mail_room),          // pick up second package
    pickup(package_b),
    go(lab_2),              // deliver to lab 2
    drop(package_b),
    go(reception)           // return to base
]).


// =====================================================
//  START: Load trained policy, then run a mission
// =====================================================

+!start
    <-
        // Load the trained RL checkpoint (eval mode = no training)
        rl.load_model(true);
        .print("==============================================");
        .print("  ALICE MISSION AGENT — BDI + Trained RL");
        .print("  Using trained policy (no retraining!)");
        .print("==============================================");

        // Alice starts at reception
        -current_region(_);
        +current_region(reception);

        // Run the delivery mission (change this to try other missions)
        !run_mission(delivery).


// =====================================================
//  MISSION EXECUTOR
// =====================================================
//  Takes a mission name, gets its sub-goals, and
//  executes them one by one. This is pure BDI planning!

+!run_mission(MissionName)
    :   mission(MissionName, SubGoals)
    <-
        .print("");
        .print(">>> STARTING MISSION: ", MissionName);
        .print(">>> Sub-goals: ", SubGoals);
        .print("");

        !execute_subgoals(SubGoals, 1);

        .print("");
        .print(">>> MISSION COMPLETE: ", MissionName);
        .print("==============================================").

// No more sub-goals — done!
+!execute_subgoals([], _).

// Execute one sub-goal, then continue with the rest
+!execute_subgoals([SubGoal | Rest], StepNum)
    <-
        .print("--- Mission Step ", StepNum, ": ", SubGoal, " ---");
        !do(SubGoal);
        !execute_subgoals(Rest, StepNum + 1).


// =====================================================
//  SUB-GOAL HANDLERS
// =====================================================

// --- GO(Room): Navigate using trained RL policy ---
// This is where RL meets BDI!
// Jason says WHERE to go, RL figures out HOW to get there.

+!do(go(TargetRoom))
    :   current_region(Current)
    <-
        if (Current == TargetRoom) {
            .print("  Already at ", TargetRoom, "!");
        } else {
            .print("  Navigating: ", Current, " -> ", TargetRoom);
            +nav_goal(TargetRoom);
            +nav_steps(0);
            !navigate_with_rl;
            -nav_goal(_);
            -nav_steps(_);
        }.

// --- PICKUP(Item): BDI-only action (belief update) ---
+!do(pickup(Item))
    :   current_region(Room)
    <-
        +carrying(Item);
        .print("  Picked up ", Item, " at ", Room).

// --- DROP(Item): BDI-only action (belief update) ---
+!do(drop(Item))
    :   current_region(Room) & carrying(Item)
    <-
        -carrying(Item);
        .print("  Delivered ", Item, " to ", Room).

+!do(drop(Item))
    :   not carrying(Item)
    <-
        .print("  WARNING: Not carrying ", Item, "!").

// --- INSPECT(Thing): BDI-only action (just logging) ---
+!do(inspect(Thing))
    :   current_region(Room)
    <-
        .print("  Inspecting ", Thing, " at ", Room).


// =====================================================
//  RL NAVIGATION LOOP
// =====================================================
//  Uses the trained DQN policy to navigate step-by-step
//  from current room to the nav_goal room.
//  Same RL call as training, but in eval mode (greedy).

// Reached the goal room!
+!navigate_with_rl
    :   current_region(Room) & nav_goal(Room)
    <-
        ?nav_steps(S);
        .print("  Arrived at ", Room, " in ", S, " steps!").

// Timeout — could not reach goal
+!navigate_with_rl
    :   nav_steps(S) & max_nav_steps(Max) & S >= Max
    <-
        ?current_region(Room);
        ?nav_goal(Goal);
        .print("  TIMEOUT: Could not reach ", Goal, " from ", Room, " in ", Max, " steps").

// Normal step — ask RL for next room
+!navigate_with_rl
    :   current_region(Current) & nav_goal(Goal) & nav_steps(S)
    <-
        // Ask the trained RL policy: "I'm at Current, I want to reach Goal, where should I go?"
        !rl_select_action(Current, Goal, 0.0, false, NextRoom);
        .print("    Step ", S, ": ", Current, " -> ", NextRoom);

        // Move (instant graph transition)
        !hop_to(NextRoom);

        // Update step counter
        -nav_steps(_);
        +nav_steps(S + 1);

        // Continue navigating
        !!navigate_with_rl.
