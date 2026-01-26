package vesna;

/**
 * ============================================================================
 * NOVAE TRACE LOGGER - LoggedVesnaAgent
 * ============================================================================
 *
 * This class combines VesnaAgent (embodied agent with WebSocket body connection)
 * with LoggedAgent's trace logging capabilities.
 *
 * Use this when you need BOTH:
 *   - Embodied agent features (connection to Godot/Unity via WebSocket)
 *   - Trace logging for explainability, RV, and learning
 *
 * Usage in .jcm configuration:
 * <pre>
 *   agent alice:alice.asl {
 *       agentClass: vesna.LoggedVesnaAgent
 *       agentArchClass: vesna.LoggedAgArch
 *       address: localhost
 *       port: 9080
 *       temper: propensions([...])      // optional
 *       strategy: random                 // optional
 *       trace_output: "logs/alice.json"  // optional
 *       trace_format: "json"             // optional: json, prolog, console
 *       trace_beliefs: true              // optional
 *   }
 * </pre>
 *
 * Reference:
 *   - "The Secret Life of Traces" - NOVAE Framework Paper
 *   - Winikoff (2024) "Towards Engineering Explainable Autonomous Systems"
 *
 * @author NOVAE Team (Implementation for Vesna)
 * @see VesnaAgent
 * @see LoggedAgent
 * @see TraceLogger
 * ============================================================================
 */

import jason.asSemantics.*;
import jason.asSyntax.*;
import jason.bb.BeliefBase;
import jason.RevisionFailedException;
import jason.runtime.Settings;

import java.util.*;
import java.util.stream.Collectors;

public class LoggedVesnaAgent extends VesnaAgent {

    // ========================================================================
    // NOVAE TRACE LOGGER FIELDS (copied from LoggedAgent)
    // ========================================================================

    /** The trace logger instance for this agent */
    protected TraceLogger traceLogger;

    /** Current reasoning cycle number */
    protected long currentCycle = 0;

    /** Configuration: whether to log belief snapshots */
    protected boolean logBeliefSnapshots = true;

    /** Configuration: whether to log intention snapshots */
    protected boolean logIntentionSnapshots = true;

    /** Configuration: whether to log event snapshots */
    protected boolean logEventSnapshots = false;

    /** Configuration: output format for traces */
    protected TraceLogger.OutputFormat traceOutputFormat = TraceLogger.OutputFormat.CONSOLE;

    /** Configuration: output file path (null = no file output) */
    protected String traceOutputPath = null;

    // ========================================================================
    // INITIALIZATION
    // ========================================================================

    /**
     * Initialize the agent with both VesnaAgent features and trace logging.
     */
    @Override
    public void initAg() {
        // Initialize VesnaAgent (body connection, temper, etc.)
        super.initAg();

        // Get agent name
        String agentName = getTS().getAgArch().getAgName();

        // Read trace configuration from settings
        Settings stts = getTS().getSettings();
        readTraceConfiguration(stts);

        // Initialize trace logger
        traceLogger = new TraceLogger(agentName, traceOutputFormat, traceOutputPath);
        traceLogger.setIncludeBeliefs(logBeliefSnapshots);
        traceLogger.setIncludeIntentions(logIntentionSnapshots);
        traceLogger.setIncludeEvents(logEventSnapshots);

        // Log the initial state as run event
        String initialGoals = getInitialGoalsAsString();
        traceLogger.logRunEvent(initialGoals);

        logger.info("[NOVAE] Trace logging initialized for embodied agent: " + agentName);
    }

    /**
     * Read trace configuration from agent settings
     */
    protected void readTraceConfiguration(Settings stts) {
        String formatStr = stts.getUserParameter("trace_format");
        if (formatStr != null) {
            try {
                traceOutputFormat = TraceLogger.OutputFormat.valueOf(formatStr.toUpperCase());
            } catch (IllegalArgumentException e) {
                logger.warning("[NOVAE] Invalid trace_format: " + formatStr + ", using CONSOLE");
            }
        }

        traceOutputPath = stts.getUserParameter("trace_output");

        String includeBeliefs = stts.getUserParameter("trace_beliefs");
        if (includeBeliefs != null) {
            logBeliefSnapshots = Boolean.parseBoolean(includeBeliefs);
        }

        String includeIntentions = stts.getUserParameter("trace_intentions");
        if (includeIntentions != null) {
            logIntentionSnapshots = Boolean.parseBoolean(includeIntentions);
        }

        String includeEvents = stts.getUserParameter("trace_events");
        if (includeEvents != null) {
            logEventSnapshots = Boolean.parseBoolean(includeEvents);
        }
    }

