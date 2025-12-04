{ include( "vesna.asl" ) }
{ include( "playgrounds/office.asl" ) }

// ============== INITIAL BELIEFS ==============
energy(80).              // Alice starts with 80% energy
coffees_today(0).        // No coffee yet today

// ============== MAIN START ==============
+!start
    :   .my_name( Me )
    <-  +ntpp(Me, senior_office_2 );
        +my_desk(senior_3_desk);
        .print( "Hello! I am Alice!" );
        !check_time_and_decide;
        !daily_routine.

// ============== TIME-BASED DECISION MAKING ==============
+!check_time_and_decide
    <-  .time(HH, MM, SS);                    // Get current system time
        +current_time(HH, MM);
        .print( "Current time is ", HH, ":", MM );
        !determine_period( HH ).

+!determine_period( Hour )
    :   Hour >= 6 & Hour < 10
    <-  +time_period( early_morning );
        .print( "It's early morning - I need coffee to wake up!" ).

+!determine_period( Hour )
    :   Hour >= 10 & Hour < 12
    <-  +time_period( late_morning );
        .print( "It's late morning - time to focus on work!" ).

+!determine_period( Hour )
    :   Hour >= 12 & Hour < 14
    <-  +time_period( lunch_time );
        .print( "It's lunch time!" ).

+!determine_period( Hour )
    :   Hour >= 14 & Hour < 17
    <-  +time_period( afternoon );
        .print( "It's afternoon - productive work time!" ).

+!determine_period( Hour )
    :   Hour >= 17 & Hour < 20
    <-  +time_period( evening );
        .print( "It's evening - wrapping up work." ).

+!determine_period( Hour )
    <-  +time_period( night );
        .print( "It's night time - I should go home!" ).

// ============== DAILY ROUTINE (Intelligent) ==============
+!daily_routine
    :   time_period( early_morning )
    <-  .print( "=== EARLY MORNING ROUTINE ===" );
        !make_and_drink_coffee;
        !go_back_to_office;
        !work_session;
        !check_energy_and_continue.

+!daily_routine
    :   time_period( late_morning ) | time_period( afternoon )
    <-  .print( "=== WORK TIME ROUTINE ===" );
        ?energy( E );
        if ( E < 50 ) {
            .print( "Low energy! Need coffee first." );
            !make_and_drink_coffee;
            !go_back_to_office;
        };
        !work_session;
        !check_energy_and_continue.

+!daily_routine
    :   time_period( lunch_time )
    <-  .print( "=== LUNCH BREAK ===" );
        !go_to( common );
        .print( "Having lunch in the common area..." );
        .wait( 5000 );
        -energy( _ );
        +energy( 100 );            // Lunch restores energy!
        .print( "Feeling refreshed after lunch!" );
        !go_back_to_office.

+!daily_routine
    :   time_period( evening ) | time_period( night )
    <-  .print( "=== END OF DAY ===" );
        !go_to( outside );
        .print( "Goodbye! See you tomorrow!" ).

// ============== ENERGY MANAGEMENT ==============
+!check_energy_and_continue
    <-  ?energy( E );
        ?coffees_today( C );
        .print( "Current energy: ", E, "% | Coffees today: ", C );
        if ( E < 30 & C < 3 ) {
            .print( "Very tired! Taking a coffee break..." );
            !make_and_drink_coffee;
            !go_back_to_office;
        };
        .print( "Continuing with my day..." ).

// ============== COFFEE (with energy boost) ==============
+!make_and_drink_coffee
    :   coffees_today( C ) & C >= 3
    <-  .print( "I've had too much coffee today! No more for me." ).

+!make_and_drink_coffee
    :   coffees_today( C ) & C < 3
    <-  .print( "I need some coffee..." );
        !go_to( coffee_machine );
        .print( "I'm at the coffee machine! Making coffee..." );
        .wait( 3000 );
        .print( "Coffee is ready! *sip sip*" );
        .wait( 2000 );
        .print( "Ahh, that was good coffee!" );
        // Update beliefs
        -coffees_today( C );
        +coffees_today( C + 1 );
        ?energy( OldE );
        -energy( OldE );
        +energy( OldE + 25 );      // Coffee gives +25 energy!
        .print( "Energy boosted! Now at ", OldE + 25, "%" ).

// ============== WORK SESSION ==============
+!work_session
    :   my_desk( MyDesk ) & ntpp( _, MyDesk )    // Already at desk
    <-  .print( "Working hard on my tasks..." );
        .wait( 5000 );
        ?energy( E );
        -energy( E );
        +energy( E - 20 );         // Work consumes 20 energy
        .print( "Work session done! Energy now: ", E - 20, "%" ).

+!work_session
    :   my_desk( MyDesk )          // Not at desk
    <-  .print( "I need to go to my desk first!" );
        !go_back_to_office;
        !work_session.

// ============== GO BACK TO OFFICE ==============
+!go_back_to_office
    :   my_desk( MyDesk )
    <-  .print( "Time to go back to work..." );
        !go_to( MyDesk );
        .print( "I'm back at my desk! Ready to work." ).