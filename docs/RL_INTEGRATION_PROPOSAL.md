
# BDI-First Learning with RL + ILP Fallback for Vesna Agents

## Project Proposal

**Author:** Zahra  
**Date:** December 2025  
**Branch:** `rl-learning`  
**Status:** Draft - Version 5.0

---

## 1. Problem Statement

### Current Situation Analysis

**What Alice ALREADY KNOWS (Hardcoded):**
```jason
{ include( "playgrounds/office.asl" ) }  // ← Complete map is given!
```
- Full office map via `office_map.asl` (all `map_ntpp`, `map_po`, `map_ec` relations)
- Navigation algorithm via `vesna.asl` (`find_path`, `go_to` plans)
- Her desk location: `+my_desk(senior_3_desk)`
- Starting position: `+ntpp(Me, senior_office_2)`

**The Real Question:** How does Alice handle situations NOT in her hardcoded knowledge?

### The Learning Challenge: BDI-First Approach

**KEY INSIGHT:** The agent should NOT start from scratch with RL exploration!

**WRONG Approach (RL-First):**
```
Agent starts → RL explores randomly → ILP learns → Agent knows map
```

**CORRECT Approach (BDI-First):**
```
Agent uses BDI knowledge → BDI fails (no plan/belief) → RL explores → ILP extracts rules → Rules added to BDI
```

### Why BDI-First with RL Fallback?

| Situation | What Happens |
|-----------|--------------|
| **Goal in known map** | BDI handles it (hardcoded knowledge works) |
| **Goal NOT in map** | BDI fails → RL takes over → learns → ILP extracts rule |
| **Next time same goal** | BDI uses learned rule (no RL needed!) |

**Key Insight:**
- BDI already works for known situations
- RL only activates when BDI has no applicable plan
- All actions (BDI success/fail, RL exploration) generate traces
- ILP learns from BOTH BDI traces AND RL traces
- Learned rules are injected back into BDI beliefs

---

## 2. The BDI-First Architecture

### 2.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    BDI-FIRST WITH RL FALLBACK SYSTEM                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐      walk(X), perceive()       ┌─────────────┐             │
│  │   GODOT     │◄──────────────────────────────►│   VESNA     │             │
│  │  (3D Env)   │                                │  (Bridge)   │             │
│  │   Office    │──── movement(success/fail) ───►│  WebSocket  │             │
│  └─────────────┘                                └──────┬──────┘             │
│                                                        │                    │
│                                                        ▼                    │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      JASON BDI AGENT (Alice)                          │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │                    NORMAL BDI OPERATION                          │ │  │
│  │  │                                                                  │ │  │
│  │  │  BELIEFS:                          PLANS:                        │ │  │
│  │  │  ┌─────────────────────────┐      ┌─────────────────────────┐   │ │  │
│  │  │  │ map_ntpp(coffee,common) │      │ +!go_to(Target)         │   │ │  │
│  │  │  │ map_po(corridor,door_c) │      │   <- vesna.asl plans    │   │ │  │
│  │  │  │ my_desk(senior_3_desk)  │      │      use find_path      │   │ │  │
│  │  │  │ learned_ntpp(printer,..)│←─────│      log_trace(result)  │   │ │  │
│  │  │  └─────────────────────────┘      └─────────────────────────┘   │ │  │
│  │  │                                                                  │ │  │
│  │  │                          ↓ If plan fails (no path found)         │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │                             │                                         │  │
│  │                             ▼                                         │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │                    RL FALLBACK MODE                              │ │  │
│  │  │                                                                  │ │  │
│  │  │  +!go_to(Target)                                                 │ │  │
│  │  │      : not find_path(Target, _)    // BDI failed!               │ │  │
│  │  │      <- !activate_rl_exploration(Target);                        │ │  │
│  │  │         !rl_select_action;                                       │ │  │
│  │  │         !execute_and_learn.                                      │ │  │
│  │  │                                                                  │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│         │                                         ▲                         │
│         │ ALL traces (BDI + RL)                   │ learned rules           │
│         ▼                                         │                         │
│  ┌─────────────┐                           ┌─────────────┐                 │
│  │   TRACE     │                           │    RULE     │                 │
│  │  COLLECTOR  │                           │  INJECTOR   │                 │
│  │  (logging)  │                           │  (update)   │                 │
│  └──────┬──────┘                           └──────▲──────┘                 │
│         │                                         │                         │
│         │ (location,action,outcome)               │ rules                   │
│         ▼                                         │                         │
│  ┌─────────────┐         ┌─────────────┐         │                         │
│  │     RL      │ traces  │    ILP      │─────────┘                         │
│  │  Q-Learning │────────►│   ILASP     │                                   │
│  │  (Python)   │         │  (Python)   │                                   │
│  └─────────────┘         └─────────────┘                                   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 The Key Difference: BDI-First Flow

**OLD (RL-First) - WRONG:**
```
1. Remove map → 2. RL explores blindly → 3. Learn everything from scratch
```

**NEW (BDI-First) - CORRECT:**
```
1. Keep map → 2. BDI works normally → 3. BDI fails (unknown goal) → 4. RL explores → 5. ILP learns → 6. Rules added to BDI
```

### 2.3 What Each Component Does

**BDI Agent (Jason) - PRIMARY:**
- Uses existing knowledge (hardcoded map + learned rules)
- Executes plans from `vesna.asl` for known situations
- Logs ALL actions (success/fail) as traces
- Detects when no plan is applicable → triggers RL

**RL (Q-Learning) - FALLBACK:**
- Only activates when BDI fails
- Explores to find a path to unknown goal
- Uses BDI's existing traces to initialize Q-values (prior knowledge!)
- Generates additional exploration traces

**ILP (ILASP) - LEARNING:**
- Learns from ALL traces (BDI successes, BDI failures, RL exploration)
- Extracts generalizable symbolic rules
- Rules are in Prolog format (compatible with AgentSpeak)

**Rule Injector - INTEGRATION:**
- Converts ILP rules to AgentSpeak beliefs
- Adds to agent's belief base: `learned_ntpp(X,Y)`, `learned_po(X,Y)`
- Next time BDI encounters same situation → uses learned rule!

---

## 3. Trace Collection: Learning from BDI Behavior

### 3.1 The Key Innovation: BDI Traces as Training Data

**Instead of RL exploring blindly, we use what the agent ALREADY DOES:**

```jason
// Modified vesna.asl - logs every action
+!go_to(Target)
    :   ntpp(Me, Here) & find_path(Here, Target, Path) & Path \== []
    <-  !log_trace(Here, go_to(Target), attempt);
        !follow_path(Path);
        !log_trace(Here, go_to(Target), success).

+!go_to(Target)
    :   ntpp(Me, Here) & not find_path(Here, Target, _)
    <-  !log_trace(Here, go_to(Target), bdi_failed);
        !activate_rl_fallback(Target).
```

