# DAY_1 Plan: RL as a Service - Find Coffee Scenario

**Date:** 2026-01-16
**Branch:** `rl-as-service`
**Approach:** Case A - Map Given to Symbolic Engine

---

## 1. Mathematical Formulation

### Standard MDP (What Supervisor Wants)

At each step $t$:

$$a_t \sim \pi(\cdot | s_t), \quad s_{t+1} \sim P(\cdot | s_t, a_t), \quad r_{t+1} = R(s_t, a_t, s_{t+1})$$

**Crucially:** $R$ is computed on Jason/VEsNA side (reward machine), NOT in the RL service.

The RL service only learns $Q$ or $\pi$, not reward or goal logic.

### Case A: Map Given

The topology $G = (S, E)$ at the region level is **fixed and known to the symbolic engine**. The agent's job is only to learn the policy $\pi$.

- You already have edges $E$ from RCC rules in `office_map.asl`
- At runtime, Jason computes valid moves:

$$A(s) = \{a : \text{target region is a neighbor in } E\}$$

- RL learns:

$$\pi^*(a | o) \quad \text{or} \quad Q^*(o, a)$$

by trial and error, but it is **not learning the graph**.

> **Simple analogy:** You have the building map on the wall. You are learning "what route choices are best," not drawing the building.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  JASON/VEsNA (Symbolic Execution Engine)                    │
│                                                             │
│  KNOWS:                                                     │
│  • RCC map (office_map.asl)                                 │
│  • Topology G = (Regions, Edges)                            │
│  • Valid moves A(s) = {neighbors in E}                      │
│                                                             │
│  COMPUTES at each step:                                     │
│  • State s_t from beliefs                                   │
│  • Valid actions A(s_t) from RCC adjacency                  │
│  • Reward r_{t+1} = R(s_t, a_t, s_{t+1})                    │
│                                                             │
│  EXECUTES: exactly ONE room hop per action                  │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ POST {s_t, A(s_t), r_t, done}
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  RL SERVICE (Learner)                                       │
│                                                             │
│  KNOWS: nothing about the map                               │
│                                                             │
│  RECEIVES: (state, valid_actions, reward, done)             │
│                                                             │
│  LEARNS: Q*(o, a) via DQN                                   │
│                                                             │
│  RETURNS: action a_t ∈ A(s_t)                               │
│                                                             │
│  MUST NOT CONTAIN:                                          │
│  ✗ Reward logic                                             │
│  ✗ Goal detection                                           │
│  ✗ Distance computation                                     │
│  ✗ Any domain/map knowledge                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. The Exact Loop (Mathematically Precise)

Let $m_t \in \{0, 1\}^{|A|}$ be an action mask where $m_t[a] = 1$ iff $a \in A(s_t)$.

At time $t$:

1. **Jason** computes $s_t$ from beliefs and computes mask $m_t$ from RCC adjacency

2. **RL service** returns action:
$$a_t = \arg\max_a \left( Q_\theta(s_t, a) + (1 - m_t[a]) \cdot (-M) \right)$$
   with $M$ a large number (masking invalid actions)

3. **Jason** executes exactly one hop consistent with $a_t$, producing $s_{t+1}$

4. **Jason** computes reward:
$$r_{t+1} = R(s_t, a_t, s_{t+1})$$

5. **RL** trains on $(s_t, a_t, r_{t+1}, s_{t+1}, m_{t+1}, \text{done})$ using masked DQN target:
$$y_t = r_{t+1} + \gamma \max_{a' \in A(s_{t+1})} Q_{\theta^-}(s_{t+1}, a')$$

This is a proper MDP step, not a temporally extended option.

---

## 4. Why NOT `go_to(X)` with Full Pathfinding

If Jason plan does:
- compute a full path
- execute `follow_path(path)` until arrival

Then your "action" is a **temporally extended action** (an option). The Bellman equation becomes:

$$Q(s, o) = \mathbb{E}\left[ \sum_{k=1}^{\tau(o)} \gamma^{k-1} r_{t+k} + \gamma^{\tau(o)} \max_{o'} Q(s_{t+\tau(o)}, o') \right]$$

where $o$ is the option "go_to(common)" and $\tau(o)$ is how many internal steps until termination.

**Why this breaks DAY_1:** If "go_to(common)" can succeed from anywhere because the symbolic engine finds a path, then the optimal policy is trivial: choose the option that ends at the goal.

You are not learning navigation, you are learning option selection.

**Fix:** One RL action = one room hop.

---

## 5. RCC Adjacency (Door-Collapsed)

From `office_map.asl`, derive edges $E$:

```
ec(X, Y)                    →  edge(X, Y)
po(X, Door) ∧ po(Door, Y)   →  edge(X, Y)
```

### Adjacency Table

| Region | Neighbors (valid actions) |
|--------|---------------------------|
| `reception` | corridor |
| `corridor` | reception, open_office, common, meeting_room, senior_office_1, senior_office_2, senior_office_3 |
| `open_office` | corridor, boss_office_1, boss_office_2, outside |
| `common` | corridor |
| `meeting_room` | corridor |
| `senior_office_1` | corridor |
| `senior_office_2` | corridor |
| `senior_office_3` | corridor |
| `boss_office_1` | open_office |
| `boss_office_2` | open_office |
| `outside` | open_office |

