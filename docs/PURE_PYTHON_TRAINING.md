# Pure Python Graph Trainer

## Problem
Training through Godot (physics, navmesh, WebSocket, signal handling) causes stuck agents, timeouts, and belief divergence. The office map is a simple 11-node graph with deterministic transitions -- no physics needed.

## Solution
Build a pure Python trainer that runs the DQN agent directly on the graph. Reuses the existing `DQNAgent` class unchanged. Saves checkpoints loadable by the Flask server for Godot inference.

## New Files

### 1. `mind/python/office_graph_env.py` — Graph Environment
- Encodes the 11-region adjacency graph (mirrors `symbolic_execution_engine.asl`)
- `reset()` → random start/goal (different), returns (state, valid_actions)
- `step(action_id)` → move to neighbor, returns (next_state, reward, done, valid_actions)
- State: 22-dim numpy array [current_one_hot | goal_one_hot]
- Rewards: -1 per step, +100 goal reached, -10 timeout (50 steps)
- Valid actions: neighbor IDs only (action masking)

### 2. `mind/python/train.py` — Training Script
- Creates `OfficeGraphEnv` + `DQNAgent` (same hyperparams)
- Runs N episodes (default 5000), calling `agent.step()` directly
- Logs every 100 episodes: success rate, avg reward, avg steps, epsilon
- Saves checkpoint to `checkpoints/<name>.pt`
- CLI args: `--episodes`, `--name`

## Existing Files (NO changes)
- `mind/python/dqn_agent.py` — used as-is
- `mind/python/dqn_server.py` — loads trained checkpoint for Godot inference via `/load/<agent_id>`

## Graph (from symbolic_execution_engine.asl)
```
Region IDs: reception=0, corridor=1, open_office=2, outside=3, common=4,
            meeting_room=5, senior_office_1=6, senior_office_2=7,
            senior_office_3=8, boss_office_1=9, boss_office_2=10

Adjacency:
  reception ↔ corridor
  corridor ↔ open_office, common, meeting_room, senior_office_1/2/3
  open_office ↔ boss_office_1, boss_office_2, outside
```

## Verification
```bash
cd mind/python
python train.py --episodes 5000 --name alice
# Should complete in seconds, print metrics, save checkpoints/alice.pt
```
Then in Godot inference mode, the Flask server loads the checkpoint:
```
POST /load/alice
```
