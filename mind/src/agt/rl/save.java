package rl;

import jason.asSemantics.*;
import jason.asSyntax.*;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

/**
 * Internal action to save the trained policy.
 * Usage: rl.save
 */
public class save extends DefaultInternalAction {

    private static final String RL_SERVICE_URL = "http://localhost:5000/save/";
    private static final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();

    @Override
    public Object execute(TransitionSystem ts, Unifier un, Term[] args) throws Exception {
        String agentName = ts.getAgArch().getAgName();

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(RL_SERVICE_URL + agentName))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.noBody())
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() != 200) {
            throw new Exception("Failed to save policy: " + response.body());
        }

        return true;
    }
}
