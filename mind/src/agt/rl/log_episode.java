package rl;

import jason.asSemantics.*;
import jason.asSyntax.*;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * Internal action to log episode results to CSV.
 * Appends one row per episode to logs/alice_episodes.csv.
 *
 * Usage in ASL:
 *   rl.log_episode(Episode, Start, Goal, Steps, Reward, Outcome)
 *
 * Where Outcome is "success" or "timeout".
 * Creates the file with headers if it doesn't exist.
 */
public class log_episode extends DefaultInternalAction {

    private static final String LOG_DIR = "logs";
    private static final String LOG_FILE = LOG_DIR + "/alice_episodes.csv";
    private static final String CSV_HEADER = "timestamp,episode,start,goal,steps,reward,outcome";
    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    @Override
    public Object execute(TransitionSystem ts, Unifier un, Term[] args) throws Exception {
        if (args.length < 6) {
            System.err.println("[log_episode] Expected 6 arguments: episode, start, goal, steps, reward, outcome");
            return false;
        }

        int episode = (int) ((NumberTerm) args[0]).solve();
        String start = args[1].toString();
        String goal = args[2].toString();
        int steps = (int) ((NumberTerm) args[3]).solve();
        double reward = ((NumberTerm) args[4]).solve();
        String outcome = args[5].toString();

        // Create logs directory if needed
        File dir = new File(LOG_DIR);
        if (!dir.exists()) {
            dir.mkdirs();
        }

        // Write header if file is new
        File logFile = new File(LOG_FILE);
        boolean writeHeader = !logFile.exists() || logFile.length() == 0;

        try (PrintWriter pw = new PrintWriter(new FileWriter(logFile, true))) {
            if (writeHeader) {
                pw.println(CSV_HEADER);
            }
            String timestamp = LocalDateTime.now().format(FMT);
            pw.println(String.format("%s,%d,%s,%s,%d,%.1f,%s",
                    timestamp, episode, start, goal, steps, reward, outcome));
        } catch (Exception e) {
            System.err.println("[log_episode] Failed to write CSV: " + e.getMessage());
            return false;
        }

        return true;
    }
}
