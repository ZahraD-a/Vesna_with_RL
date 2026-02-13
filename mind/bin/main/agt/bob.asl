{ include( "vesna.asl" ) }
{ include( "playgrounds/office.asl" ) }

// ============================================================
//                    BOB - Junior Employee
// ============================================================

+!start
    :   .my_name(Me)
    <-  +ntpp(Me, open_office);
        +my_desk(junior_1_desk);
        .print("");
        .print("BOB STARTED - Junior Employee");
        .print("Location: Open Office");
        .print("");
        .wait(5000);
        !do_my_tasks.

+!do_my_tasks
    <-  
        // Task 1: Say hello to Alice
        .print("BOB Task 1: Say hello to Alice");
        .print("  Bob sends hello to Alice...");
        .send(alice, tell, hello);
        .wait(3000);
        
        // Task 2: Go to desk
        .print("");
        .print("BOB Task 2: Go to my desk");
        !go_to(junior_1_desk);
        .wait(1000);
        .print("  Bob is working at his desk...");
        .wait(3000);
        
        // Task 3: Get coffee
        .print("");
        .print("BOB Task 3: Get coffee");
        !go_to(coffee_machine);
        .wait(1000);
        .print("  Bob is making coffee...");
        .wait(3000);
        
        // Task 4: Go to reception
        .print("");
        .print("BOB Task 4: Go to reception");
        !go_to(reception);
        .wait(1000);
        .print("  Bob is at reception...");
        .wait(3000);
        
        // Task 5: Ask Alice for help
        .print("");
        .print("BOB Task 5: Ask Alice for help");
        .print("  Bob needs help with a report!");
        .send(alice, achieve, help_with_report);
        .wait(10000);
        
        // Task 6: Return to desk
        .print("");
        .print("BOB Task 6: Return to desk");
        !go_to(junior_1_desk);
        .wait(1000);
        .print("  Bob is back at his desk!");
        
        .print("");
        .print("BOB FINISHED ALL TASKS");
        .print("").

// ============== RECEIVE MESSAGES FROM ALICE ==============

+hello_back[source(alice)]
    <-  .print("");
        .print("MESSAGE FROM ALICE: Hello back!");
        .print("  Bob: Nice to hear from Alice!");
        .print("").

+report_done[source(alice)]
    <-  .print("");
        .print("MESSAGE FROM ALICE: Report done!");
        .print("  Bob: Thank you Alice!");
        .print("").