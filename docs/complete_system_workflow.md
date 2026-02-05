# Complete System Workflow - All Branches Explained

## 🌳 Three Training Approaches

### Branch Comparison

| Branch | Environment | Speed | Use Case |
|--------|-------------|-------|----------|
| `pure_python_training` | Graph simulation | 40s for 5000 episodes | Fast pre-training |
| `visual_python_training` | Godot 3D | Hours (real-time) | Visual validation |
| `rl-as-service-zahra` | Godot 3D | Real-time | Production inference |

---

## 📊 Branch 1: `pure_python_training` - Fast Graph Training

**Goal**: Train DQN quickly without physics simulation

### Workflow

```
START
  │
  ├─→ [1] Load office_graph_env.py
  │      │
  │      ├─ REGION_IDS: {reception:0, corridor:1, open_office:2, ...}
  │      └─ ADJACENCY: {0:[1], 1:[0,2,4,5,6,7,8], 2:[1,3,9,10], ...}
  │
  ├─→ [2] Initialize DQNAgent
  │      │
  │      ├─ policy_net: Input(22) → Hidden(64) → Hidden(64) → Output(11)
  │      ├─ target_net: Copy of policy_net (updated every 10 episodes)
  │      ├─ ReplayBuffer: Store last 10,000 transitions
  │      └─ Hyperparameters: epsilon=1.0, gamma=0.99, lr=0.001
  │
  └─→ [3] Training Loop (5000 episodes)
      │
      ┌──────────────────────────────────────────────────┐
      │  FOR episode = 1 to 5000                         │
      │                                                   │
      │  ┌─→ [3.1] env.reset()                           │
      │  │    │                                           │
      │  │    ├─ Random start: e.g., open_office (id=2)  │
      │  │    ├─ Random goal: e.g., meeting_room (id=5)  │
      │  │    └─ Return state: [0,0,1,0,0,0,0,0,0,0,0,   │
      │  │                       0,0,0,0,0,1,0,0,0,0,0]   │
      │  │         current ↑           goal ↑             │
      │  │                                                │
      │  ├─→ [3.2] agent.reset_episode()                 │
      │  │    └─ Clear prev_state, prev_action           │
      │  │                                                │
      │  └─→ [3.3] Episode Loop (until done)             │
      │       │                                           │
      │       ┌───────────────────────────────────────┐   │
      │       │  WHILE not done:                      │   │
      │       │                                       │   │
      │       │  [A] agent.step(state, valid, r, d)  │   │
      │       │      │                                │   │
      │       │      ├─ Store transition if prev exists│  │
      │       │      │  Transition(o=prev_state,      │   │
      │       │      │            a=prev_action,      │   │
      │       │      │            r=reward,           │   │
      │       │      │            o2=state,           │   │
      │       │      │            valid=valid_actions,│   │
      │       │      │            done=done)          │   │
      │       │      │                                │   │
      │       │      ├─ Train if buffer >= 32        │   │
      │       │      │  │                             │   │
      │       │      │  └─→ Sample 32 transitions    │   │
      │       │      │      Compute Q(s,a)           │   │
      │       │      │      Compute target:          │   │
      │       │      │        r + γ*max Q'(s',a')    │   │
      │       │      │      Loss = Huber(Q, target)  │   │
      │       │      │      Backprop & update weights│   │
      │       │      │                                │   │
      │       │      ├─ Select action:               │   │
      │       │      │  IF random() < epsilon:       │   │
      │       │      │    action = random(valid)     │   │
      │       │      │  ELSE:                        │   │
      │       │      │    Q = policy_net(state)      │   │
      │       │      │    Mask invalid: Q[invalid]=-∞│   │
      │       │      │    action = argmax(Q)         │   │
      │       │      │                                │   │
      │       │      └─ Return action                │   │
      │       │                                       │   │
      │       │  [B] env.step(action)                │   │
      │       │      │                                │   │
      │       │      ├─ Move: current = action       │   │
      │       │      ├─ Check goal:                  │   │
      │       │      │  IF current == goal:          │   │
      │       │      │    reward = +100, done = True │   │
      │       │      │  ELIF steps >= 50:            │   │
      │       │      │    reward = -10, done = True  │   │
      │       │      │  ELSE:                        │   │
      │       │      │    reward = -1, done = False  │   │
      │       │      │                                │   │
      │       │      └─ Return (state, r, done, valid)│  │
      │       │                                       │   │
      │       └───────────────────────────────────────┘   │
      │                                                   │
      │  [3.4] Episode Done                               │
      │   │                                                │
      │   ├─ Decay epsilon: ε = max(0.01, ε * 0.995)     │
      │   ├─ Every 10 eps: target_net ← policy_net       │
      │   └─ Log: Episode X | Success Y% | Avg steps Z   │
      │                                                   │
      └───────────────────────────────────────────────────┘
      │
      └─→ [4] Save Model
           └─ torch.save(policy_net, "checkpoints/alice.pt")

END (99.2% success, 2.1 avg steps)
```

