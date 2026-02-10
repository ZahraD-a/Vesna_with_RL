# VEsNA with Reinforcement Learning

A cognitive agent that learns to navigate an office environment using Deep Q-Network (DQN).
The agent (Alice) lives in a Godot 3D world and learns the shortest path from any room to any other room
through trial and error across thousands of episodes.

The system combines three layers: a game engine (Godot) for the physical world, a BDI agent framework
(JaCaMo/Jason) for symbolic reasoning, and a Python neural network (DQN) for learning.


## Project Structure

```
Vesna_with_RL/
|
|__ env/office/                        Godot 3D environment (the office world)
|
|__ mind/
|   |__ src/agt/
|   |   |__ alice_rl.asl               RL training agent (episodes, rewards, loop)
|   |   |__ rl_bridge.asl              Codec between Jason symbols and Python numbers
|   |   |__ vesna.asl                  Base agent (body connection via WebSocket)
|   |   |__ rl/
|   |   |   |__ select_action.java     HTTP client: sends state to Python, gets action back
|   |   |   |__ load_model.java        HTTP client: loads checkpoint from Python
|   |   |   |__ save_model.java        HTTP client: saves checkpoint to Python
|   |   |   |__ random_region.java     Utility: picks random region from a list
|   |   |__ vesna/
|   |       |__ VesnaAgent.java        Agent architecture (WebSocket to Godot body)
|   |       |__ via/walk.java          Internal action: walk body to location
|   |       |__ via/teleport.java      Internal action: teleport body to region
|   |
|   |__ python/
|   |   |__ dqn_agent.py               DQN neural network, replay buffer, training logic
|   |   |__ dqn_server.py              Flask REST API wrapping the DQN agent
|   |   |__ requirements.txt           Python dependencies (flask, torch, numpy)
|   |
|   |__ playgrounds/office/
|   |   |__ office_map.asl             Spatial map of the office (RCC relations)
|   |
|   |__ vesna_rl.jcm                   JaCaMo config for RL training
|   |__ build.gradle                   Gradle build (tasks: run, runRL)
|
|__ checkpoints/                       Saved model files (alice.pt)
|__ logs/                              Runtime logs
|__ start_all.sh                       Launches everything (Godot, Python, Jason)
|__ stop_all.sh                        Stops all processes
```


## How to Run

### Prerequisites

1. Godot 4.5+ installed
2. Python 3.10+ with a virtual environment
3. JDK 17 (bundled in mind/jdk-17.0.13+11/)

### Setup Python (first time only)

```bash
cd mind/python
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

### Start Training

Run the startup script. It launches all three components in order:

```bash
./start_all.sh
```

This does three things:
1. Starts Godot (the 3D office environment)
2. Starts the Python RL service (Flask server on port 5000)
3. Starts JaCaMo with the alice_rl agent (connects to both Godot and Python)

The agent will train for 3000 episodes by default. Checkpoints are saved every 50 episodes
to the checkpoints/ folder.

### Run Trained Policy (Inference)

After training, change eval_mode in alice_rl.asl:

```
eval_mode(true).
```

Then run start_all.sh again. The agent will use its learned policy without exploring.

### Monitor Training

```bash
curl http://localhost:5000/health
curl http://localhost:5000/stats/alice
```


## The Three Layers

The system has three processes running at the same time. Each one has a different job:

**Godot** (env/office/) is the physical world. It renders the 3D office, simulates the agent's
body, detects when the body enters a room, and reports back via WebSocket.

**JaCaMo/Jason** (mind/src/agt/) is the brain. It decides what reward to give, manages episodes,
encodes the world into numbers, decodes numbers back into actions, and controls the body.

**Python DQN** (mind/python/) is the learner. It receives a numeric state vector, picks the best
action using a neural network, stores experiences in a replay buffer, and trains itself.

Jason owns the reward logic and world knowledge. Python owns the learning algorithm.
They never mix. Jason sends numbers to Python, Python sends a number back.


## Full Training Flow (Step by Step)

Below is what happens from the moment you start training until the agent completes an episode.
Each step shows which file runs the logic.

### Startup

When start_all.sh runs, it launches Godot first, then Python, then JaCaMo.
JaCaMo reads vesna_rl.jcm which creates one agent named "alice" using alice_rl.asl.
The agent's initial goal is `!start`.

**File: vesna_rl.jcm**
```
agent alice:alice_rl.asl {
    ag-class: vesna.VesnaAgent
    goals: start
}
```

VesnaAgent.java connects to the Godot body via WebSocket. Now the agent has a body in the 3D world.

### Episode Begin

**File: alice_rl.asl**

The `+!start` plan loads the neural network from a checkpoint (or starts fresh if none exists),
then enters the episode loop.

For each episode, `+!run_episode` does:
1. Calls `!randomize_start_goal` to pick a random start room and goal room
2. Calls `!go_to_start` to teleport the body to the start room
3. Enters `!rl_loop` which runs step by step until the episode ends

### One RL Step (the core loop)

This is where Jason and Python talk to each other. Here is what happens on a single step:

```
STEP 1: Jason checks where the agent is
    File: alice_rl.asl (rl_loop, CASE 3)
    The agent reads current_region and goal_region from its beliefs.
    It picks the right reward: -1 per step, +100 for goal, -10 for timeout.

