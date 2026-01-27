"""
DQN REST API Server for VEsNA RL Service.

Contract:
- Jason computes reward and done (reward machine stays in Jason).
- Python receives observation o_t (here: 11-dim one-hot), valid actions, and
  the reward/done from the PREVIOUS transition, then returns the next action.

Endpoints:
  POST /select_action  - action selection + (optional) training on previous transition
  POST /reset          - reset episode memory for an agent
  GET  /health         - health + stats
  GET  /stats/<agent_id>
  POST /save/<agent_id>
  POST /load/<agent_id>
"""

import logging
import os
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from flask import Flask, jsonify, request

from dqn_agent import DQNAgent

# Checkpoints directory at project root (Vesna_RL/checkpoints)
CHECKPOINT_DIR = Path(__file__).parent.parent.parent / "checkpoints"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vesna-rl-service")

app = Flask(__name__)

agents: Dict[str, DQNAgent] = {}


# ============================================================
#              EPISODE METRICS TRACKER
# ============================================================
@dataclass
class EpisodeMetrics:
    """Tracks metrics for a single agent across episodes."""
    total_episodes: int = 0
    total_successes: int = 0  # Goal reached (reward >= 90)
    total_timeouts: int = 0   # Timeout (reward < 0 on done)

    # Current episode tracking
    current_steps: int = 0
    current_reward: float = 0.0

    # Rolling window for averages (last 100 episodes)
    recent_rewards: deque = field(default_factory=lambda: deque(maxlen=100))
    recent_steps: deque = field(default_factory=lambda: deque(maxlen=100))
    recent_successes: deque = field(default_factory=lambda: deque(maxlen=100))

    def record_step(self, reward: float):
        """Record a step within the current episode."""
        self.current_steps += 1
        self.current_reward += reward

    def end_episode(self, final_reward: float, success: bool):
        """End the current episode and record metrics."""
        self.current_reward += final_reward
        self.total_episodes += 1

        if success:
            self.total_successes += 1
            self.recent_successes.append(1)
        else:
            self.total_timeouts += 1
            self.recent_successes.append(0)

        self.recent_rewards.append(self.current_reward)
        self.recent_steps.append(self.current_steps)

        # Reset for next episode
        self.current_steps = 0
        self.current_reward = 0.0

    def get_summary(self) -> Dict[str, Any]:
        """Get current metrics summary."""
        avg_reward = np.mean(self.recent_rewards) if self.recent_rewards else 0.0
        avg_steps = np.mean(self.recent_steps) if self.recent_steps else 0.0
        success_rate = np.mean(self.recent_successes) * 100 if self.recent_successes else 0.0

        return {
            "total_episodes": self.total_episodes,
            "total_successes": self.total_successes,
            "total_timeouts": self.total_timeouts,
            "success_rate_all": (self.total_successes / max(1, self.total_episodes)) * 100,
            "avg_reward_100": avg_reward,
            "avg_steps_100": avg_steps,
            "success_rate_100": success_rate,
        }


# Region ID to name mapping for readable logs
REGION_NAMES = {
    0: "reception", 1: "corridor", 2: "open_office", 3: "outside",
    4: "common", 5: "meeting_room", 6: "senior_office_1", 7: "senior_office_2",
    8: "senior_office_3", 9: "boss_office_1", 10: "boss_office_2"
}

metrics: Dict[str, EpisodeMetrics] = {}


def get_or_create_agent(agent_id: str) -> DQNAgent:
    if agent_id not in agents:
        logger.info("Creating new agent: %s", agent_id)
        agents[agent_id] = DQNAgent(state_size=22, action_size=11)  # Goal-conditioned
        metrics[agent_id] = EpisodeMetrics()
    return agents[agent_id]


def get_metrics(agent_id: str) -> EpisodeMetrics:
    if agent_id not in metrics:
        metrics[agent_id] = EpisodeMetrics()
    return metrics[agent_id]


def _bad_request(msg: str, code: int = 400):
    return jsonify({"error": msg}), code


def _parse_valid_actions(raw: Any, action_size: int) -> List[int]:
    if not isinstance(raw, list) or len(raw) == 0:
        raise ValueError("valid_actions must be a non-empty list")

    out: List[int] = []
    for x in raw:
        if not isinstance(x, int):
            raise ValueError("valid_actions must contain integers")
        if x < 0 or x >= action_size:
            raise ValueError(f"valid_actions id out of range: {x}")
        out.append(x)

    # Dedup for safety, keep order stable
    seen = set()
    deduped = []
    for a in out:
        if a not in seen:
            seen.add(a)
            deduped.append(a)
    return deduped