---

## 🎮 Branch 2: `visual_python_training` - Godot 3D Training

**Goal**: Train in actual 3D environment with physics

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GODOT 3D ENVIRONMENT                      │
│  ┌────────────────────────────────────────────────────┐     │
│  │  office.tscn (3D Scene)                            │     │
│  │  ├─ NavigationRegion3D (pathfinding mesh)         │     │
│  │  ├─ Area3D nodes: reception, corridor, etc.       │     │
│  │  └─ actor.gd (Alice character controller)         │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────┬──────────────────────────────────────┬────────┘
              │ WebSocket                             │ WebSocket
              │ (navigation commands)                 │ (perceptions)
              ▼                                       ▼
┌─────────────────────────────┐      ┌─────────────────────────┐
│     JASON BDI AGENT         │◄────►│   PYTHON RL SERVICE     │
│  ┌──────────────────────┐   │ HTTP │  ┌──────────────────┐   │
│  │ alice_rl.asl         │   │      │  │ dqn_server.py    │   │
│  │ ├─ Episode loop      │   │      │  │ ├─ Flask app     │   │
│  │ ├─ Reward calc       │   │      │  │ ├─ DQNAgent      │   │
│  │ └─ rl_select_action  │───┼──────┼─→│ └─ /select_action│   │
│  │                      │   │      │  │                  │   │
│  │ symbolic_execution_  │   │      │  └──────────────────┘   │
│  │ engine.asl           │   │      │                         │
│  │ ├─ region_id/2       │   │      │  Training happens here  │
│  │ ├─ neighbor/2        │   │      │  with real 3D episodes  │
│  │ └─ build_state       │   │      │                         │
│  └──────────────────────┘   │      └─────────────────────────┘
└─────────────────────────────┘
```

### Workflow

```
START
  │
  ├─→ [1] bash start_all.sh
  │      │
  │      ├─ Start Godot (3D environment loads)
  │      │   └─ office.tscn with 11 Area3D regions
  │      │
  │      ├─ Start Python RL Service
  │      │   ├─ Load DQNAgent (state=22, action=11)
  │      │   └─ Flask server on localhost:5000
  │      │
  │      └─ Start Jason (JaCaMo)
  │          └─ Run alice_rl.asl
  │
  └─→ [2] Alice Agent Starts (!start goal)
      │
      ├─→ [2.1] Load model
      │    └─ rl.load_model(eval_mode=true/false)
      │        └─ HTTP POST /load_model → dqn_agent.load()
      │
      ├─→ [2.2] Teleport to start position
      │    ├─ vesna.teleport(100, 4.0, -3.0)
      │    └─ WebSocket → Godot → actor.gd.teleport()
      │
      └─→ [3] Episode Loop (!run_episode)
          │
          ┌──────────────────────────────────────────────────┐
          │  EPISODE N                                       │
          │                                                  │
          │  [3.1] Reset position                           │
          │   └─ Teleport back to start (100, 4, -3)        │
          │                                                  │
          │  [3.2] RL Loop (!rl_loop)                       │
          │   │                                              │
          │   ┌────────────────────────────────────────┐     │
          │   │  WHILE current != goal AND step < 50   │     │
          │   │                                        │     │
          │   │  [A] Get current perception            │     │
          │   │      ?current_region(Region)           │     │
          │   │      (Set by +region_entered trigger)  │     │
          │   │                                        │     │
          │   │  [B] Build state & get valid actions   │     │
          │   │      !rl_select_action(current, goal,  │     │
          │   │                       reward, done, →) │     │
          │   │      │                                 │     │
          │   │      ├─→ symbolic_execution_engine.asl │     │
          │   │      │   │                             │     │
          │   │      │   ├─ !build_goal_state_vector   │     │
          │   │      │   │  state = [                  │     │
          │   │      │   │    one_hot(current_id),     │     │
          │   │      │   │    one_hot(goal_id)         │     │
          │   │      │   │  ]                          │     │
          │   │      │   │                             │     │
          │   │      │   └─ !get_valid_action_ids     │     │
          │   │      │      valid = neighbor_ids       │     │
          │   │      │                                 │     │
          │   │      └─→ select_action.java            │     │
          │   │          │                             │     │
          │   │          ├─ Build JSON request         │     │
          │   │          │  {                          │     │
          │   │          │    "state": [22 values],    │     │
          │   │          │    "valid_actions": [ids],  │     │
          │   │          │    "reward": -1.0,          │     │
          │   │          │    "done": false,           │     │
          │   │          │    "mode": "training"       │     │
          │   │          │  }                          │     │
          │   │          │                             │     │
          │   │          └─→ HTTP POST /select_action  │     │
          │   │              │                         │     │
          │   │              └─→ dqn_server.py         │     │
          │   │                  │                     │     │
          │   │                  ├─ agent.step()       │     │
          │   │                  │  └─ Same as pure   │     │
          │   │                  │     branch logic    │     │
          │   │                  │                     │     │
          │   │                  └─ Return JSON        │     │
          │   │                     {                  │     │
          │   │                       "action": 1,     │     │
          │   │                       "explanation": { │     │
          │   │                         "q_values": [], │     │
          │   │                         "mode": "..."  │     │
          │   │                       }                │     │
          │   │                     }                  │     │
          │   │                                        │     │
          │   │  [C] Execute navigation                │     │
          │   │      !hop_to(TargetRegion)             │     │
          │   │      │                                 │     │
          │   │      ├─→ Check if door needed          │     │
          │   │      │   (office_map.asl RCC-8)        │     │
          │   │      │                                 │     │
          │   │      └─→ vesna.moveto(region)          │     │
          │   │          │                             │     │
          │   │          └─→ WebSocket → Godot         │     │
          │   │              │                         │     │
          │   │              └─→ actor.gd              │     │
          │   │                  ├─ NavigationAgent3D  │     │
          │   │                  ├─ Physics movement   │     │
          │   │                  └─ Area3D detection   │     │
          │   │                      │                 │     │
          │   │                      └─→ region_entered│     │
          │   │                          signal        │     │
          │   │                          │             │     │
          │   │                          └─→ WebSocket │     │
          │   │                              → Jason   │     │
          │   │                                        │     │
          │   │  [D] Update beliefs                    │     │
          │   │      +region_entered(corridor, _)      │     │
          │   │       ├─ -current_region(_)            │     │
          │   │       ├─ +current_region(corridor)     │     │
          │   │       ├─ -ntpp(alice, _)               │     │
          │   │       └─ +ntpp(alice, corridor)        │     │
          │   │                                        │     │
          │   │  [E] Update step & reward              │     │
          │   │      -step(S)                          │     │
          │   │      +step(S+1)                        │     │
          │   │      episode_reward = ER - 1           │     │
          │   │                                        │     │
          │   └────────────────────────────────────────┘     │
          │                                                  │
          │  [3.3] Episode Termination                      │
          │   │                                              │
          │   ├─ IF current == goal:                        │
          │   │   ├─ reward = +100                          │
          │   │   └─ !rl_select_action(..., done=true)      │
          │   │       (DQN learns goal transition)          │
          │   │                                              │
          │   └─ IF steps >= 50:                            │
          │       ├─ reward = -10                           │
          │       └─ !rl_select_action(..., done=true)      │
          │           (DQN learns timeout penalty)          │
          │                                                  │
          │  [3.4] Next Episode                             │
          │   └─ .wait(1000) then !run_episode              │
          │                                                  │
          └──────────────────────────────────────────────────┘

