package vesna;

/**
 * ============================================================================
 * NOVAE TRACE LOGGER - TraceLogger
 * ============================================================================
 *
 * This class manages the collection and storage of execution traces.
 * It acts as the "Trace Logger" component in the NOVAE architecture diagram.
 *
 * Features:
 *   - Collects TraceEntry objects during agent execution
 *   - Supports multiple output formats (JSON, Prolog, Console)
 *   - Can write traces to files for offline analysis
 *   - Thread-safe for multi-agent systems
 *   - Configurable filtering (log only certain types of changers)
 *
 * Usage in .jcm configuration:
 *   agent alice:alice.asl {
 *       agentClass: vesna.LoggedAgent
 *       agentArchClass: vesna.LoggedAgArch
 *       trace_output: "logs/alice_trace.json"    // optional
 *       trace_format: "json"                      // json, prolog, or console
 *       trace_beliefs: true                       // include belief snapshots
 *   }
 *
 * Reference: "The Secret Life of Traces" - NOVAE Framework Paper
 *
 * @author NOVAE Team (Implementation for Vesna)
 * @see TraceEntry
 * @see LoggedAgent
 * @see LoggedAgArch
 * ============================================================================
 */

import java.io.*;
import java.nio.file.*;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.logging.Logger;
import java.util.stream.Collectors;

public class TraceLogger {

  // ========================================================================
  // CONFIGURATION
  // ========================================================================

  public enum OutputFormat {
    JSON, // For external tools, ML pipelines
    PROLOG, // For BDIExplainer / AgentSpeaX
    CONSOLE, // Human-readable console output
    ALL // Output in all formats
  }

  // ========================================================================
  // INSTANCE FIELDS
  // ========================================================================

  /** Name of the agent this logger belongs to */
  private final String agentName;

  /** Thread-safe collection of trace entries */
  private final CopyOnWriteArrayList<TraceEntry> traceEntries;

  /** Output format for this logger */
  private OutputFormat outputFormat = OutputFormat.CONSOLE;

  /** Path to output file (if file output is enabled) */
  private String outputFilePath = null;

  /** Whether to include belief snapshots in traces */
  private boolean includeBeliefs = true;

  /** Whether to include intention snapshots in traces */
  private boolean includeIntentions = true;

  /** Whether to include event queue snapshots in traces */
  private boolean includeEvents = false;

  /** Whether to log to console in real-time */
  private boolean realTimeConsoleOutput = true;

  /** Logger for this class */
  private Logger logger;

  /** Filter: which changer types to log (null = log all) */
  private Set<TraceEntry.ChangerType> changerTypeFilter = null;

  /** Run event that started this trace */
  private String runEvent = null;

  /** Final state when execution completes */
  private String finalState = null;

  // ========================================================================
  // STATIC REGISTRY FOR MULTI-AGENT SYSTEMS
  // ========================================================================

  /**
   * Registry of all trace loggers in the system.
   * Allows collecting traces from all agents for MAS-level analysis.
   */
  private static final Map<String, TraceLogger> loggerRegistry = new ConcurrentHashMap<>();

  /**
   * Get the trace logger for a specific agent
   */
  public static TraceLogger getLogger(String agentName) {
    return loggerRegistry.get(agentName);
  }

  /**
   * Get all registered trace loggers
   */
  public static Collection<TraceLogger> getAllLoggers() {
    return loggerRegistry.values();
  }

  /**
   * Collect all traces from all agents (for MAS-level analysis)
   */
  public static List<TraceEntry> getAllTraces() {
    return loggerRegistry.values().stream()
        .flatMap(logger -> logger.getTraceEntries().stream())
        .sorted(Comparator.comparing(TraceEntry::getTimestamp))
        .collect(Collectors.toList());
  }

  // ========================================================================
  // CONSTRUCTOR
  // ========================================================================

  /**
   * Create a new TraceLogger for an agent
   *
   * @param agentName Name of the agent
   */
  public TraceLogger(String agentName) {
    this.agentName = agentName;
    this.traceEntries = new CopyOnWriteArrayList<>();
    this.logger = Logger.getLogger("TraceLogger." + agentName);

    // Register this logger
    loggerRegistry.put(agentName, this);

    logger.info("[TRACE LOGGER] Initialized for agent: " + agentName);
  }

  /**
   * Create a new TraceLogger with custom configuration
   *
   * @param agentName    Name of the agent
   * @param outputFormat Output format
   * @param outputPath   Path to output file (can be null)
   */
  public TraceLogger(String agentName, OutputFormat outputFormat, String outputPath) {
    this(agentName);
    this.outputFormat = outputFormat;
    this.outputFilePath = outputPath;
  }

  // ========================================================================
  // CONFIGURATION METHODS
  // ========================================================================

  public TraceLogger setOutputFormat(OutputFormat format) {
    this.outputFormat = format;
    return this;
  }

