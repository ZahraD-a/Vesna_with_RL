# Complete Execution Workflow Diagram with Input/Output

## 🎯 Scenario: Alice navigating from "open_office" to "outside"

---

## 🔷 MASTER FLOWCHART - Complete System Overview

```mermaid
flowchart TB
    Start([🎬 START: Episode 55<br/>Alice at open_office<br/>Goal: outside]) --> Init

    Init[📋 INITIALIZATION<br/>• episode = 55<br/>• step = 0<br/>• reward = 0<br/>• Teleport to start position]
    
    Init --> Belief[💭 BELIEF UPDATE<br/>Godot WebSocket ↓<br/>region_entered: open_office<br/>current_region = open_office]
    
    Belief --> Loop[🔁 RL LOOP START<br/>Check: open_office ≟ outside<br/>Result: NOT equal → Continue]
    
    Loop --> Encode[🔢 STATE ENCODING<br/>Input: open_office, outside<br/>Process:<br/>• region_id open_office → 2<br/>• region_id outside → 3<br/>• one_hot 2 → [0,0,1,0,0,0,0,0,0,0,0]<br/>• one_hot 3 → [0,0,0,1,0,0,0,0,0,0,0]<br/>Output:<br/>[0,0,1,0,0,0,0,0,0,0,0,<br/> 0,0,0,1,0,0,0,0,0,0,0]]
    
    Encode --> Adjacent[🗺️ ADJACENCY LOOKUP<br/>Input: open_office<br/>Process:<br/>.findall neighbor open_office, N<br/>Output:<br/>Neighbors = [corridor, outside, common]<br/>ActionIds = [1, 3, 4]]
    
    Adjacent --> JavaHTTP[☕ JAVA INTERNAL ACTION<br/>File: select_action.java<br/>Input:<br/>• state: [0,0,1,0,...,1,0,0,0,0,0]<br/>• valid_actions: [1,3,4]<br/>• reward: -1.0<br/>• done: false<br/>HTTP POST → Python:5000]
    
    JavaHTTP --> PyReceive[🐍 PYTHON DQN AGENT<br/>File: dqn_agent.py<br/>Receives HTTP request]
    
    PyReceive --> PyMemory{📦 MEMORY CHECK<br/>Has prev_state?}
    
    PyMemory -->|YES| PyStore[💾 STORE TRANSITION<br/>prev_state, prev_action,<br/>reward:-1.0, state, done:false<br/>→ ReplayBuffer 156]
    
    PyMemory -->|NO| PySkip[⏭️ Skip Storage<br/>First step]
    
    PyStore --> PyTrain{🎓 TRAINING CHECK<br/>len memory ≥ 32?}
    PySkip --> PyTrain
    
    PyTrain -->|YES| PyBatch[🧠 TRAIN DQN<br/>Sample 32 transitions<br/>Bellman equation:<br/>Q s,a = r + γ·max Q s',a'<br/>Loss: 0.0234<br/>Backprop + optimize]
    
    PyTrain -->|NO| PyNoTrain[⏭️ Skip Training]
    
    PyBatch --> PySelect[🎯 ACTION SELECTION<br/>epsilon = 0.01 inference<br/>Q-network forward pass:<br/>Q[1] corridor = 45.678<br/>Q[3] outside = 98.234 ⭐<br/>Q[4] common = 34.567<br/>Mask invalid actions<br/>argmax → action = 3]
    
    PyNoTrain --> PySelect
    
    PySelect --> PyReturn[📤 PYTHON RESPONSE<br/>HTTP 200 JSON:<br/>action_id: 3<br/>explanation:<br/>  q_values: 1:45.678, 3:98.234, 4:34.567<br/>  selected_q: 98.234<br/>  exploration: greedy<br/>  mode: inference]
    
    PyReturn --> JavaTrace[📊 TRACE LOGGING<br/>File: select_action.java<br/>Create TraceEntry:<br/>ACTION: RL_ACTION: 3<br/>from=open_office<br/>goal=outside<br/>reward=-1.0<br/>mode=inference<br/>alternatives:<br/>• corridor Q=45.678<br/>• common Q=34.567<br/>Console: [TRACE #111]]
    
    JavaTrace --> Convert[🔄 ID → REGION<br/>id_to_region 3, TargetRegion<br/>3 → outside]
    
    Convert --> Print[🖨️ PRINT ACTION<br/>Console:<br/>→ RL selected: outside]
    
    Print --> HopTo[🚶 EXECUTE MOVEMENT<br/>File: symbolic_execution_engine.asl<br/>!hop_to outside<br/>vesna.walk outside]
    
    HopTo --> WSOut[📡 WEBSOCKET → GODOT<br/>File: VesnaAgent.java<br/>JSON:<br/>type: walk_to<br/>data: target: outside]
    
    WSOut --> GodotNav[🎮 GODOT NAVIGATION<br/>File: vesna.gd<br/>NavigationAgent3D<br/>• Calculate path<br/>• Move at 60 FPS<br/>• Physics updates<br/>• Collision detection]
    
    GodotNav --> GodotRegion[🎯 REGION DETECTION<br/>Area3D collision:<br/>Vesna enters outside zone]
    
    GodotRegion --> WSIn[📡 WEBSOCKET ← GODOT<br/>JSON:<br/>type: region_entered<br/>status: outside]
    
    WSIn --> UpdateBelief[💭 UPDATE BELIEFS<br/>File: symbolic_execution_engine.asl<br/>+region_entered outside<br/>-current_region _<br/>+current_region outside]
    
    UpdateBelief --> WSComplete[✅ MOVEMENT COMPLETE<br/>Godot WebSocket:<br/>type: movement<br/>status: completed<br/>.wait unblocks]
    
    WSComplete --> IncStep[➕ INCREMENT STEP<br/>step = 0 + 1 = 1<br/>episode_reward = 0 + -1 = -1]
    
    IncStep --> CheckGoal{🎯 GOAL CHECK<br/>current_region ≟ goal_region<br/>outside ≟ outside}
    
    CheckGoal -->|NOT EQUAL| Loop
    
    CheckGoal -->|EQUAL ✓| GoalReached[🎉 GOAL REACHED!<br/>File: alice_rl.asl line 83<br/>Console:<br/>*** GOAL REACHED in 1 steps! ***<br/>Final RL call:<br/>reward: +100.0<br/>done: true]
    
    GoalReached --> FinalTrace[📊 FINAL TRACE<br/>Console:<br/>[TRACE #112] ACTION: RL_ACTION: 2<br/>from=outside, goal=outside<br/>reward=100.0, mode=inference]
    
    FinalTrace --> CalcReward[💰 TOTAL REWARD<br/>episode_reward = -1<br/>+ goal_bonus = +100<br/>Total: 99]
    
    CalcReward --> PrintTotal[🖨️ PRINT SUMMARY<br/>Console:<br/>Episode 55 total reward: 99]
    
    PrintTotal --> NextEp[🔄 NEXT EPISODE<br/>episode = 55 + 1 = 56<br/>Reset step, reward<br/>Wait 1000ms]
    
    NextEp --> End([🏁 END Episode 55<br/>Start Episode 56])
    
    style Start fill:#e1f5e1,stroke:#2d6a2d,stroke-width:3px
    style End fill:#ffe1e1,stroke:#8b0000,stroke-width:3px
    style GoalReached fill:#fff3cd,stroke:#856404,stroke-width:3px
    style Encode fill:#d1ecf1,stroke:#004085,stroke-width:2px
    style PySelect fill:#f8d7da,stroke:#721c24,stroke-width:2px
    style GodotNav fill:#d4edda,stroke:#155724,stroke-width:2px
    style JavaTrace fill:#fff3cd,stroke:#856404,stroke-width:2px
    style PyBatch fill:#cce5ff,stroke:#004085,stroke-width:2px
```