    // ========================================================================
    // PLAN SELECTION - WITH TEMPER AND LOGGING
    // ========================================================================

    /**
     * Override selectOption to log plan selection.
     * This method already handles temper-based selection from VesnaAgent;
     * we add logging on top of that.
     *
     * @param options List of applicable options
     * @return The selected option
     */
    @Override
    public Option selectOption(List<Option> options) {
        // Let VesnaAgent handle temper-based selection
        Option selected = super.selectOption(options);

        if (selected != null && options.size() > 0) {
            logPlanSelection(selected, options);
        }

        return selected;
    }

    /**
     * Log a plan selection event with all alternatives
     */
    protected void logPlanSelection(Option selected, List<Option> allOptions) {
        Plan selectedPlan = selected.getPlan();
        String planContent = selectedPlan.toASString();
        String trigger = selectedPlan.getTrigger().toString();
        String context = selectedPlan.getContext() != null ? selectedPlan.getContext().toString() : "true";

        List<String> alternatives = allOptions.stream()
                .filter(opt -> opt != selected)
                .map(opt -> opt.getPlan().toASString())
                .collect(Collectors.toList());

        TraceEntry.Builder builder = new TraceEntry.Builder(
                getTS().getAgArch().getAgName(),
                TraceEntry.ChangerType.PLAN_SELECTION,
                "Selected plan for: " + trigger
        )
                .cycleNumber(currentCycle)
                .planUsed(planContent)
                .trigger(trigger)
                .contextEvaluated(context)
                .alternativesNotSelected(alternatives)
                .result("success");

        addStateSnapshots(builder);
        traceLogger.log(builder.build());
    }

    // ========================================================================
    // INTENTION SELECTION - WITH TEMPER AND LOGGING
    // ========================================================================

    /**
     * Override selectIntention to log intention selection.
     * This method already handles temper-based selection from VesnaAgent;
     * we add logging on top of that.
     *
     * @param intentions Queue of intentions
     * @return The selected intention
     */
    @Override
    public Intention selectIntention(Queue<Intention> intentions) {
        // Let VesnaAgent handle temper-based selection
        Intention selected = super.selectIntention(intentions);

        if (selected != null) {
            logIntentionSelection(selected, intentions);
        }

        return selected;
    }

    /**
     * Log an intention selection event
     */
    protected void logIntentionSelection(Intention selected, Queue<Intention> allIntentions) {
        String intentionContent = selected.peek() != null
                ? selected.peek().getTrigger().toString()
                : "unknown";

        List<String> alternatives = allIntentions.stream()
                .filter(i -> i != selected)
                .map(i -> i.peek() != null ? i.peek().getTrigger().toString() : "unknown")
                .collect(Collectors.toList());

        TraceEntry.Builder builder = new TraceEntry.Builder(
                getTS().getAgArch().getAgName(),
                TraceEntry.ChangerType.INTENTION_SELECTION,
                intentionContent
        )
                .cycleNumber(currentCycle)
                .alternativesNotSelected(alternatives)
                .result("success");

        addStateSnapshots(builder);
        traceLogger.log(builder.build());
    }

    // ========================================================================
    // BELIEF OPERATIONS
    // ========================================================================

    @Override
    public boolean addBel(Literal bel) throws RevisionFailedException {
        boolean result = super.addBel(bel);
        if (result) {
            logBeliefChange(TraceEntry.ChangerType.BELIEF_ADDITION, bel);
        }
        return result;
    }

    @Override
    public boolean delBel(Literal bel) throws RevisionFailedException {
        boolean result = super.delBel(bel);
        if (result) {
            logBeliefChange(TraceEntry.ChangerType.BELIEF_DELETION, bel);
        }
        return result;
    }

    protected void logBeliefChange(TraceEntry.ChangerType type, Literal bel) {
        TraceEntry.Builder builder = new TraceEntry.Builder(
                getTS().getAgArch().getAgName(),
                type,
                bel.toString()
        )
                .cycleNumber(currentCycle)
                .result("success");

        if (logBeliefSnapshots) {
            builder.beliefsSnapshot(getCurrentBeliefsAsList());
        }

        traceLogger.log(builder.build());
    }

    // ========================================================================
    // BODY INTERACTION LOGGING (VESNA-SPECIFIC)
    // ========================================================================

    /**
     * Override perform to log body actions sent to Godot/Unity
     */
    @Override
    public void perform(String action) {
        // Log the body action
        TraceEntry entry = new TraceEntry.Builder(
                getTS().getAgArch().getAgName(),
                TraceEntry.ChangerType.ACTION,
                "BODY_ACTION: " + action
        )
                .cycleNumber(currentCycle)
                .metadata("type=body_command")
                .result("sent")
                .build();

        traceLogger.log(entry);

        // Send to body
        super.perform(action);
    }