  public TraceLogger setOutputFilePath(String path) {
    this.outputFilePath = path;
    return this;
  }

  public TraceLogger setIncludeBeliefs(boolean include) {
    this.includeBeliefs = include;
    return this;
  }

  public TraceLogger setIncludeIntentions(boolean include) {
    this.includeIntentions = include;
    return this;
  }

  public TraceLogger setIncludeEvents(boolean include) {
    this.includeEvents = include;
    return this;
  }

  public TraceLogger setRealTimeConsoleOutput(boolean enabled) {
    this.realTimeConsoleOutput = enabled;
    return this;
  }

  /**
   * Set filter to only log specific changer types
   *
   * @param types The changer types to log (null = log all)
   */
  public TraceLogger setChangerTypeFilter(TraceEntry.ChangerType... types) {
    if (types == null || types.length == 0) {
      this.changerTypeFilter = null;
    } else {
      this.changerTypeFilter = new HashSet<>(Arrays.asList(types));
    }
    return this;
  }

  // ========================================================================
  // LOGGING METHODS
  // ========================================================================

  /** Max entries to keep in memory (prevents OOM during long training runs) */
  private int maxInMemoryEntries = 1000;

  /**
   * Set the maximum number of trace entries to keep in memory.
   * Older entries are discarded (they are still written to file if configured).
   * Set to 0 to disable in-memory storage entirely (file-only mode).
   */
  public TraceLogger setMaxInMemoryEntries(int max) {
    this.maxInMemoryEntries = max;
    return this;
  }

  /**
   * Log a trace entry
   *
   * @param entry The trace entry to log
   */
  public void log(TraceEntry entry) {
    // Check filter
    if (changerTypeFilter != null && !changerTypeFilter.contains(entry.getChangerType())) {
      return;
    }

    // Add to in-memory collection (with cap to prevent OOM)
    if (maxInMemoryEntries > 0) {
      if (traceEntries.size() >= maxInMemoryEntries) {
        // Remove oldest entries in bulk (clear half) to avoid doing this every call
        int removeCount = maxInMemoryEntries / 2;
        for (int i = 0; i < removeCount && !traceEntries.isEmpty(); i++) {
          traceEntries.remove(0);
        }
      }
      traceEntries.add(entry);
    }

    // Real-time console output
    if (realTimeConsoleOutput) {
      System.out.println(entry.toString());
    }

    // Write to file if configured
    if (outputFilePath != null) {
      appendToFile(entry);
    }
  }

  /**
   * Log the run event (start of execution)
   *
   * @param runEvent Description of the run event (e.g., initial goals)
   */
  public void logRunEvent(String runEvent) {
    this.runEvent = runEvent;
    logger.info("[TRACE] Run event: " + runEvent);

    TraceEntry entry = new TraceEntry.Builder(agentName, TraceEntry.ChangerType.REASONING_CYCLE,
        "RUN_EVENT: " + runEvent)
        .cycleNumber(0)
        .result("started")
        .build();
    log(entry);
  }

  /**
   * Log the final state (end of execution)
   *
   * @param finalState Description of the final state
   */
  public void logFinalState(String finalState) {
    this.finalState = finalState;
    logger.info("[TRACE] Final state: " + finalState);

    TraceEntry entry = new TraceEntry.Builder(agentName, TraceEntry.ChangerType.REASONING_CYCLE,
        "FINAL_STATE: " + finalState)
        .cycleNumber(-1)
        .result("completed")
        .build();
    log(entry);
  }

  // ========================================================================
  // OUTPUT METHODS
  // ========================================================================

  /**
   * Get all trace entries
   */
  public List<TraceEntry> getTraceEntries() {
    return new ArrayList<>(traceEntries);
  }

  /**
   * Export all traces to JSON format
   */
  public String exportToJson() {
    StringBuilder sb = new StringBuilder();
    sb.append("{\n");
    sb.append("  \"agent\": \"").append(agentName).append("\",\n");
    sb.append("  \"runEvent\": \"").append(runEvent != null ? runEvent : "").append("\",\n");
    sb.append("  \"finalState\": \"").append(finalState != null ? finalState : "").append("\",\n");
    sb.append("  \"traceCount\": ").append(traceEntries.size()).append(",\n");
    sb.append("  \"traces\": [\n");

    for (int i = 0; i < traceEntries.size(); i++) {
      sb.append("    ").append(traceEntries.get(i).toJson().replace("\n", "\n    "));
      if (i < traceEntries.size() - 1) {
        sb.append(",");
      }
      sb.append("\n");
    }

    sb.append("  ]\n");
    sb.append("}\n");
    return sb.toString();
  }