---

## ❓ DEEP DIVE: Key Concepts Explained

### 🗺️ **Does the Agent Know the Map?**

**Answer: YES (Symbolic) and NO (Subsymbolic)** - This is the core innovation!

#### What Jason KNOWS (Symbolic Layer):
```prolog
// Complete map in office_map.asl
neighbor(corridor, reception).
neighbor(corridor, open_office).
neighbor(corridor, outside).
neighbor(open_office, corridor).
neighbor(open_office, outside).
neighbor(open_office, common).
// ... 28 more neighbor facts
```
✅ Jason has FULL map knowledge
✅ Knows all 11 regions and connections
✅ Can reason about spatial relationships

#### What Python DQN KNOWS (Subsymbolic Layer):
```python
# dqn_agent.py receives:
state = [0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0]  # Just numbers!
valid_actions = [1, 3, 4]  # Just integers!
reward = -1.0  # Just a float!
```
❌ NO knowledge of room names
❌ NO knowledge of map layout
❌ NO knowledge of spatial relationships
❌ Doesn't know what "outside" or "corridor" means

**The Python DQN is BLIND to domain semantics!**

---

### 🧠 **What Does RL Actually Learn?**

The DQN learns the **Q-Function: Q(s,a)** = Expected cumulative reward from state `s` taking action `a`

#### Learning Timeline Example:

**Episode 1** (Random Exploration, ε=1.0):
```
State: [0,1,0,... 0,0,0,1,0,...]  (corridor → outside)
         ↑current    ↑goal

Random action selection:
  Q[1]=0.0, Q[2]=0.0, Q[3]=0.0, Q[4]=0.0  (all zero, untrained)
  Randomly picks action=1 (reception, wrong way!)
  
Path taken: corridor → reception → corridor → outside
Steps: 3, Reward: -3 + 100 = 97
```

**Episode 20** (Learning, ε=0.5):
```
State: [0,1,0,... 0,0,0,1,0,...]  (corridor → outside)

Q-values after 20 episodes:
  Q[1] = 82.3  (reception, learned this takes longer)
  Q[3] = 91.7  (outside, learned this is direct!) ⭐
  Q[4] = 79.1  (common, learned this is detour)
  
50% chance: exploit → picks action=3 (outside)
Path: corridor → outside
Steps: 1, Reward: -1 + 100 = 99 (better!)
```

**Episode 100** (Mastered, ε=0.01):
```
State: [0,1,0,... 0,0,0,1,0,...]  (corridor → outside)

Q-values after convergence:
  Q[1] = 85.234  (reception)
  Q[3] = 98.876  (outside, optimal!) ⭐
  Q[4] = 83.567  (common)
  
99% chance: exploit → picks action=3
Consistently takes optimal 1-step path
```

#### What Was Learned?
- **NOT**: "Go outside when at corridor"
- **YES**: "For state vector [0,1,0,...,0,0,0,1,0,...], action 3 maximizes Q"
- The DQN learned 121 optimal policies (11 start × 11 goal combinations)
- Each learned through trial-and-error over ~200 episodes

---

### 🎭 **Action Masking - Preventing Invalid Moves**

**Problem:** Neural network always outputs 11 Q-values (one per region), but most are INVALID (walls block them)!

#### Without Masking (BROKEN):
```python
# At corridor, network outputs:
Q-values = [
    45.2,   # 0: reception
    12.8,   # 1: corridor (can't go to yourself!)
    15.3,   # 2: open_office
    98.7,   # 3: outside
    34.1,   # 4: common
    67.4,   # 5: meeting_room (WALL! not connected!)
    82.9,   # 6: senior_office_1 (WALL!)
    91.2,   # 7: senior_office_2 (WALL!)
    55.6,   # 8: senior_office_3 (WALL!)
    73.8,   # 9: boss_office_1 (WALL!)
    88.5    # 10: boss_office_2 (WALL!)
]

argmax → action=98.7 (outside) ✓ LUCKY!
But could pick 91.2 (senior_office_2) ✗ INVALID WALL!
```

#### With Action Masking (CORRECT):
```python
# Step 1: Jason finds valid neighbors (symbolic reasoning)
# File: symbolic_execution_engine.asl line 110
!get_valid_action_ids(ActionIds);
// Queries: neighbor(corridor, X)
// Returns: ActionIds = [1, 3, 4]  (reception, outside, common)

# Step 2: Send ONLY valid actions to Python
# File: select_action.java line 52
request.put("valid_actions", validActionsArray);  // [1, 3, 4]

# Step 3: Python masks invalid Q-values
# File: dqn_agent.py line 78-82
def select_action(self, state, valid_actions):
    with torch.no_grad():
        q_values = self.policy_net(state)  # All 11 Q-values
        
        # Mask: Set invalid actions to -infinity
        mask = torch.full((self.n_actions,), float('-inf'))
        mask[valid_actions] = 0  # Only valid actions get 0
        masked_q = q_values + mask
        
        # Now argmax ONLY picks from valid actions!
        action = masked_q.argmax().item()

# Masked result:
Original Q-values:  [45.2, 12.8, 15.3, 98.7, 34.1, 67.4, 82.9, 91.2, 55.6, 73.8, 88.5]
Mask applied:       [  0,  -inf,  -inf,    0,    0,  -inf, -inf, -inf, -inf, -inf, -inf]
Masked Q-values:    [45.2, -inf, -inf, 98.7, 34.1, -inf, -inf, -inf, -inf, -inf, -inf]
                      ↑            ↑      ↑
                   valid        valid  valid

argmax → 98.7 (action=3: outside) ✓ GUARANTEED VALID!
```

