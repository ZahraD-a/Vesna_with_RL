# Solution: Goal-Conditioned Reinforcement Learning

## Overview

This document describes the solution to the fixed-path learning problem using **Goal-Conditioned Reinforcement Learning (GCRL)**, backed by research from the RL community.

## The Solution

Extend the state representation to include both the **current position** and the **goal position**:

```
State = [current_region_one_hot | goal_region_one_hot]
      = [11 dimensions] + [11 dimensions]
      = 22 dimensions total
```

Combined with **randomized training** (random starts, random goals), this enables the agent to learn general navigation.

## Research Foundation

### Universal Value Function Approximators (UVFA)

**Paper**: Schaul, T., Horgan, D., Gregor, K., & Silver, D. (2015). *Universal Value Function Approximators*. ICML.

Key insight: Instead of learning V(s) or Q(s,a), learn **V(s,g)** or **Q(s,a,g)** where g is the goal.

> "A universal value function V(s,g) generalizes over both states s and goals g. This allows a single function approximator to represent the values for any goal, enabling knowledge transfer between goals."

**Our Application**:
- State input = concatenation of current state and goal state
- Single network learns navigation to ALL goals
- Knowledge transfers: learning path A→B helps learn path A→C

### Hindsight Experience Replay (HER)

**Paper**: Andrychowicz, M., et al. (2017). *Hindsight Experience Replay*. NeurIPS.

Key insight: Failed episodes can be relabeled with achieved goals for additional learning signal.

> "Instead of considering only the goal that the agent was trying to achieve, we also consider the goal that was actually achieved... This provides a much denser reward signal."

**Our Application** (optional enhancement):
- If agent tries to reach `common` but ends at `corridor` (timeout)
- Relabel: "What if the goal was `corridor`?" → successful episode!
- Provides learning signal even from failures

### Goal-Conditioned Policy Learning

**Paper**: Liu, M., et al. (2022). *Goal-Conditioned Reinforcement Learning: Problems and Solutions*. IJCAI Survey.

Key taxonomy of GCRL approaches:

| Approach | Description | Our Choice |
|----------|-------------|------------|
| Goal as input | Concatenate goal to state | **Yes** |
| Goal as reward shaping | Modify reward based on goal | Already doing |
| Hierarchical goals | Multi-level goal decomposition | Not needed |
| Goal generation | Automatic curriculum | Future work |

## Implementation Design

### State Encoding

**Before (11 dims)**:
```
current = senior_office_2
state = [0,0,0,0,0,0,0,1,0,0,0]
```

**After (22 dims)**:
```
current = senior_office_2, goal = common
state = [0,0,0,0,0,0,0,1,0,0,0, 0,0,0,0,1,0,0,0,0,0,0]
         └── current ──────┘   └── goal ──────────┘
```

### Network Architecture

```
Input Layer:  22 neurons (current_one_hot + goal_one_hot)
Hidden 1:     64 neurons, ReLU
Hidden 2:     64 neurons, ReLU
Output Layer: 11 neurons (Q-value per action)
```

The network learns: **Q(current, goal, action) → expected return**

### Training Protocol

```
for episode in range(max_episodes):
    start = random.choice(all_regions)
    goal = random.choice(all_regions - {start})

    state = one_hot(start) + one_hot(goal)

    while not done:
        action = epsilon_greedy(Q(state))
        next_region = execute(action)

        if next_region == goal:
            reward = +100
            done = True
        else:
            reward = -1

        state = one_hot(next_region) + one_hot(goal)
```

### Integration with RCC

Goal-conditioned RL integrates seamlessly with the existing RCC-based action masking:

| Component | Role | Change Required |
|-----------|------|-----------------|
| RCC relations | Define valid transitions | None |
| Action masking | Restrict to neighbors | None |
| State encoding | Current position | **Extended to include goal** |
| Reward function | Goal achievement | None (already goal-based) |
| Policy network | Action selection | **Input size 11→22** |

The key insight: **RCC constrains the action space; goal-conditioning extends the state space**. They are orthogonal.

## Code Changes

### 1. Python RL Agent (dqn_agent.py)

```python
# Before
state_size: int = 11

# After
state_size: int = 22  # 11 current + 11 goal
```

### 2. Python Server (dqn_server.py)

```python
# Before
if state.shape != (11,):
    return _bad_request("state must have exactly 11 elements")

# After
if state.shape != (22,):
    return _bad_request("state must have exactly 22 elements")
```

### 3. Symbolic Engine (symbolic_execution_engine.asl)

