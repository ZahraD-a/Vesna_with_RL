package vesna;

/**
 * ============================================================================
 * NOVAE TRACE LOGGER - LoggedAgArch
 * ============================================================================
 *
 * This class extends Jason's AgArch class to add architecture-level trace
 * logging. It captures events that occur at the architecture level:
 *   - Action executions (external actions on the environment)
 *   - Message sending and receiving
 *   - Perception updates
 *
 * This complements LoggedAgent which captures cognitive-level events
 * (plan selection, belief updates, etc.).
 *
 * Together, LoggedAgent + LoggedAgArch provide complete trace logging
 * as specified in the NOVAE framework.
 *
 * Usage in .jcm configuration:
 * <pre>
 *   agent r1:r1.asl {
 *       agentClass: vesna.LoggedAgent
 *       agentArchClass: vesna.LoggedAgArch
 *   }
 * </pre>
 *
 * Reference:
 *   - "The Secret Life of Traces" - NOVAE Framework Paper
 *   - Winikoff (2024) "Towards Engineering Explainable Autonomous Systems"
 *
 * @author NOVAE Team (Implementation for Vesna)
 * @see LoggedAgent
 * @see TraceLogger
 * @see TraceEntry
 * ============================================================================
 */

import jason.architecture.AgArch;
import jason.asSemantics.*;
import jason.asSyntax.*;
import jason.infra.local.LocalAgArch;
import jason.ReceiverNotFoundException;

import java.util.*;
import java.util.logging.Logger;

public class LoggedAgArch extends LocalAgArch {

    // ========================================================================
    // NOVAE TRACE LOGGER FIELDS
    // ========================================================================

    /** Logger for console output */
    protected transient Logger logger;

    /** Reference to the trace logger (shared with LoggedAgent) */
    protected TraceLogger traceLogger;

    /** Current cycle number (synced with LoggedAgent) */
    protected long currentCycle = 0;

    // ========================================================================
    // INITIALIZATION
    // ========================================================================

    /**
     * Called when the agent architecture is initialized
     */
    @Override
    public void init() throws Exception {
        super.init();
        logger = Logger.getLogger("LoggedAgArch." + getAgName());
        logger.info("[NOVAE AgArch] Initialized for agent: " + getAgName());
    }

    /**
     * Get or create the trace logger.
     * If LoggedAgent is used, we share its trace logger.
     * Otherwise, we create our own.
     */
    protected TraceLogger getTraceLogger() {
        if (traceLogger == null) {
            // Try to get the trace logger from LoggedAgent
            if (getTS() != null && getTS().getAg() instanceof LoggedAgent) {
                traceLogger = ((LoggedAgent) getTS().getAg()).getTraceLogger();
            }

            // If still null, try to get from registry
            if (traceLogger == null) {
                traceLogger = TraceLogger.getLogger(getAgName());
            }

            // If still null, create our own
            if (traceLogger == null) {
                traceLogger = new TraceLogger(getAgName());
            }
        }
        return traceLogger;
    }

    // ========================================================================
    // ACTION EXECUTION LOGGING
    // ========================================================================

    /**
     * Override act to log action executions.
     * This captures external actions performed on the environment.
     *
     * @param action The action to execute
     */
    @Override
    public void act(ActionExec action) {
        // Log the action before execution
        logActionStart(action);

        // Execute the action
        super.act(action);
    }

    /**
     * Override actionExecuted to log action completion.
     *
     * @param action The action that was executed
     */
    @Override
    public void actionExecuted(ActionExec action) {
        super.actionExecuted(action);

        // Log the action result
        logActionComplete(action);
    }

    /**
     * Log the start of an action execution
     */
    protected void logActionStart(ActionExec action) {
        String actionContent = action.getActionTerm().toString();
        String intention = action.getIntention() != null
                ? action.getIntention().peek().getTrigger().toString()
                : "unknown";

        TraceEntry entry = new TraceEntry.Builder(
                getAgName(),
                TraceEntry.ChangerType.ACTION,
                actionContent
        )
                .cycleNumber(getCurrentCycle())
                .trigger(intention)
                .metadata("status=started")
                .result("pending")
                .build();

        getTraceLogger().log(entry);
    }

    /**
     * Log the completion of an action execution
     */
    protected void logActionComplete(ActionExec action) {
        String actionContent = action.getActionTerm().toString();
        String result = action.getResult() ? "success" : "failure";
        String failureReason = action.getFailureReason() != null
                ? action.getFailureReason().toString()
                : null;

        TraceEntry.Builder builder = new TraceEntry.Builder(
                getAgName(),
                TraceEntry.ChangerType.ACTION,
                actionContent + " [completed]"
        )
                .cycleNumber(getCurrentCycle())
                .result(result);

        if (failureReason != null) {
            builder.metadata("failure_reason=" + failureReason);
        }

        getTraceLogger().log(builder.build());
    }

    // ========================================================================
    // MESSAGE LOGGING
    // ========================================================================

    /**
     * Override sendMsg to log outgoing messages.
     *
     * @param m The message to send
     */
    @Override
    public void sendMsg(Message m) throws ReceiverNotFoundException {
        // Log the message before sending
        logMessageSent(m);

        // Send the message
        super.sendMsg(m);
    }