#### Why This Matters:
- **Safety**: Agent can never try to walk through walls
- **Efficiency**: Learns faster (doesn't waste episodes hitting walls)
- **Hybrid Intelligence**: Symbolic (Jason) constrains subsymbolic (DQN)

---

### 🔢 **Encoding & Decoding - Complete Example**

#### Encoding: Region Names → State Vector (Jason → Python)

**Goal:** Convert human-readable regions into numbers for neural network

```prolog
% File: symbolic_execution_engine.asl line 85-104

% Example: Current=open_office, Goal=outside

% Step 1: Get region IDs
region_id(open_office, 2);   % Look up: open_office = ID 2
region_id(outside, 3);       % Look up: outside = ID 3

% Step 2: Create one-hot vectors (11 dimensions each)
one_hot_encode(2, CurrentVector);
// Creates: [0,0,1,0,0,0,0,0,0,0,0]
//              ↑
//           position 2 = 1 (all others = 0)

one_hot_encode(3, GoalVector);
// Creates: [0,0,0,1,0,0,0,0,0,0,0]
//                ↑
//             position 3 = 1

% Step 3: Concatenate (append goal to current)
append(CurrentVector, GoalVector, StateVector);
// Result: [0,0,1,0,0,0,0,0,0,0,0, 0,0,0,1,0,0,0,0,0,0,0]
//          └─────current────────┘ └──────goal─────────┘
//              11 floats              11 floats
//          Total: 22-dimensional state vector
```

**Visual Example:**
```
Region Names:        open_office  →  outside
                           ↓              ↓
Region IDs:                2       →      3
                           ↓              ↓
One-Hot Current:    [0,0,1,0,0,0,0,0,0,0,0]
One-Hot Goal:       [0,0,0,1,0,0,0,0,0,0,0]
                           ↓
Concatenate:        [0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0]
                     └────────────────────┴────────────────────┘
                       Current (11)         Goal (11)
                              ↓
                    Python DQN Input (22 floats)
```

#### Why One-Hot Encoding?
- Neural networks need **numerical input**
- One-hot creates **orthogonal representations** (no false similarity)
- Example: `corridor(ID=1)` and `open_office(ID=2)` are NOT "close" just because 1 and 2 are close numbers
- One-hot: `[0,1,0,...]` vs `[0,0,1,...]` → Neural network learns distinct features

---

#### Decoding: Action ID → Region Name (Python → Jason)

**Goal:** Convert neural network output (integer) back into region for movement

```prolog
% File: symbolic_execution_engine.asl line 139-141

% Python returned: action_id = 3

% Decode to region name
id_to_region(3, TargetRegion);
// Lookup table (inverse of region_id):
// id_to_region(0, reception).
// id_to_region(1, corridor).
// id_to_region(2, open_office).
// id_to_region(3, outside).      ← Match!
// ...

// Result: TargetRegion = outside
```

**Complete Round-Trip Example:**

```
┌─────────────────────────────────────────────────────────────┐
│ ENCODING (Jason → Python)                                    │
├─────────────────────────────────────────────────────────────┤
│ Input:  current_region(open_office), goal_region(outside)   │
│         ↓                                                     │
│ Step 1: region_id(open_office, 2) → CurrentId = 2           │
│         region_id(outside, 3) → GoalId = 3                   │
│         ↓                                                     │
│ Step 2: one_hot(2) → [0,0,1,0,0,0,0,0,0,0,0]                │
│         one_hot(3) → [0,0,0,1,0,0,0,0,0,0,0]                │
│         ↓                                                     │
│ Step 3: append → [0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0] │
│         ↓                                                     │
│ Output: StateVector (22 floats) sent via HTTP to Python     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PYTHON DQN PROCESSING                                        │
├─────────────────────────────────────────────────────────────┤
│ Input:  StateVector[22], ValidActions=[1,3,4]               │
│         ↓                                                     │
│ Step 1: q_values = policy_net(StateVector)                  │
│         → [45.2, 12.8, 15.3, 98.7, 34.1, ...]              │
│         ↓                                                     │
│ Step 2: Apply action mask                                    │
│         → [45.2, -inf, -inf, 98.7, 34.1, -inf, ...]        │
│         ↓                                                     │
│ Step 3: argmax → action_id = 3                              │
│         ↓                                                     │
│ Output: JSON: {"action_id": 3, "q_values": {...}}           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ DECODING (Python → Jason)                                    │
├─────────────────────────────────────────────────────────────┤
│ Input:  action_id = 3 (from Python HTTP response)           │
│         ↓                                                     │
│ Step 1: id_to_region(3, TargetRegion)                       │
│         → TargetRegion = outside                             │
│         ↓                                                     │
│ Step 2: !hop_to(outside)                                     │
│         → vesna.walk(outside)                                │
│         ↓                                                     │
│ Output: WebSocket to Godot: {"type":"walk_to","data":"outside"} │
└─────────────────────────────────────────────────────────────┘
```

---

### 📊 **Complete Mapping Table**

| Region Name | ID | One-Hot Vector (11-dim) | Coordinates (Godot) |
|-------------|----|-----------------------|---------------------|
| reception | 0 | `[1,0,0,0,0,0,0,0,0,0,0]` | (3, 1.2, -22) |
| corridor | 1 | `[0,1,0,0,0,0,0,0,0,0,0]` | (3, 1.2, -2.5) |
| open_office | 2 | `[0,0,1,0,0,0,0,0,0,0,0]` | (-8, 1.2, 9) |
| outside | 3 | `[0,0,0,1,0,0,0,0,0,0,0]` | (3, 1.2, 25) |
| common | 4 | `[0,0,0,0,1,0,0,0,0,0,0]` | (-10, 1.2, -15) |
| meeting_room | 5 | `[0,0,0,0,0,1,0,0,0,0,0]` | (18, 1.2, 9) |
| senior_office_1 | 6 | `[0,0,0,0,0,0,1,0,0,0,0]` | (18, 1.2, -15) |
| senior_office_2 | 7 | `[0,0,0,0,0,0,0,1,0,0,0]` | (18, 1.2, -2.5) |
| senior_office_3 | 8 | `[0,0,0,0,0,0,0,0,1,0,0]` | (-10, 1.2, 20) |
| boss_office_1 | 9 | `[0,0,0,0,0,0,0,0,0,1,0]` | (18, 1.2, 20) |
| boss_office_2 | 10 | `[0,0,0,0,0,0,0,0,0,0,1]` | (-10, 1.2, -2.5) |

---

### 🎯 **Key Insight: Domain-Agnostic RL**

```
┌──────────────────────────────────────────────────────────┐
│ SYMBOLIC (Jason)          SUBSYMBOLIC (Python)           │
│ ═══════════════          ════════════════════            │
│                                                           │
│ "Alice needs to go       Q([0,0,1,0,0,0,0,0,0,0,0,       │
│  from open_office              0,0,0,1,0,0,0,0,0,0,0], 3) │
│  to outside"                   = 98.7                     │
│                                                           │
│ ↑ Human semantics        ↑ Pure mathematics              │
│ ↑ Domain knowledge       ↑ Domain-agnostic               │
│ ↑ Reasoning              ↑ Pattern recognition           │
└──────────────────────────────────────────────────────────┘
```

**Why this matters:**
- Same Python DQN could learn ANY grid-world navigation (warehouse, hospital, maze)
- Only Jason needs to change (new map, new neighbor facts)
- RL service is REUSABLE across domains!

---

### 🔗 **"Symbolic Constrains Subsymbolic" - Deep Explanation**

This is the **key innovation** of hybrid AI: The symbolic layer CONTROLS what the subsymbolic layer is allowed to do.

#### Concrete Example: Wall Prevention

**Scenario:** Alice at corridor, goal is outside

---

**WITHOUT Symbolic Constraint (Pure DQN - DANGEROUS!):**

DQN neural network outputs Q-values for ALL 11 actions:

| Action ID | Region           | Q-Value | Valid? |
|-----------|------------------|---------|--------|
| 0         | reception        | 45.2    | ✓ Yes  |
| 1         | corridor         | 12.8    | ✗ Self |
| 2         | open_office      | 88.9    | ✗ WALL!|
| 3         | outside          | 98.7    | ✓ Yes  |
| 4         | common           | 76.3    | ✗ WALL!|
| 5         | meeting_room     | 92.1    | ✗ WALL!|
| 6         | senior_office_1  | 67.4    | ✗ WALL!|
| 7         | senior_office_2  | 82.9    | ✗ WALL!|
| 8         | senior_office_3  | 55.6    | ✗ WALL!|
| 9         | boss_office_1    | 73.8    | ✗ WALL!|
| 10        | boss_office_2    | 91.2    | ✗ WALL!|

**Problem:** 
- DQN picks argmax(Q) = 98.7 (outside) ✓ Works THIS time
- BUT: If during training Q[5]=105.3 (meeting_room) accidentally gets high, DQN would pick meeting_room → Alice walks into WALL → Crash!
- The DQN doesn't KNOW about walls - it only knows Q-values!

---

**WITH Symbolic Constraint (Your Hybrid System - SAFE!):**

**Step 1: Jason (Symbolic) checks map**

File: `mind/src/agt/symbolic_execution_engine.asl` line 110

Jason executes:
```prolog
.findall(N, neighbor(corridor, N), Neighbors)
```

Looks up facts in `office_map.asl`:
```prolog
neighbor(corridor, reception).     ← Found!
neighbor(corridor, open_office).   ← NOT in map (no connection)
neighbor(corridor, outside).       ← Found!
neighbor(corridor, common).        ← NOT in map
```

**Result:** 
- Neighbors = [reception, outside]
- Valid ActionIds = [0, 3] ← ONLY 2 out of 11!

---

**Step 2: Jason COMMANDS DQN via HTTP**

File: `mind/src/env/select_action.java` line 52

JSON sent to Python:
```json
{
  "state": [0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0],
  "valid_actions": [0, 3],
  "reward": -1.0,
  "done": false
}
```
**Note:** `valid_actions` is the constraint from Jason!

---

**Step 3: Python DQN applies mask**

File: `mind/python/dqn_agent.py` line 78

```python
def select_action(self, state, valid_actions):
    q_values = self.policy_net(state)
    # Output: [45.2, 12.8, 88.9, 98.7, 76.3, 92.1, ...]
    
    # Create mask: -infinity for invalid actions
    mask = torch.full((11,), float('-inf'))
    mask[valid_actions] = 0  # Only [0, 3] get 0
    
    masked_q = q_values + mask
    # Result: [45.2, -inf, -inf, 98.7, -inf, -inf, -inf, -inf, -inf, -inf, -inf]
    
    action = masked_q.argmax()  # Must be 0 or 3, no other choice!
    return 3  # outside (Q=98.7 > 45.2)
```

---

**VISUALIZATION of Masking:**

```
Before mask:
[45.2, 12.8, 88.9, 98.7, 76.3, 92.1, 67.4, 82.9, 55.6, 73.8, 91.2]
  ✓     ✗     ✗     ✓     ✗     ✗     ✗     ✗     ✗     ✗     ✗

Mask applied:
[  0,  -∞,   -∞,    0,   -∞,   -∞,   -∞,   -∞,   -∞,   -∞,   -∞]

After mask (addition):
[45.2, -∞,   -∞,  98.7,  -∞,   -∞,   -∞,   -∞,   -∞,   -∞,   -∞]
  ↑                 ↑
  Can only pick these two!

argmax → 98.7 (index 3 = outside) ✓ GUARANTEED VALID!
```

**Result:** DQN can NEVER pick invalid action! Symbolic knowledge CONSTRAINS subsymbolic choice.

#### Why This Hybrid Approach is Powerful:

| Aspect | Pure Symbolic | Pure DQN | Hybrid (Your System) |
|--------|---------------|----------|----------------------|
| **Knows map** | ✓ Yes (facts) | ✗ No (learns) | ✓ Yes (symbolic) |
| **Learns optimal paths** | ✗ No (hardcoded) | ✓ Yes (Q-learning) | ✓ Yes (subsymbolic) |
| **Can violate physics** | ✗ No (logic prevents) | ✓ Yes (might try walls) | ✗ No (symbolic blocks) |
| **Adapts to new goals** | ✗ No (new rules needed) | ✓ Yes (same network) | ✓ Yes (subsymbolic) |
| **Explainable** | ✓ Yes (reasoning trace) | ✗ No (black box) | ✓ Yes (symbolic+Q-values) |

**Result:** You get the BEST of both worlds!
- Symbolic: Safety, explainability, domain knowledge
- Subsymbolic: Learning, optimization, generalization

---

### 🔢 **The Complete ID Mapping - How It's Defined**

The region-to-ID mapping is **manually defined** by the developer in the code:

#### Definition Location:
**File:** `mind/src/agt/symbolic_execution_engine.asl` (lines 25-35)

```prolog
// MANUALLY DEFINED by developer:
region_id(reception,       0).   ← Developer assigns: reception = 0
region_id(corridor,        1).   ← Developer assigns: corridor = 1
region_id(open_office,     2).   ← Developer assigns: open_office = 2
region_id(outside,         3).   ← Developer assigns: outside = 3
region_id(common,          4).   ← Developer assigns: common = 4
region_id(meeting_room,    5).   ← Developer assigns: meeting_room = 5
region_id(senior_office_1, 6).   ← Developer assigns: senior_office_1 = 6
region_id(senior_office_2, 7).   ← Developer assigns: senior_office_2 = 7
region_id(senior_office_3, 8).   ← Developer assigns: senior_office_3 = 8
region_id(boss_office_1,   9).   ← Developer assigns: boss_office_1 = 9
region_id(boss_office_2,  10).   ← Developer assigns: boss_office_2 = 10

num_regions(11).  ← Total count (must match!)
```

#### How One-Hot Encoding Uses These IDs:

```prolog
// Example: Encode "open_office"

Step 1: Look up ID
───────────────────
region_id(open_office, CurrentId).
→ CurrentId = 2  (from the table above)


Step 2: Create one-hot vector
──────────────────────────────
one_hot_encode(2, Vector).

Creates 11-element list where ONLY position 2 is 1:
Position:  0  1  2  3  4  5  6  7  8  9 10
          [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0]
                 ↑
                ID=2 position set to 1

All others are 0 (that's why it's called "one-hot" - only ONE position is "hot"/1)


Step 3: Complete example with two regions
──────────────────────────────────────────
Current region: open_office → ID 2 → [0,0,1,0,0,0,0,0,0,0,0]
Goal region:    outside     → ID 3 → [0,0,0,1,0,0,0,0,0,0,0]

Concatenate (append goal to current):
[0,0,1,0,0,0,0,0,0,0,0, 0,0,0,1,0,0,0,0,0,0,0]
 └───── 11 floats ─────┘ └───── 11 floats ─────┘
   Current encoding        Goal encoding
         Total: 22-dimensional state vector
```

#### Complete Mapping Table with Examples:

```
┌────────────────────┬────┬─────────────────────────┬──────────────────────────┐
│ Region Name        │ ID │ One-Hot (11-dim)        │ Example State if Current │
├────────────────────┼────┼─────────────────────────┼──────────────────────────┤
│ reception          │  0 │ [1,0,0,0,0,0,0,0,0,0,0] │ [1,0,0,0,0,0,0,0,0,0,0,  │
│                    │    │                         │  0,0,0,1,0,0,0,0,0,0,0]  │
│                    │    │                         │  ↑current    ↑goal(out)  │
├────────────────────┼────┼─────────────────────────┼──────────────────────────┤
│ corridor           │  1 │ [0,1,0,0,0,0,0,0,0,0,0] │ [0,1,0,0,0,0,0,0,0,0,0,  │
│                    │    │                         │  0,0,0,1,0,0,0,0,0,0,0]  │
├────────────────────┼────┼─────────────────────────┼──────────────────────────┤
│ open_office        │  2 │ [0,0,1,0,0,0,0,0,0,0,0] │ [0,0,1,0,0,0,0,0,0,0,0,  │
│                    │    │                         │  0,0,0,1,0,0,0,0,0,0,0]  │
├────────────────────┼────┼─────────────────────────┼──────────────────────────┤
│ outside            │  3 │ [0,0,0,1,0,0,0,0,0,0,0] │ [0,0,0,1,0,0,0,0,0,0,0,  │
│                    │    │                         │  0,0,0,1,0,0,0,0,0,0,0]  │
│                    │    │                         │  (current=goal=outside!) │
├────────────────────┼────┼─────────────────────────┼──────────────────────────┤
│ common             │  4 │ [0,0,0,0,1,0,0,0,0,0,0] │ [0,0,0,0,1,0,0,0,0,0,0,  │
│                    │    │                         │  0,0,0,1,0,0,0,0,0,0,0]  │
├────────────────────┼────┼─────────────────────────┼──────────────────────────┤
│ meeting_room       │  5 │ [0,0,0,0,0,1,0,0,0,0,0] │ [0,0,0,0,0,1,0,0,0,0,0,  │
│                    │    │                         │  0,0,0,1,0,0,0,0,0,0,0]  │
├────────────────────┼────┼─────────────────────────┼──────────────────────────┤
│ senior_office_1    │  6 │ [0,0,0,0,0,0,1,0,0,0,0] │ [0,0,0,0,0,0,1,0,0,0,0,  │
│                    │    │                         │  0,0,0,1,0,0,0,0,0,0,0]  │
├────────────────────┼────┼─────────────────────────┼──────────────────────────┤
│ senior_office_2    │  7 │ [0,0,0,0,0,0,0,1,0,0,0] │ [0,0,0,0,0,0,0,1,0,0,0,  │
│                    │    │                         │  0,0,0,1,0,0,0,0,0,0,0]  │
├────────────────────┼────┼─────────────────────────┼──────────────────────────┤
│ senior_office_3    │  8 │ [0,0,0,0,0,0,0,0,1,0,0] │ [0,0,0,0,0,0,0,0,1,0,0,  │
│                    │    │                         │  0,0,0,1,0,0,0,0,0,0,0]  │
├────────────────────┼────┼─────────────────────────┼──────────────────────────┤
│ boss_office_1      │  9 │ [0,0,0,0,0,0,0,0,0,1,0] │ [0,0,0,0,0,0,0,0,0,1,0,  │
│                    │    │                         │  0,0,0,1,0,0,0,0,0,0,0]  │
├────────────────────┼────┼─────────────────────────┼──────────────────────────┤
│ boss_office_2      │ 10 │ [0,0,0,0,0,0,0,0,0,0,1] │ [0,0,0,0,0,0,0,0,0,0,1,  │
│                    │    │                         │  0,0,0,1,0,0,0,0,0,0,0]  │
└────────────────────┴────┴─────────────────────────┴──────────────────────────┘

Note: All examples assume goal = "outside" (ID=3) for illustration
```

#### Why This Mapping Is Important:

1. **Bidirectional Translation:**
   ```
   Encoding:  "open_office" → 2 → [0,0,1,0,0,0,0,0,0,0,0]
   Decoding:  3 → "outside"
   ```

2. **IDs MUST be 0-indexed and consecutive:**
   - Python expects: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
   - Can't skip: [0, 1, 5, 9, 10] ✗ Would break one-hot encoding!

3. **Order doesn't matter semantically:**
   - You could swap: `reception=5, meeting_room=0`
   - But be consistent across encoding/decoding!

4. **Adding new regions:**
   ```prolog
   // To add "kitchen" region:
   region_id(kitchen, 11).        ← Next available ID
   num_regions(12).               ← Update count
   neighbor(corridor, kitchen).   ← Add connections
   
   // Python DQN automatically adapts:
   // - Input layer: 22 → 24 (12+12)
   // - Output layer: 11 → 12 actions
   // (Requires retraining from scratch)
   ```

---

### 🧩 **Architecture Overview**
This is a **Hybrid AI System** combining:
- **Symbolic AI** (Jason/AgentSpeak) - High-level reasoning and decision-making
- **Subsymbolic AI** (Python DQN) - Deep reinforcement learning for navigation
- **Embodied AI** (Godot 3D) - Physical simulation and spatial perception

### 🔄 **Complete Workflow in 20 Steps**

| Step | Component | What Happens | Input | Output |
|------|-----------|--------------|-------|--------|
| 1 | Jason | Initialize episode | episode=55, goal=outside | Console: "EPISODE 55" |
| 2 | Jason → Godot | Teleport to start | coords=(3,1.2,-22) | WebSocket: teleport |
| 3 | Godot → Jason | Confirm region | - | region_entered: open_office |
| 4 | Jason | Update beliefs | - | current_region(open_office) |
| 5 | Jason | Check goal | open_office ≠ outside | Continue loop |
| 6 | Symbolic Engine | Encode state | regions→IDs | StateVector[22] |
| 7 | Symbolic Engine | Find neighbors | open_office | [corridor,outside,common] |
| 8 | Symbolic Engine | Convert to IDs | region names | ActionIds=[1,3,4] |
| 9 | Java | Build HTTP request | state+actions+reward | JSON payload |
| 10 | Java → Python | Send request | HTTP POST | - |
| 11 | Python | Store transition | prev experience | ReplayBuffer ← transition |
| 12 | Python | Train DQN | 32 random samples | Q-network weights updated |
| 13 | Python | Select action | Q-values + epsilon | action_id=3 (outside) |
| 14 | Python → Java | Return response | HTTP 200 | JSON: action+explanation |
| 15 | Java | Log trace | action+alternatives | Console: [TRACE #111] |
| 16 | Jason | Convert ID→name | 3 | "outside" |
| 17 | Jason → Godot | Execute movement | walk(outside) | WebSocket: walk_to |
| 18 | Godot | Navigate 3D space | target=outside | Physics simulation |
| 19 | Godot → Jason | Region entered | collision detected | region_entered: outside |
| 20 | Jason | Goal achieved! | outside==outside | Reward +100, Episode done |

### 🎯 **Key Innovations**

1. **Domain-Agnostic RL Service**
   - Python knows nothing about rooms/offices
   - All domain knowledge in Jason (symbolic layer)
   - Pure state vectors (22 floats) for learning

2. **Explainable AI**
   - Every decision logged with Q-values
   - Shows alternatives NOT selected
   - Full reasoning trace in JSON/Prolog

3. **Embodied Cognition**
   - Agent has physical body in 3D world
   - Real navigation with obstacles
   - Perception through collision detection

4. **Closed-Loop Architecture**
   ```
   Perception → Reasoning → Learning → Action → Perception
   (Godot)    (Jason)      (Python)   (Godot)    (Loop)
   ```

### 📈 **Learning Process**

- **Experience Replay**: Stores 10,000 transitions
- **Batch Training**: 32 samples per step
- **Target Network**: Updated every 10 episodes
- **Epsilon Decay**: 1.0 → 0.01 (exploration → exploitation)
- **Goal-Conditioned**: Same policy works for any start/goal pair

### 🔧 **Technology Stack**

| Layer | Technology | Purpose |
|-------|------------|---------|
| Symbolic | Jason/AgentSpeak | BDI reasoning, plan selection |
| Integration | Java + HTTP | Bridge Jason ↔ Python |
| Learning | PyTorch DQN | Deep Q-learning |
| Embodiment | Godot 4 + GDScript | 3D simulation, navigation |
| Communication | WebSocket + REST | Real-time bidirectional messaging |
| Explainability | NOVAE Trace Logger | Decision provenance tracking |

### 💡 **Real-World Applications**

- **Office Navigation**: Autonomous robots in workspaces
- **Hospital Assistance**: Guiding patients/staff
- **Warehouse Logistics**: Picking and delivery
- **Smart Buildings**: Adaptive building management
- **Research Platform**: Hybrid AI experimentation

---

## 📊 STEP-BY-STEP WORKFLOW WITH INPUT/OUTPUT

### **STEP 1: Episode Initialization**
**File:** `alice_rl.asl` (lines 57-70)

**Input:**
- `episode(55)` - Current episode number
- `goal_region(outside)` - Target destination
- `start_position(3, 1.2, -22)` - Reception coordinates

**Process:**
```jason
+!run_episode
    :   episode(Ep)
    <-  .print("========== EPISODE ", Ep, " ==========");
        +step(0);
        +episode_reward(0);
        !reset_position;
        !rl_loop.
```

**Output:**
```
[alice] ========== EPISODE 55 ==========
```

**State Changes:**
- `step(0)` added to belief base
- `episode_reward(0)` added to belief base

---

### **STEP 2: Teleport to Start Position**
**File:** `alice_rl.asl` (lines 72-76)

**Input:**
- `start_position(3, 1.2, -22)`

**Process:**
```jason
+!reset_position
    <-  ?start_position(X, Y, Z);
        vesna.teleport(X, Y, Z);
        .wait({+movement(completed, destination_reached)}).
```

**WebSocket Output → Godot:**
```json
{
  "type": "teleport",
  "data": {
    "x": 3,
    "y": 1.2,
    "z": -22
  }
}
```

**WebSocket Input ← Godot:**
```json
{
  "type": "region_entered",
  "data": {
    "status": "open_office",
    "reason": "body_entered"
  }
}
```

**Console Output:**
```
Received message: {"data":{"reason":"body_entered","status":"open_office","type":"region_entered"},"receiver":"vesna","sender":"body","type":"signal"}
```

**State Changes:**
- `current_region(open_office)` added to belief base

---

### **STEP 3: Check Goal Condition**
**File:** `alice_rl.asl` (lines 82-96, 114-131)

**Input:**
- `current_region(open_office)`
- `goal_region(outside)`
- `step(0)`

**Process:**
```jason
+!rl_loop
    :   current_region(Region) & step(S)
    <-  ?goal_region(GoalRegion);
        .print("Step ", S, ": at ", Region, " (goal: ", GoalRegion, ")");
```

**Output:**
```
[alice] Step 0: at open_office (goal: outside)
```

**Decision:** `open_office ≠ outside` → Continue to RL action selection

---

### **STEP 4: Build State Vector**
**File:** `symbolic_execution_engine.asl` (lines 85-104)

**Input:**
- `CurrentRegion = "open_office"`
- `GoalRegion = "outside"`

**Process:**
```jason
+!build_goal_state_vector(CurrentRegion, GoalRegion, StateVector)
    <-  region_id(CurrentRegion, CurrentId);      // open_office → 2
        region_id(GoalRegion, GoalId);             // outside → 3
        !one_hot_encode(CurrentId, 11, CurrentVec);
        !one_hot_encode(GoalId, 11, GoalVec);
        .concat(CurrentVec, GoalVec, StateVector).
```

**Intermediate Values:**
```
CurrentId = 2
GoalId = 3

CurrentVec (one-hot for position 2):
[0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0]
     ↑
   open_office

GoalVec (one-hot for position 3):
[0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]
        ↑
     outside
```

**Output:**
```
StateVector = [0,0,1,0,0,0,0,0,0,0,0, 0,0,0,1,0,0,0,0,0,0,0]
              |________11 dims_______|  |________11 dims_______|
                  current_region            goal_region
```

---

### **STEP 5: Get Valid Actions (Adjacency)**
**File:** `symbolic_execution_engine.asl` (lines 110-117)

**Input:**
- `CurrentRegion = "open_office"`

**Process:**
```jason
+!get_valid_action_ids(CurrentRegion, ActionIds)
    <-  .findall(N, neighbor(CurrentRegion, N), Neighbors);
        !regions_to_ids(Neighbors, ActionIds).
```

**Adjacency Facts (from symbolic_execution_engine.asl lines 41-77):**
```jason
neighbor(open_office, corridor).
neighbor(open_office, outside).
neighbor(open_office, common).
```

**Intermediate:**
```
Neighbors = ["corridor", "outside", "common"]
```

**Recursive Conversion (regions_to_ids):**
```
corridor     → region_id(corridor, 1)     → 1
outside      → region_id(outside, 3)      → 3
common       → region_id(common, 4)       → 4
```

**Output:**
```
ActionIds = [1, 3, 4]
```

---

### **STEP 6: Java Internal Action - HTTP Request**
**File:** `select_action.java` (lines 40-105)

**Input:**
- `StateVector = [0,0,1,0,0,0,0,0,0,0,0, 0,0,0,1,0,0,0,0,0,0,0]`
- `ValidActionIds = [1, 3, 4]`
- `Reward = -1.0`
- `Done = false`

**Process:**
```java
JSONObject requestBody = new JSONObject();
requestBody.put("agent_id", "alice");
requestBody.put("state", stateArray);
requestBody.put("valid_actions", validActionsArray);
requestBody.put("reward", -1.0);
requestBody.put("done", false);

HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("http://localhost:5000/select_action"))
    .header("Content-Type", "application/json")
    .POST(HttpRequest.BodyPublishers.ofString(requestBody.toString()))
    .build();
```

**HTTP Request (POST to Python):**
```json
{
  "agent_id": "alice",
  "state": [0,0,1,0,0,0,0,0,0,0,0, 0,0,0,1,0,0,0,0,0,0,0],
  "valid_actions": [1, 3, 4],
  "reward": -1.0,
  "done": false
}
```

---

### **STEP 7: Python DQN - Store Previous Transition**
**File:** `dqn_agent.py` (lines 85-120)

**Input:** HTTP request from Java

**Process:**
```python
def step_with_explanation(self, state, valid_actions, reward, done):
    # Store previous transition
    if self.prev_state is not None:
        transition = (
            self.prev_state,      # [0,0,1,0,0,0,0,0,0,0,0, 0,0,0,0,0,1,0,0,0,0,0]
            self.prev_action,     # 3
            reward,               # -1.0
            state,                # [0,0,1,0,0,0,0,0,0,0,0, 0,0,0,1,0,0,0,0,0,0,0]
            done                  # False
        )
        self.memory.append(transition)
```

**Output:**
```
ReplayBuffer size: 156 transitions
Memory now contains: [..., (prev_state, prev_action, -1.0, current_state, False)]
```

---

### **STEP 8: Python DQN - Training (if enough samples)**
**File:** `dqn_agent.py` (lines 140-185)

**Input:**
- `len(memory) = 156 >= batch_size(32)`

**Process:**
```python
if len(self.memory) >= self.batch_size:
    # Sample 32 random transitions
    batch = random.sample(self.memory, self.batch_size)
    
    for (s, a, r, s_next, d) in batch:
        # Bellman equation
        if d:
            target_q = r  # Terminal state
        else:
            with torch.no_grad():
                next_q_values = self.target_network(s_next)
                target_q = r + self.gamma * torch.max(next_q_values)
        
        # Current Q prediction
        current_q = self.q_network(s)[a]
        
        # Loss and backprop
        loss = F.smooth_l1_loss(current_q, target_q)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
```

**Output:**
```
Training completed: 32 transitions processed
Loss: 0.0234
Q-network weights updated
```

---

### **STEP 9: Python DQN - Action Selection**
**File:** `dqn_agent.py` (lines 200-240)

**Input:**
- `state = [0,0,1,0,0,0,0,0,0,0,0, 0,0,0,1,0,0,0,0,0,0,0]`
- `valid_actions = [1, 3, 4]`
- `epsilon = 0.01` (inference mode)

**Process:**
```python
exploration = "greedy"
if np.random.random() < self.epsilon:  # 0.005 < 0.01
    # EXPLOIT: Use Q-network
    with torch.no_grad():
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        q_values = self.q_network(state_tensor).squeeze().numpy()
        
        # Mask invalid actions
        masked_q = np.full(11, -np.inf)
        for a in valid_actions:
            masked_q[a] = q_values[a]
        
        action = np.argmax(masked_q)
else:
    # EXPLORE: Random
    action = np.random.choice(valid_actions)
    exploration = "random"
```

**Q-Values (all 11 regions):**
```
Q[0] (reception)      = 12.345  → masked (not valid)
Q[1] (corridor)       = 45.678  → valid
Q[2] (open_office)    = 23.456  → masked (not valid)
Q[3] (outside)        = 98.234  → valid ✓ MAX
Q[4] (common)         = 34.567  → valid
Q[5] (meeting_room)   = 67.890  → masked (not valid)
...
```

**Output:**
```
selected_action = 3 (outside)
selected_q = 98.234
exploration = "greedy"
mode = "inference"
```

---

### **STEP 10: Python - Return Response**
**File:** `dqn_server.py` (lines 50-80)

**HTTP Response:**
```json
{
  "action_id": 3,
  "explanation": {
    "q_values": {
      "1": 45.678,
      "3": 98.234,
      "4": 34.567
    },
    "selected_q": 98.234,
    "exploration": "greedy",
    "mode": "inference",
    "epsilon": 0.01
  }
}
```

---

### **STEP 11: Java - Create Trace Entry**
**File:** `select_action.java` (lines 145-210)

**Input:** JSON response from Python

**Process:**
```java
// Decode state
int currentRegionId = 2;  // open_office
int goalRegionId = 3;     // outside

// Build trace content
StringBuilder content = new StringBuilder();
content.append("RL_ACTION: ").append(actionId);           // 3
content.append(" | from=").append(REGION_NAMES[2]);       // open_office
content.append(" | goal=").append(REGION_NAMES[3]);       // outside
content.append(" | reward=").append(-1.0);
content.append(" | mode=").append("inference");

// Build alternatives
List<String> alternatives = new ArrayList<>();
alternatives.add("corridor (Q=45.678 < selected Q=98.234)");
alternatives.add("common (Q=34.567 < selected Q=98.234)");

TraceEntry entry = new TraceEntry.Builder("alice", ACTION, content.toString())
    .alternativesNotSelected(alternatives)
    .result("success")
    .metadata("Q-values: {...} | exploration=greedy")
    .build();

logger.log(entry);
```

**Console Output:**
```
[TRACE #111] Cycle 0 | alice | ACTION: RL_ACTION: 3 | from=open_office | goal=outside | reward=-1.0 | mode=inference (2 alternatives not selected)
```

**Trace File Output (logs/alice_rl_trace.json):**
```json
{
  "id": 111,
  "timestamp": "2026-02-04T10:30:45.123Z",
  "cycle": 0,
  "agent": "alice",
  "changerType": "ACTION",
  "changerContent": "RL_ACTION: 3 | from=open_office | goal=outside | reward=-1.0 | mode=inference",
  "alternativesNotSelected": [
    "corridor (Q=45.678 < selected Q=98.234)",
    "common (Q=34.567 < selected Q=98.234)"
  ],
  "result": "success",
  "metadata": "Q-values: {corridor=45.678, outside=98.234*, common=34.567} | exploration=greedy"
}
```

---

### **STEP 12: Convert Action ID to Region Name**
**File:** `symbolic_execution_engine.asl` (lines 135-137)

**Input:**
- `ActionId = 3`

**Process:**
```jason
id_to_region(ActionId, TargetRegion).
// Lookup: id_to_region(3, outside)
```

**Output:**
```
TargetRegion = "outside"
```

---

### **STEP 13: Print Selected Action**
**File:** `alice_rl.asl` (line 121)

**Input:**
- `TargetRegion = "outside"`

**Output:**
```
[alice]   -> RL selected: outside
```

---

### **STEP 14: Execute Movement**
**File:** `symbolic_execution_engine.asl` (lines 156-180)

**Input:**
- `TargetRegion = "outside"`

**Process:**
```jason
+!hop_to(TargetRegion)
    <-  vesna.walk(TargetRegion);
        .wait({+movement(completed, destination_reached)}).
```

**WebSocket Output → Godot:**
```json
{
  "type": "walk_to",
  "data": {
    "target": "outside"
  }
}
```

---

### **STEP 15: Godot Navigation**
**File:** `vesna.gd` (Godot script)

**Input:** WebSocket message `walk_to: outside`

**Process:**
```gdscript
func _on_websocket_message(msg):
    if msg.type == "walk_to":
        var target = msg.data.target
        navigation_agent.target_position = get_target_position(target)

func _physics_process(delta):
    if navigation_agent.is_navigation_finished():
        return
    
    var next_position = navigation_agent.get_next_path_position()
    var velocity = (next_position - global_position).normalized() * speed
    velocity = move_and_slide(velocity)
```

**Output:**
- Vesna avatar moves through 3D space
- Physics updates at 60 FPS
- Navigation path calculated by NavigationServer3D

---

### **STEP 16: Region Detection**
**File:** `vesna.gd` + Godot Area3D

**Input:** Vesna body enters "outside" Area3D collision zone

**Process:**
```gdscript
func _on_area_entered(area):
    if area.is_in_group("regions"):
        var region_name = area.name  // "outside"
        send_websocket({
            "type": "region_entered",
            "data": {
                "status": region_name,
                "reason": "body_entered"
            }
        })
```

**WebSocket Output → Jason:**
```json
{
  "type": "region_entered",
  "data": {
    "status": "outside",
    "reason": "body_entered"
  }
}
```

**Console Output:**
```
Received message: {"data":{"reason":"body_entered","status":"outside","type":"region_entered"},"receiver":"vesna","sender":"body","type":"signal"}
```

---

### **STEP 17: Update Beliefs**
**File:** `symbolic_execution_engine.asl` (lines 147-153)

**Input:** WebSocket message received

**Process:**
```jason
+region_entered(NewRegion)[source(body)]
    <-  -current_region(_);
        +current_region(NewRegion).
```

**State Changes:**
```
Before: current_region(open_office)
After:  current_region(outside)
```

---

### **STEP 18: Movement Completion**
**File:** Godot → Jason

**WebSocket Output → Jason:**
```json
{
  "type": "movement",
  "data": {
    "status": "completed",
    "reason": "destination_reached"
  }
}
```

**Process:**
```jason
.wait({+movement(completed, destination_reached)}).
// Unblocks and continues execution
```

---

### **STEP 19: Check Goal Achievement**
**File:** `alice_rl.asl` (lines 82-96)

**Input:**
- `current_region(outside)`
- `goal_region(outside)`

**Process:**
```jason
+!rl_loop
    :   current_region(Region) & goal_region(Region)
    <-  ?step(S);
        ?episode(Ep);
        .print("*** GOAL REACHED in ", S, " steps! ***");
        !rl_select_action(Region, Region, 100.0, true, _);
        ?episode_reward(ER);
        NewER = ER + 100;
        -episode_reward(_);
        +episode_reward(NewER);
        .print("Episode ", Ep, " total reward: ", NewER);
        !next_episode.
```

**Console Output:**
```
[alice] *** GOAL REACHED in 1 steps! ***
[alice] Episode 55 total reward: 99
```

**Final RL Call (with done=true):**
```json
HTTP POST {
  "agent_id": "alice",
  "state": [0,0,0,1,0,0,0,0,0,0,0, 0,0,0,1,0,0,0,0,0,0,0],
  "valid_actions": [2, 1, 4],  // neighbors of outside
  "reward": 100.0,
  "done": true
}
```

**Console Output:**
```
[TRACE #112] Cycle 0 | alice | ACTION: RL_ACTION: 2 | from=outside | goal=outside | reward=100.0 | mode=inference
```

---

### **STEP 20: Episode Completion**
**File:** `alice_rl.asl` (lines 129-140)

**Input:**
- `episode(55)`

**Process:**
```jason
+!next_episode
    :   episode(Ep)
    <-  NewEp = Ep + 1;
        -episode(_);
        +episode(NewEp);
        -step(_);
        -episode_reward(_);
        .wait(1000);
        !run_episode.
```

**State Changes:**
```
episode(55) → episode(56)
Removed: step(_), episode_reward(_)
```

**Output:**
```
[alice] 
[alice] ========== EPISODE 56 ==========
```

---

## 🔄 Complete Data Flow Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    EPISODE 55 COMPLETE FLOW                     │
└─────────────────────────────────────────────────────────────────┘

INPUT (Initial State):
  ├─ current_region: "open_office"
  ├─ goal_region: "outside"
  ├─ step: 0
  └─ episode_reward: 0

PROCESSING:
  Step 1: Encode state → [0,0,1,0,0,0,0,0,0,0,0, 0,0,0,1,0,0,0,0,0,0,0]
  Step 2: Find neighbors → [1, 3, 4] (corridor, outside, common)
  Step 3: HTTP → Python DQN
  Step 4: Train on 32 samples
  Step 5: Q-values → {1: 45.678, 3: 98.234, 4: 34.567}
  Step 6: Select action 3 (outside) - highest Q-value
  Step 7: Convert 3 → "outside"
  Step 8: WebSocket → Godot walk_to(outside)
  Step 9: Godot navigation (3D physics)
  Step 10: Region entered → "outside"
  Step 11: Update current_region → "outside"
  Step 12: Check goal: outside == outside ✓

OUTPUT (Final State):
  ├─ current_region: "outside" (GOAL REACHED!)
  ├─ step: 1
  ├─ episode_reward: 99 (-1 for step + 100 for goal)
  ├─ episode: 56 (incremented)
  └─ Traces logged: 2 entries (#111, #112)

REWARD CALCULATION:
  Initial:     0
  Step 0:     -1  (normal movement penalty)
  Goal:     +100  (achievement bonus)
  ──────────────
  Total:      99
```

---

## 📋 Data Structure Reference

### Region ID Mapping
```
ID  | Region Name      | Coordinates (approx)
----|------------------|---------------------
0   | reception        | (3, 1.2, -22)
1   | corridor         | (20, 1.2, -20)
2   | open_office      | (45, 1.2, -30)
3   | outside          | (80, 1.2, 15)
4   | common           | (60, 1.2, 5)
5   | meeting_room     | (100, 1.2, -10)
6   | senior_office_1  | (120, 1.2, -25)
7   | senior_office_2  | (130, 1.2, -35)
8   | senior_office_3  | (140, 1.2, -45)
9   | boss_office_1    | (145, 1.2, -15)
10  | boss_office_2    | (148, 1.2, -30)
```

### State Vector Structure (22 dimensions)
```
Positions  0-10: Current region (one-hot encoded)
Positions 11-21: Goal region (one-hot encoded)

Example: open_office(2) → outside(3)
[0,0,1,0,0,0,0,0,0,0,0, 0,0,0,1,0,0,0,0,0,0,0]
     ↑                        ↑
  position 2              position 3
```

### Adjacency Graph
```
neighbor(reception,       corridor).
neighbor(corridor,        reception).
neighbor(corridor,        open_office).
neighbor(corridor,        outside).
neighbor(corridor,        common).
neighbor(open_office,     corridor).
neighbor(open_office,     outside).
neighbor(open_office,     common).
neighbor(outside,         open_office).
neighbor(outside,         corridor).
neighbor(outside,         common).
neighbor(common,          corridor).
neighbor(common,          outside).
neighbor(common,          open_office).
neighbor(common,          meeting_room).
neighbor(meeting_room,    common).
neighbor(meeting_room,    senior_office_1).
...
```

---

## 🔍 Key Takeaways

1. **Symbolic → Subsymbolic Bridge:** Jason converts symbolic regions to numeric vectors
2. **HTTP as Integration Layer:** Java bridges Jason and Python via REST API
3. **Explainability First:** Every RL decision logged with Q-values and alternatives
4. **Embodied Perception:** Godot provides ground truth via WebSocket signals
5. **Closed Loop:** Perception → Reasoning → Action → Perception

## Detailed Component Breakdown

### 1. Jason Agent (alice_rl.asl)
- **Line 64**: Episode start
- **Line 117**: Print current state
- **Line 119**: Call !rl_select_action
- **Line 121**: Print selected action
- **Line 123**: Execute !hop_to
- **Line 125-130**: Update counters, recurse

### 2. Symbolic Execution Engine (symbolic_execution_engine.asl)
- **Lines 85-104**: !build_goal_state_vector (encoding)
- **Lines 110-117**: !get_valid_action_ids (adjacency)
- **Lines 120-137**: !rl_select_action (orchestration)
- **Lines 156-180**: !hop_to (movement execution)
- **Lines 147-153**: +region_entered (perception)

### 3. Java Internal Action (select_action.java)
- **Lines 40-100**: Build HTTP request
- **Lines 102-115**: Send POST to Python
- **Lines 117-140**: Parse response
- **Lines 145-210**: Create explainability trace

### 4. Python RL Service (dqn_agent.py)
- **Lines 85-120**: step_with_explanation
- **Lines 140-180**: Experience replay & training
- **Lines 200-230**: Epsilon-greedy selection
- **Lines 240-270**: Q-network forward pass

### 5. Godot Body (vesna.gd)
- **Lines 50-80**: WebSocket message handler
- **Lines 100-150**: Navigation system
- **Lines 200-250**: Region detection (Area3D)

## Key Data Structures

### State Vector (22 dimensions)
```
Position 0-10:  Current region (one-hot)
Position 11-21: Goal region (one-hot)

Example: outside(3) → meeting_room(5)
[0,0,0,1,0,0,0,0,0,0,0, 0,0,0,0,0,1,0,0,0,0,0]
       ↑                        ↑
    outside                meeting_room
```

### Valid Actions (neighbors only)
```
neighbor(outside, open_office).  → ActionId = [2]
neighbor(outside, corridor).     → ActionId = [1]
neighbor(outside, common).       → ActionId = [4]
```

### Region ID Mapping
```
0:  reception
1:  corridor
2:  open_office
3:  outside
4:  common
5:  meeting_room
6:  senior_office_1
7:  senior_office_2
8:  senior_office_3
9:  boss_office_1
10: boss_office_2
```

## Message Flow Summary

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│    Jason     │   HTTP  │    Python    │  WS     │    Godot     │
│  alice_rl    │ ──────> │  dqn_server  │ <────── │   vesna.gd   │
│              │ <────── │              │ ──────> │              │
└──────────────┘  JSON   └──────────────┘  JSON   └──────────────┘
      ↓                         ↓                        ↓
  Symbolic AI            Subsymbolic AI            Embodiment
  (reasoning)             (learning)               (physics)
```

## Timeline of One Step

1. **t=0ms**: Jason starts !rl_loop
2. **t=5ms**: Symbolic engine encodes state
3. **t=10ms**: Java sends HTTP POST
4. **t=15ms**: Python receives request
5. **t=20ms**: DQN training (if enough samples)
6. **t=25ms**: Epsilon-greedy selection
7. **t=30ms**: Python returns action
8. **t=35ms**: Java logs TRACE entry
9. **t=40ms**: Jason executes !hop_to
10. **t=45ms**: WebSocket to Godot
11. **t=50-500ms**: Physical movement in 3D
12. **t=505ms**: Region entered signal
13. **t=510ms**: Jason updates beliefs
14. **t=515ms**: Recursive !rl_loop call

## Reward Flow

```
Step 0: outside → open_office     reward = -1.0
Step 1: open_office → corridor    reward = -1.0
Step 2: corridor → meeting_room   reward = -1.0
Step 3: meeting_room == goal      reward = +100.0, done=true

Total Episode Reward: -3.0 + 100.0 = 97.0
```
