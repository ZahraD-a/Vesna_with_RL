package vesna;

/**
 * ============================================================================
 * NOVAE TRACE LOGGER - TraceEntry
 * ============================================================================
 *
 * This class represents a single entry in the execution trace.
 * Based on the NOVAE framework paper: "The Secret Life of Traces"
 *
 * A NOVAE trace entry captures:
 *   - STATE: The agent's state before the changer (beliefs, intentions, events)
 *   - CHANGER: What caused the state change (action, plan selection, belief update, goal)
 *   - ALTERNATIVES: Other options that were NOT selected (for "Why not Y?" questions)
 *
 * Reference: Winikoff, M. (2024). "Towards Engineering Explainable Autonomous Systems"
 *            https://link.springer.com/chapter/10.1007/978-3-031-71152-7_9
 * Author: Abdulhamid Mohammed Mousa Ahmed Mousa , creator of this TraceLogger
 *
 * @author NOVAE Team (Implementation for Vesna)
 * @see TraceLogger
 * @see LoggedAgent
 * ============================================================================
 */

import jason.asSyntax.*;
import jason.asSemantics.*;
import java.util.List;
import java.util.ArrayList;
import java.util.stream.Collectors;
import java.time.Instant;

public class TraceEntry {

    // ========================================================================
    // TRACE ENTRY TYPES
    // ========================================================================

    public enum ChangerType {
        ACTION,              // External action on environment
        INTERNAL_ACTION,     // Internal action (.print, .send, etc.)
        PLAN_SELECTION,      // A plan was selected from applicable plans
        BELIEF_ADDITION,     // Belief added to belief base
        BELIEF_DELETION,     // Belief removed from belief base
        GOAL_ADDITION,       // Achievement goal added
        GOAL_DELETION,       // Goal dropped
        EVENT_ADDITION,      // Event added to event queue
        INTENTION_SELECTION, // Intention selected from intention queue
        INTENTION_FINISHED,  // Intention completed
        INTENTION_FAILED,    // Intention failed
        MESSAGE_SENT,        // Message sent to another agent
        MESSAGE_RECEIVED,    // Message received from another agent
        REASONING_CYCLE      // Complete reasoning cycle snapshot
    }

    // ========================================================================
    // TRACE ENTRY FIELDS
    // ========================================================================

    /** Unique identifier for this trace entry */
    private final long id;

    /** Timestamp when this entry was created */
    private final Instant timestamp;

    /** The reasoning cycle number */
    private final long cycleNumber;

    /** Name of the agent that generated this trace */
    private final String agentName;

    /** Type of changer that caused this trace entry */
    private final ChangerType changerType;

    /** The changer content (action, plan, belief, etc.) as string */
    private final String changerContent;

    /** The plan that was used (if applicable) */
    private final String planUsed;

    /** The trigger that caused this (if applicable) */
    private final String trigger;

    /** Context/guard that was evaluated (if applicable) */
    private final String contextEvaluated;

    /** Alternatives that were NOT selected - crucial for "Why not Y?" questions */
    private final List<String> alternativesNotSelected;

    /** Current beliefs snapshot (can be filtered for relevance) */
    private final List<String> beliefsSnapshot;

    /** Current intentions snapshot */
    private final List<String> intentionsSnapshot;

    /** Current events queue snapshot */
    private final List<String> eventsSnapshot;

    /** Result of the changer execution */
    private final String result; // "success", "failure", "pending"

    /** Additional metadata */
    private final String metadata;

    // ========================================================================
    // STATIC COUNTER FOR UNIQUE IDS
    // ========================================================================

    private static long idCounter = 0;

    // ========================================================================
    // CONSTRUCTOR
    // ========================================================================

