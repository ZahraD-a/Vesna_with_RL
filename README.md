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
|   |   |__ alice_rl.asl               Reward machine and episode manager
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
      "action_id": 1
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


## System Workflow

The full workflow shows how the three layers communicate during training.
Each arrow is a real message passing between processes.

```
+==================+          +====================+          +===================+
|                  |          |                    |          |                   |
|  GODOT ENGINE    |          |  JASON / JaCaMo    |          |  PYTHON DQN       |
|  (3D World)      |          |  (Brain)           |          |  (Learner)        |
|                  |          |                    |          |                   |
+========+=========+          +==========+=========+          +=========+=========+
         |                               |                              |
         |   WebSocket connected         |                              |
         | <============================ |                              |
         |                               |                              |
         |                               |  POST /load/alice            |
         |                               | ===========================> |
         |                               |            {stats}           |
         |                               | <=========================== |
         |                               |                              |
         |                          +!run_episode                       |
         |                          randomize start/goal                |
         |                               |                              |
         |    vesna.teleport(start)      |                              |
         | <============================ |                              |
         |    region_entered(start)      |                              |
         | ============================> |                              |
         |                               |                              |
         |                          +!rl_loop                           |
         |                          ENCODE state                        |
         |                          [one_hot current | one_hot goal]    |
         |                          valid_actions = neighbor IDs        |
         |                               |                              |
         |                               |  POST /select_action         |
         |                               |  {state, valid_actions,      |
         |                               |   reward, done}              |
         |                               | ===========================> |
         |                               |                              |
         |                               |          store transition    |
         |                               |          train mini-batch    |
         |                               |          pick action         |
         |                               |                              |
         |                               |          {action_id: 1}      |
         |                               | <=========================== |
         |                               |                              |
         |                          DECODE action_id                    |
         |                          id_to_region(1) = corridor          |
         |                               |                              |
         |    vesna.walk(door)           |                              |
         | <============================ |                              |
         |    movement(completed)        |                              |
         | ============================> |                              |
         |    vesna.walk(corridor)       |                              |
         | <============================ |                              |
         |    region_entered(corridor)   |                              |
         | ============================> |                              |
         |                               |                              |
         |                          step + 1                            |
         |                          repeat !rl_loop                     |
         |                               |                              |
         |                          (repeats until goal or timeout)     |
         |                               |                              |
         |                          +!end_episode                       |
         |                               |  POST /save/alice            |
         |                               | ===========================> |
         |                               |          save alice.pt       |
         |                               |          {ok}                |
         |                               | <=========================== |
         |                               |                              |
         |                          next episode                        |
         |                          (repeat 3000 times)                 |
         |                               |                              |
```

**What each layer owns:**

Godot owns the physical simulation. It moves the 3D body, detects room entry,
and reports perceptions back through WebSocket.

Jason owns the reward machine. It decides what reward to assign (+100 goal,
-1 step, -10 timeout), manages episodes, encodes/decodes between symbols
and numbers, and controls the body.

Python owns the learning. It stores experiences, trains the neural network,
and picks actions. It never knows about room names or maps, only integer IDs
and float vectors.

 
## Why Random Start and Goal (Goal-Conditioned RL)

This project uses goal-conditioned reinforcement learning with randomized start and goal
regions.  

### The Problem with Fixed Start and Goal

If the agent always trains from reception to meeting_room, it learns exactly one path.
It cannot generalize. Drop it in boss_office_2 with a goal of open_office and it has
never seen that situation before. The policy is useless outside the one pair it memorized.
 

### Goal-Conditioned RL

The solution comes from goal-conditioned RL, introduced by Schaul et al. in
"Universal Value Function Approximators" (ICML 2015). The core idea: instead of
training a separate policy for each goal, train one policy that takes the goal as input.

In this project, the state vector encodes both where the agent is and where it needs to go:

```
state = [current_region_one_hot | goal_region_one_hot]
         11 dimensions             11 dimensions
```

The neural network sees both pieces of information and learns a single policy that works
for any start-goal combination. One network, all 110 possible pairs (11 rooms x 10 goals).

Schaul et al. showed that this generalization works because similar states share similar
Q-values. If the agent learns that corridor is useful for reaching meeting_room, that
knowledge partially transfers to reaching senior_office_1, because corridor connects
to both.

**Reference:** Schaul, T., Horgan, D., Gregor, K., and Silver, D. "Universal Value Function
Approximators." Proceedings of the 32nd International Conference on Machine Learning
(ICML), 2015.

### Why Randomizing Start and Goal Helps

Each episode picks a random start and a random goal (ensuring they differ). This does
three things:

**1. Covers the full state space.**
With 11 rooms and 10 possible goals per room, there are 110 start-goal combinations.
Random sampling ensures the agent sees all of them over 3000 episodes. Each combination
appears roughly 27 times on average, giving enough experience to learn each one.

**2. Prevents overfitting to one path.**
If the agent always starts at reception, it only learns Q-values for states reachable from
reception. The Q-values for boss_office_2 or senior_office_3 as starting points would be
untrained and unreliable. Randomization forces the network to learn useful values everywhere
in the map.

