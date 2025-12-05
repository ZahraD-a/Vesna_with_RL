{ include( "vesna.asl" ) }
{ include( "playgrounds/office.asl" ) }

// ============================================================
//                    ALICE - Senior Employee
// ============================================================

+!start
    :   .my_name(Me)
    <-  +ntpp(Me, senior_office_2);
        +my_desk(senior_3_desk);
        .print("");
        .print("ALICE STARTED - Senior Employee");
        .print("Location: Senior Office 2");
        .print("");
        !do_my_tasks.

+!do_my_tasks
    <-  
        // Task 1: Go to desk
        .print("ALICE Task 1: Go to my desk");
        !go_to(senior_3_desk);
        .wait(1000);
        .print("  Alice is working at her desk...");
        .wait(3000);
        
        // Task 2: Get coffee
        .print("");
        .print("ALICE Task 2: Get coffee");
        !go_to(coffee_machine);
        .wait(1000);
        .print("  Alice is making coffee...");
        .wait(3000);
        
        // Task 3: Return to desk after coffee
        .print("");
        .print("ALICE Task 3: Return to desk");
        !go_to(senior_3_desk);
        .wait(1000);
        .print("  Alice is back at her desk!");
        
        .print("");
        .print("ALICE FINISHED - Waiting for Bob...");
        .print("").

// ============== RECEIVE MESSAGES FROM BOB ==============

+hello[source(bob)]
    <-  .print("");
        .print("MESSAGE FROM BOB: Hello!");
        .print("  Alice sends hello back...");
        .send(bob, tell, hello_back);
        .print("").

+!help_with_report[source(bob)]
    <-  .print("");
        .print("MESSAGE FROM BOB: Needs help with report!");
        .print("  Alice is going to help Bob...");
        !go_to(open_office);
        .wait(1000);
        .print("  Alice arrived at Bob's location");
        .print("  Helping Bob with the report...");
        .wait(4000);
        .print("  Report completed!");
        .send(bob, tell, report_done);
        .print("");
        .print("ALICE: Returning to my desk");
        !go_to(senior_3_desk);
        .wait(1000);
        .print("  Alice is back at her desk!");
        .print("").