STEP 2: Jason encodes the world into numbers
    File: rl_bridge.asl (build_state_vector, get_valid_action_ids)
    Converts region names into a 22-number vector:
      current_region one-hot (11 numbers) + goal_region one-hot (11 numbers)
    Example: agent at boss_office_1 (ID 9), goal meeting_room (ID 5)
      State = [0,0,0,0,0,0,0,0,0,1,0, 0,0,0,0,0,1,0,0,0,0,0]
    Also finds which rooms are neighbors (valid actions) and converts
    their names to integer IDs.

STEP 3: Jason calls Python via Java
    File: rl_bridge.asl calls rl.select_action(StateVector, ValidActionIds, Reward, Done, ActionId)
    File: rl/select_action.java packages everything into JSON and sends HTTP POST to Python

    The HTTP request looks like:
    {
      "agent_id": "alice",
      "state": [0,0,0,0,0,0,0,0,0,1,0, 0,0,0,0,0,1,0,0,0,0,0],
      "valid_actions": [1, 8],
      "reward": -1.0,
      "done": false
    }

STEP 4: Python picks an action
    File: dqn_server.py receives the POST at /select_action
    File: dqn_agent.py (step_with_explanation) does the actual work:
      a) Stores the previous transition in replay buffer
      b) Trains a mini-batch if enough samples exist
      c) Picks action: random (exploration) or neural network (exploitation)
      d) Returns the chosen action ID

    The HTTP response looks like:
    {
      "action_id": 1,
      "explanation": { "exploration": "greedy", "q_values": {"1": 3.2, "8": 1.5} }
    }

STEP 5: Java passes the action ID back to Jason
    File: rl/select_action.java parses the response, extracts action_id,
    and unifies it with the ActionId variable in Jason.

STEP 6: Jason decodes the action ID back to a room name
    File: rl_bridge.asl
    ?id_to_region(ActionId, TargetRegion) converts 1 back to "corridor"

STEP 7: Jason moves the body
    File: rl_bridge.asl (hop_to)
    If there is a door between current room and target room:
      walk to door (vesna.walk) then walk to room (vesna.walk)
    If rooms are directly connected:
      walk to room (vesna.walk)
    Each walk command goes through VesnaAgent.java which sends it
    over WebSocket to the Godot body.

STEP 8: Godot moves the body and reports back
    File: Godot engine (env/office/)
    The 3D body walks to the target. When it enters the new room,
    Godot sends a region_entered signal back through WebSocket.
    File: rl_bridge.asl (+region_entered) updates current_region belief.

STEP 9: Loop continues
    File: alice_rl.asl
    Step counter increments. The loop calls !rl_loop again.
    This repeats until the agent reaches the goal or times out.
