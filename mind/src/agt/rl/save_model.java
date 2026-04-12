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
 * Internal action to save the current model checkpoint via HTTP.
 *
 * Usage in ASL:
 *   rl.save_model
 *
 * Saves to: checkpoints/{agent_name}.pt (or default path on server)
 *
 * Checkpoint naming convention:
 *   - alice11.pt   (11-region graph-based training)
 *   - alice50.pt   (50-region graph-based training)
 *   - alice103.pt  (103-region graph-based training)
 * The checkpoint filename is determined by the agent_name in the .jcm config.
 */
public class save_model extends DefaultInternalAction {

    private static final String RL_SERVICE_BASE = System.getenv().getOrDefault("RL_SERVICE_URL", "http://localhost:5000").replace("/select_action", "");
    private static final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(30))
            .build();

    @Override
    public Object execute(TransitionSystem ts, Unifier un, Term[] args) throws Exception {
        String agentName = ts.getAgArch().getAgName();

        JSONObject requestBody = new JSONObject();
        String url = RL_SERVICE_BASE + "/save/" + agentName;

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(requestBody.toString()))
                .build();

        try {
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                JSONObject responseJson = new JSONObject(response.body());
                String path = responseJson.optString("path", "unknown");
                System.out.println("[" + agentName + "] Model saved to: " + path);
                return true;
            } else {
                System.err.println("[" + agentName + "] Failed to save model: " + response.body());
                return false;
            }
        } catch (java.net.ConnectException e) {
            System.err.println("[" + agentName + "] RL service not available at " + RL_SERVICE_BASE);
            return false;
        }
    }
}