### 3.2 Trace Format

```python
trace = {
  "source": "bdi" | "rl",           # Who generated this trace?
  "location": "senior_office_2",
  "goal": "coffee_machine",
  "action": "go_to(coffee_machine)",
  "outcome": "success" | "fail" | "bdi_failed",
  "path_used": ["door_senior_2", "corridor", "door_common", "common"],
  "steps": 4
}
```

### 3.3 Types of Traces

| Trace Type | Source | Meaning | Used For |
|------------|--------|---------|----------|
| **BDI Success** | Normal operation | Agent knew how to reach goal | Positive ILP examples |
| **BDI Failure** | No applicable plan | Goal not in map | Trigger RL + negative examples |
| **RL Exploration** | Fallback mode | Agent trying to find unknown goal | RL Q-values + ILP examples |
| **RL Success** | Fallback found goal | RL discovered path | Positive ILP examples |

### 3.4 Example Traces from Alice's Day

**Morning (BDI handles known goals):**
```python
traces = [
  {"source": "bdi", "location": "senior_office_2", "goal": "coffee_machine", 
   "action": "go_to(coffee_machine)", "outcome": "success", 
   "path": ["door_senior_2", "corridor", "door_common", "common"], "steps": 4},
  
  {"source": "bdi", "location": "common", "goal": "senior_3_desk", 
   "action": "go_to(senior_3_desk)", "outcome": "success", 
   "path": ["door_common", "corridor", "door_senior_3", "senior_office_3"], "steps": 4},
]
```

**Afternoon (BDI fails on unknown goal):**
```python
traces.append(
  {"source": "bdi", "location": "senior_office_2", "goal": "printer",
   "action": "go_to(printer)", "outcome": "bdi_failed",
   "reason": "no_path_found"}  # ← TRIGGERS RL!
)

# RL takes over and explores:
traces.extend([
  {"source": "rl", "location": "senior_office_2", "action": "walk(door_senior_2)", 
   "outcome": "success", "reward": 5},
  {"source": "rl", "location": "corridor", "action": "walk(door_common)", 
   "outcome": "success", "reward": 5},
  {"source": "rl", "location": "common", "action": "perceive()", 
   "outcome": "no_printer", "reward": -2},
  {"source": "rl", "location": "common", "action": "walk(door_common)", 
   "outcome": "success", "reward": 1},
  {"source": "rl", "location": "corridor", "action": "walk(reception)", 
   "outcome": "success", "reward": 10},
  {"source": "rl", "location": "reception", "action": "perceive()", 
   "outcome": "found_printer!", "reward": 100},
])
```

---

## 4. RL Fallback Mode: When BDI Fails

### 4.1 When Does RL Activate?

RL is NOT the default behavior. It only activates when:

```jason
+!go_to(Target)
    :   ntpp(Me, Here) & not find_path(Here, Target, _)  // BDI has NO plan!
    <-  .print("BDI failed! Activating RL for: ", Target);
        !activate_rl_fallback(Target).
```

**Triggers:**
- Goal object not in `map_ntpp` beliefs (e.g., `printer` never defined)
- Path cannot be computed (room not connected in known map)
- New environment (transferred to different office)

### 4.2 RL Uses BDI Knowledge as Prior

**Critical Insight:** RL doesn't start from zero! It uses what BDI knows:

```python
def initialize_q_values_from_bdi(agent_beliefs):
    """Use BDI's existing knowledge to initialize Q-values"""
    Q = {}
    
    # BDI knows these connections work (from map_po)
    for (room, door) in agent_beliefs.get("map_po"):
        Q[(room, f"walk({door})")] = 0.8  # High initial value!
    
    # BDI knows these are adjacent (from map_ec)
    for (room1, room2) in agent_beliefs.get("map_ec"):
        Q[(room1, f"walk({room2})")] = 0.7
    
    # Unknown actions start at 0
    return Q
```

### 4.3 RL Exploration Strategy

When in fallback mode:

```python
def rl_explore(current_location, goal, agent_beliefs, epsilon=0.2):
    """Explore when BDI doesn't know how to reach goal"""
    
    # Get Q-values (initialized from BDI knowledge)
    Q = get_q_table()
    
    # Get all possible actions from current location
    actions = get_available_actions(current_location)
    
    # ε-greedy: mostly exploit BDI knowledge, sometimes explore
    if random() < epsilon:
        return random.choice(actions)  # Explore unknown
    else:
        return argmax(Q[current_location])  # Use BDI priors
```

### 4.4 RL Reward Function (Fallback Mode Only)

| Event | Reward | Rationale |
|-------|--------|-----------|
| Find goal object | **+100** | Primary objective achieved |
| Enter new room | **+10** | Encourages exploration |
| Successful walk | **+1** | Valid action |
| Failed walk | **-5** | Learn from mistakes |
| Revisit explored room | **-2** | Avoid circles |

---

## 5. ILP Rule Learning from Combined Traces

### 5.1 ILP Learns from BOTH BDI and RL Traces

**Key Insight:** ILP doesn't just learn from RL exploration. It learns from EVERYTHING the agent does:

| Trace Source | Example | What ILP Learns |
|--------------|---------|-----------------|
| BDI Success | `go_to(coffee_machine)` worked | Path pattern for coffee_machine |
| BDI Failure | `go_to(printer)` failed | Printer not in known map |
| RL Exploration | `walk(reception)` found printer | `ntpp(printer, reception)` |

### 5.2 Converting Traces to ILP Examples

**From BDI Success Traces:**
```prolog
% BDI successfully navigated to coffee_machine
#pos({ntpp(coffee_machine, common)}, {}, {
  source(bdi).
  goal(coffee_machine).
  path([door_senior_2, corridor, door_common, common]).
  outcome(success).
}).

% BDI knows corridor connects to door_common
#pos({po(corridor, door_common)}, {}, {
  source(bdi).
  walked_from(corridor).
  walked_to(door_common).
  outcome(success).
}).
```

**From RL Exploration Traces:**
```prolog
% RL discovered printer is in reception!
#pos({ntpp(printer, reception)}, {}, {
  source(rl).
  goal(printer).
  found_at(reception).
  outcome(success).
}).
```

### 5.3 Rules ILP Should Learn

From combined BDI + RL traces, ILP extracts:

**Rule 1: Object Location Pattern (from RL discoveries)**
```prolog
ntpp(Object, Room) :-
  rl_trace(goal(Object), found_at(Room), success).
```