    /**
     * Override vesnaHandleMsg to log incoming body messages
     */
    @Override
    public void vesnaHandleMsg(String msg) {
        // Log the incoming body message
        TraceEntry entry = new TraceEntry.Builder(
                getTS().getAgArch().getAgName(),
                TraceEntry.ChangerType.MESSAGE_RECEIVED,
                "BODY_MESSAGE: " + msg
        )
                .cycleNumber(currentCycle)
                .metadata("type=body_perception")
                .result("received")
                .build();

        traceLogger.log(entry);

        // Process the message
        super.vesnaHandleMsg(msg);
    }

    // ========================================================================
    // REASONING CYCLE HOOK
    // ========================================================================

    public void onReasoningCycleStart() {
        currentCycle++;
    }

    // ========================================================================
    // STATE SNAPSHOT HELPERS
    // ========================================================================

    protected void addStateSnapshots(TraceEntry.Builder builder) {
        if (logBeliefSnapshots) {
            builder.beliefsSnapshot(getCurrentBeliefsAsList());
        }
        if (logIntentionSnapshots) {
            builder.intentionsSnapshot(getCurrentIntentionsAsList());
        }
        if (logEventSnapshots) {
            builder.eventsSnapshot(getCurrentEventsAsList());
        }
    }

    protected List<String> getCurrentBeliefsAsList() {
        List<String> beliefs = new ArrayList<>();
        BeliefBase bb = getBB();
        if (bb != null) {
            Iterator<Literal> it = bb.iterator();
            while (it.hasNext()) {
                beliefs.add(it.next().toString());
            }
        }
        return beliefs;
    }

    protected List<String> getCurrentIntentionsAsList() {
        List<String> intentions = new ArrayList<>();
        if (getTS() != null && getTS().getC() != null) {
            Iterator<Intention> it = getTS().getC().getAllIntentions();
            while (it.hasNext()) {
                Intention i = it.next();
                if (i.peek() != null) {
                    intentions.add(i.peek().getTrigger().toString());
                }
            }
        }
        return intentions;
    }

    /**
     * Get the current cycle number (for external access)
     */
    public long getCurrentCycle() {
        return currentCycle;
    }

    protected List<String> getCurrentEventsAsList() {
        List<String> events = new ArrayList<>();
        if (getTS() != null && getTS().getC() != null) {
            for (Event e : getTS().getC().getEvents()) {
                events.add(e.getTrigger().toString());
            }
        }
        return events;
    }

    protected String getInitialGoalsAsString() {
        List<String> goals = new ArrayList<>();
        if (getTS() != null && getTS().getC() != null) {
            for (Event e : getTS().getC().getEvents()) {
                goals.add(e.getTrigger().toString());
            }
        }
        return goals.isEmpty() ? "no initial goals" : String.join(", ", goals);
    }

    // ========================================================================
    // SHUTDOWN
    // ========================================================================

    public void stopAg() {
        String finalBeliefs = String.join(", ", getCurrentBeliefsAsList());
        traceLogger.logFinalState("Final beliefs: " + finalBeliefs);
        traceLogger.shutdown();
        logger.info("[NOVAE] Trace logging shutdown for embodied agent: " + getTS().getAgArch().getAgName());
    }

    // ========================================================================
    // PUBLIC ACCESSORS
    // ========================================================================

    public TraceLogger getTraceLogger() {
        return traceLogger;
    }

    public List<TraceEntry> getTraceEntries() {
        return traceLogger.getTraceEntries();
    }

    public String exportTraces(TraceLogger.OutputFormat format) {
        switch (format) {
            case JSON:
                return traceLogger.exportToJson();
            case PROLOG:
                return traceLogger.exportToProlog();
            default:
                return traceLogger.exportToConsole();
        }
    }

    public void logCustomEntry(String changerType, String content, String metadata) {
        TraceEntry.ChangerType type;
        try {
            type = TraceEntry.ChangerType.valueOf(changerType.toUpperCase());
        } catch (IllegalArgumentException e) {
            type = TraceEntry.ChangerType.REASONING_CYCLE;
        }

        TraceEntry.Builder builder = new TraceEntry.Builder(
                getTS().getAgArch().getAgName(),
                type,
                content
        )
                .cycleNumber(currentCycle)
                .metadata(metadata)
                .result("success");

        addStateSnapshots(builder);
        traceLogger.log(builder.build());
    }
}