    /**
     * Override checkMail to log incoming messages.
     */
    @Override
    public void checkMail() {
        // Get messages before they're processed
        int beforeCount = getTS().getC().getMailBox().size();

        super.checkMail();

        // Log any new messages
        // Note: This is a simplified approach. In practice, you might want
        // to override the actual message receiving mechanism.
        int afterCount = getTS().getC().getMailBox().size();
        if (afterCount > beforeCount) {
            // New messages were received - they'll be logged when processed
            logger.fine("[NOVAE] " + (afterCount - beforeCount) + " new message(s) received");
        }
    }

    /**
     * Log an outgoing message
     */
    protected void logMessageSent(Message m) {
        String content = String.format("to(%s) ilf(%s) content(%s)",
                m.getReceiver(),
                m.getIlForce(),
                m.getPropCont() != null ? m.getPropCont().toString() : "null");

        TraceEntry entry = new TraceEntry.Builder(
                getAgName(),
                TraceEntry.ChangerType.MESSAGE_SENT,
                content
        )
                .cycleNumber(getCurrentCycle())
                .metadata("receiver=" + m.getReceiver() + ";ilforce=" + m.getIlForce())
                .result("success")
                .build();

        getTraceLogger().log(entry);
    }

    /**
     * Log an incoming message (call this when processing received messages)
     */
    public void logMessageReceived(Message m) {
        String content = String.format("from(%s) ilf(%s) content(%s)",
                m.getSender(),
                m.getIlForce(),
                m.getPropCont() != null ? m.getPropCont().toString() : "null");

        TraceEntry entry = new TraceEntry.Builder(
                getAgName(),
                TraceEntry.ChangerType.MESSAGE_RECEIVED,
                content
        )
                .cycleNumber(getCurrentCycle())
                .metadata("sender=" + m.getSender() + ";ilforce=" + m.getIlForce())
                .result("success")
                .build();

        getTraceLogger().log(entry);
    }

    // ========================================================================
    // REASONING CYCLE HOOK
    // ========================================================================

    /**
     * Override reasoningCycleStarting to track cycle number and trigger
     * LoggedAgent's cycle start hook.
     */
    @Override
    public void reasoningCycleStarting() {
        currentCycle++;

        // Notify LoggedAgent about cycle start
        if (getTS() != null && getTS().getAg() instanceof LoggedAgent) {
            ((LoggedAgent) getTS().getAg()).onReasoningCycleStart();
        }

        super.reasoningCycleStarting();
    }

    /**
     * Get the current reasoning cycle number
     */
    protected long getCurrentCycle() {
        // Prefer LoggedAgent's cycle number if available
        if (getTS() != null && getTS().getAg() instanceof LoggedAgent) {
            return ((LoggedAgent) getTS().getAg()).getCurrentCycle();
        }
        return currentCycle;
    }

    // ========================================================================
    // PERCEPTION LOGGING (OPTIONAL)
    // ========================================================================

    /**
     * Override perceive to optionally log perception updates.
     * Note: This can be very verbose, so it's disabled by default.
     */
    @Override
    public Collection<Literal> perceive() {
        Collection<Literal> perceptions = super.perceive();

        // Uncomment to enable perception logging:
        // if (perceptions != null && !perceptions.isEmpty()) {
        //     logPerceptions(perceptions);
        // }

        return perceptions;
    }

    /**
     * Log perception updates
     */
    protected void logPerceptions(Collection<Literal> perceptions) {
        StringBuilder content = new StringBuilder("Perceived: ");
        content.append(perceptions.size()).append(" literals");

        TraceEntry entry = new TraceEntry.Builder(
                getAgName(),
                TraceEntry.ChangerType.REASONING_CYCLE,
                content.toString()
        )
                .cycleNumber(getCurrentCycle())
                .metadata("perception_count=" + perceptions.size())
                .result("success")
                .build();

        getTraceLogger().log(entry);
    }

    // ========================================================================
    // SHUTDOWN
    // ========================================================================

    /**
     * Override stop to ensure trace logger is properly shut down.
     */
    @Override
    public void stop() {
        // Notify LoggedAgent to stop (which will handle trace export)
        if (getTS() != null && getTS().getAg() instanceof LoggedAgent) {
            ((LoggedAgent) getTS().getAg()).stopAg();
        } else if (traceLogger != null) {
            // If no LoggedAgent, handle shutdown ourselves
            traceLogger.shutdown();
        }

        logger.info("[NOVAE AgArch] Stopped for agent: " + getAgName());

        super.stop();
    }

    // ========================================================================
    // UTILITY METHODS
    // ========================================================================

    /**
     * Manually log an internal action execution.
     * Call this from custom internal actions to trace their execution.
     *
     * @param actionName Name of the internal action (e.g., ".print")
     * @param args       Arguments passed to the action
     * @param result     Result of the action ("success" or "failure")
     */
    public void logInternalAction(String actionName, Term[] args, String result) {
        StringBuilder content = new StringBuilder(actionName);
        content.append("(");
        for (int i = 0; i < args.length; i++) {
            if (i > 0) content.append(", ");
            content.append(args[i].toString());
        }
        content.append(")");

        TraceEntry entry = new TraceEntry.Builder(
                getAgName(),
                TraceEntry.ChangerType.INTERNAL_ACTION,
                content.toString()
        )
                .cycleNumber(getCurrentCycle())
                .result(result)
                .build();

        getTraceLogger().log(entry);
    }
}
