package vesna;

import jason.asSemantics.*;
import jason.asSyntax.*;

import org.json.JSONObject;

public class says extends DefaultInternalAction {

    // This DefaultInternalAction is used to display messages in the env;
    // Depending on the quantity of information you want to use in the env
    // you can change the cardinality of args
    // vesna.says( msg )            Ag says msg;
    // vesna.says( to, msg )        Ag says msg to; 
    // vesna.says( perf, to, msg )  Ag says msg to with perf(ormative)
   
    @Override
    public Object execute( TransitionSystem ts, Unifier un, Term[] args ) throws Exception {

        if ( args.length == 0 || args.length > 3 )
            return false;

        // // String performative = args[0].toString();
        // // String recipient = args[1].toString();
        // // String msg = args[2].toString();

        JSONObject action = new JSONObject();
        action.put( "sender", "mind" );
        action.put( "receiver", "body" );
        action.put( "type", "say" );
        JSONObject data = new JSONObject();

        if ( args.length == 1 ) 
            data.put( "msg", args[0].toString() );
        else if ( args.length == 2 ) {
            data.put( "recipient", args[0].toString() );
            data.put( "msg", args[1].toString() );
        }
        else if ( args.length == 3 ) {
            data.put( "performative", args[0].toString() );
            data.put( "recipient", args[1].toString() );
            data.put( "msg", args[2].toString() );
        }
        action.put( "data", data );

        VesnaAgent ag = ( VesnaAgent ) ts.getAg();
        ag.perform( action.toString() );

        return true;
    }
}
