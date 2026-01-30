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

```mermaid
flowchart TB
    subgraph JASON["JASON (Symbolic Layer)"]
        KB["Knowledge Base<br/>neighbor/2 facts"]
        RM["Reward Machine<br/>+100 / -10 / -1"]
        ENC["State Encoder<br/>One-Hot 22-dim"]
        DEC["Action Decoder<br/>ID → Region Name"]
    end

    subgraph PYTHON["PYTHON (Neural Layer)"]
        DQN["DQN Network<br/>22 → 64 → 64 → 11"]
        MASK["Action Masking<br/>invalid = -∞"]
        REPLAY["Experience Replay<br/>Buffer"]
    end

    subgraph GODOT["GODOT (3D Environment)"]
        NAV["Physical Navigation"]
        REGION["Region Detection"]
    end

    KB -->|valid_actions| MASK
    ENC -->|state vector| DQN
    DQN -->|Q-values| MASK
    MASK -->|best action| REPLAY
    REPLAY -->|train| DQN
    MASK -->|action_id| DEC
    DEC -->|region name| NAV
    NAV -->|region_entered| JASON
    RM -->|reward| PYTHON
```

---

## 2. System Architecture

### 2.1 High-Level Architecture

```mermaid
flowchart LR
    subgraph Symbolic["Symbolic Layer (Jason)"]
        A1["Domain Knowledge"]
        A2["Reward Computation"]
        A3["Action Validation"]
    end

    subgraph Neural["Neural Layer (Python)"]
        B1["DQN Learning"]
        B2["Policy Storage"]
        B3["Action Selection"]
    end

    subgraph Physical["Physical Layer (Godot)"]
        C1["3D Rendering"]
        C2["Movement"]
        C3["Perception"]
    end

    Symbolic <-->|HTTP REST API| Neural
    Symbolic <-->|Signals| Physical
```

### 2.2 The Office Environment (11 Regions)

```mermaid
flowchart TB
    outside["outside (3)"]
    open_office["open_office (2)"]
    boss1["boss_office_1 (9)"]
    boss2["boss_office_2 (10)"]
    corridor["corridor (1)"]
    reception["reception (0)"]
    common["common (4)"]
    meeting["meeting_room (5)"]
    senior1["senior_office_1 (6)"]
    senior2["senior_office_2 (7)"]
    senior3["senior_office_3 (8)"]

    outside --- open_office
    open_office --- boss1
    open_office --- boss2
    open_office --- corridor
    corridor --- reception
    corridor --- common
    corridor --- meeting
    corridor --- senior1
    corridor --- senior2
    corridor --- senior3

    style corridor fill:#ffcc00
    style open_office fill:#ffcc00
```

### 2.3 Knowledge Base (KB) - Adjacency Facts

```mermaid
flowchart LR
    subgraph RCC8["Original RCC-8"]
        R1["ec(corridor, open_office)"]
        R2["po(corridor, door1)"]
        R3["po(door1, meeting_room)"]
    end

    subgraph DERIVED["Derived neighbor/2"]
        D1["neighbor(corridor, open_office)"]
        D2["neighbor(corridor, meeting_room)"]
    end

    R1 -->|"direct (ec)"| D1
    R2 -->|"through door"| D2
    R3 -->|"(po + po)"| D2
```

---

## 3. Encoding and Decoding

### 3.1 Two Types of Encoding

```mermaid
flowchart TB
    subgraph ID_ENC["ID Encoding (for Actions)"]
        direction LR
        I1["corridor"] -->|"region_id/2"| I2["1"]
        I3["meeting_room"] -->|"region_id/2"| I4["5"]
    end

    subgraph ONEHOT["One-Hot Encoding (for States)"]
        direction LR
        O1["corridor (ID=1)"] -->|"build_one_hot/5"| O2["[0,1,0,0,0,0,0,0,0,0,0]"]
        O3["meeting_room (ID=5)"] -->|"build_one_hot/5"| O4["[0,0,0,0,0,1,0,0,0,0,0]"]
    end
```

### 3.2 Goal-Conditioned State (22-dim)

```mermaid
flowchart LR
    subgraph INPUT["Inputs"]
        CURR["Current: corridor"]
        GOAL["Goal: meeting_room"]
    end

    subgraph ENCODE["One-Hot Encode"]
        E1["[0,1,0,0,0,0,0,0,0,0,0]"]
        E2["[0,0,0,0,0,1,0,0,0,0,0]"]
    end

    subgraph OUTPUT["Concatenate"]
        OUT["[0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0]<br/>22 dimensions"]
    end

    CURR --> E1
    GOAL --> E2
    E1 --> OUT
    E2 --> OUT
```