```

### Episode End

**File: alice_rl.asl**

When the episode ends (goal reached or timeout), the `+!end_episode` plan:
1. Logs the total reward for this episode
2. Auto-saves the model every 50 episodes (calls rl.save_model)
3. Cleans up beliefs (step, episode_reward)
4. Starts the next episode with a new random start and goal

After all 3000 episodes, training stops and the final policy is saved.


## Encoding and Decoding

The codec lives in rl_bridge.asl. It translates between Jason's symbolic world
(room names, spatial relations) and Python's numerical world (integers, float vectors).

### Encoding (Jason to Python)

Everything that converts names into numbers before sending to Python.

**Region name to integer ID**
```
region_to_id(reception, 0)
region_to_id(corridor, 1)
...
region_to_id(boss_office_2, 10)
```

**Region to one-hot vector (build_one_hot_vector)**
```
meeting_room (ID 5) becomes [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]
```

**State vector (build_state_vector)**
Concatenates two one-hot vectors into a 22-dim observation:
```
[current_region_one_hot (11) | goal_region_one_hot (11)]
```

**Valid actions (get_valid_action_ids)**
Finds all neighbor rooms using spatial relations from office_map.asl,
then converts their names to integer IDs:
```
[corridor, common] becomes [1, 4]
```

### Decoding (Python to Jason)

Everything that converts numbers back into names and physical actions after
receiving from Python.

**Integer ID to region name**
```
id_to_region(5, meeting_room)   (reverse lookup of region_to_id)
```

**Action to physical movement (hop_to)**
Takes a region name and walks the body there, handling doors if needed:
```
hop_to(meeting_room) calls vesna.walk(door) then vesna.walk(meeting_room)
```


## Communication Summary

```
Godot (3D World)          Jason (Brain)              Python (Learner)
      |                        |                          |
      |   WebSocket            |      HTTP POST           |
      | <--- body connected    |                          |
      |                        |                          |
      |                   +!start                         |
      |                   rl.load_model ---- POST /load ---->
      |                        |         <--- stats ------  |
      |                        |                          |
      |                   +!run_episode                   |
      |  <-- teleport body     |                          |
      |  region_entered -->    |                          |
      |                        |                          |
      |                   +!rl_loop                       |
      |                   encode state                    |
      |                   rl.select_action - POST /select_action ->
      |                        |         <--- action_id --  |
      |                   decode action                   |
      |  <-- walk body         |                          |
      |  region_entered -->    |                          |
      |                   (loop repeats)                  |
      |                        |                          |
      |                   +!end_episode                   |
      |                   rl.save_model --- POST /save --->
      |                        |         <--- ok --------  |
```


## Configuration

All training parameters are at the top of alice_rl.asl:

| Parameter       | Default | What it does                              |
|-----------------|---------|-------------------------------------------|
| max_steps       | 50      | Steps before episode times out            |
| max_episodes    | 3000    | Total episodes to train                   |
| eval_mode       | false   | true = use trained policy, false = learn  |
| save_interval   | 50      | Save checkpoint every N episodes          |
| reward_goal     | +100    | Reward when agent reaches goal room       |
| reward_step     | -1      | Reward per step (encourages short paths)  |
| reward_timeout  | -10     | Reward when episode times out             |

DQN hyperparameters are in dqn_agent.py:

| Parameter       | Default | What it does                              |
|-----------------|---------|-------------------------------------------|
| learning_rate   | 0.001   | Adam optimizer learning rate              |
| gamma           | 0.99    | Discount factor for future rewards        |
| epsilon_start   | 1.0     | Initial exploration rate                  |
| epsilon_end     | 0.01    | Minimum exploration rate                  |
| epsilon_decay   | 0.995   | Multiply epsilon by this each episode     |
| batch_size      | 32      | Training batch size from replay buffer    |
| buffer_size     | 10000   | Maximum replay buffer capacity            |
| target_update   | 10      | Update target network every N episodes    |
| hidden_size     | 64      | Hidden layer size in the neural network   |


## The Office Map

11 rooms connected by doors and direct passages. Defined in office_map.asl
using RCC (Region Connection Calculus) spatial relations.

Rooms: reception, corridor, open_office, outside, common, meeting_room,
senior_office_1, senior_office_2, senior_office_3, boss_office_1, boss_office_2

The agent must learn which sequence of rooms to walk through to get from
any start room to any goal room in the fewest steps.