  /**
   * Export all traces to Prolog format (for BDIExplainer)
   */
  public String exportToProlog() {
    StringBuilder sb = new StringBuilder();
    sb.append("% ============================================================================\n");
    sb.append("% NOVAE Trace Export - Agent: ").append(agentName).append("\n");
    sb.append("% Generated: ").append(Instant.now().toString()).append("\n");
    sb.append("% ============================================================================\n\n");

    if (runEvent != null) {
      sb.append("% Run event\n");
      sb.append("run_event('").append(agentName).append("', '").append(escapeProlog(runEvent)).append("').\n\n");
    }

    sb.append("% Trace entries\n");
    for (TraceEntry entry : traceEntries) {
      sb.append(entry.toProlog()).append("\n");
    }

    if (finalState != null) {
      sb.append("\n% Final state\n");
      sb.append("final_state('").append(agentName).append("', '").append(escapeProlog(finalState)).append("').\n");
    }

    return sb.toString();
  }

  /**
   * Export to console-friendly format
   */
  public String exportToConsole() {
    StringBuilder sb = new StringBuilder();
    sb.append("=".repeat(80)).append("\n");
    sb.append("NOVAE TRACE - Agent: ").append(agentName).append("\n");
    sb.append("=".repeat(80)).append("\n\n");

    if (runEvent != null) {
      sb.append("Run Event: ").append(runEvent).append("\n\n");
    }

    sb.append("Trace Entries (").append(traceEntries.size()).append(" total):\n");
    sb.append("-".repeat(80)).append("\n");

    for (TraceEntry entry : traceEntries) {
      sb.append(entry.toString()).append("\n");
    }

    sb.append("-".repeat(80)).append("\n");

    if (finalState != null) {
      sb.append("\nFinal State: ").append(finalState).append("\n");
    }

    return sb.toString();
  }

  /**
   * Write all traces to a file
   *
   * @param filePath Path to the output file
   * @param format   Output format
   */
  public void writeToFile(String filePath, OutputFormat format) {
    String content;
    switch (format) {
      case JSON:
        content = exportToJson();
        break;
      case PROLOG:
        content = exportToProlog();
        break;
      case CONSOLE:
      default:
        content = exportToConsole();
        break;
    }

    try {
      Path path = Paths.get(filePath);
      Files.createDirectories(path.getParent());
      Files.writeString(path, content);
      logger.info("[TRACE] Written to file: " + filePath);
    } catch (IOException e) {
      logger.severe("[TRACE] Failed to write to file: " + e.getMessage());
    }
  }

  /**
   * Append a single entry to the output file
   */
  private void appendToFile(TraceEntry entry) {
    if (outputFilePath == null)
      return;

    try {
      String content;
      switch (outputFormat) {
        case JSON:
          content = entry.toJson() + ",\n";
          break;
        case PROLOG:
          content = entry.toProlog();
          break;
        default:
          content = entry.toString() + "\n";
          break;
      }

      Path path = Paths.get(outputFilePath);
      Files.createDirectories(path.getParent());
      Files.writeString(path, content, StandardOpenOption.CREATE, StandardOpenOption.APPEND);
    } catch (IOException e) {
      logger.warning("[TRACE] Failed to append to file: " + e.getMessage());
    }
  }

  // ========================================================================
  // UTILITY METHODS
  // ========================================================================

  /**
   * Clear all trace entries
   */
  public void clear() {
    traceEntries.clear();
    runEvent = null;
    finalState = null;
  }

  /**
   * Get the number of trace entries
   */
  public int size() {
    return traceEntries.size();
  }

  /**
   * Unregister this logger (call on agent termination)
   */
  public void shutdown() {
    // Write final traces if file output is enabled
    if (outputFilePath != null && outputFormat != OutputFormat.CONSOLE) {
      writeToFile(outputFilePath, outputFormat);
    }

    loggerRegistry.remove(agentName);
    logger.info("[TRACE LOGGER] Shutdown for agent: " + agentName);
  }

  private String escapeProlog(String s) {
    if (s == null)
      return "";
    return s.replace("'", "\\'").replace("\n", " ").replace("\r", "");
  }

  // ========================================================================
  // GETTERS
  // ========================================================================

  public String getAgentName() {
    return agentName;
  }

  public OutputFormat getOutputFormat() {
    return outputFormat;
  }

  public String getOutputFilePath() {
    return outputFilePath;
  }

  public boolean isIncludeBeliefs() {
    return includeBeliefs;
  }

  public boolean isIncludeIntentions() {
    return includeIntentions;
  }

  public boolean isIncludeEvents() {
    return includeEvents;
  }

  public String getRunEvent() {
    return runEvent;
  }

  public String getFinalState() {
    return finalState;
  }
}

// ============================================================================
// CONCURRENT HASH MAP IMPORT (needed at top of file, adding here for reference)
// ============================================================================
// Note: Add this import at the top: import
// java.util.concurrent.ConcurrentHashMap;