    private TraceEntry(Builder builder) {
        this.id = ++idCounter;
        this.timestamp = Instant.now();
        this.cycleNumber = builder.cycleNumber;
        this.agentName = builder.agentName;
        this.changerType = builder.changerType;
        this.changerContent = builder.changerContent;
        this.planUsed = builder.planUsed;
        this.trigger = builder.trigger;
        this.contextEvaluated = builder.contextEvaluated;
        this.alternativesNotSelected = builder.alternativesNotSelected != null
            ? new ArrayList<>(builder.alternativesNotSelected)
            : new ArrayList<>();
        this.beliefsSnapshot = builder.beliefsSnapshot != null
            ? new ArrayList<>(builder.beliefsSnapshot)
            : new ArrayList<>();
        this.intentionsSnapshot = builder.intentionsSnapshot != null
            ? new ArrayList<>(builder.intentionsSnapshot)
            : new ArrayList<>();
        this.eventsSnapshot = builder.eventsSnapshot != null
            ? new ArrayList<>(builder.eventsSnapshot)
            : new ArrayList<>();
        this.result = builder.result;
        this.metadata = builder.metadata;
    }

    // ========================================================================
    // BUILDER PATTERN - For flexible trace entry creation
    // ========================================================================

    public static class Builder {
        private long cycleNumber;
        private String agentName;
        private ChangerType changerType;
        private String changerContent;
        private String planUsed;
        private String trigger;
        private String contextEvaluated;
        private List<String> alternativesNotSelected;
        private List<String> beliefsSnapshot;
        private List<String> intentionsSnapshot;
        private List<String> eventsSnapshot;
        private String result = "success";
        private String metadata;

        public Builder(String agentName, ChangerType changerType, String changerContent) {
            this.agentName = agentName;
            this.changerType = changerType;
            this.changerContent = changerContent;
        }

        public Builder cycleNumber(long cycleNumber) {
            this.cycleNumber = cycleNumber;
            return this;
        }

        public Builder planUsed(String planUsed) {
            this.planUsed = planUsed;
            return this;
        }

        public Builder trigger(String trigger) {
            this.trigger = trigger;
            return this;
        }

        public Builder contextEvaluated(String contextEvaluated) {
            this.contextEvaluated = contextEvaluated;
            return this;
        }

        public Builder alternativesNotSelected(List<String> alternatives) {
            this.alternativesNotSelected = alternatives;
            return this;
        }

        public Builder beliefsSnapshot(List<String> beliefs) {
            this.beliefsSnapshot = beliefs;
            return this;
        }

        public Builder intentionsSnapshot(List<String> intentions) {
            this.intentionsSnapshot = intentions;
            return this;
        }

        public Builder eventsSnapshot(List<String> events) {
            this.eventsSnapshot = events;
            return this;
        }

        public Builder result(String result) {
            this.result = result;
            return this;
        }

        public Builder metadata(String metadata) {
            this.metadata = metadata;
            return this;
        }

        public TraceEntry build() {
            return new TraceEntry(this);
        }
    }

    // ========================================================================
    // GETTERS
    // ========================================================================

    public long getId() { return id; }
    public Instant getTimestamp() { return timestamp; }
    public long getCycleNumber() { return cycleNumber; }
    public String getAgentName() { return agentName; }
    public ChangerType getChangerType() { return changerType; }
    public String getChangerContent() { return changerContent; }
    public String getPlanUsed() { return planUsed; }
    public String getTrigger() { return trigger; }
    public String getContextEvaluated() { return contextEvaluated; }
    public List<String> getAlternativesNotSelected() { return new ArrayList<>(alternativesNotSelected); }
    public List<String> getBeliefsSnapshot() { return new ArrayList<>(beliefsSnapshot); }
    public List<String> getIntentionsSnapshot() { return new ArrayList<>(intentionsSnapshot); }
    public List<String> getEventsSnapshot() { return new ArrayList<>(eventsSnapshot); }
    public String getResult() { return result; }
    public String getMetadata() { return metadata; }

    // ========================================================================
    // OUTPUT FORMATS
    // ========================================================================

