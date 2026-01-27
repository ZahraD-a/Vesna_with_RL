package vesna.via;

/**
 * ============================================================================
 * NOVAE TRACE LOGGER - log_trace Internal Action
 * ============================================================================
 *
 * This internal action allows agents to log custom trace entries from their
 * ASL plans. Use this to trace important events that are not automatically
 * captured by LoggedAgent/LoggedAgArch.
 *
 * Usage in ASL plans:
 * <pre>
 *   +!my_goal : true <-
 *       vesna.via.log_trace("ACTION", "Starting my_goal execution");
 *       // ... do something ...
 *       vesna.via.log_trace("ACTION", "Completed step 1", "step=1;status=ok");
 *       // ... do more ...
 *       vesna.via.log_trace("ACTION", "my_goal finished successfully").
 * </pre>
 *
 * Parameters:
 *   - Arg 0: Changer type (string) - one of:
 *            ACTION, INTERNAL_ACTION, PLAN_SELECTION, BELIEF_ADDITION,
 *            BELIEF_DELETION, GOAL_ADDITION, GOAL_DELETION, EVENT_ADDITION,
 *            INTENTION_SELECTION, MESSAGE_SENT, MESSAGE_RECEIVED, REASONING_CYCLE
 *   - Arg 1: Content (string) - description of what happened
 *   - Arg 2: (optional) Metadata (string) - additional key=value pairs
 *
 * Reference:
 *   - "The Secret Life of Traces" - NOVAE Framework Paper
 *
 * @author NOVAE Team (Implementation for Vesna)
 * @see vesna.LoggedAgent
 * @see vesna.TraceLogger
 * ============================================================================
 */

import jason.JasonException;
import jason.asSemantics.*;
import jason.asSyntax.*;

import vesna.LoggedAgent;
import vesna.LoggedVesnaAgent;
import vesna.TraceLogger;
import vesna.TraceEntry;

public class log_trace extends DefaultInternalAction {

    @Override
    public Object execute(TransitionSystem ts, Unifier un, Term[] args) throws Exception {

        // Validate arguments
        if (args.length < 2) {
            throw new JasonException("log_trace requires at least 2 arguments: changerType, content");
        }

        // Get arguments
        String changerType = args[0].toString().replace("\"", "");
        String content = args[1].toString().replace("\"", "");
        String metadata = args.length > 2 ? args[2].toString().replace("\"", "") : null;

        // Get the trace logger
        TraceLogger traceLogger = null;

        // Try to get from LoggedAgent
        if (ts.getAg() instanceof LoggedAgent) {
            traceLogger = ((LoggedAgent) ts.getAg()).getTraceLogger();
        } else if (ts.getAg() instanceof LoggedVesnaAgent) {
            traceLogger = ((LoggedVesnaAgent) ts.getAg()).getTraceLogger();
        }

        // If no LoggedAgent, try to get from registry
        if (traceLogger == null) {
            String agentName = ts.getAgArch().getAgName();
            traceLogger = TraceLogger.getLogger(agentName);
        }

        // If still no logger, create one
        if (traceLogger == null) {
            String agentName = ts.getAgArch().getAgName();
            traceLogger = new TraceLogger(agentName);
            ts.getLogger().warning("[log_trace] Created new TraceLogger - consider using LoggedAgent/LoggedVesnaAgent");
        }

        // Parse changer type
        TraceEntry.ChangerType type;
        try {
            type = TraceEntry.ChangerType.valueOf(changerType.toUpperCase());
        } catch (IllegalArgumentException e) {
            type = TraceEntry.ChangerType.REASONING_CYCLE;
            ts.getLogger().warning("[log_trace] Unknown changer type: " + changerType + ", using REASONING_CYCLE");
        }

        // Get cycle number if available
        long cycleNumber = 0;
        if (ts.getAg() instanceof LoggedAgent) {
            cycleNumber = ((LoggedAgent) ts.getAg()).getCurrentCycle();
        } else if (ts.getAg() instanceof LoggedVesnaAgent) {
            cycleNumber = ((LoggedVesnaAgent) ts.getAg()).getCurrentCycle();
        }

        // Build and log the trace entry
        TraceEntry.Builder builder = new TraceEntry.Builder(
                ts.getAgArch().getAgName(),
                type,
                content
        )
                .cycleNumber(cycleNumber)
                .result("success");

        if (metadata != null) {
            builder.metadata(metadata);
        }

        traceLogger.log(builder.build());

        return true;
    }
}