LOOP FOREVER (or until stopped)
```

---

## 🚀 Branch 3: `rl-as-service-zahra` - Production Inference

**Goal**: Use trained model for intelligent navigation

### Workflow (Same as visual_python_training but with eval_mode=true)

```
Key Differences:
  ├─ eval_mode(true) in alice_rl.asl
  │   └─ Python DQN in inference-only mode
  │       ├─ Loads trained alice.pt checkpoint
  │       ├─ No weight updates (no training)
  │       ├─ Epsilon = 0.01 (99% exploitation)
  │       └─ No experience replay storage
  │
  └─ Agent uses learned policy
      ├─ Episode 1: ~2 steps (optimal path)
      ├─ Episode 10: ~2 steps (consistent)
      └─ Success rate: 99%+
```

---

## 🔑 Key Components Explained

### 1. State Representation (22-dimensional)

```python
# Current region: open_office (id=2)
# Goal region: meeting_room (id=5)

current_one_hot = [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0]
                      ↑ position 2

goal_one_hot = [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]
                         ↑ position 5

state = current_one_hot + goal_one_hot
      = [0,0,1,0,0,0,0,0,0,0,0, 0,0,0,0,0,1,0,0,0,0,0]
```

### 2. Action Masking

```python
# At open_office (id=2), valid neighbors: [1, 3, 9, 10]
# Q-values from network: [35, 98, 40, 25, 30, 45, 20, 15, 10, 50, 55]