@app.route("/select_action", methods=["POST"])
def select_action():
    """
    Request JSON:
    {
      "agent_id": "alice",
      "state": [..11 floats..],      # o_t, one-hot region
      "valid_actions": [1,4, ...],   # A(o_t), neighbors only
      "reward": -1.0,               # reward from previous transition (arrived at this state)
      "done": false                 # whether previous transition ended episode
    }

    Response JSON:
    { "action_id": 1 }
    """
    if not request.is_json:
        return _bad_request("Content-Type must be application/json", 415)

    try:
        data = request.get_json(silent=False)  # raises on invalid JSON :contentReference[oaicite:4]{index=4}
        if not isinstance(data, dict):
            return _bad_request("JSON body must be an object")

        agent_id = str(data.get("agent_id", "default"))

        state_raw = data.get("state", None)
        if not isinstance(state_raw, list):
            return _bad_request("state must be a list of length 22 (current + goal)")

        state = np.asarray(state_raw, dtype=np.float32)
        if state.shape != (22,):
            return _bad_request("state must have exactly 22 elements (11 current + 11 goal)")

        agent = get_or_create_agent(agent_id)
        valid_actions = _parse_valid_actions(data.get("valid_actions", None), agent.action_size)

        reward = float(data.get("reward", 0.0))
        done = bool(data.get("done", False))

        action_id = agent.step(
            state=state,
            valid_actions=valid_actions,
            reward=reward,
            done=done,
        )

        # Extract current (first 11) and goal (last 11) from state
        current_region = int(state[:11].argmax())
        goal_region = int(state[11:].argmax())
        current_name = REGION_NAMES.get(current_region, str(current_region))
        goal_name = REGION_NAMES.get(goal_region, str(goal_region))
        action_name = REGION_NAMES.get(action_id, str(action_id))

        # Track metrics
        m = get_metrics(agent_id)

        if done:
            # Episode ended - determine success or timeout
            success = reward >= 90  # Goal reached gives +100, timeout gives -10
            m.end_episode(reward, success)

            # Log episode summary
            summary = m.get_summary()
            status = "SUCCESS" if success else "TIMEOUT"
            logger.info(
                "========== [%s] EPISODE %d %s ==========",
                agent_id.upper(), m.total_episodes, status
            )
            logger.info(
                "  Steps: %d | Reward: %.1f | Goal: %s",
                int(summary["avg_steps_100"]) if m.recent_steps else m.current_steps,
                m.recent_rewards[-1] if m.recent_rewards else 0,
                goal_name
            )
            logger.info(
                "  Last 100: SuccessRate=%.1f%% AvgReward=%.1f AvgSteps=%.1f",
                summary["success_rate_100"],
                summary["avg_reward_100"],
                summary["avg_steps_100"]
            )
            logger.info(
                "  Overall:  SuccessRate=%.1f%% (%d/%d) Epsilon=%.3f",
                summary["success_rate_all"],
                summary["total_successes"],
                summary["total_episodes"],
                agent.epsilon
            )
        else:
            # Normal step
            m.record_step(reward)
            logger.debug(
                "[%s] step cur=%s goal=%s r=%.1f -> %s",
                agent_id, current_name, goal_name, reward, action_name
            )

        return jsonify({"action_id": int(action_id)})

    except Exception as e:
        logger.exception("Error in /select_action")
        return jsonify({"error": str(e)}), 400


@app.route("/reset", methods=["POST"])
def reset():
    if not request.is_json:
        return _bad_request("Content-Type must be application/json", 415)
    try:
        data = request.get_json(silent=False)
        agent_id = str((data or {}).get("agent_id", "default"))
        agent = get_or_create_agent(agent_id)
        agent.reset_episode()
        logger.info("[%s] Reset episode memory", agent_id)
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.exception("Error in /reset")
        return jsonify({"error": str(e)}), 400


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "agents": {
            aid: {
                **agent.get_stats(),
                "metrics": metrics[aid].get_summary() if aid in metrics else {}
            }
            for aid, agent in agents.items()
        },
    })


@app.route("/stats/<agent_id>", methods=["GET"])
def stats(agent_id: str):
    if agent_id not in agents:
        return jsonify({"error": f"Agent {agent_id} not found"}), 404
    return jsonify({
        **agents[agent_id].get_stats(),
        "metrics": metrics[agent_id].get_summary() if agent_id in metrics else {}
    })


@app.route("/save/<agent_id>", methods=["POST"])
def save(agent_id: str):
    if agent_id not in agents:
        return jsonify({"error": f"Agent {agent_id} not found"}), 404

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    path = CHECKPOINT_DIR / f"{agent_id}.pt"
    agents[agent_id].save(str(path))
    return jsonify({"status": "ok", "path": str(path)})


@app.route("/load/<agent_id>", methods=["POST"])
def load(agent_id: str):
    path = CHECKPOINT_DIR / f"{agent_id}.pt"
    if not path.exists():
        return jsonify({"error": f"Checkpoint not found: {path}"}), 404

    agent = get_or_create_agent(agent_id)
    agent.load(str(path))
    return jsonify({"status": "ok", "stats": agent.get_stats()})


def main():
    port = int(os.environ.get("PORT", "5000"))
    logger.info("Starting VEsNA RL Service on port %d", port)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
