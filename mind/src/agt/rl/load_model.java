package rl;

import jason.asSemantics.*;
import jason.asSyntax.*;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

import org.json.JSONObject;

/**
 * Internal action to load a trained model from checkpoint and optionally enable eval mode.
 *
 * Usage in ASL:
 *   rl.load_model(eval)      - Load checkpoint for this agent, eval=true for inference mode
 *   rl.load_model(true)      - Load and enable eval mode (inference only, no training)
 *   rl.load_model(false)     - Load but keep training mode (continues learning)
 *
 * Example:
 *   +!start <- rl.load_model(true); ...  // Load alice.pt in eval mode
 */
public class load_model extends DefaultInternalAction {

    private static final String RL_SERVICE_BASE = "http://localhost:5000";
    private static final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();

    @Override
    public Object execute(TransitionSystem ts, Unifier un, Term[] args) throws Exception {
        if (args.length != 1) {
            throw new Exception("load_model requires 1 argument: EvalMode (true/false)");
        }

        String agentName = ts.getAgArch().getAgName();
        boolean evalMode = args[0].toString().equals("true");

        // Build request JSON
        JSONObject requestBody = new JSONObject();
        requestBody.put("eval", evalMode);

        String url = RL_SERVICE_BASE + "/load/" + agentName;

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(requestBody.toString()))
                .build();

        try {
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                JSONObject responseJson = new JSONObject(response.body());
                String mode = evalMode ? "INFERENCE (eval)" : "TRAINING";
                System.out.println("[" + agentName + "] Loaded model from checkpoint - Mode: " + mode);

                // Log stats if available
                if (responseJson.has("stats")) {
                    JSONObject stats = responseJson.getJSONObject("stats");
                    System.out.println("[" + agentName + "] Model stats: episode=" + stats.optInt("episode", 0)
                        + ", epsilon=" + stats.optDouble("epsilon", 1.0)
                        + ", steps=" + stats.optInt("steps", 0));
                }
                return true;
            } else if (response.statusCode() == 404) {
                // Checkpoint not found - this is OK for first run
                System.out.println("[" + agentName + "] No checkpoint found - starting fresh");
                return true;  // Don't fail, just continue with fresh agent
            } else {
                System.err.println("[" + agentName + "] Failed to load model: " + response.body());
                return false;
            }
        } catch (java.net.ConnectException e) {
            System.err.println("[" + agentName + "] RL service not available at " + RL_SERVICE_BASE);
            throw new Exception("RL service not running. Start it with: python mind/python/dqn_server.py");
        }
    }
}
