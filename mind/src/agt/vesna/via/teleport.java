package vesna;

import jason.asSemantics.*;
import jason.asSyntax.*;

import org.json.JSONObject;

/**
 * Internal action to teleport an agent instantly to a target region.
 * Used for RL training where we need to reset the agent to random positions.
 *
 * Usage in ASL:
 *   vesna.teleport(Region)
 *
 * Example:
 *   vesna.teleport(corridor)
 *   // Agent instantly moves to corridor without walking animation
 */
public class teleport extends DefaultInternalAction {

    @Override
    public Object execute(TransitionSystem ts, Unifier un, Term[] args) throws Exception {

        if (args.length != 1 || !args[0].isLiteral()) {
            throw new Exception("teleport requires exactly 1 argument: target region");
        }

        String target = args[0].toString();

        JSONObject data = new JSONObject();
        data.put("target", target);

        JSONObject action = new JSONObject();
        action.put("sender", ts.getAgArch().getAgName());
        action.put("receiver", "body");
        action.put("type", "teleport");
        action.put("data", data);

        VesnaAgent ag = (VesnaAgent) ts.getAg();
        ag.perform(action.toString());

        return true;
    }
}