### 3.3 Encoding/Decoding Flow

```mermaid
sequenceDiagram
    participant Jason as Jason (Symbolic)
    participant Python as Python (Neural)

    Note over Jason: Agent at "corridor", goal "meeting_room"

    Jason->>Jason: Encode current: corridor → 1
    Jason->>Jason: Encode goal: meeting_room → 5
    Jason->>Jason: Build one-hot: [0,1,0,...] | [0,0,0,0,0,1,...]
    Jason->>Jason: Query KB: neighbor(corridor, X)?
    Jason->>Jason: Encode neighbors: [0,2,4,5,6,7,8]

    Jason->>Python: HTTP POST {state: [...22 floats...], valid_actions: [0,2,4,5,6,7,8]}

    Python->>Python: DQN computes Q-values
    Python->>Python: Apply mask
    Python->>Python: Select action: 2

    Python->>Jason: {action_id: 2}

    Jason->>Jason: Decode: 2 → "open_office"
    Jason->>Jason: Execute: hop_to(open_office)
```

---

## 4. Action Masking (KB Constraints)

### 4.1 The Masking Process

```mermaid
flowchart TB
    subgraph STEP1["Step 1: Jason computes valid actions"]
        S1A["Agent at: corridor"]
        S1B["KB Query: neighbor(corridor, X)?"]
        S1C["Results: reception, open_office,<br/>common, meeting_room,<br/>senior_office_1,2,3"]
        S1D["Encode: [0, 2, 4, 5, 6, 7, 8]"]

        S1A --> S1B --> S1C --> S1D
    end

    subgraph STEP2["Step 2: Python applies mask"]
        S2A["DQN outputs Q for ALL 11:<br/>[0.3, 0.8, 0.9, 0.1, 0.5, 0.7, 0.4, 0.3, 0.2, 0.95, 0.85]"]
        S2B["Build mask:<br/>[0, -∞, 0, -∞, 0, 0, 0, 0, 0, -∞, -∞]"]
        S2C["Q + mask:<br/>[0.3, -∞, 0.9, -∞, 0.5, 0.7, 0.4, 0.3, 0.2, -∞, -∞]"]
        S2D["argmax → 2 (open_office)"]

        S2A --> S2B --> S2C --> S2D
    end

    S1D -->|"valid_actions"| S2A

    style S2D fill:#90EE90
```

### 4.2 Masking Visualization

```mermaid
flowchart LR
    subgraph QVALS["Q-Values (from DQN)"]
        Q0["Q[0]=0.3"]
        Q1["Q[1]=0.8"]
        Q2["Q[2]=0.9"]
        Q3["Q[3]=0.1"]
        Q9["Q[9]=0.95"]
        Q10["Q[10]=0.85"]
    end

    subgraph VALID["Valid Actions"]
        V["[0, 2, 4, 5, 6, 7, 8]<br/>corridor(1) NOT included!<br/>boss offices NOT included!"]
    end

    subgraph MASK["After Masking"]
        M0["0.3 ✓"]
        M1["-∞ ✗"]
        M2["0.9 ✓ BEST"]
        M3["-∞ ✗"]
        M9["-∞ ✗"]
        M10["-∞ ✗"]
    end

    Q0 --> M0
    Q1 --> M1
    Q2 --> M2
    Q3 --> M3
    Q9 --> M9
    Q10 --> M10

    VALID --> MASK

    style M2 fill:#90EE90
    style M1 fill:#ff6666
    style M3 fill:#ff6666
    style M9 fill:#ff6666
    style M10 fill:#ff6666
```

### 4.3 Why Mask in Python?

```mermaid
flowchart TB
    subgraph BAD["❌ If mask in Jason only"]
        B1["Jason sends 1 action"]
        B2["RL has no choice"]
        B3["Cannot learn!"]
        B1 --> B2 --> B3
    end

    subgraph GOOD["✓ Current design"]
        G1["Jason sends list of valid options"]
        G2["RL chooses BEST among valid"]
        G3["RL learns optimal policy!"]
        G1 --> G2 --> G3
    end

    style BAD fill:#ffcccc
    style GOOD fill:#ccffcc
```

---

## 5. The Complete Flow

### 5.1 One RL Step (Sequence Diagram)