**Rule 2: Navigation Pattern (from BDI successes)**
```prolog
reachable(Here, Target) :-
  bdi_trace(from(Here), goal(Target), success, Path),
  Path \= [].
```

**Rule 3: Door Connection Pattern**
```prolog
connected_via_door(Room1, Room2) :-
  po(Room1, Door),
  po(Door, Room2),
  is_door(Door).
```

### 5.4 Injecting Learned Rules Back to BDI

```jason
// After ILP learns: printer is in reception
+learned_ntpp(printer, reception).

// Now BDI can handle !go_to(printer) without RL!
+!go_to(Target)
    :   ntpp(Me, Here) & 
        learned_ntpp(Target, TargetRoom) &  // ← Uses learned belief!
        find_path(Here, TargetRoom, Path)
    <-  !follow_path(Path);
        vesna.walk(Target).
```
---

## 6. Complete Learning Cycle: Alice's Day

### 6.1 Scenario: BDI-First with RL Fallback

**Setup:**
- Alice is in `senior_office_2`
- She has the hardcoded map (`office_map.asl`)
- Some objects ARE in the map (coffee_machine in common)
- Some objects are NOT in the map (printer - location unknown!)

### 6.2 Morning: BDI Handles Known Goals

**Alice wants coffee (coffee_machine IS in map):**

```jason
// Alice's goal
!go_to(coffee_machine)

// BDI checks beliefs:
?ntpp(coffee_machine, common).     // YES! map_ntpp says it's in common
?find_path(senior_office_2, common, Path).  // Path = [door_senior_2, corridor, door_common, common]

// BDI executes successfully:
// → walk(door_senior_2) → walk(corridor) → walk(door_common) → walk(common)
// → GOAL REACHED!

// Trace logged:
trace: {source: "bdi", from: "senior_office_2", goal: "coffee_machine", outcome: "success", steps: 4}
```

**No RL needed! BDI knows the path.**

### 6.3 Afternoon: BDI Fails on Unknown Goal

**Alice needs to find the printer (printer NOT in map!):**

```jason
// Alice's goal
!go_to(printer)

// BDI checks beliefs:
?ntpp(printer, Room).     // FAIL! printer not in any map_ntpp belief!

// BDI cannot find path because it doesn't know where printer is
?find_path(senior_office_2, ???, Path).  // Can't compute - no target room!

// BDI FAILS → RL ACTIVATES:
.print("BDI failed! Unknown object: printer");
!activate_rl_fallback(printer).

// Trace logged:
trace: {source: "bdi", from: "senior_office_2", goal: "printer", outcome: "bdi_failed", reason: "unknown_object"}
```

### 6.4 RL Fallback Explores (Using BDI Knowledge)

```
RL Mode Active: Finding printer
Using BDI knowledge as priors (Q-values initialized from map_po, map_ec)

Step  State                Action                 Outcome    Q-prior  Reward
─────────────────────────────────────────────────────────────────────────────
1     at(senior_office_2)  walk(door_senior_2)   SUCCESS    0.8      +5
      [BDI knew this works via map_po]
      
2     at(corridor)         walk(door_common)     SUCCESS    0.8      +5
      [BDI knew this, checking common first]
      
3     at(common)           perceive()            no_printer -        -2
      [Printer not here!]
      
4     at(common)           walk(door_common)     SUCCESS    0.8      +1
      [Return to corridor]
      
5     at(corridor)         walk(reception)       SUCCESS    0.7      +10
      [BDI knew ec(corridor,reception), try adjacent room]
      
6     at(reception)        perceive()            FOUND!     -        +100
      [PRINTER IS IN RECEPTION!]

RL Episode Complete: Found printer in 6 steps
```

### 6.5 ILP Learns from Combined Traces

After the episode, ILP processes ALL traces:

**BDI Traces (morning):**
- `go_to(coffee_machine)` succeeded via [door_senior_2, corridor, door_common, common]
- Reinforces known paths

**RL Traces (afternoon):**
- `perceive()` in common → no printer (negative)
- `perceive()` in reception → found printer (positive!)

**ILP Extracts New Rule:**
```prolog
ntpp(printer, reception).  % LEARNED from RL exploration!
```

### 6.6 Rule Injection: BDI Learns!

```jason
// New belief added to Alice:
+learned_ntpp(printer, reception).

// Tomorrow, when Alice needs printer:
!go_to(printer)

// BDI checks:
?learned_ntpp(printer, reception).  // YES! Learned yesterday!
?find_path(senior_office_2, reception, Path).  // Path = [door_senior_2, corridor, reception]

// BDI handles it! No RL needed!
```

### 6.7 The Complete Cycle Visualized

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ALICE'S LEARNING CYCLE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  DAY 1 MORNING: BDI Works                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ !go_to(coffee_machine)                                       │   │
│  │    ↓                                                         │   │
│  │ BDI finds path (hardcoded map) → SUCCESS                     │   │
│  │    ↓                                                         │   │
│  │ Trace logged: {source:bdi, outcome:success}                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  DAY 1 AFTERNOON: BDI Fails → RL Takes Over                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ !go_to(printer)                                              │   │
│  │    ↓                                                         │   │
│  │ BDI fails (printer not in map) → TRIGGER RL                  │   │
│  │    ↓                                                         │   │
│  │ RL explores (uses BDI Q-priors) → finds printer in reception │   │
│  │    ↓                                                         │   │
│  │ Trace logged: {source:rl, found:reception}                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  NIGHT: ILP Learns from Traces                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ILP analyzes all traces (BDI + RL)                           │   │
│  │    ↓                                                         │   │
│  │ Extracts rule: ntpp(printer, reception)                      │   │
│  │    ↓                                                         │   │
│  │ Injects as belief: +learned_ntpp(printer, reception)         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  DAY 2: BDI Knows!                                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ !go_to(printer)                                              │   │
│  │    ↓                                                         │   │
│  │ BDI finds path using learned_ntpp → SUCCESS (no RL needed!)  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. Why BDI-First with RL Fallback is Better

### 7.1 Comparison of Approaches

| Approach | When it Works | Problem |
|----------|---------------|---------|
| **Pure BDI** | When map is complete | Cannot handle unknown situations |
| **Pure RL** | Always explores | Ignores existing knowledge, slow |
| **RL-First Hybrid** | Remove map, learn everything | Wastes BDI's existing knowledge! |
| **BDI-First (Ours)** | Use BDI, RL only when needed | Best of both worlds |

### 7.2 The Key Advantage: Learning FROM What You Already Know

