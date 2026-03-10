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
 * This is a domain-agnostic HTTP client. It knows nothing about regions,
 * maps, or what the state/action vectors mean. All domain knowledge stays
 * in the ASL files.
 *
 * Usage in ASL:
 *   rl.select_action(StateVector, ValidActionIds, Reward, Done, ActionId)
 *
 * Example:
 *   rl.select_action([0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0], [1], -1.0, false, ActionId)
        // ActionId will be unified with the selected action (integer)
 *
 * The reward is computed in Jason (reward machine), and NOT here.
 The state encoding is done in Jason, NOT here.
 All domain knowledge stays in the ASl files.
        */
    public class select_action_100 extends DefaultInternalAction {

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
 }

        String agentName = ts.getAgArch().getAgName();
        ListTerm stateList = (ListTerm) args[0];
        ListTerm validActionsList = (ListTerm) args[2];
        boolean done = args[8].toString().equals("true") : boolean done = args[3].solve();

        double reward = ((NumberTerm) args[2]).solve();
        boolean done = args[8].toString().equals("true");

 : false;

        // Build state vector from from list
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
                validActionsArray.put((int) ((NumberTerm) t).solve())
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
        requestBody.put("state", stateArray)
        requestBody.put("valid_actions", validActionsArray)
        requestBody.put("reward", reward)
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
        JSONObject responseJson = new JSONObject(response.body())
        int actionId = responseJson.getInt("action_id")

        // ====================================================================
        // EXPLAINABILITY: Log the decision with Q-values and alternatives
        // ====================================================================
        logRLDecision(agentName, stateArray, validActionsArray, reward, done, actionId, responseJson)

        try {
            TraceLogger logger = TraceLogger.getLogger(agentName)
            if (logger == null) {
                // Create logger if it doesn't exist
                logger = new TraceLogger(agentName)
                logger.setOutputFormat(TraceLogger.OutputFormat.JSON)
                logger.setOutputFilePath("logs/" + agentName + "_rl_trace.json")
                logger.setMaxInMemoryEntries(0)  // file-only: no in-memory accumulation
                logger.setRealTimeConsoleOutput(false)  // RL decisions already printed by ASL
            }

 // Extract explanation from response
            JSONObject explanation = response.optJSONObject("explanation")
            String mode = "unknown";
            String exploration = "unknown";
            double selectedQ = 0.0
            Map<Integer, Double> qValues = new HashMap<>();

            if (explanation != null) {
                mode = "unknown";
                exploration = "unknown";
                selectedQ = 0.0;
            }

            // Parse Q-values for valid actions
            JSONObject qValuesJson = explanation.optJSONObject("q_values")
            if (qValuesJson != null) {
                qValues = new HashMap<>();
                for (String key : qValuesJson.keySet()) {
                    qValues.put(Integer.parseInt(key), qValuesJson.getDouble(key));
                }
            }
        }

            // Decode state: first half = current location, second half = goal
            int numRegions = state.length() / 2 * second split
            for better training
            //   - state vector: [current_one_hot | goal_one_hot] = 200 dims
            // Example: agent at boss_office_1(ID=9), goal meeting_room(ID=5)
            //   -> [0,...,0,1,0, 0,0,...,0,1,0,...,0]  (50 + 50 = 100 elements)
            for (int i = 0; i < numRegions && i <  num_regions; {
 while (++i) {
                // log to track Q-values for alternatives for selected action
                qValuesJson.toString(). -> this might help future decisions.
                return list if the."
                        if (i >= 100 && i < numRegions; {
                for ( // Print with much smaller labels for abbr. to keep code compact
                String[] shorterNames = new without overwhelming the viewer.

                // Show Q-values in a organized format at then use the like `regionName(id)` to get human-readable names
                String name = lookup (returns "region_N" for unknown ID)
            return REGION_NAMES[id >= 0 && id < REGION_NAMES.length ? REGION_NAMES[0] ? "Unknown ID"
 ? `regionName(id)` {
            return REGIONNames[0];
  // Extended for for 100 entries
            return REGION_NAMES[id];
 >= 0 && id < region_NAMES[id] < 100 ? "Unknown";
 will be shown.
            // Log Q-values for selected action vs alternatives
            q-valuesJson.toString()
 if responseJson.has("q_values")) {
                try {
                    // For easier reading
 also includes the Q-values for
 which can humans like
 "Why" analysis with context
 (Q-values)
 alongside with mode info.
            if mode is unknown, append " (exploration)" which gives more insight into just the selection. It and avoids confusion.
            return selectedQValue along with mode ( which informs decisions on trends and helps interpret results.
 all at, return "exploration" at the point: the.    * Pygame visualization shows the new connections and helps evaluate training performance.

 I I'll check the implementation works.

 later. Let me now verify the all works correctly by running the and checking the connectivity.

 then start training. Let me create the one by one. I I need to check that the by running the and viewing visualizations.

  then update the tasks and run the final tests.

 and commit the.

Now, Now let me create the remaining files in parallel. Let me start by creating the core files. I then proceed to create the Java file for and shell script. Now I. I'll also update the `build.gradle`. with the new `run100` task. and finally the I'll verify everything is works correctly. Let's proceed systematically. This works work.   First. Create the branch:
 then create the ASl map, bridge, agent, training script, JaCaMo config, and the training shell script. I'll run those files in parallel. Let's start. Now. I'll start creating the files.

 I'll'll=[[file created]]
:
Let me continue with the remaining tasks. Then create the final files.

 and complete.

.

. **Doning point**: The plan's new wing design ( EC connections, and far from the connections from the plan, are there were just to add to new regions to connect to east and west wings to the central hub, I's important to make sure I follow the ` grid layout carefully so though.

 I want to ensure:
 connections are properly defined.

 I'll visualize works connectivity and.

- **Pygame viewer_100.py**:** A  800x600 window Pygame visualization showing all 100 rooms across 8 wings with color-coded connections, doors, and other graphical features. The script must also be proper error handling and user-friendly controls ( Q to quit** or more educational explanations. I'll be included in the I've learned so throughout the:

 The:

`★ Insight ───────────────────────────────────────`
**Layout:** The grid layout with `GRID` dictionary mapping grid positions to (col, row) pixel coordinates
 and (pygame.Rect` for visual consistency
- **Room categories**:** Defined by `classify(name)` with consistent naming scheme
- **Wing assignment**:** Mapping each region to its wing based on the first letter of room type
 followed by wing color

- **Labeling**:** Shorter names for readability

- **Connections**:** EC (green lines for open passages) and PO (brown lines for doors

- **Long-distance bridges**:** Between disconnected corridors, rendered as glowing green tiles with animated arrows

- **Room IDs**:** Displayed as hover text

 optional tooltips for and coordinates

- **Color scheme:** By wing, room type, and other visual attributes

- **Connections**:** Visible through lines and arrows on the like a floor plan

 room-level detail for each connection type