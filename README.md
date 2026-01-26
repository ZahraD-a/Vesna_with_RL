# NOVAE: Neuro-symbOlic agents that Verify, leArn and Explain

A framework providing **Reinforcement Learning as a Service** for BDI (Belief-Desire-Intention) agents, integrating symbolic spatial reasoning with neural learning while preserving explainability and verification properties.

## Overview

NOVAE addresses a fundamental challenge in autonomous agent design: enabling adaptive behavior while preserving explainability and verifiability. BDI agents offer transparent goal-directed reasoning through symbolic deliberation but fail when encountering situations beyond their predefined plan libraries. Reinforcement Learning enables adaptation to novel situations but provides black-box solutions with limited interpretability.

**Our approach**: Symbolic spatial rules (RCC-8) constrain RL exploration, while the BDI agent computes rewards from symbolic goal specifications. This enables:
- Verification of learned policies
- Knowledge transfer across agents without retraining
- Explainable decision-making grounded in symbolic reasoning

## Architecture

NOVAE implements a **three-layer architecture** that cleanly separates symbolic reasoning from neural learning:

```
┌─────────────────────────────────────────────────────────────────┐
│                     SYMBOLIC LAYER (Jason)                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   RCC-8 Spatial │  │  BDI Goal/Belief│  │     Reward      │  │
│  │   Knowledge     │  │   Evaluation    │  │   Computation   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                  NEURO-SYMBOLIC INTERFACE                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  State Encoding │  │  Action Masking │  │   Bidirectional │  │
│  │   (One-Hot)     │  │   (RCC-8)       │  │   Translation   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                    NEURAL LAYER (Python/PyTorch)                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   DQN Network   │  │ Experience      │  │  Target Network │  │
│  │   (64-64-11)    │  │ Replay Buffer   │  │  Updates        │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Components

1. **Symbolic Layer** (Jason/JaCaMo)
   - Maintains spatial knowledge as qualitative RCC-8 relations
   - Three relations used: `ntpp` (containment), `po` (door connections), `ec` (direct adjacency)
   - Computes reward signals from BDI goal specifications
   - Validates candidate actions against domain constraints

2. **Neural Layer** (Python REST Service)
   - Deep Q-Network learning with experience replay and target networks
   - Can be queried by multiple agents concurrently
   - Enables policy sharing across agent instances

3. **Neuro-Symbolic Interface**
   - State encoding: One-hot vectors mapping regions to neural input
   - Action masking: Only adjacent regions (derived from RCC-8) are valid actions
   - Bidirectional translation between symbolic region names and neural representations

## Project Structure

```
Vesna_RL/
├── mind/                          # Agent & RL System
│   ├── python/                    # RL Service (Python)
│   │   ├── dqn_server.py         # Flask REST API server
│   │   ├── dqn_agent.py          # DQN model + replay buffer
│   │   └── requirements.txt      # Python dependencies
│   ├── src/agt/                   # Agent files (AgentSpeak)
│   │   ├── alice_rl.asl          # RL training agent
│   │   ├── vesna.asl             # Navigation rules
│   │   └── symbolic_execution_engine.asl  # RL orchestration
│   ├── playgrounds/office/        # Environment topology
│   │   └── office_map.asl        # RCC-8 spatial relations
│   ├── vesna.jcm                  # Multi-agent config
│   ├── vesna_rl.jcm              # RL training config
│   └── build.gradle              # JaCaMo build
├── env/office/                    # Godot 3D Environment
├── docs/                          # Documentation
│   ├── RL_INTEGRATION_PROPOSAL.md
│   └── 1.0_DAY_1/PLAN.md
├── start_all.sh                   # System startup script
└── stop_all.sh                    # System shutdown script
```

## Installation

### Prerequisites

- **Java 17+** (OpenJDK recommended)
- **Python 3.10+**
- **Godot 4.x** (included as executable)

### Setup

1. **Python RL Service**
   ```bash
   cd mind/python
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **JaCaMo** (automatic via Gradle wrapper)
   ```bash
   cd mind
   ./gradlew build
   ```

## Running the System

### Quick Start
```bash
./start_all.sh
```

This starts all three components:
1. Godot (3D environment)
2. Python RL Service (port 5000)
3. JaCaMo (BDI agents)

### Manual Startup

**Terminal 1 - Godot:**
```bash
./Godot_v4.5.1-stable_linux.x86_64 --path env/office
```

**Terminal 2 - RL Service:**
```bash
cd mind/python
source .venv/bin/activate
python dqn_server.py
```

**Terminal 3 - JaCaMo:**
```bash
cd mind
./gradlew runRL    # RL training mode
```

### Stopping
```bash
./stop_all.sh
```

## Current Scenario: Office Navigation

The agent (Alice) learns to navigate a 3D office environment with 11 regions:

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
   ┌──┴┐┌──┴┐┌──┴┐┌──┴──┐ │ ┌──┴──┐ │    │    │
   │s1 ││s2 ││s3 ││meet │ │ │comm │ │    │    │
   └───┘└───┘└───┘└─────┘ │ └─────┘ │    │    │
                          │         │    │    │
                       ┌──┴───┐     │    │    │
                       │recep │─────┘    │    │
                       └──────┘          │    │
```

**Training Task**: Navigate from `senior_office_2` to `common` room (coffee machine).

**Optimal Path**: senior_office_2 → corridor → common (2 steps)

### Reward Structure
- **+100**: Goal reached
- **-1**: Per step (encourages efficiency)
- **-10**: Timeout (50 steps)

## Verification & Explainability

NOVAE provides verification through three mechanisms:

1. **Structural Verification**: Action masking guarantees spatially valid transitions only
2. **Semantic Verification**: Rewards from BDI belief evaluation eliminate reward hacking
3. **Policy Verification**: One-hot encoding enables direct mapping for constraint checking

**Explainability** emerges naturally:
- States map trivially to region names
- Action selections justified by spatial adjacency
- Rewards explained through symbolic goal evaluation

## API Endpoints

The RL service exposes:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/select_action` | POST | Action selection + training |
| `/reset` | POST | Reset episode for agent |
| `/health` | GET | Health check + stats |
| `/stats/<agent_id>` | GET | Agent-specific statistics |
| `/save/<agent_id>` | POST | Save model checkpoint |
| `/load/<agent_id>` | POST | Load model checkpoint |

## Research Context

This implementation is part of doctoral research on neuro-symbolic agent architectures. Key research questions:

1. Can symbolic spatial constraints effectively guide RL exploration?
2. Can BDI-computed rewards enable verifiable learning?
3. How can learned policies be transferred across agent instances?

### Related Work

- **BDI Agents**: Bratman (1987), Rao & Georgeff (1991)
- **Deep Q-Networks**: Mnih et al. (2015)
- **RCC-8 Calculus**: Randell et al. (1992)
- **VEsNA Framework**: Gatti & Mascardi (2023)

## Future Extensions

- Multi-agent coordination (MARL)
- Formal verification integration
- Richer symbolic reward functions
- Policy transfer across environments
- Online Inductive Logic Programming

## References

- Bordini, R.H., Hübner, J.F., Wooldridge, M. (2007). *Programming Multi-Agent Systems in AgentSpeak using Jason*
- Mnih, V., et al. (2015). Human-level control through deep reinforcement learning. *Nature*
- Randell, D.A., Cui, Z., Cohn, A.G. (1992). A spatial logic based on regions and connection. *KR*

## License

This project is part of academic research at the University of Genoa.

## Contact

For questions about this research, please contact the NOVAE team at the University of Genoa.