```mermaid
sequenceDiagram
    participant J as Jason
    participant P as Python DRL Service
    participant G as Godot

    Note over J: current_region(corridor)<br/>goal_region(meeting_room)

    J->>J: 1. Build state vector (22-dim one-hot)
    J->>J: 2. Get valid actions from KB [0,2,4,5,6,7,8]
    J->>J: 3. Compute reward (-1 for normal step)

    J->>P: HTTP POST /select_action<br/>{state, valid_actions, reward, done}

    P->>P: 4. Store transition in replay buffer
    P->>P: 5. Train DQN (sample batch)
    P->>P: 6. Compute Q-values for state
    P->>P: 7. Apply mask (invalid → -∞)
    P->>P: 8. ε-greedy selection

    P->>J: {action_id: 2, explanation: {q_values, ...}}

    J->>J: 9. Decode: 2 → open_office
    J->>G: 10. vesna.walk(open_office)
    G->>J: 11. region_entered(open_office)
    J->>J: 12. Update beliefs, continue loop
```

### 5.2 Episode Lifecycle

```mermaid
flowchart TB
    START([Start Episode]) --> RESET["Reset position<br/>vesna.teleport(X,Y,Z)"]
    RESET --> LOOP["RL Loop Step"]

    LOOP --> ENCODE["Encode state (22-dim)"]
    ENCODE --> VALID["Get valid actions from KB"]
    VALID --> SEND["Send to Python"]
    SEND --> RECEIVE["Receive action"]
    RECEIVE --> DECODE["Decode action"]
    DECODE --> EXECUTE["Execute movement"]
    EXECUTE --> REWARD["Compute reward"]

    REWARD --> GOAL{"Goal<br/>reached?"}
    GOAL -->|Yes| SUCCESS["reward = +100<br/>done = true"]
    GOAL -->|No| TIMEOUT{"Timeout?<br/>step >= 50"}

    TIMEOUT -->|Yes| FAIL["reward = -10<br/>done = true"]
    TIMEOUT -->|No| STEP["reward = -1<br/>done = false"]

    STEP --> LOOP
    SUCCESS --> NEXT["Next Episode"]
    FAIL --> NEXT
    NEXT --> RESET

    style SUCCESS fill:#90EE90
    style FAIL fill:#ff6666
```

### 5.3 Reward Machine Logic

```mermaid
flowchart TB
    STATE["Current State"]

    STATE --> CHECK1{"current_region = goal_region?"}
    CHECK1 -->|Yes| R1["Reward = +100<br/>Done = TRUE"]
    CHECK1 -->|No| CHECK2{"step >= max_steps?"}

    CHECK2 -->|Yes| R2["Reward = -10<br/>Done = TRUE"]
    CHECK2 -->|No| R3["Reward = -1<br/>Done = FALSE"]

    style R1 fill:#90EE90
    style R2 fill:#ff6666
    style R3 fill:#ffffcc
```

### 5.4 Training vs Inference

```mermaid
flowchart TB
    subgraph TRAIN["Training Mode (Exploration)"]
        T1["ε-greedy action selection"]
        T2["Store transitions"]
        T3["Update DQN weights"]
        T4["Decay ε over time"]
        T1 --> T2 --> T3 --> T4
    end

    subgraph INFER["Inference Mode (Exploitation)"]
        I1["Greedy action selection"]
        I2["No training"]
        I3["Log Q-values for explanation"]
        I1 --> I2 --> I3
    end

    TRAIN -->|"After sufficient training"| INFER
```

---

## 6. Code Reference

### 6.1 File Structure

```mermaid
flowchart TB
    subgraph REPO["Vesna_RL/"]
        subgraph MIND["mind/"]
            subgraph PY["python/"]
                P1["dqn_server.py<br/>Flask REST API"]
                P2["dqn_agent.py<br/>DQN + Replay"]
            end
            subgraph ASL["src/agt/"]
                A1["symbolic_execution_engine.asl<br/>Encoding, KB, Valid Actions"]
                A2["alice_rl.asl<br/>Reward Machine, Episode Loop"]
            end
        end
    end
```

### 6.2 Key Functions Map