```prolog
// New: Build goal-conditioned state vector
+!build_goal_conditioned_state(CurrentRegion, GoalRegion, StateVector)
    <-  !build_state_vector(CurrentRegion, CurrentVec);
        !build_state_vector(GoalRegion, GoalVec);
        .concat(CurrentVec, GoalVec, StateVector).

// Updated RL action selection
+!rl_select_action(CurrentRegion, GoalRegion, Reward, Done, TargetRegion)
    <-  !build_goal_conditioned_state(CurrentRegion, GoalRegion, StateVector);
        !get_valid_action_ids(CurrentRegion, ValidActionIds);
        rl.select_action(StateVector, ValidActionIds, Reward, Done, ActionId);
        ?id_to_region(ActionId, TargetRegion).
```

### 4. Agent Configuration (alice_rl.asl)

```prolog
// All navigable regions
possible_regions([reception, corridor, open_office, outside, common,
                  meeting_room, senior_office_1, senior_office_2,
                  senior_office_3, boss_office_1, boss_office_2]).

// Random start and goal selection
+!select_random_start_goal(Start, Goal)
    <-  ?possible_regions(Regions);
        .shuffle(Regions, Shuffled);
        .nth(0, Shuffled, Start);
        .nth(1, Shuffled, Goal).
```

## Expected Results

### Training Convergence

| Metric | Before (Fixed) | After (Goal-Conditioned) |
|--------|---------------|-------------------------|
| Episodes to converge | ~150 | ~500-1000 (more to learn) |
| Paths learned | 1 | 110 (11×10 start-goal pairs) |
| Generalization | None | Complete |

### Policy Quality

After training, the agent should achieve:

```
Any start → Any goal (different from start)

Example paths learned:
- reception → common: reception → corridor → common (2 steps)
- common → outside: common → corridor → open_office → outside (3 steps)
- boss_office_1 → senior_office_3: boss_office_1 → open_office → corridor → senior_office_3 (3 steps)
```

### Verification

The learned policy can be verified symbolically:
1. Extract Q-values for each (current, goal) pair
2. Check that argmax action leads toward goal
3. Validate all actions respect RCC adjacency

## Future Extensions

### 1. Hindsight Experience Replay (HER)

```python
# After failed episode (timeout at some region)
for achieved_goal in visited_regions:
    # Relabel trajectory with achieved_goal as the goal
    relabeled_transitions = relabel(trajectory, achieved_goal)
    replay_buffer.add(relabeled_transitions)
```

### 2. Curriculum Learning

Start with nearby goals, gradually increase difficulty:
```python
def sample_goal(current, difficulty):
    # difficulty 1: 1-hop neighbors only
    # difficulty 2: 2-hop neighbors
    # difficulty N: any region
    return sample_within_distance(current, difficulty)
```

### 3. Multi-Agent Goal Coordination

```prolog
// Agent A wants to reach X, Agent B wants to reach Y
// Coordinate to avoid collisions using RCC
+!coordinate_goals(AgentGoals)
    <-  !check_path_conflicts(AgentGoals, Conflicts);
        !resolve_conflicts(Conflicts).
```

## References

1. Schaul, T., Horgan, D., Gregor, K., & Silver, D. (2015). Universal Value Function Approximators. *Proceedings of the 32nd International Conference on Machine Learning (ICML)*.

2. Andrychowicz, M., Wolski, F., Ray, A., Schneider, J., Fong, R., Welinder, P., ... & Zaremba, W. (2017). Hindsight Experience Replay. *Advances in Neural Information Processing Systems (NeurIPS)*.

3. Liu, M., Zhu, M., & Zhang, W. (2022). Goal-Conditioned Reinforcement Learning: Problems and Solutions. *Proceedings of the International Joint Conference on Artificial Intelligence (IJCAI)*.

4. Kaelbling, L. P. (1993). Learning to Achieve Goals. *Proceedings of the International Joint Conference on Artificial Intelligence (IJCAI)*.

5. Plappert, M., et al. (2018). Multi-Goal Reinforcement Learning: Challenging Robotics Environments and Request for Research. *arXiv preprint arXiv:1802.09464*.

## Conclusion

Goal-Conditioned RL is the appropriate solution for learning general navigation because:

1. **Theoretically sound**: Backed by UVFA and GCRL research
2. **Minimal changes**: Only extends state space, preserves RCC action masking
3. **Complete generalization**: Single network learns all navigation paths
4. **Verifiable**: Learned policy can be symbolically checked against RCC constraints
5. **Extensible**: Foundation for HER, curriculum learning, multi-agent coordination
