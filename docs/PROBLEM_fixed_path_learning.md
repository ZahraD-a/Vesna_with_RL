# Problem: Fixed-Path Learning in RL Navigation

## Overview

This document describes a fundamental limitation discovered in the initial RL implementation for agent navigation in the NOVAE framework.

## The Problem

The agent learns a **fixed template** (a single path from one specific location to one specific goal) rather than **general navigation knowledge** that would allow it to navigate from any location to any destination.

### Observed Behavior

After training for 200+ episodes with the configuration:
```prolog
start_region(senior_office_2).
goal_region(common).
```

The agent successfully learns the optimal path:
```
senior_office_2 → corridor → common  (2 steps)
```

However, when tested with different scenarios:

| Test Scenario | Expected | Actual Result |
|---------------|----------|---------------|
| reception → common | reception → corridor → common | Agent confused, random behavior |
| common → outside | common → corridor → open_office → outside | Agent confused, random behavior |
| boss_office_1 → meeting_room | boss_office_1 → open_office → corridor → meeting_room | Agent confused, random behavior |

The agent only knows **one path** and cannot generalize.

## Root Cause Analysis

### Current State Representation

The state is encoded as an 11-dimensional one-hot vector representing only the **current location**:

```
State = [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]
         ↑                    ↑
         reception            senior_office_2 (current)
```

### What the Network Learns

With this representation, the Q-network learns a mapping:

```
Q(current_region) → action
```

For example:
- `Q([0,0,0,0,0,0,0,1,0,0,0])` → "go to corridor" (action 1)
- `Q([0,1,0,0,0,0,0,0,0,0,0])` → "go to common" (action 4)

This is essentially a **lookup table** for the single trained path:

```
senior_office_2 → corridor → common
```

### The Missing Information

The network has no information about the **goal**. It cannot distinguish between:
- "I'm at corridor, trying to reach common"
- "I'm at corridor, trying to reach reception"
- "I'm at corridor, trying to reach outside"

All three scenarios produce the same input to the network, but require different actions!

## Visual Illustration

### Office Layout
```
                    ┌─────────────┐
                    │   outside   │
                    └──────┬──────┘
                           │
┌──────────┬───────────────┼───────────────┬──────────┐
│boss_off_1│               │               │boss_off_2│
└────┬─────┘         ┌─────┴─────┐         └────┬─────┘
     │               │open_office│              │
     └───────────────┴─────┬─────┴──────────────┘
                           │
     ┌─────────────────────┴─────────────────────┐
     │                  corridor                  │
     └┬────┬────┬────┬────┬────┬────┬────┬────┬─┘
      │    │    │    │    │    │    │    │    │
   ┌──┴┐┌──┴┐┌──┴┐┌──┴──┐ │ ┌──┴──┐
   │s1 ││s2 ││s3 ││meet │ │ │comm │
   └───┘└───┘└───┘└─────┘ │ └─────┘
                          │
                       ┌──┴───┐
                       │recep │
                       └──────┘
```

### What Gets Learned (Current)
```
Only this single path is learned:

senior_office_2 ──→ corridor ──→ common
     [START]                      [GOAL]
```

### What Should Be Learned (Desired)
```
Full navigation graph - any start to any goal:

     ┌─────────────────────────────────────────┐
     │                                         │
     ▼                                         │
reception ←──→ corridor ←──→ open_office ←──→ outside
                  │              │
                  ├──→ common    ├──→ boss_office_1
                  ├──→ meeting   ├──→ boss_office_2
                  ├──→ senior_1
                  ├──→ senior_2
                  └──→ senior_3
```

## Mathematical Formulation

### Current (Broken) Formulation

The Q-function is defined as:
```
Q: S → R^|A|
```

Where:
- S = {region₀, region₁, ..., region₁₀} (11 states)
- A = {region₀, region₁, ..., region₁₀} (11 actions)

The policy π(s) = argmax_a Q(s, a) gives the same action regardless of the goal.

### Required (Goal-Conditioned) Formulation

The Q-function should be:
```
Q: S × G → R^|A|
```

Where:
- S = current state (11 dims)
- G = goal state (11 dims)
- Combined input = 22 dimensions

The policy π(s, g) = argmax_a Q(s, g, a) can now vary based on the goal.

## Impact

| Aspect | Impact |
|--------|--------|
| **Generalization** | Zero - agent only works for trained start/goal pair |
| **Reusability** | None - must retrain for each new goal |
| **Knowledge Transfer** | Impossible - learned Q-values are goal-specific but don't encode goal |
| **Practical Use** | Limited to single-task navigation |

## Conclusion

The fixed-path learning problem stems from an incomplete state representation that omits goal information. The solution requires transitioning to **Goal-Conditioned Reinforcement Learning** where the state includes both current position and target destination.

See: [SOLUTION_goal_conditioned_rl.md](./SOLUTION_goal_conditioned_rl.md) for the solution.

## References

- Kaelbling, L.P. (1993). Learning to Achieve Goals. IJCAI.
- Schaul, T., et al. (2015). Universal Value Function Approximators. ICML.
