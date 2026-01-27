package vesna;

/**
 * ============================================================================
 * NOVAE TRACE LOGGER - LoggedAgent
 * ============================================================================
 *
 * This class extends Jason's Agent class to add trace logging capabilities.
 * It captures the "State" and "Changer" information needed for:
 *   - Runtime Verification (RV)
 *   - Explainability (answering "Why X?" and "Why not Y?" questions)
 *   - Learning from traces
 *
 * What is logged:
 *   - Plan selections (with alternatives not selected)
 *   - Belief additions and deletions
 *   - Goal additions
 *   - Intention selections
 *   - Internal action executions
 *
 * Usage in .jcm configuration:
 * <pre>
 *   agent r1:r1.asl {
 *       agentClass: vesna.LoggedAgent
 *       agentArchClass: vesna.LoggedAgArch
 *   }
 * </pre>
 *
 * Or for Vesna embodied agents:
 * <pre>
 *   agent alice:alice.asl {
 *       agentClass: vesna.LoggedVesnaAgent   // If you need both Vesna + Logging
 *       agentArchClass: vesna.LoggedAgArch
 *       address: localhost
 *       port: 9080
 *   }
 * </pre>
 *
 * Reference:
 *   - "The Secret Life of Traces" - NOVAE Framework Paper
 *   - Winikoff (2024) "Towards Engineering Explainable Autonomous Systems"
 *
 * @author NOVAE Team (Implementation for Vesna)
 * @see TraceLogger
 * @see TraceEntry
 * @see LoggedAgArch
 * ============================================================================
 */

import jason.asSemantics.*;
import jason.asSyntax.*;
import jason.bb.BeliefBase;
import jason.RevisionFailedException;
import jason.runtime.Settings;

import java.util.*;
import java.util.logging.Logger;
import java.util.stream.Collectors;

public class LoggedAgent extends Agent {

    // ========================================================================
    // NOVAE TRACE LOGGER FIELDS
    // ========================================================================

    /** The trace logger instance for this agent */
    protected TraceLogger traceLogger;

    /** Current reasoning cycle number */
    protected long currentCycle = 0;

    /** Logger for console output */
    protected transient Logger logger;

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
     * Initialize the agent with trace logging capabilities.
     * Override this method to add custom initialization.
     */
    @Override
    public void initAg() {
        super.initAg();

        // Get agent name and initialize logger
        String agentName = getTS().getAgArch().getAgName();
        logger = getTS().getLogger();

        // Read configuration from settings
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

        logger.info("[NOVAE] Trace logging initialized for agent: " + agentName);
    }

