package vesna;

import jason.asSemantics.*;
import jason.asSyntax.*;

import org.json.JSONObject;

/**
 * Internal action to teleport the agent instantly.
 *
 * Usage in ASL:
 *   vesna.teleport(region_name)         -- teleport to a named region
 *   vesna.teleport(X, Y, Z)            -- teleport to exact coordinates
 */
public class teleport extends DefaultInternalAction {

    @Override
    public Object execute( TransitionSystem ts, Unifier un, Term[] args ) throws Exception {

        VesnaAgent ag = ( VesnaAgent ) ts.getAg();

        JSONObject data = new JSONObject();

        if ( args.length == 1 && args[0].isLiteral() ) {
            // teleport(region_name)
            data.put( "type", "region" );
            data.put( "target", args[0].toString() );
        } else if ( args.length == 3 && args[0].isNumeric() && args[1].isNumeric() && args[2].isNumeric() ) {
            // teleport(X, Y, Z)
            data.put( "type", "coordinates" );
            data.put( "x", ( ( NumberTerm ) args[0] ).solve() );
            data.put( "y", ( ( NumberTerm ) args[1] ).solve() );
            data.put( "z", ( ( NumberTerm ) args[2] ).solve() );
        } else {
            throw new Exception( "teleport requires 1 arg (region name) or 3 args (x, y, z)" );
        }

        JSONObject action = new JSONObject();
        action.put( "sender", ts.getAgArch().getAgName() );
        action.put( "receiver", "body" );
        action.put( "type", "teleport" );
        action.put( "data", data );

        ag.perform( action.toString() );

        return true;
    }

}