```mermaid
flowchart LR
    subgraph JASON["Jason Functions"]
        J1["region_id/2<br/>ID encoding table"]
        J2["id_to_region/2<br/>ID decoding"]
        J3["neighbor/2<br/>KB adjacency"]
        J4["build_goal_state_vector/3<br/>One-hot encoding"]
        J5["get_valid_action_ids/2<br/>Query KB"]
        J6["rl_select_action/5<br/>Main RL wrapper"]
        J7["rl_loop/0<br/>Reward machine"]
    end

    subgraph PYTHON["Python Functions"]
        P1["_masked_argmax()<br/>Apply mask"]
        P2["step_with_explanation()<br/>Action + train"]
        P3["/select_action<br/>HTTP endpoint"]
    end

    J5 -->|valid_actions| P1
    J4 -->|state| P2
    J6 -->|HTTP| P3
    P3 -->|action_id| J2
```

### 6.3 Function Details

| Function | File:Line | Purpose |
|----------|-----------|---------|
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

### 7.1 Separation of Concerns

```mermaid
flowchart TB
    subgraph SYMBOLIC["Symbolic (Jason)"]
        S1["✓ Knows domain"]
        S2["✓ Computes rewards"]
        S3["✓ Ensures safety"]
        S4["✗ Does NOT learn"]
    end

    subgraph NEURAL["Neural (Python)"]
        N1["✗ Domain-agnostic"]
        N2["✗ No reward logic"]
        N3["✓ Uses mask for safety"]
        N4["✓ Learns policy"]
    end

    SYMBOLIC <-->|"Complementary"| NEURAL
```

### 7.2 Why Goal-Conditioned State?

```mermaid
flowchart TB
    subgraph WITHOUT["Without Goal in State"]
        W1["Need 11 policies"]
        W2["One per goal"]
        W3["No generalization"]
    end

    subgraph WITH["With Goal in State"]
        G1["State = [current | goal]"]
        G2["ONE policy"]
        G3["Works for ALL goals"]
        G4["Generalization!"]
    end

    style WITHOUT fill:#ffcccc
    style WITH fill:#ccffcc
```

### 7.3 Benefits of Action Masking

```mermaid
flowchart TB
    subgraph BENEFITS["Action Masking Benefits"]
        B1["Guaranteed safe exploration"]
        B2["Faster learning<br/>(smaller action space)"]
        B3["Never tries impossible actions"]
        B4["KB constraints always respected"]
    end
```

### 7.4 Why Reward Machine in Symbolic Layer?

```mermaid
flowchart LR
    subgraph SYMBOLIC_REWARD["Reward in Jason"]
        SR1["Explainable:<br/>'reward=+100 because<br/>goal_region(X) matched'"]
        SR2["Easy to modify"]
        SR3["Python stays domain-agnostic"]
    end

    subgraph NEURAL_REWARD["If reward in Python"]
        NR1["Black box"]
        NR2["Hard to explain"]
        NR3["Domain-specific code in RL"]
    end

    SYMBOLIC_REWARD -->|"Better"| CHOICE["Current Design ✓"]

    style SYMBOLIC_REWARD fill:#ccffcc
    style NEURAL_REWARD fill:#ffcccc
```

---

## Summary Architecture

```mermaid
flowchart TB
    subgraph NEURO_SYMBOLIC["NEURO-SYMBOLIC RL ARCHITECTURE"]
        subgraph SYM["SYMBOLIC (Jason)"]
            KB["KB Constraints<br/>neighbor(X,Y)"]
            RM["Reward Machine<br/>+100/-10/-1"]
            ENC["State Encoder<br/>[curr|goal] 22-dim"]
            DEC["Action Decoder<br/>2 → open_office"]
        end

        subgraph NEU["NEURAL (Python)"]
            DQN["DQN Network<br/>22→64→64→11"]
            MASK["Action Masking<br/>invalid = -∞"]
            REPLAY["Experience<br/>Replay Buffer"]
        end
    end

    KB -->|"valid_actions"| MASK
    ENC -->|"state"| DQN
    DQN -->|"Q-values"| MASK
    MASK -->|"train"| REPLAY
    REPLAY -->|"batch"| DQN
    MASK -->|"action_id"| DEC
    RM -->|"reward"| REPLAY

    style KB fill:#E8F5E9
    style RM fill:#E8F5E9
    style ENC fill:#E8F5E9
    style DEC fill:#E8F5E9
    style DQN fill:#E3F2FD
    style MASK fill:#E3F2FD
    style REPLAY fill:#E3F2FD
```

---

## Key Insight

> **Symbolic knowledge (KB, rewards) constrains and guides neural learning, while the neural network handles the complexity of finding optimal policies within those constraints.**

This neuro-symbolic approach combines:
- **Safety** from symbolic constraints
- **Flexibility** from neural learning
- **Explainability** from symbolic reward computation
