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
 * Internal action to request action selection from RL service for 100-region map.
 *
 * This is a DOMAIN-AGNOSTIC HTTP client. It knows nothing about regions,
 * maps, or what the state/action vectors mean. All domain knowledge stays
 * in the ASL files.
 *
 * Usage in ASL:
 *   rl.select_action_100(StateVector, ValidActionIds, Reward, Done, ActionId)
 *
 * Example:
 *   rl.select_action_100([0,0,...,1,...,0], [1], -1.0, false, ActionId)
 *   // ActionId will be unified with the selected action (integer)
 *
 * The reward is computed in Jason (reward machine), NOT in Python.
 * The state encoding is done in Jason, NOT here.
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
            throw new Exception("select_action_100 requires 5 arguments: StateVector, ValidActionIds, Reward, Done, ActionId");
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

        // Log the decision for explainability
        logRLDecision(agentName, stateArray, validActionsArray, reward, done, actionId, responseJson);

        // Return action ID as number (let ASL convert to region name)
        return un.unifies(args[4], ASSyntax.createNumber(actionId));
    }

    /**
     * Log the RL decision for explainability.
     */
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

            // Decode state: first half = current location, second half = goal
            int numRegions = state.length() / 2;
            int currentRegionId = -1;
            int goalRegionId = -1;
            for (int i = 0; i < numRegions && i < state.length(); i++) {
                if (state.getDouble(i) > 0.5) currentRegionId = i;
            }
            for (int i = numRegions; i < numRegions * 2 && i < state.length(); i++) {
                if (state.getDouble(i) > 0.5) goalRegionId = i - numRegions;
            }

            // Build explanation content
            StringBuilder content = new StringBuilder();
            content.append("RL_ACTION: ").append(actionId);
            content.append(" | from=").append(regionName(currentRegionId));
            content.append(" | goal=").append(regionName(goalRegionId));
            content.append(" | reward=").append(reward);
            content.append(" | mode=").append(mode);

            // Build alternatives
            List<String> alternatives = new ArrayList<>();
            for (int i = 0; i < validActions.length(); i++) {
                int altAction = validActions.getInt(i);
                if (altAction != actionId) {
                    double altQ = qValues.getOrDefault(altAction, 0.0);
                    String reason = (altQ < selectedQ)
                        ? "Q=" + String.format("%.3f", altQ) + " < selected Q=" + String.format("%.3f", selectedQ)
                        : "not selected";
                    alternatives.add(regionName(altAction) + " (" + reason + ")");
                }
            }

            // Build metadata with full Q-values
            StringBuilder metadata = new StringBuilder();
            metadata.append("Q-values: {");
            for (Map.Entry<Integer, Double> entry : qValues.entrySet()) {
                metadata.append(regionName(entry.getKey())).append("=");
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

    // Region name lookup for 100-region map
    private static final String[] REGION_NAMES = {
        // North Wing (0-12)
        "corridor_north",   // 0
        "office_1",         // 1
        "office_2",         // 2
        "office_3",         // 3
        "office_4",         // 4
        "office_5",         // 5
        "meeting_room_2",   // 6
        "meeting_room_3",   // 7
        "lab_1",            // 8
        "lab_2",            // 9
        "server_room",      // 10
        "mail_room",        // 11
        "reception",        // 12

        // Central Hub (13-30)
        "corridor",         // 13
        "open_office",      // 14
        "boss_office_1",    // 15
        "boss_office_2",    // 16
        "print_room",       // 17
        "outside",          // 18
        "senior_office_1",  // 19
        "senior_office_2",  // 20
        "senior_office_3",  // 21
        "meeting_room",     // 22
        "restroom_1",       // 23
        "storage_1",        // 24
        "executive_suite",  // 25
        "supply_closet",    // 26
        "common",           // 27
        "kitchen",          // 28
        "library",          // 29
        "phone_booth_1",    // 30

        // South Wing (31-45)
        "corridor_south",   // 31
        "office_6",         // 32
        "office_7",         // 33
        "office_8",         // 34
        "office_9",         // 35
        "office_10",        // 36
        "cafeteria",        // 37
        "gym",              // 38
        "restroom_2",       // 39
        "archive",          // 40
        "training_room",    // 41
        "terrace",          // 42
        "lounge",           // 43
        "wellness_room",    // 44
        "phone_booth_2",    // 45

        // Lobby Complex (46-49)
        "lobby",            // 46
        "security_desk",    // 47
        "conference_room",  // 48
        "parking",          // 49

        // East Wing (50-63)
        "corridor_east",    // 50
        "lab_3",            // 51
        "lab_4",            // 52
        "lab_5",            // 53
        "lab_6",            // 54
        "server_room_2",    // 55
        "server_room_3",    // 56
        "data_center",      // 57
        "tech_office_1",    // 58
        "tech_office_2",    // 59
        "server_maintenance", // 60
        "network_room",     // 61
        "backup_power",     // 62
        "telecom_room",     // 63

        // West Wing (64-77)
        "corridor_west",    // 64
        "storage_2",        // 65
        "storage_3",        // 66
        "storage_4",        // 67
        "storage_5",        // 68
        "storage_6",        // 69
        "workshop",         // 70
        "equipment_room",   // 71
        "hazmat_storage",   // 72
        "loading_bay",      // 73
        "recycling_center", // 74
        "courier_station",  // 75
        "freight_elevator", // 76
        "dock_office",      // 77

        // Annex (78-89)
        "annex_corridor",   // 78
        "wellness_center",  // 79
        "meditation_room",  // 80
        "fitness_studio",   // 81
        "yoga_room",        // 82
        "game_room",        // 83
        "music_room",       // 84
        "art_studio",       // 85
        "rooftop_garden",   // 86
        "outdoor_seating",  // 87
        "bike_storage",     // 88
        "shower_room",      // 89

        // Extended Rooms (90-102)
        "office_11",        // 90
        "office_12",        // 91
        "office_13",        // 92
        "office_14",        // 93
        "office_15",        // 94
        "meeting_room_6",   // 95
        "meeting_room_7",   // 96
        "break_room_2",     // 97
        "pantry_2",         // 98
        "copy_center",      // 99
        "scanner",          // 100
        "server_room_4",    // 101
        "server_room_5",    // 102
    };

    /** Safe region name lookup — returns "region_N" for unknown IDs. */
    private static String regionName(int id) {
        if (id >= 0 && id < REGION_NAMES.length) {
            return REGION_NAMES[id];
        }
        return "region_" + id;
    }
}