# Apply mask:
masked = [-∞, 98, -∞, 25, -∞, -∞, -∞, -∞, -∞, 50, 55]
         invalid ↑    valid ↑   ↑ all invalid    ↑  valid

# argmax selects: action = 1 (corridor) with Q=98
```

### 3. Reward Function

```python
def compute_reward(current, goal, steps, max_steps):
    if current == goal:
        return +100.0  # Success!
    elif steps >= max_steps:
        return -10.0   # Timeout penalty
    else:
        return -1.0    # Step penalty (encourages shorter paths)
```

### 4. Training vs Inference

| Mode | Epsilon | Training | Buffer | Speed |
|------|---------|----------|--------|-------|
| Training | 1.0 → 0.01 | ✅ Weights update | ✅ Store transitions | Slow |
| Inference | 0.01 (fixed) | ❌ Frozen weights | ❌ No storage | Fast |

---

## 📈 Learning Progress

### Episode Timeline (pure_python_training)

```
Episode    1: 90% success, 14.5 avg steps, ε=1.0    (random exploration)
Episode  100: 90% success, 14.5 avg steps, ε=0.606  (learning patterns)
Episode  200: 98% success,  7.3 avg steps, ε=0.367  (finding good paths)
Episode  600: 100% success, 4.3 avg steps, ε=0.049  (near optimal)
Episode  700: 100% success, 2.5 avg steps, ε=0.030  (optimal path!)
Episode 5000: 100% success, 2.1 avg steps, ε=0.01   (mastered)
```

### What Agent Learns (Q-values example)

```
State: current=open_office, goal=meeting_room

Before Training (Episode 1):
  Q(open_office → corridor)     = 12  (random)
  Q(open_office → outside)      = 45  (random)
  Q(open_office → boss_office_1)= 67  (random)
  Q(open_office → boss_office_2)= 23  (random)
  → Agent picks boss_office_1 (highest Q, but wrong!)

After Training (Episode 5000):
  Q(open_office → corridor)     = 98  ← LEARNED: Best path!
  Q(open_office → outside)      = -50 ← LEARNED: Dead end
  Q(open_office → boss_office_1)= -30 ← LEARNED: Wrong direction
  Q(open_office → boss_office_2)= -25 ← LEARNED: Wrong direction
  → Agent picks corridor (99% of time, 1% explores)
```

---

## 🎯 Summary

### Pure Python Training
- **Fast**: 40 seconds for 5000 episodes
- **Simple**: Graph transitions only
- **Purpose**: Pre-train weights quickly

### Visual Python Training  
- **Realistic**: 3D navigation with physics
- **Slow**: Real-time episodes (~30 sec each)
- **Purpose**: Validate in realistic environment

### Production (rl-as-service-zahra)
- **Inference**: Uses pre-trained model
- **Fast**: No weight updates
- **Purpose**: Deployed intelligent agent

**Recommended Workflow:**
1. Train on `pure_python_training` (40 seconds)
2. Copy `checkpoints/alice.pt` to other branches
3. Validate on `visual_python_training` (if needed)
4. Deploy on `rl-as-service-zahra` (production)
