package rl;

import jason.asSemantics.*;
import jason.asSyntax.*;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.HashMap;

import org.json.JSONArray;
import org.json.JSONObject;

import vesna.TraceLogger;
import vesna.TraceEntry;

/**
 * Internal action to request action selection from RL service.
 *
 * This is a DOMAIN-AGNOSTIC HTTP client. It knows nothing about regions,
 * maps, or what the state/action vectors mean. All domain knowledge stays
 * in the ASL files.
 *
 * Usage in ASL:
 *   rl.select_action(StateVector, ValidActionIds, Reward, Done, ActionId)
 *
 * Example:
 *   rl.select_action([0,0,0,0,0,0,0,1,0,0,0], [1], -1.0, false, ActionId)
 *   // ActionId will be unified with the selected action (integer)
 *
 * The reward is computed in Jason (reward machine), NOT in Python.
 * The state encoding is done in Jason, NOT here.
 */
public class select_action extends DefaultInternalAction {

    private static final String RL_SERVICE_URL = "http://localhost:5000/select_action";
    private static final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .build();

    @Override
    public Object execute(TransitionSystem ts, Unifier un, Term[] args) throws Exception {
        // Args: StateVector (list), ValidActionIds (list of ints), Reward, Done, ActionId (output)
        if (args.length != 5) {
            throw new Exception("select_action requires 5 arguments: StateVector, ValidActionIds, Reward, Done, ActionId");
        }

        String agentName = ts.getAgArch().getAgName();
        ListTerm stateList = (ListTerm) args[0];
        ListTerm validActionsList = (ListTerm) args[1];
        double reward = ((NumberTerm) args[2]).solve();
        boolean done = args[3].toString().equals("true");

        // Build state vector from list
        JSONArray stateArray = new JSONArray();
        for (Term t : stateList) {
            if (t.isNumeric()) {
                stateArray.put(((NumberTerm) t).solve());
            } else {
                stateArray.put(Double.parseDouble(t.toString()));
            }
        }

        // Build valid actions array from list
        JSONArray validActionsArray = new JSONArray();
        for (Term t : validActionsList) {
            if (t.isNumeric()) {
                validActionsArray.put((int) ((NumberTerm) t).solve());
            } else {
                validActionsArray.put(Integer.parseInt(t.toString()));
            }
        }

        if (validActionsArray.isEmpty()) {
            throw new Exception("No valid actions provided");
        }

        // Build request JSON
        JSONObject requestBody = new JSONObject();
        requestBody.put("agent_id", agentName);
        requestBody.put("state", stateArray);
        requestBody.put("valid_actions", validActionsArray);
        requestBody.put("reward", reward);
        requestBody.put("done", done);

        // Send HTTP request
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(RL_SERVICE_URL))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(requestBody.toString()))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() != 200) {
            throw new Exception("RL service error: " + response.body());
        }

        // Parse response
        JSONObject responseJson = new JSONObject(response.body());
        int actionId = responseJson.getInt("action_id");

        // ====================================================================
        // EXPLAINABILITY: Log the decision with Q-values and alternatives
        // ====================================================================
        logRLDecision(agentName, stateArray, validActionsArray, reward, done, actionId, responseJson);

        // Return action ID as number (let ASL convert to region name)
        return un.unifies(args[4], ASSyntax.createNumber(actionId));
    }

    /**
     * Log the RL decision for explainability.
     * Creates a TraceEntry with:
     *   - Q-values for all valid actions
     *   - Why this action was selected
     *   - What alternatives were NOT selected (and why)
     */
    private void logRLDecision(String agentName, JSONArray state, JSONArray validActions,
                                double reward, boolean done, int actionId, JSONObject response) {
        try {
            TraceLogger logger = TraceLogger.getLogger(agentName);
            if (logger == null) {
                // Create logger if it doesn't exist
                logger = new TraceLogger(agentName);
                logger.setOutputFormat(TraceLogger.OutputFormat.JSON);
                logger.setOutputFilePath("logs/" + agentName + "_rl_trace.json");
            }

            // Extract explanation from response
            JSONObject explanation = response.optJSONObject("explanation");
            String mode = "unknown";
            String exploration = "unknown";
            double selectedQ = 0.0;
            Map<Integer, Double> qValues = new HashMap<>();

            if (explanation != null) {
                mode = explanation.optString("mode", "unknown");
                exploration = explanation.optString("exploration", "unknown");
                selectedQ = explanation.optDouble("selected_q", 0.0);

                // Parse Q-values for valid actions
                JSONObject qValuesJson = explanation.optJSONObject("q_values");
                if (qValuesJson != null) {
                    for (String key : qValuesJson.keySet()) {
                        qValues.put(Integer.parseInt(key), qValuesJson.getDouble(key));
                    }
                }
            }

            // Decode state: first 11 = current location, next 11 = goal
            int currentRegionId = -1;
            int goalRegionId = -1;
            for (int i = 0; i < 11 && i < state.length(); i++) {
                if (state.getDouble(i) > 0.5) currentRegionId = i;
            }
            for (int i = 11; i < 22 && i < state.length(); i++) {
                if (state.getDouble(i) > 0.5) goalRegionId = i - 11;
            }

            // Build explanation content
            StringBuilder content = new StringBuilder();
            content.append("RL_ACTION: ").append(actionId);
            content.append(" | from=").append(REGION_NAMES[currentRegionId]);
            content.append(" | goal=").append(REGION_NAMES[goalRegionId]);
            content.append(" | reward=").append(reward);
            content.append(" | mode=").append(mode);

            // Build alternatives (actions NOT selected)
            List<String> alternatives = new ArrayList<>();
            for (int i = 0; i < validActions.length(); i++) {
                int altAction = validActions.getInt(i);
                if (altAction != actionId) {
                    double altQ = qValues.getOrDefault(altAction, 0.0);
                    String reason = (altQ < selectedQ)
                        ? "Q=" + String.format("%.3f", altQ) + " < selected Q=" + String.format("%.3f", selectedQ)
                        : "not selected";
                    alternatives.add(REGION_NAMES[altAction] + " (" + reason + ")");
                }
            }

            // Build metadata with full Q-values
            StringBuilder metadata = new StringBuilder();
            metadata.append("Q-values: {");
            for (Map.Entry<Integer, Double> entry : qValues.entrySet()) {
                metadata.append(REGION_NAMES[entry.getKey()]).append("=");
                metadata.append(String.format("%.3f", entry.getValue()));
                if (entry.getKey() == actionId) metadata.append("*");  // Mark selected
                metadata.append(", ");
            }
            metadata.append("} | exploration=").append(exploration);

            // Create and log the trace entry
            TraceEntry entry = new TraceEntry.Builder(agentName, TraceEntry.ChangerType.ACTION, content.toString())
                .alternativesNotSelected(alternatives)
                .result(done ? "episode_end" : "success")
                .metadata(metadata.toString())
                .build();

            logger.log(entry);

        } catch (Exception e) {
            System.err.println("[RL TRACE] Failed to log decision: " + e.getMessage());
        }
    }

    // Region name lookup for explainability
    private static final String[] REGION_NAMES = {
        "reception",       // 0
        "corridor",        // 1
        "open_office",     // 2
        "outside",         // 3
        "common",          // 4
        "meeting_room",    // 5
        "senior_office_1", // 6
        "senior_office_2", // 7
        "senior_office_3", // 8
        "boss_office_1",   // 9
        "boss_office_2"    // 10
    };
}