    /**
     * Convert to JSON format for external processing
     */
    public String toJson() {
        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        sb.append("  \"id\": ").append(id).append(",\n");
        sb.append("  \"timestamp\": \"").append(timestamp.toString()).append("\",\n");
        sb.append("  \"cycle\": ").append(cycleNumber).append(",\n");
        sb.append("  \"agent\": \"").append(agentName).append("\",\n");
        sb.append("  \"changerType\": \"").append(changerType.name()).append("\",\n");
        sb.append("  \"changerContent\": \"").append(escapeJson(changerContent)).append("\",\n");

        if (planUsed != null) {
            sb.append("  \"planUsed\": \"").append(escapeJson(planUsed)).append("\",\n");
        }
        if (trigger != null) {
            sb.append("  \"trigger\": \"").append(escapeJson(trigger)).append("\",\n");
        }
        if (contextEvaluated != null) {
            sb.append("  \"contextEvaluated\": \"").append(escapeJson(contextEvaluated)).append("\",\n");
        }

        sb.append("  \"alternativesNotSelected\": ").append(listToJsonArray(alternativesNotSelected)).append(",\n");
        sb.append("  \"beliefs\": ").append(listToJsonArray(beliefsSnapshot)).append(",\n");
        sb.append("  \"intentions\": ").append(listToJsonArray(intentionsSnapshot)).append(",\n");
        sb.append("  \"events\": ").append(listToJsonArray(eventsSnapshot)).append(",\n");
        sb.append("  \"result\": \"").append(result).append("\"");

        if (metadata != null) {
            sb.append(",\n  \"metadata\": \"").append(escapeJson(metadata)).append("\"");
        }

        sb.append("\n}");
        return sb.toString();
    }

    /**
     * Convert to Prolog format for the BDIExplainer
     * This format is compatible with AgentSpeaX explainer
     */
    public String toProlog() {
        StringBuilder sb = new StringBuilder();
        sb.append("% Trace entry ").append(id).append(" at cycle ").append(cycleNumber).append("\n");
        sb.append("trace_entry(").append(id).append(", ");
        sb.append(cycleNumber).append(", ");
        sb.append("'").append(agentName).append("', ");
        sb.append(changerType.name().toLowerCase()).append(", ");
        sb.append("'").append(escapeProlog(changerContent)).append("'");

        if (planUsed != null) {
            sb.append(", plan('").append(escapeProlog(planUsed)).append("')");
        }

        sb.append(").\n");

        // Add alternatives as separate facts (for "Why not?" queries)
        for (String alt : alternativesNotSelected) {
            sb.append("alternative_not_selected(").append(id).append(", '");
            sb.append(escapeProlog(alt)).append("').\n");
        }

        // Add beliefs snapshot
        for (String belief : beliefsSnapshot) {
            sb.append("belief_at(").append(id).append(", '");
            sb.append(escapeProlog(belief)).append("').\n");
        }

        return sb.toString();
    }

    /**
     * Human-readable format for console output
     */
    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("[TRACE #").append(id).append("] ");
        sb.append("Cycle ").append(cycleNumber).append(" | ");
        sb.append(agentName).append(" | ");
        sb.append(changerType.name()).append(": ");
        sb.append(changerContent);

        if (!alternativesNotSelected.isEmpty()) {
            sb.append(" (").append(alternativesNotSelected.size()).append(" alternatives not selected)");
        }

        return sb.toString();
    }

    // ========================================================================
    // HELPER METHODS
    // ========================================================================

    private String escapeJson(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }

    private String escapeProlog(String s) {
        if (s == null) return "";
        return s.replace("'", "\\'")
                .replace("\n", " ")
                .replace("\r", "");
    }

    private String listToJsonArray(List<String> list) {
        if (list == null || list.isEmpty()) {
            return "[]";
        }
        return "[" + list.stream()
                .map(s -> "\"" + escapeJson(s) + "\"")
                .collect(Collectors.joining(", ")) + "]";
    }
}