    /**
     * Read trace configuration from agent settings
     */
    protected void readTraceConfiguration(Settings stts) {
        // Read trace output format
        String formatStr = stts.getUserParameter("trace_format");
        if (formatStr != null) {
            try {
                traceOutputFormat = TraceLogger.OutputFormat.valueOf(formatStr.toUpperCase());
            } catch (IllegalArgumentException e) {
                logger.warning("[NOVAE] Invalid trace_format: " + formatStr + ", using CONSOLE");
            }
        }

        // Read trace output path
        traceOutputPath = stts.getUserParameter("trace_output");

        // Read what to include in traces
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
    // PLAN SELECTION - CRUCIAL FOR "WHY NOT Y?" QUESTIONS
    // ========================================================================

    /**
     * Override selectOption to log plan selection with alternatives.
     * This is crucial for answering "Why not Y?" questions - we need to know
     * what alternatives existed and were NOT selected.
     *
     * @param options List of applicable options (plans with unifiers)
     * @return The selected option
     */
    @Override
    public Option selectOption(List<Option> options) {
        // Let the parent class select the option
        Option selected = super.selectOption(options);

        if (selected != null && options.size() > 0) {
            // Log the plan selection with alternatives
            logPlanSelection(selected, options);
        }

        return selected;
    }

    /**
     * Log a plan selection event with all alternatives
     */
    protected void logPlanSelection(Option selected, List<Option> allOptions) {
        // Get the selected plan details
        Plan selectedPlan = selected.getPlan();
        String planContent = selectedPlan.toASString();
        String trigger = selectedPlan.getTrigger().toString();
        String context = selectedPlan.getContext() != null ? selectedPlan.getContext().toString() : "true";

        // Get alternatives (plans that were NOT selected)
        List<String> alternatives = allOptions.stream()
                .filter(opt -> opt != selected)
                .map(opt -> opt.getPlan().toASString())
                .collect(Collectors.toList());

        // Build the trace entry
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

        // Add state snapshots if configured
        addStateSnapshots(builder);

        // Log the entry
        traceLogger.log(builder.build());
    }

    // ========================================================================
    // INTENTION SELECTION
    // ========================================================================

    /**
     * Override selectIntention to log intention selection.
     *
     * @param intentions Queue of intentions to choose from
     * @return The selected intention
     */
    @Override
    public Intention selectIntention(Queue<Intention> intentions) {
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

    /**
     * Override addBel to log belief additions.
     *
     * @param bel The belief to add
     * @return true if belief was added
     */
    @Override
    public boolean addBel(Literal bel) throws RevisionFailedException {
        boolean result = super.addBel(bel);

        if (result) {
            logBeliefChange(TraceEntry.ChangerType.BELIEF_ADDITION, bel);
        }

        return result;
    }

    /**
     * Override delBel to log belief deletions.
     *
     * @param bel The belief to delete
     * @return true if belief was deleted
     */
    @Override
    public boolean delBel(Literal bel) throws RevisionFailedException {
        boolean result = super.delBel(bel);

        if (result) {
            logBeliefChange(TraceEntry.ChangerType.BELIEF_DELETION, bel);
        }

        return result;
    }

    /**
     * Log a belief change event
     */
    protected void logBeliefChange(TraceEntry.ChangerType type, Literal bel) {
        TraceEntry.Builder builder = new TraceEntry.Builder(
                getTS().getAgArch().getAgName(),
                type,
                bel.toString()
        )
                .cycleNumber(currentCycle)
                .result("success");

        // Only add belief snapshot for belief changes if configured
        if (logBeliefSnapshots) {
            builder.beliefsSnapshot(getCurrentBeliefsAsList());
        }

        traceLogger.log(builder.build());
    }

    // ========================================================================
    // REASONING CYCLE HOOK
    // ========================================================================

    /**
     * Called at the beginning of each reasoning cycle.
     * Override to add custom cycle start behavior.
     */
    public void onReasoningCycleStart() {
        currentCycle++;

        // Log reasoning cycle start (optional - can be verbose)
        // Uncomment if you want to log every cycle:
        /*
        TraceEntry.Builder builder = new TraceEntry.Builder(
                getTS().getAgArch().getAgName(),
                TraceEntry.ChangerType.REASONING_CYCLE,
                "Cycle " + currentCycle + " started"
        )
                .cycleNumber(currentCycle);
        addStateSnapshots(builder);
        traceLogger.log(builder.build());
        */
    }

    // ========================================================================
    // STATE SNAPSHOT HELPERS
    // ========================================================================

    /**
     * Add current state snapshots to a trace entry builder
     */
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

    /**
     * Get current beliefs as a list of strings
     */
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

    /**
     * Get current intentions as a list of strings
     */
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

    /**
     * Get current events as a list of strings
     */
    protected List<String> getCurrentEventsAsList() {
        List<String> events = new ArrayList<>();
        if (getTS() != null && getTS().getC() != null) {
            for (Event e : getTS().getC().getEvents()) {
                events.add(e.getTrigger().toString());
            }
        }
        return events;
    }

    /**
     * Get initial goals as a string (for run event logging)
     */
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

    /**
     * Called when the agent is being stopped.
     * Exports final traces and cleans up.
     */
    public void stopAg() {
        // Log final state
        String finalBeliefs = String.join(", ", getCurrentBeliefsAsList());
        traceLogger.logFinalState("Final beliefs: " + finalBeliefs);

        // Shutdown the trace logger (writes to file if configured)
        traceLogger.shutdown();

        logger.info("[NOVAE] Trace logging shutdown for agent: " + getTS().getAgArch().getAgName());
    }

    // ========================================================================
    // PUBLIC ACCESSORS
    // ========================================================================

    /**
     * Get the trace logger for external access
     */
    public TraceLogger getTraceLogger() {
        return traceLogger;
    }

    /**
     * Get all trace entries
     */
    public List<TraceEntry> getTraceEntries() {
        return traceLogger.getTraceEntries();
    }

    /**
     * Export traces to a specific format
     */
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

    /**
     * Manually log a custom trace entry (for use in plans/internal actions)
     */
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