```
┌─────────────────────────────────────────────────────────────────┐
│                   BDI-FIRST ADVANTAGES                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Existing BDI Knowledge:          What We GAIN:                 │
│  ┌─────────────────┐             ┌─────────────────┐           │
│  │ - Office map    │             │ - Handle unknown │           │
│  │ - Navigation    │ + RL/ILP = │ - Learn new locs │           │
│  │ - RCC rules     │             │ - Adapt to change│           │
│  │ - Goal plans    │             │ - Transfer rules │           │
│  └─────────────────┘             └─────────────────┘           │
│                                                                 │
│  We DON'T throw away BDI knowledge!                             │
│  We EXTEND it with RL when needed!                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.3 Concrete Benefits

1. **Efficiency:** BDI handles known situations immediately (no exploration)
2. **Learning:** RL discovers new knowledge when BDI fails
3. **Integration:** Learned rules become BDI beliefs (permanent learning)
4. **Transfer:** General rules (like "doors connect rooms") apply everywhere
5. **Explainability:** All decisions traceable (BDI reasoning + learned rules)

---

## 8. Implementation Plan

### Phase 1: Documentation & Design (Current)
- [x] Create branch `rl-learning`
- [x] Write proposal document (this file)
- [x] Define BDI-First architecture
- [ ] Review and finalize approach

### Phase 2: Trace Logging in BDI
- [ ] Modify `vesna.asl` to log all actions
- [ ] Create trace format specification
- [ ] Implement `log_trace` internal action
- [ ] Test trace collection during normal BDI operation

### Phase 3: RL Fallback Module
- [ ] Create `scripts/rl_fallback.py` with Q-learning
- [ ] Implement BDI-to-Q-value initialization
- [ ] Create `!activate_rl_fallback` plan
- [ ] Connect RL module to Jason via WebSocket
- [ ] Test RL activation when BDI fails

### Phase 4: ILP Learning
- [ ] Set up ILASP environment
- [ ] Create `scripts/trace_to_ilp.py` converter
- [ ] Process BOTH BDI and RL traces
- [ ] Learn rules from combined traces
- [ ] Validate learned rules

### Phase 5: Rule Injection
- [ ] Create `scripts/rule_injector.py`
- [ ] Convert ILP rules to `learned_ntpp`, `learned_po` beliefs
- [ ] Modify `vesna.asl` to use learned beliefs
- [ ] Test: BDI uses learned rules (no RL needed)

### Phase 6: Evaluation
- [ ] Compare: BDI-only vs BDI+RL-Fallback
- [ ] Measure: How quickly new goals are learned
- [ ] Test: Once learned, goals handled by BDI
- [ ] Document results

---

## 9. Files to Create

| File | Purpose |
|------|---------|
| `docs/RL_INTEGRATION_PROPOSAL.md` | This document |
| `scripts/rl_fallback.py` | Q-learning fallback module |
| `scripts/trace_collector.py` | Log BDI + RL traces |
| `scripts/trace_to_ilp.py` | Convert traces to ILP format |
| `scripts/ilp_learner.py` | ILASP integration |
| `scripts/rule_injector.py` | Inject rules to agent beliefs |
| `mind/src/agt/vesna_learning.asl` | Extended vesna.asl with trace logging |
| `mind/src/agt/learned_beliefs.asl` | Generated file with learned beliefs |

---

## 10. Success Criteria

1. **BDI Works Normally:** Known goals handled without RL
2. **RL Fallback:** Unknown goals trigger RL exploration
3. **Trace Collection:** All actions logged (BDI + RL)
4. **ILP Learning:** Rules extracted from combined traces
5. **Rule Injection:** Learned rules become BDI beliefs
6. **Re-use:** Once learned, BDI handles goal (no RL needed!)

---

## 11. References

- JaCaMo Framework: https://jacamo-lang.github.io/
- Jason AgentSpeak: https://jason-lang.github.io/
- ILASP (ILP System): https://doc.ilasp.com/
- Q-Learning: Watkins, C.J.C.H. (1989). Learning from Delayed Rewards
- Vesna Toolkit: https://github.com/VEsNA-ToolKit/vesna-light

---

## 12. Appendix: Office Map Reference

### Room Hierarchy (BDI Already Knows This)
```
office
├── reception (ec: corridor)
├── corridor (hub - connects to most rooms)
├── open_office (ec: corridor)
│   └── junior desks
├── common (via door_common from corridor)
│   └── coffee_machine  ← KNOWN
├── meeting_room (via door_meeting_room)
├── senior_office_1, 2, 3 (via doors)
│   └── senior desks
├── boss_office_1, 2 (via doors from open_office)
└── outside (via doors from open_office)
```

### What BDI Knows vs What It Learns

| Knowledge | Source |
|-----------|--------|
| Room connections (po, ec) | Hardcoded in `office_map.asl` |
| coffee_machine location | Hardcoded: `map_ntpp(coffee_machine, common)` |
| printer location | **LEARNED:** `learned_ntpp(printer, reception)` |
| New object locations | **LEARNED:** via RL exploration + ILP |

---

## 13. Summary: BDI-First with RL Fallback

| Component | Role | When Active |
|-----------|------|-------------|
| **BDI (Jason)** | Use existing knowledge, execute plans | ALWAYS (primary) |
| **RL (Q-Learning)** | Explore when BDI fails | Only when no applicable plan |
| **ILP (ILASP)** | Extract rules from traces | Periodically (batch learning) |
| **Rule Injector** | Add learned rules to BDI | After ILP extracts rules |

**The Cycle:**
```
BDI operates → logs traces → BDI fails → RL explores → ILP learns → rules injected → BDI knows!
```

---

## 14. Knowledge Transfer Between Agents

### 14.1 The Problem: Asymmetric Knowledge

Alice and Bob have **different knowledge** based on their experience:

| Agent | Has Plan For | Doesn't Know |
|-------|--------------|--------------|
| **Alice** (Senior) | Coffee making, navigation, desk work | - |
| **Bob** (Junior) | Desk work, basic navigation | Coffee making! |

**Key Insight:** Alice's traces about coffee-making can teach Bob, without Bob needing to learn from scratch!

### 14.2 Knowledge Transfer Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                   KNOWLEDGE TRANSFER SYSTEM                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │                    ALICE (has knowledge)                         │        │
│  │                                                                  │        │
│  │  Plans: +!make_coffee <- go_to(coffee_machine); use(machine).   │        │
│  │  Experience: 50+ successful coffee traces                        │        │
│  │                                                                  │        │
│  └──────────────────────────┬──────────────────────────────────────┘        │
│                             │                                                │
│                             │ traces logged                                  │
│                             ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │              SHARED TRACE BUFFER (ALL AGENTS)                    │        │
│  │                                                                  │        │
│  │  [{agent:alice, action:go_to(coffee_machine), outcome:success}, │        │
│  │   {agent:alice, action:use(coffee_machine), outcome:success},   │        │
│  │   {agent:alice, action:take(coffee), outcome:success},          │        │
│  │   ...]                                                           │        │
│  │                                                                  │        │
│  └──────────────────────────┬──────────────────────────────────────┘        │
│                             │                                                │
│                             │ ILP learns from ALL traces                     │
│                             ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │                    ILP RULE LEARNING                             │        │
│  │                                                                  │        │
│  │  From Alice's traces, learns ABSTRACT rule:                      │        │
│  │                                                                  │        │
│  │  make_coffee(Agent) :-                                           │        │
│  │      ntpp(Agent, common),                                        │        │
│  │      ntpp(coffee_machine, common),                               │        │
│  │      can_use(Agent, coffee_machine).                             │        │
│  │                                                                  │        │
│  │  Note: Rule uses AGENT variable, not "alice"!                    │        │
│  └──────────────────────────┬──────────────────────────────────────┘        │
│                             │                                                │
│                             │ generalized rules                              │
│                             ▼                                                │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │                  RULE INJECTOR (TO ALL)                          │        │
│  │                                                                  │        │
│  │  Injects learned rules to BOTH Alice AND Bob                     │        │
│  └─────────────────────────────┬───────────────────────────────────┘        │
│                                │                                             │
│                 ┌──────────────┴──────────────┐                             │
│                 ▼                              ▼                             │
│  ┌─────────────────────────┐    ┌─────────────────────────┐                │
│  │        ALICE            │    │          BOB             │                │
│  │  (already knew this)    │    │  (NOW KNOWS TOO!)        │                │
│  │                         │    │                          │                │
│  │  +learned_make_coffee.  │    │  +learned_make_coffee.   │                │
│  └─────────────────────────┘    └─────────────────────────┘                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 14.3 Abstraction: From Specific to General

The key is **abstracting** Alice's specific traces into **general rules** that work for ANY agent:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ABSTRACTION PROCESS                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ALICE'S SPECIFIC TRACES:                                                   │
│  ─────────────────────────                                                  │
│  trace_1: {agent: alice, action: go_to(common), from: senior_office_2}     │
│  trace_2: {agent: alice, action: walk(coffee_machine), at: common}         │
│  trace_3: {agent: alice, action: use(coffee_machine), outcome: coffee}     │
│                                                                             │
│                              │                                              │
│                              │ ILP ABSTRACTION                              │
│                              ▼                                              │
│                                                                             │
│  GENERAL RULE (works for any agent):                                        │
│  ───────────────────────────────────                                        │
│  +!make_coffee                                                              │
│      :  ntpp(Me, CurrentRoom)                 // Agent is somewhere        │
│      <- !go_to(common);                       // Go to common room         │
│         vesna.walk(coffee_machine);           // Walk to machine           │
│         vesna.grab(coffee_machine);           // Use it                    │
│         .print("Got coffee!").                                              │
│                                                                             │
│  Note: "alice" is replaced with "Me" (any agent!)                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 14.4 ILP Abstraction Examples

**From Alice's Traces → General Rules:**

| Alice's Trace | Abstracted Rule | Applicable To |
|---------------|-----------------|---------------|
| `alice: go_to(coffee_machine) → success` | `reachable(coffee_machine, common)` | Any agent |
| `alice: use(coffee_machine) → got_coffee` | `produces(coffee_machine, coffee)` | Any agent |
| `alice: path [door_senior_2, corridor, door_common]` | `path_pattern(senior_office, common, via_corridor)` | Any senior office |

```prolog
% ILP learns from Alice's traces:

