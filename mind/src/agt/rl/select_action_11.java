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
 * Internal action: select_action_11 — RL action selection for 11 region map.
 *
 * Used by: bridge_11.asl
 * Checkpoint: alice11.pt
 *
 * Usage in ASL:
 *   rl.select_action_11(StateVector, ValidActionIds, Reward, Done, ActionId)
 */
public class select_action_11 extends DefaultInternalAction {

    private static final String RL_SERVICE_URL = System.getenv().getOrDefault(
        "RL_SERVICE_URL", "http://localhost:5000/select_action");
    private static final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .build();

    @Override
    public Object execute(TransitionSystem ts, Unifier un, Term[] args) throws Exception {
        if (args.length != 5) {
            throw new Exception("select_action_11 requires 5 arguments: StateVector, ValidActionIds, Reward, Done, ActionId");
        }

        String agentName = ts.getAgArch().getAgName();
        ListTerm stateList = (ListTerm) args[0];
        ListTerm validActionsList = (ListTerm) args[1];
        double reward = ((NumberTerm) args[2]).solve();
        boolean done = args[3].toString().equals("true");

        JSONArray stateArray = new JSONArray();
        for (Term t : stateList) {
            if (t.isNumeric()) {
                stateArray.put(((NumberTerm) t).solve());
            } else {
                stateArray.put(Double.parseDouble(t.toString()));
            }
        }

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

        JSONObject requestBody = new JSONObject();
        requestBody.put("agent_id", agentName);
        requestBody.put("state", stateArray);
        requestBody.put("valid_actions", validActionsArray);
        requestBody.put("reward", reward);
        requestBody.put("done", done);

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(RL_SERVICE_URL))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(requestBody.toString()))
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() != 200) {
            throw new Exception("RL service error: " + response.body());
        }

        JSONObject responseJson = new JSONObject(response.body());
        int actionId = responseJson.getInt("action_id");

        logRLDecision(agentName, stateArray, validActionsArray, reward, done, actionId, responseJson);

        return un.unifies(args[4], ASSyntax.createNumber(actionId));
    }

    private void logRLDecision(String agentName, JSONArray state, JSONArray validActions,
                                double reward, boolean done, int actionId, JSONObject response) {
        try {
            TraceLogger logger = TraceLogger.getLogger(agentName);
            if (logger == null) {
                logger = new TraceLogger(agentName);
                logger.setOutputFormat(TraceLogger.OutputFormat.JSON);
                logger.setOutputFilePath("logs/" + agentName + "_rl_trace.json");
                logger.setMaxInMemoryEntries(0);
                logger.setRealTimeConsoleOutput(false);
            }

            JSONObject explanation = response.optJSONObject("explanation");
            String mode = "unknown";
            String exploration = "unknown";
            double selectedQ = 0.0;
            Map<Integer, Double> qValues = new HashMap<>();

            if (explanation != null) {
                mode = explanation.optString("mode", "unknown");
                exploration = explanation.optString("exploration", "unknown");
                selectedQ = explanation.optDouble("selected_q", 0.0);

                JSONObject qValuesJson = explanation.optJSONObject("q_values");
                if (qValuesJson != null) {
                    for (String key : qValuesJson.keySet()) {
                        qValues.put(Integer.parseInt(key), qValuesJson.getDouble(key));
                    }
                }
            }

            int numRegions = state.length() / 2;
            int currentRegionId = -1;
            int goalRegionId = -1;
            for (int i = 0; i < numRegions && i < state.length(); i++) {
                if (state.getDouble(i) > 0.5) currentRegionId = i;
            }
            for (int i = numRegions; i < numRegions * 2 && i < state.length(); i++) {
                if (state.getDouble(i) > 0.5) goalRegionId = i - numRegions;
            }

            StringBuilder content = new StringBuilder();
            content.append("RL_ACTION: ").append(actionId);
            content.append(" | from=").append(currentRegionId);
            content.append(" | goal=").append(goalRegionId);
            content.append(" | reward=").append(reward);
            content.append(" | mode=").append(mode);

            List<String> alternatives = new ArrayList<>();
            for (int i = 0; i < validActions.length(); i++) {
                int altAction = validActions.getInt(i);
                if (altAction != actionId) {
                    double altQ = qValues.getOrDefault(altAction, 0.0);
                    String reason = (altQ < selectedQ)
                        ? "Q=" + String.format("%.3f", altQ) + " < selected Q=" + String.format("%.3f", selectedQ)
                        : "not selected";
                    alternatives.add("action_" + altAction + " (" + reason + ")");
                }
            }

            StringBuilder metadata = new StringBuilder();
            metadata.append("Q-values: {");
            for (Map.Entry<Integer, Double> entry : qValues.entrySet()) {
                metadata.append(entry.getKey()).append("=");
                metadata.append(String.format("%.3f", entry.getValue()));
                if (entry.getKey() == actionId) metadata.append("*");
                metadata.append(", ");
            }
            metadata.append("} | exploration=").append(exploration);

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
}