---

## 6. State Space

**States $S$:** regions only

$$s_t \in \{\text{reception}, \text{corridor}, \text{open\_office}, \ldots\}$$

**Encoding:** One-hot vector of length 11 (number of regions)

```python
state = [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]  # senior_office_2
#        rec cor ope out com mee sr1 sr2 sr3 bo1 bo2
```

**Note:** One-hot is sufficient because this is a room-level MDP. The process is Markov: next room depends only on (current_room, action).

---

## 7. Action Space

**Actions $A$:** 11 region targets (keep fixed size for DQN)

| ID | Target Region |
|----|---------------|
| 0 | reception |
| 1 | corridor |
| 2 | open_office |
| 3 | outside |
| 4 | common |
| 5 | meeting_room |
| 6 | senior_office_1 |
| 7 | senior_office_2 |
| 8 | senior_office_3 |
| 9 | boss_office_1 |
| 10 | boss_office_2 |

**Valid action set $A(s)$:** Only neighbors of current region (from adjacency table).

**Implementation:** Mask invalid actions to $-\infty$ before argmax.

---

## 8. Reward Function (Computed in Jason)

$$r_{t+1} = R(s_t, a_t, s_{t+1})$$

| Condition | Reward | Rationale |
|-----------|--------|-----------|
| $s_{t+1} = \text{common}$ (goal) | +100 | Goal achieved |
| Otherwise | -1 | Step penalty |

**Terminal:** Episode ends when agent reaches `common` or after 50 steps.

---

## 9. DQN Hyperparameters

```python
config = {
    "learning_rate": 0.001,
    "gamma": 0.99,
    "epsilon_start": 1.0,
    "epsilon_end": 0.01,
    "epsilon_decay": 0.995,
    "batch_size": 32,
    "buffer_size": 10000,
    "target_update": 10,
    "hidden_size": 64,
}
```

---

## 10. API Design

### POST /select_action

**Request:**
```json
{
  "agent_id": "alice",
  "state": [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
  "valid_actions": [1],
  "reward": -1.0,
  "done": false
}
```

**Response:**
```json
{
  "action_id": 1
}
```

### GET /health

**Response:**
```json
{
  "status": "ok",
  "episode": 42,
  "epsilon": 0.15
}
```

---

## 11. Folder Structure

```
/home/hamid/Desktop/Projects/Vesna_RL/
├── mind/
│   ├── python/                        # RL Service
│   │   ├── dqn_server.py              # Flask API
│   │   ├── dqn_agent.py               # DQN + replay buffer
│   │   ├── requirements.txt
│   │   └── .venv/
│   ├── src/agt/
│   │   ├── vesna.asl                  # Existing RCC rules
│   │   ├── alice_rl.asl               # RL-enabled agent (NEW)
│   │   └── rl/
│   │       └── select_action.java     # HTTP client (NEW)
│   └── playgrounds/office/
│       └── office_map.asl             # RCC topology
├── start_all.sh                       # Godot → Python → Jason
└── stop_all.sh
```

---

## 12. Start Order

```bash
# 1. Godot (environment)
./Godot_v4.5.1-stable_linux.x86_64 --path env/office

# 2. Python RL Service (wait for health)
cd mind/python && source .venv/bin/activate && python dqn_server.py

# 3. Jason (connects to both)
cd mind && ./gradlew run
```

---

## 13. Acceptance Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| 1 | Reward computed in Jason, NOT Python | Inspect code |
| 2 | Python receives (state, valid_actions, reward), returns action_id | Inspect API |
| 3 | One RL step = one room hop | Log shows single transitions |
| 4 | Coffee plan removed from agent | alice_rl.asl has no coffee plan |
| 5 | Agent learns to reach coffee | Steps decrease over episodes |
| 6 | Valid actions from RCC | Jason computes A(s) from adjacency |

---

## 14. Expected Learning

**Optimal path:** senior_office_2 → corridor → common (2 steps)

**Learning curve:**
- Episodes 1-20: Random exploration (~5-15 steps)
- Episodes 50-100: Converging (~2-5 steps)
- Episodes 100+: Optimal (~2 steps)

---

## 15. Files to Create

| Priority | File | Description |
|----------|------|-------------|
| 1 | `mind/python/dqn_agent.py` | DQN model + masked training |
| 1 | `mind/python/dqn_server.py` | Flask REST API |
| 1 | `mind/python/requirements.txt` | Dependencies |
| 2 | `mind/src/agt/rl/select_action.java` | HTTP client |
| 2 | `mind/src/agt/alice_rl.asl` | RL agent (no coffee plan) |
| 3 | `start_all.sh` | Launch script |

---

## 16. Summary

> **What RL learns:** "What route choices are best" (policy)
>
> **What RL does NOT learn:** The map/topology (already in Jason via RCC)
>
> **Key constraint:** One RL step = one room hop (not full pathfinding)