**3. Builds a universal navigation policy.**
After training, the agent can be dropped in any room, given any goal, and find a short path.
This is the whole point: one trained model handles all navigation tasks in the office.

This approach relates to domain randomization, introduced by Tobin et al. in "Domain
Randomization for Transferring Deep Neural Networks from Simulation to the Real World"
(IROS 2017). Their key insight was that randomizing training conditions in simulation
produces policies that are robust to variation. The same principle applies here: randomizing
start and goal positions produces a navigation policy robust to any start-goal pair.

**Reference:** Tobin, J., Fong, R., Ray, A., Schneider, J., Zaremba, W., and Abbeel, P.
"Domain Randomization for Transferring Deep Neural Networks from Simulation to the Real
World." IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS), 2017.

### Hindsight Experience Replay (Related Approach)

A related technique is Hindsight Experience Replay (HER) by Andrychowicz et al. (NeurIPS
2017). HER addresses a common problem in goal-conditioned RL: the agent rarely reaches
the goal early in training, so it gets almost no positive reward signal.

HER solves this by relabeling failed episodes. If the agent was trying to reach meeting_room
but ended up at corridor, HER creates an extra training sample where corridor was the goal.
The agent "pretends" it succeeded, getting a +100 reward for reaching corridor. This way,
every episode produces useful learning signal, even failures.

This project does not use HER, but it handles the sparse reward problem through a
different mechanism: the step penalty (reward_step = -1). Every step costs the agent,
so even before it discovers the goal, it learns to avoid long wandering paths. Combined
with epsilon-greedy exploration and 3000 episodes, the agent discovers goals often enough
to learn without HER.

**Reference:** Andrychowicz, M., Wolski, F., Ray, A., Schneider, J., Fong, R., Welinder, P.,
McGrew, B., Tobin, J., Abbeel, P., and Zaremba, W. "Hindsight Experience Replay."
Advances in Neural Information Processing Systems (NeurIPS), 2017.

### How Learning Accumulates Across Episodes

One episode is one attempt at one specific start-goal pair. The agent does not learn a
complete path in a single episode. Learning builds up gradually across many episodes,
and the same pair can appear more than once.

Here is what happens concretely:

**Episode 12:** start = boss_office_1, goal = reception.
The agent wanders randomly (epsilon is still high). It takes 38 steps and times out.
But every step produced a transition (state, action, reward, next_state) that went into
the replay buffer. The neural network trained on small batches from this buffer. It learned
a little: "being at corridor with goal reception and stepping toward open_office gave -1,
that was not great."

**Episode 47:** start = corridor, goal = reception.
By chance, the random selection picked a pair that overlaps with episode 12. The agent
has seen corridor before. Its Q-values for corridor are slightly better now. It finds
reception in 8 steps. The +100 goal reward propagates through training, strengthening
the Q-values along the path it took.

**Episode 203:** start = boss_office_1, goal = reception (same as episode 12).
The same pair appears again. But now the agent has trained on thousands of transitions
from many different episodes. The Q-values for boss_office_1 are much better. The agent
already knows that corridor leads toward reception (learned from episode 47 and others).
It reaches the goal in 5 steps.

**The key mechanism is the replay buffer.** It stores transitions from ALL past episodes
(up to 10,000). When Python trains a mini-batch, it samples 32 random transitions from
this buffer. A batch might contain a transition from episode 12, another from episode 47,
and another from episode 180. The neural network learns from all of them together.

This means:
- Knowledge from one pair transfers to other pairs that share rooms along the way
- Episode 47 (corridor to reception) helps episode 203 (boss_office_1 to reception)
  because both paths go through corridor
- The same pair appearing multiple times is not wasted. Each time, the agent has better
  Q-values and makes better decisions, reinforcing what works

With 110 possible start-goal combinations (11 rooms x 10 goals) and 3000 episodes,
each pair appears roughly 27 times on average. Early appearances are mostly random
exploration. Later appearances use the learned policy and refine it further.

### How It Works in This Project

The randomization happens in alice_rl.asl at the start of each episode:

```
+!run_episode
    :   episode(Ep)
    <-
        !randomize_start_goal;       // pick new random start and goal
        ...
```

The `!randomize_start_goal` plan picks from all 11 regions, ensures start and goal differ,
and stores them as beliefs. The rl_bridge.asl encodes both into the state vector that
Python receives. Python never knows room names. It just sees a 22-number vector and
learns which actions lead to high reward for each vector pattern.

By episode 3000, the agent has seen enough start-goal pairs that its Q-network has learned
a general navigation map of the entire office encoded in its weights.


## The Office Map

11 rooms connected by doors and direct passages. Defined in office_map.asl
using RCC (Region Connection Calculus) spatial relations.

Rooms: reception, corridor, open_office, outside, common, meeting_room,
senior_office_1, senior_office_2, senior_office_3, boss_office_1, boss_office_2

The agent must learn which sequence of rooms to walk through to get from
any start room to any goal room in the fewest steps.