% Rule 1: Location knowledge (abstracted)
ntpp(coffee_machine, common).  % Object location - universal

% Rule 2: Skill/procedure (abstracted from alice to Agent)
can_make_coffee(Agent) :-
    can_reach(Agent, common),
    not occupied(coffee_machine).

% Rule 3: Path pattern (abstracted from specific office)
can_reach(Agent, common) :-
    ntpp(Agent, Office),
    office_type(Office, senior_office),  % Generalized!
    connected(Office, corridor),
    connected(corridor, common).
```

### 14.5 Knowledge Transfer Scenarios

#### Scenario 1: Bob Learns Coffee from Alice's Traces

```
TIME: Morning
─────────────────────────────────────────────────────────────────────

Alice (knows coffee):
  !make_coffee
  → go_to(common) [success]
  → use(coffee_machine) [success]
  → Trace logged: {agent:alice, goal:coffee, outcome:success, 
                   path:[door_senior_2, corridor, door_common, common]}

Bob (doesn't know coffee):
  !make_coffee
  → BDI FAILS: no applicable plan!
  → Logs: {agent:bob, goal:coffee, outcome:bdi_failed}

TIME: Learning Phase
─────────────────────────────────────────────────────────────────────

ILP sees BOTH traces:
  - Alice succeeded with path X
  - Bob failed (no plan)

ILP learns ABSTRACT rule:
  make_coffee_plan(Agent) :-
      go_to(Agent, common),
      use(Agent, coffee_machine).

Rule injected to BOTH agents:
  +learned_coffee_procedure.

TIME: Afternoon
─────────────────────────────────────────────────────────────────────

Bob tries again:
  !make_coffee
  → BDI checks: learned_coffee_procedure? YES!
  → Follows learned plan → SUCCESS!
  → Bob learned from Alice's experience!
```

#### Scenario 2: Generalization Across Offices

```prolog
% Alice works in senior_office_2
% Alice's traces show: senior_office_2 → corridor → common

% ILP abstracts to general pattern:
path_to_common(Agent) :-
    ntpp(Agent, Office),
    has_door(Office, Door),
    po(Door, corridor),
    po(corridor, door_common),
    po(door_common, common).

% Now Bob (in open_office) can use this pattern!
% His path: open_office → corridor → common
% Different starting point, SAME abstract pattern!
```

### 14.6 Types of Transferable Knowledge

| Knowledge Type | Example | Abstraction Level |
|----------------|---------|-------------------|
| **Object Locations** | `coffee_machine is in common` | Universal (all agents) |
| **Procedures/Skills** | `how to make coffee` | Abstract (any agent can do it) |
| **Path Patterns** | `offices connect via corridor` | Generalized (office type, not specific) |
| **Resource Rules** | `wait if occupied` | Universal (any agent, any resource) |
| **Social Norms** | `junior asks senior for help` | Role-based (senior/junior) |

### 14.7 Benefits of Knowledge Transfer

```
┌─────────────────────────────────────────────────────────────────┐
│              WITHOUT KNOWLEDGE TRANSFER                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Alice: learns coffee in 10 episodes                            │
│  Bob:   learns coffee in 10 episodes (starts from scratch!)     │
│                                                                 │
│  Total learning: 20 episodes                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              WITH KNOWLEDGE TRANSFER                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Alice: learns coffee in 10 episodes                            │
│  ILP:   abstracts Alice's traces → general rule                 │
│  Bob:   receives rule → uses immediately!                       │
│                                                                 │
│  Total learning: 10 episodes (50% reduction!)                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 15. Multi-Agent Reinforcement Learning (MARL)

### 15.1 Multi-Agent Environment: Alice and Bob

With two agents (Alice and Bob) operating in the same environment, we need **Multi-Agent RL** to learn coordination patterns:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    MULTI-AGENT ARCHITECTURE                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐         ┌─────────────────┐                            │
│  │     ALICE       │         │      BOB        │                            │
│  │  (Senior Agent) │         │  (Junior Agent) │                            │
│  │   Port: 9080    │◄───────►│   Port: 9081    │                            │
│  │                 │ .send() │                 │                            │
│  └────────┬────────┘         └────────┬────────┘                            │
│           │                           │                                      │
│           │ traces                    │ traces                               │
│           ▼                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │                 SHARED TRACE BUFFER                          │            │
│  │  [{agent:alice, loc:..., action:..., outcome:...},          │            │
│  │   {agent:bob, loc:..., action:..., outcome:...},            │            │
│  │   {agents:[alice,bob], type:coordination, ...}]             │            │
│  └─────────────────────────────────────────────────────────────┘            │
│           │                                                                  │
│           │ combined traces                                                  │
│           ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │                JOINT Q-LEARNING                              │            │
│  │  Q(s, a_alice, a_bob) → expected_reward                     │            │
│  │                                                              │            │
│  │  State: (alice_loc, bob_loc, coffee_machine_state, ...)     │            │
│  │  Actions: (alice_action, bob_action) - JOINT                 │            │
│  └──────────────────────────────────┬──────────────────────────┘            │
│                                     │                                        │
│                                     │ coordination_rules                     │
│                                     ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │              ONLINE ILP (INCREMENTAL)                        │            │
│  │  Learns: coordination_rule(alice, bob, coffee_machine)      │            │
│  │          priority_rule(senior, junior, resource)            │            │
│  │          help_pattern(bob_stuck, alice_available)           │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 14.2 Coordination Scenarios to Learn

| Scenario | Agents Involved | What MARL Learns |
|----------|-----------------|------------------|
| **Coffee Machine Conflict** | Alice, Bob both want coffee | Turn-taking: who goes first? |
| **Help Request** | Bob asks Alice for help | When to ask, when to accept |
| **Resource Sharing** | Both need printer | Avoid deadlock, share efficiently |
| **Meeting Room** | Both heading to meeting | Coordination on arrival |

### 14.3 Joint Q-Learning for Coordination

```python
# Multi-Agent Q-Learning
class MultiAgentQLearning:
    def __init__(self, agents):
        self.agents = agents  # ["alice", "bob"]
        # Q-table indexed by joint state and joint action
        self.Q = {}  # Q[(state_alice, state_bob), (action_alice, action_bob)]
    
    def get_joint_state(self):
        """Get combined state of both agents"""
        return {
            "alice_loc": get_agent_location("alice"),
            "bob_loc": get_agent_location("bob"),
            "coffee_machine_free": is_resource_free("coffee_machine"),
            "alice_at_desk": is_at_desk("alice"),
            "bob_waiting_help": is_waiting("bob")
        }
    
    def update(self, joint_state, joint_action, joint_reward, next_joint_state):
        """Update Q-values for joint actions"""
        # Standard Q-learning update with joint state-action pairs
        old_q = self.Q.get((joint_state, joint_action), 0)
        max_next_q = max(self.Q.get((next_joint_state, a), 0) 
                        for a in self.get_joint_actions())
        
        self.Q[(joint_state, joint_action)] = old_q + alpha * (
            joint_reward + gamma * max_next_q - old_q
        )
```

### 14.4 Coordination Reward Structure

| Situation | Joint Reward | Rationale |
|-----------|--------------|-----------|
| Both reach goals without conflict | **+50** | Successful coordination |
| One waits for other | **+20** | Polite behavior |
| Alice helps Bob successfully | **+100** | Collaboration rewarded |
| Both try coffee machine simultaneously | **-30** | Conflict penalty |
| Bob waits too long for help | **-10** | Timeout penalty |
| Deadlock (both waiting) | **-50** | Avoid mutual blocking |

### 14.5 Traces for Multi-Agent Learning

```python
# Single-agent trace
single_trace = {
    "agent": "alice",
    "location": "common",
    "action": "use(coffee_machine)",
    "outcome": "success"
}

# Coordination trace (captures interaction)
coordination_trace = {
    "type": "coordination",
    "agents": ["alice", "bob"],
    "situation": "coffee_machine_conflict",
    "alice_action": "wait",
    "bob_action": "use(coffee_machine)",
    "outcome": "bob_first_then_alice",
    "joint_reward": 40  # Both got coffee, no conflict
}

# Help interaction trace
help_trace = {
    "type": "help_interaction",
    "requester": "bob",
    "helper": "alice",
    "bob_request": "help_with_report",
    "alice_response": "coming_to_help",
    "alice_action": "go_to(bob_desk)",
    "outcome": "help_provided",
    "joint_reward": 100
}
```

---

## 16. Online (Incremental) ILP

### 16.1 Why Online ILP Instead of Batch?

| Aspect | Batch ILP | **Online ILP** |
|--------|-----------|----------------|
| When learns | End of episode | After every N traces |
| Latency | High (wait for batch) | **Low (real-time)** |
| Memory | Store all traces | Rolling window |
| Adaptability | Slow to change | **Fast adaptation** |
| Rule updates | Replace all rules | **Incremental refinement** |

### 16.2 Online ILP Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      ONLINE ILP PIPELINE                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TRACE STREAM (from BDI + RL + MARL)                                        │
│  ────────────────────────────────────────────────────────────────►          │
│  t1 → t2 → t3 → t4 → t5 → t6 → t7 → t8 → t9 → t10 → ...                    │
│                              │                    │                          │
│                              │ Every N traces     │                          │
│                              ▼                    ▼                          │
│                    ┌──────────────┐      ┌──────────────┐                   │
│                    │ ILP BATCH 1  │      │ ILP BATCH 2  │                   │
│                    │ (t1...t5)    │      │ (t6...t10)   │                   │
│                    └──────┬───────┘      └──────┬───────┘                   │
│                           │                     │                            │
│                           ▼                     ▼                            │
│                    ┌──────────────┐      ┌──────────────┐                   │
│                    │ Rule Set v1  │  ──► │ Rule Set v2  │  ──► ...          │
│                    │              │      │ (refined)    │                   │
│                    └──────────────┘      └──────────────┘                   │
│                           │                     │                            │
│                           ▼                     ▼                            │
│                    ┌───────────────────────────────────────┐                │
│                    │         RULE INJECTOR (LIVE)          │                │
│                    │   Injects rules as they are learned   │                │
│                    └───────────────────────────────────────┘                │
│                                     │                                        │
│                      ┌──────────────┼──────────────┐                        │
│                      ▼              ▼              ▼                        │
│                 ┌─────────┐   ┌─────────┐   ┌─────────────┐                │
│                 │  ALICE  │   │   BOB   │   │ SHARED RULES│                │
│                 │ beliefs │   │ beliefs │   │ (both use)  │                │
│                 └─────────┘   └─────────┘   └─────────────┘                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 16.3 Incremental Rule Learning

```python
class OnlineILP:
    def __init__(self, batch_size=5):
        self.trace_buffer = []
        self.batch_size = batch_size
        self.current_rules = set()
        self.rule_version = 0
    
    def add_trace(self, trace):
        """Add trace to buffer, trigger learning if batch ready"""
        self.trace_buffer.append(trace)
        
        if len(self.trace_buffer) >= self.batch_size:
            self.learn_incrementally()
    
    def learn_incrementally(self):
        """Learn from current batch, refine existing rules"""
        # Convert traces to ILP examples
        examples = self.traces_to_examples(self.trace_buffer)
        
        # Use existing rules as background knowledge (incremental!)
        background = self.current_rules
        
        # Learn new rules that are CONSISTENT with existing ones
        new_rules = ilasp.induce(
            examples=examples,
            background=background,
            mode="incremental"  # Don't replace, refine!
        )
        
        # Merge new rules with existing
        self.current_rules = self.merge_rules(self.current_rules, new_rules)
        self.rule_version += 1
        
        # Inject to agents immediately
        self.inject_rules(self.current_rules)
        
        # Clear buffer (keep last trace for continuity)
        self.trace_buffer = self.trace_buffer[-1:]
    
    def inject_rules(self, rules):
        """Push rules to agents in real-time"""
        for agent in ["alice", "bob"]:
            for rule in rules:
                send_to_agent(agent, f"+{rule}")
```

### 16.4 Rule Evolution Over Time

```
Time    Traces Seen                      Rules Learned
─────────────────────────────────────────────────────────────────────────
t=5     alice:coffee→success             ntpp(coffee_machine, common)
        bob:coffee→success               
        alice:desk→success               
        bob:desk→success               
        alice:help_bob→success           

t=10    bob:printer→rl_found             ntpp(printer, reception)    [NEW]
        alice:wait_coffee→success        wait_if(coffee_in_use)      [NEW]
        bob:reception→success
        alice:coffee→success
        coordination:alice_wait          priority(senior, junior)    [NEW]

t=15    bob:ask_help→success             help_when(bob_stuck, alice_free)  [NEW]
        alice:go_help→success
        bob:report_done→success
        alice:return_desk→success
        bob:meeting→success              (no new rule - existing cover this)

t=20    (refinement)                     priority(senior, junior) REFINED to:
                                         priority(Agent1, Agent2) :- 
                                           senior(Agent1), junior(Agent2)
```

---

## 17. System Explainability

### 17.1 Why Explainability Matters

BDI agents are naturally more explainable than pure RL because they have:
- **Beliefs**: What the agent knows
- **Desires**: What the agent wants  
- **Intentions**: What the agent is doing

We extend this with **trace-based explanations** and **rule provenance**.

### 17.2 Explainability Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     EXPLAINABILITY SYSTEM                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  USER QUERY: "Why did Alice wait before using the coffee machine?"          │
│                                     │                                        │
│                                     ▼                                        │
│  ┌───────────────────────────────────────────────────────────────┐          │
│  │                    EXPLANATION ENGINE                          │          │
│  │                                                                │          │
│  │  1. Find relevant traces                                       │          │
│  │  2. Identify decision point                                    │          │
│  │  3. Extract applicable rules                                   │          │
│  │  4. Trace rule origin (hardcoded vs learned)                   │          │
│  │  5. Generate natural language explanation                      │          │
│  └───────────────────────────────────────────────────────────────┘          │
│                                     │                                        │
│                                     ▼                                        │
│  ┌───────────────────────────────────────────────────────────────┐          │
│  │                      EXPLANATION                               │          │
│  │                                                                │          │
│  │  "Alice waited because:                                        │          │
│  │   1. Bob was using the coffee machine (belief: occupied)       │          │
│  │   2. Rule: wait_if(coffee_in_use) was triggered                │          │
│  │   3. This rule was LEARNED from coordination traces at t=10    │          │
│  │   4. The rule exists because earlier, conflict caused delay"   │          │
│  └───────────────────────────────────────────────────────────────┘          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 17.3 Three Levels of Explanation

#### Level 1: What Happened (Trace-Based)

```python
def explain_what(agent, action, time):
    """Simple trace lookup"""
    trace = get_trace(agent, time)
    return f"""
    Agent: {trace['agent']}
    Action: {trace['action']}
    Location: {trace['location']}
    Outcome: {trace['outcome']}
    Timestamp: {trace['time']}
    """

# Example output:
# Agent: Alice
# Action: wait(coffee_machine)
# Location: common
# Outcome: waited_3_seconds
# Timestamp: 10:23:45
```

#### Level 2: Why It Happened (Rule-Based)

```python
def explain_why(agent, action, time):
    """Find which rule triggered the action"""
    trace = get_trace(agent, time)
    beliefs = get_beliefs_at_time(agent, time)
    
    # Find matching plan/rule
    matching_rules = []
    for rule in agent.rules:
        if rule.matches(trace['context'], trace['action']):
            matching_rules.append(rule)
    
    return f"""
    Action: {action}
    
    Triggered by rule: {matching_rules[0]}
    
    Because beliefs at time {time}:
    - occupied(coffee_machine) = True
    - ntpp(bob, common) = True
    - senior(alice) = True
    
    Rule interpretation:
    "If coffee machine is occupied, wait before using"
    """

# Example output:
# Action: wait(coffee_machine)
# 
# Triggered by rule: wait_if(occupied(coffee_machine))
# 
# Because beliefs at time 10:23:45:
# - occupied(coffee_machine) = True
# - ntpp(bob, common) = True
# 
# Rule interpretation:
# "If coffee machine is occupied, wait before using"
```

#### Level 3: How It Was Learned (Provenance-Based)

```python
def explain_how_learned(rule):
    """Trace the origin of a learned rule"""
    rule_metadata = get_rule_metadata(rule)
    
    return f"""
    Rule: {rule}
    
    Origin: {rule_metadata['source']}
    
    Learned from traces:
    {rule_metadata['training_traces']}
    
    First introduced: {rule_metadata['version_introduced']}
    
    Learning context:
    "This rule was learned after observing that when both agents
    tried to use the coffee machine at the same time (trace #42, #47),
    it caused delays. The ILP system extracted this rule at version 2
    to prevent future conflicts."
    
    Confidence: {rule_metadata['confidence']}%
    Times applied: {rule_metadata['usage_count']}
    """

# Example output:
# Rule: wait_if(occupied(Resource))
# 
# Origin: LEARNED (not hardcoded)
# 
# Learned from traces:
# - trace #42: alice + bob → coffee conflict → delay 5s
# - trace #47: alice + bob → coffee conflict → delay 3s
# - trace #52: alice waited → bob finished → alice used → no delay
# 
# First introduced: Rule version 2 (t=10)
# 
# Learning context:
# "This rule was learned after observing conflicts at the coffee machine..."
# 
# Confidence: 95%
# Times applied: 23
```

### 17.4 Explanation Query Interface

```jason
// Agent can explain its own decisions
+?explain(Action, Explanation)
    <-  !get_last_trace(Trace);
        !get_applicable_rules(Trace, Rules);
        !get_rule_sources(Rules, Sources);
        .concat("I did ", Action, " because ", Rules, 
                ". This rule ", Sources, Explanation).

// User asks: "Alice, why did you wait?"
// Alice responds: "I did wait(coffee_machine) because 
//   rule wait_if(occupied(X)) matched. This rule was 
//   learned from coordination traces after Bob and I 
//   had conflicts at the coffee machine."
```

### 17.5 Explanation Types Summary

| Question Type | Explanation Level | Data Source |
|---------------|-------------------|-------------|
| "What did Alice do?" | **Trace** | Action log |
| "Why did she wait?" | **Rule** | Belief + matching rule |
| "Where did this rule come from?" | **Provenance** | ILP learning history |
| "What would happen if...?" | **Counterfactual** | Rule simulation |
| "How confident is the rule?" | **Statistics** | Usage + success rate |

### 17.6 Explainability in MARL Context

```python
def explain_coordination(agents, situation):
    """Explain multi-agent coordination decisions"""
    traces = get_coordination_traces(agents, situation)
    
    return f"""
    Coordination Event: {situation}
    
    Agents: {agents}
    
    Joint State:
    - Alice: at(common), goal(coffee)
    - Bob: at(common), goal(coffee)
    - Coffee machine: occupied(by: none)
    
    Decision:
    - Alice chose: wait
    - Bob chose: use(coffee_machine)
    
    Why this coordination:
    - Rule: priority(junior, senior, resource) → junior goes first
    - This encourages senior to mentor/support junior
    - Learned from: help interaction patterns (traces #60-75)
    
    Outcome: Both got coffee, no conflict
    Joint reward: +40
    """
```

---

## 18. Updated Implementation Plan

### Phase 1: Documentation & Design ✅
- [x] Create branch `rl-learning`
- [x] Write proposal document
- [x] Define BDI-First architecture
- [x] Add MARL section
- [x] Add Online ILP section  
- [x] Add Explainability section

### Phase 2: Multi-Agent Setup ✅
- [x] Create Bob agent
- [x] Configure both agents in `vesna.jcm`
- [x] Implement message passing (`.send`)
- [x] Test communication (hello, help_request)

### Phase 3: Trace Logging System
- [ ] Create shared trace buffer
- [ ] Log single-agent traces (location, action, outcome)
- [ ] Log coordination traces (joint actions, interactions)
- [ ] Add trace metadata (timestamp, agent, source)

### Phase 4: MARL Implementation
- [ ] Implement joint state representation
- [ ] Create Joint Q-Learning module
- [ ] Define coordination reward structure
- [ ] Connect to agents via WebSocket

### Phase 5: Online ILP
- [ ] Implement incremental trace batching
- [ ] Set up ILASP for incremental learning
- [ ] Create rule merger (refine, don't replace)
- [ ] Implement live rule injection

### Phase 6: Explainability
- [ ] Create trace query interface
- [ ] Implement rule provenance tracking
- [ ] Build explanation generator
- [ ] Add `?explain` query capability to agents

### Phase 7: Evaluation
- [ ] Test single-agent learning (Alice alone)
- [ ] Test multi-agent coordination (Alice + Bob)
- [ ] Measure learning speed (online vs batch)
- [ ] Evaluate explanation quality
- [ ] Document results

---

## 19. Summary: Complete Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                   BDI-FIRST MARL WITH ONLINE ILP                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌─────────────┐                              ┌─────────────┐                 │
│   │    ALICE    │◄────── .send() messages ────►│     BOB     │                 │
│   │   (BDI)     │                              │    (BDI)    │                 │
│   └──────┬──────┘                              └──────┬──────┘                 │
│          │                                            │                         │
│          │ traces                                     │ traces                  │
│          ▼                                            ▼                         │
│   ┌─────────────────────────────────────────────────────────────────┐          │
│   │              SHARED TRACE BUFFER (STREAMING)                     │          │
│   └─────────────────────────────┬───────────────────────────────────┘          │
│                                 │                                               │
│              ┌──────────────────┼──────────────────┐                           │
│              ▼                  ▼                  ▼                           │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐               │
│   │  JOINT Q-TABLE  │  │   ONLINE ILP    │  │  EXPLAINABILITY │               │
│   │     (MARL)      │  │  (INCREMENTAL)  │  │     ENGINE      │               │
│   └────────┬────────┘  └────────┬────────┘  └────────┬────────┘               │
│            │                    │                    │                         │
│            │                    │                    │                         │
│            ▼                    ▼                    ▼                         │
│   ┌─────────────────────────────────────────────────────────────────┐          │
│   │                    RULE INJECTOR (LIVE)                          │          │
│   │     Injects learned rules to BOTH agents in real-time           │          │
│   └─────────────────────────────────────────────────────────────────┘          │
│                                                                                 │
│   LEARNING CYCLE:                                                               │
│   1. Agents operate (BDI plans)                                                │
│   2. Traces collected (single + coordination)                                  │
│   3. Every N traces → Online ILP learns                                        │
│   4. MARL learns coordination patterns                                         │
│   5. Rules injected to agents                                                  │
│   6. Explainability tracks provenance                                          │
│   7. Agents use new knowledge → back to step 1                                 │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

*Document Version: 7.0 - Knowledge Transfer + MARL + Online ILP + Explainability*
