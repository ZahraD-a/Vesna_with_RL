# Deep Reinforcement Learning as a Service - VEsNA Architecture

## Author: Zahra Daoui
## Project: NOVAE VEsNA Learning

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Architecture](#2-system-architecture)
3. [Encoding and Decoding](#3-encoding-and-decoding)
4. [Action Masking (KB Constraints)](#4-action-masking-kb-constraints)
5. [The Complete Flow](#5-the-complete-flow)
6. [Code Reference](#6-code-reference)
7. [Key Design Decisions](#7-key-design-decisions)

---

## 1. Overview

This system implements **Deep Reinforcement Learning as a Service (DRLaaS)** where:

- A **BDI agent (Jason)** handles symbolic reasoning, domain knowledge, and reward computation
- An **external Python service** handles neural network learning (DQN)
- They communicate via **HTTP REST API**

```
┌─────────────────────────┐         HTTP          ┌─────────────────────────┐
│                         │◄──────────────────────►│                         │
│    JASON (Symbolic)     │                        │   PYTHON (Neural)       │
│                         │                        │                         │
│  - Domain knowledge     │                        │  - DQN network          │
│  - Reward computation   │                        │  - Experience replay    │
│  - Action validation    │                        │  - Policy learning      │
│  - State encoding       │                        │  - Action selection     │
│                         │                        │                         │
└─────────────────────────┘                        └─────────────────────────┘
           │
           ▼
┌─────────────────────────┐
│    GODOT (3D World)     │
│                         │
│  - Physical navigation  │
│  - Visual rendering     │
│  - Region detection     │
└─────────────────────────┘
```

---

## 2. System Architecture

### 2.1 The Two Layers

| Layer | Technology | Responsibility |
|-------|------------|----------------|
| **Symbolic** | Jason (AgentSpeak) | KB, rewards, valid actions, encoding/decoding |
| **Neural** | Python (PyTorch) | DQN learning, Q-value computation, action masking |

### 2.2 The Environment

The office environment has **11 regions**:

```
                    ┌──────────────┐
                    │   outside    │
                    │     (3)      │
                    └──────┬───────┘
                           │
┌──────────┐    ┌──────────┴───────────┐    ┌──────────────┐
│boss      │────│                      │────│ boss         │
│office_1  │    │     open_office      │    │ office_2     │
│  (9)     │    │        (2)           │    │   (10)       │
└──────────┘    └──────────┬───────────┘    └──────────────┘
                           │
┌──────────┐    ┌──────────┴───────────┐    ┌──────────────┐
│reception │────│                      │────│   common     │
│   (0)    │    │      corridor        │    │    (4)       │
└──────────┘    │        (1)           │    └──────────────┘
                │                      │
                └───┬───────┬──────┬───┘
                    │       │      │
              ┌─────┴──┐ ┌──┴───┐ ┌┴─────────────────────┐
              │meeting │ │senior│ │senior_office_2,3     │
              │room(5) │ │off_1 │ │    (7, 8)            │
              └────────┘ │ (6)  │ └──────────────────────┘
                         └──────┘
```

### 2.3 Knowledge Base (KB)

The KB stores **spatial adjacency** derived from RCC-8 relations:

```prolog
% symbolic_execution_engine.asl:49-77

% These facts define which rooms are connected (can walk between)
neighbor(reception, corridor).
neighbor(corridor, reception).
neighbor(corridor, open_office).
neighbor(open_office, corridor).
neighbor(corridor, common).
neighbor(corridor, meeting_room).
neighbor(corridor, senior_office_1).
neighbor(corridor, senior_office_2).
neighbor(corridor, senior_office_3).
neighbor(open_office, boss_office_1).
neighbor(open_office, boss_office_2).
neighbor(open_office, outside).
% ... (bidirectional)
```

**Origin**: These were derived from RCC-8 relations:
- `ec(X, Y)` (externally connected) → `neighbor(X, Y)`
- `po(X, Door) ∧ po(Door, Y)` (through door) → `neighbor(X, Y)`

---

## 3. Encoding and Decoding

### 3.1 Two Types of Encoding

The system uses **two different encodings**:

| Type | Purpose | Example | Dimension |
|------|---------|---------|-----------|
| **ID Encoding** | Action representation | `corridor → 1` | 1 integer |
| **One-Hot Encoding** | State representation | `corridor → [0,1,0,0,0,0,0,0,0,0,0]` | 11-dim vector |

### 3.2 ID Encoding (for Actions)

**Definition** (symbolic_execution_engine.asl:25-35):
```prolog
region_id(reception,       0).
region_id(corridor,        1).
region_id(open_office,     2).
region_id(outside,         3).
region_id(common,          4).
region_id(meeting_room,    5).
region_id(senior_office_1, 6).
region_id(senior_office_2, 7).
region_id(senior_office_3, 8).
region_id(boss_office_1,   9).
region_id(boss_office_2,  10).
```

**Encoding** (region name → ID):
```prolog
% Used in get_valid_action_ids
+!regions_to_ids([R | Rs], [Id | Ids])
    :   region_id(R, Id)           % lookup: corridor → 1
    <-  !regions_to_ids(Rs, Ids).
```

**Decoding** (ID → region name):
```prolog
% symbolic_execution_engine.asl:40
id_to_region(Id, Region) :- region_id(Region, Id).   % 1 → corridor
```

### 3.3 One-Hot Encoding (for States)

**What is One-Hot?**
A vector where only one position is 1, rest are 0.

```
Region        ID    One-Hot Vector (11 dimensions)
─────────────────────────────────────────────────────
reception      0    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
corridor       1    [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
open_office    2    [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0]
outside        3    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]
common         4    [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]
meeting_room   5    [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]
...
```

**Implementation** (symbolic_execution_engine.asl:84-105):
```prolog
+!build_one_hot(TargetId, N, I, Acc, StateVector)
    :   I < N
    <-  if (I == TargetId) {
            NewAcc = [1 | Acc];    % This position = 1
        } else {
            NewAcc = [0 | Acc];    % Other positions = 0
        }
        !build_one_hot(TargetId, N, I + 1, NewAcc, StateVector).
```

### 3.4 Goal-Conditioned State Vector

The state sent to the neural network is **22-dimensional**:

```
State = [current_region_one_hot | goal_region_one_hot]
        ├────── 11 dims ────────┤├───── 11 dims ──────┤
```

**Example**: Agent at corridor, goal is meeting_room:
```
current = corridor    → [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
goal = meeting_room   → [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]

State = [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]
        ├────────── current ──────────┤├────────── goal ──────────────┤
```

**Implementation** (symbolic_execution_engine.asl:89-93):
```prolog
+!build_goal_state_vector(CurrentRegion, GoalRegion, StateVector)
    :   region_id(CurrentRegion, CurrentId)
      & region_id(GoalRegion, GoalId)
      & num_regions(N)
    <-  !build_one_hot(CurrentId, N, 0, [], CurrentVec);
        !build_one_hot(GoalId, N, 0, [], GoalVec);
        .concat(CurrentVec, GoalVec, StateVector).   % Concatenate
```

**Why Goal-Conditioned?**
One trained policy works for ANY goal. Without this, you'd need 11 separate policies.

---

## 4. Action Masking (KB Constraints)

### 4.1 The Problem

The neural network outputs Q-values for **all 11 actions**, but some are physically impossible (can't teleport to non-adjacent rooms).

### 4.2 The Solution: Two-Step Process

```
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 1: JASON computes valid actions from KB                            │
│                                                                         │
│   Agent location: corridor                                              │
│                                                                         │
│   KB Query: neighbor(corridor, X)?                                      │
│   Results:  [reception, open_office, common, meeting_room,              │
│              senior_office_1, senior_office_2, senior_office_3]         │
│                                                                         │
│   Encode to IDs: valid_actions = [0, 2, 4, 5, 6, 7, 8]                 │
│                                                                         │
│   Send to Python via HTTP                                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 2: PYTHON applies mask to Q-values                                 │
│                                                                         │
│   Neural network computes Q-values for ALL 11 actions:                  │
│                                                                         │
│   Action:   [0]   [1]   [2]   [3]   [4]   [5]   [6]   [7]   [8]  [9] [10]│
│   Q-value:  0.3   0.8   0.9   0.1   0.5   0.7   0.4   0.3   0.2  0.95 0.85│
│                   ^^^         ^^^                                ^^^^  ^^^│
│                   corridor    outside                         boss offices│
│                   NOT in      NOT in                          NOT in      │
│                   valid_acts  valid_acts                      valid_acts  │
│                                                                         │
│   Build mask (valid=0, invalid=-∞):                                     │
│   Mask:     [0]  [-∞]  [0]  [-∞]  [0]   [0]   [0]   [0]   [0] [-∞] [-∞] │
│                                                                         │
│   Q + Mask: 0.3   -∞   0.9   -∞   0.5   0.7   0.4   0.3   0.2  -∞   -∞  │
│                        ^^^                                              │
│                        HIGHEST among valid!                             │
│                                                                         │
│   argmax → action 2 (open_office)                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Code Implementation

**JASON - Compute valid actions** (symbolic_execution_engine.asl:112-119):
```prolog
+!get_valid_action_ids(Region, ActionIds)
    <-  .findall(N, neighbor(Region, N), Neighbors);  % Query KB
        !regions_to_ids(Neighbors, ActionIds).         % Convert to IDs

+!regions_to_ids([R | Rs], [Id | Ids])
    :   region_id(R, Id)
    <-  !regions_to_ids(Rs, Ids).
```

**PYTHON - Apply mask** (dqn_agent.py:120-123):
```python
def _masked_argmax(self, q_values, valid_actions):
    # Initialize all actions as impossible (-infinity)
    mask = torch.full((self.action_size,), float("-inf"))

    # Valid actions get no penalty (0)
    mask[valid_actions] = 0.0

    # Add mask to Q-values and select maximum
    return int((q_values + mask).argmax().item())
```

### 4.4 Why Mask in Python, Not Jason?

| Approach | Description | Problem |
|----------|-------------|---------|
| Mask in Jason only | Send only 1 action to RL | RL can't learn (no choice) |
| **Mask in Python** | Send valid list, RL chooses best | RL learns optimal among valid |

The RL needs **options** to learn which is best. Jason provides options, Python chooses.

---

## 5. The Complete Flow

### 5.1 One RL Step (Detailed)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           JASON (Symbolic Layer)                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. Get current state                                                    │
│     ?current_region(corridor).                                           │
│     ?goal_region(meeting_room).                                          │
│                                                                          │
│  2. Build goal-conditioned state vector (22-dim)                         │
│     !build_goal_state_vector(corridor, meeting_room, StateVector).       │
│     StateVector = [0,1,0,0,0,0,0,0,0,0,0, 0,0,0,0,0,1,0,0,0,0,0]        │
│                   ├─── current ────────┤├───── goal ─────────┤          │
│                                                                          │
│  3. Compute valid actions from KB                                        │
│     !get_valid_action_ids(corridor, ValidActionIds).                     │
│     ValidActionIds = [0, 2, 4, 5, 6, 7, 8]                              │
│                                                                          │
│  4. Compute reward (Reward Machine)                                      │
│     - Goal reached? → reward = +100, done = true                         │
│     - Timeout?      → reward = -10,  done = true                         │
│     - Normal step?  → reward = -1,   done = false                        │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │  HTTP POST /select_action
                                    │  {
                                    │    "state": [0,1,0,...,0,0,0,0,0,1,0,...],
                                    │    "valid_actions": [0, 2, 4, 5, 6, 7, 8],
                                    │    "reward": -1.0,
                                    │    "done": false
                                    │  }
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           PYTHON (Neural Layer)                           │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  5. Store previous transition in replay buffer                           │
│     memory.push(prev_state, prev_action, reward, state, valid_actions)   │
│                                                                          │
│  6. Train DQN (if enough samples)                                        │
│     - Sample batch from replay buffer                                    │
│     - Compute target: y = r + γ * max Q(s', a')  [masked]               │
│     - Update network: minimize Huber(Q(s,a) - y)                         │
│                                                                          │
│  7. Select action (ε-greedy with masking)                               │
│                                                                          │
│     if random() < ε:                                                    │
│         action = random.choice(valid_actions)  # Explore                 │
│     else:                                                                │
│         q_values = network(state)              # [0.3, 0.8, 0.9, ...]   │
│         action = masked_argmax(q_values, valid_actions)  # Exploit       │
│                                                                          │
│     Selected: action = 2 (open_office)                                   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │  HTTP Response
                                    │  {
                                    │    "action_id": 2,
                                    │    "explanation": {
                                    │      "q_values": {"0": 0.3, "2": 0.9, ...},
                                    │      "selected_q": 0.9,
                                    │      "exploration": "greedy"
                                    │    }
                                    │  }
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           JASON (Symbolic Layer)                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  8. Decode action ID to region name                                      │
│     ?id_to_region(2, TargetRegion).                                      │
│     TargetRegion = open_office                                           │
│                                                                          │
│  9. Execute physical movement                                            │
│     !hop_to(open_office).                                                │
│     vesna.walk(open_office).                                             │
│                                                                          │
│ 10. Update beliefs                                                       │
│     -current_region(_).                                                  │
│     +current_region(open_office).                                        │
│                                                                          │
│ 11. Continue to next step                                                │
│     !rl_loop.                                                            │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Episode Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EPISODE LIFECYCLE                                │
└─────────────────────────────────────────────────────────────────────────┘

  START EPISODE
       │
       ▼
  ┌─────────────────┐
  │ Reset position  │  vesna.teleport(X, Y, Z)
  │ to start        │  current_region(reception)
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐     ┌─────────────────────────────────────────────┐
  │ RL Loop Step    │────►│ 1. Encode state (22-dim one-hot)            │
  │                 │     │ 2. Get valid actions from KB                │
  │                 │     │ 3. Send to Python, get action               │
  │                 │     │ 4. Decode action, execute movement          │
  │                 │     │ 5. Compute reward                           │
  └────────┬────────┘     └─────────────────────────────────────────────┘
           │
           ▼
  ┌─────────────────┐
  │ Goal reached?   │───YES───► reward = +100, done = true ──► END EPISODE
  └────────┬────────┘
           │NO
           ▼
  ┌─────────────────┐
  │ Timeout?        │───YES───► reward = -10, done = true ──► END EPISODE
  │ (step >= 50)    │
  └────────┬────────┘
           │NO
           ▼
       reward = -1
       done = false
           │
           └──────► Back to RL Loop Step
```

---

## 6. Code Reference

### 6.1 File Structure

```
Vesna_RL/
├── mind/
│   ├── python/
│   │   ├── dqn_server.py      # Flask REST API
│   │   └── dqn_agent.py       # DQN network + replay buffer
│   │
│   └── src/agt/
│       ├── symbolic_execution_engine.asl   # Encoding, KB, valid actions
│       └── alice_rl.asl                    # Reward machine, episode loop
```

### 6.2 Key Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `region_id/2` | symbolic_execution_engine.asl:25-35 | ID encoding table |
| `id_to_region/2` | symbolic_execution_engine.asl:40 | ID decoding |
| `neighbor/2` | symbolic_execution_engine.asl:49-77 | KB adjacency facts |
| `build_goal_state_vector/3` | symbolic_execution_engine.asl:89-93 | One-hot state encoding |
| `get_valid_action_ids/2` | symbolic_execution_engine.asl:112-114 | Query KB for valid actions |
| `rl_select_action/5` | symbolic_execution_engine.asl:127-135 | Main RL call wrapper |
| `rl_loop/0` | alice_rl.asl:66-116 | Reward machine + episode loop |
| `_masked_argmax()` | dqn_agent.py:120-123 | Apply mask to Q-values |
| `step_with_explanation()` | dqn_agent.py:154-220 | Action selection + training |
| `/select_action` | dqn_server.py:75-150 | HTTP endpoint |

---

## 7. Key Design Decisions

### 7.1 Why Separate Symbolic and Neural?

| Aspect | Symbolic (Jason) | Neural (Python) |
|--------|------------------|-----------------|
| **Knows domain** | YES (rooms, adjacency) | NO (just numbers) |
| **Computes rewards** | YES (goal logic) | NO |
| **Ensures safety** | YES (valid actions) | Uses mask |
| **Learns policy** | NO | YES (DQN) |

**Benefit**: The neural network is domain-agnostic. It could learn ANY navigation task, not just this office.

### 7.2 Why Goal-Conditioned State?

Without goal in state:
- Need separate policy for each goal
- 11 goals × 1 policy each = 11 policies

With goal in state:
- State = [current | goal]
- ONE policy works for ALL goals
- **Generalization!**

### 7.3 Why Action Masking?

Without masking:
- Agent might try to go from `reception` to `boss_office_1` directly
- Physically impossible
- Wastes learning time on invalid actions

With masking:
- Agent ONLY considers valid neighbors
- Learns faster (smaller action space)
- **Guaranteed safe exploration**

### 7.4 Why Reward Machine in Symbolic Layer?

The reward logic is **symbolic knowledge**:
- "Goal reached" is a logical condition: `current_region(X) ∧ goal_region(X)`
- "Timeout" is a step count: `step(S) ∧ S >= 50`

Keeping rewards in Jason means:
- Rewards are **explainable** (not black-box)
- Easy to modify reward structure
- Python RL service stays **domain-agnostic**

---

## Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    NEURO-SYMBOLIC RL ARCHITECTURE                        │
│                                                                         │
│   SYMBOLIC (Jason)                    NEURAL (Python)                   │
│   ════════════════                    ═══════════════                   │
│                                                                         │
│   ┌─────────────────┐                ┌─────────────────┐               │
│   │ KB Constraints  │                │ DQN Network     │               │
│   │ neighbor(X,Y)   │───valid_acts──►│ 22→64→64→11    │               │
│   └─────────────────┘                └────────┬────────┘               │
│                                               │                         │
│   ┌─────────────────┐                         │ Q-values                │
│   │ Reward Machine  │                         ▼                         │
│   │ +100/-10/-1     │                ┌─────────────────┐               │
│   └─────────────────┘                │ Action Masking  │               │
│                                      │ invalid = -∞    │               │
│   ┌─────────────────┐                └────────┬────────┘               │
│   │ State Encoder   │                         │                         │
│   │ [curr|goal]     │                         │ best valid action       │
│   │ 22-dim one-hot  │                         ▼                         │
│   └─────────────────┘                ┌─────────────────┐               │
│                                      │ Experience      │               │
│   ┌─────────────────┐                │ Replay Buffer   │               │
│   │ Action Decoder  │◄───action_id───└─────────────────┘               │
│   │ 2 → open_office │                                                   │
│   └─────────────────┘                                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**The key insight**: Symbolic knowledge (KB, rewards) constrains and guides neural learning, while the neural network handles the complexity of finding optimal policies within those constraints.
