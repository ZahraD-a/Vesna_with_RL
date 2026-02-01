"""
DQN REST API Server for VEsNA RL Service.

Contract:
- Jason computes reward and done (reward machine stays in Jason).
- Python receives observation o_t (22-dim: current_one_hot | goal_one_hot),
  valid actions, and the reward/done from the PREVIOUS transition, then
  returns the next action.

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
from typing import Any, Dict, List

import numpy as np
from flask import Flask, jsonify, request

from dqn_agent import DQNAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vesna-rl-service")

app = Flask(__name__)

CHECKPOINT_DIR = os.environ.get("CHECKPOINT_DIR", "checkpoints")

agents: Dict[str, DQNAgent] = {}


def get_or_create_agent(agent_id: str) -> DQNAgent:
    if agent_id not in agents:
        logger.info("Creating new agent: %s", agent_id)
        agents[agent_id] = DQNAgent(state_size=22, action_size=11)
    return agents[agent_id]


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
      "state": [..22 floats..],      # o_t, [current_one_hot | goal_one_hot]
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
            return _bad_request("state must be a list of length 22")

        state = np.asarray(state_raw, dtype=np.float32)
        if state.shape != (22,):
            return _bad_request("state must have exactly 22 elements")

        agent = get_or_create_agent(agent_id)
        valid_actions = _parse_valid_actions(data.get("valid_actions", None), agent.action_size)

        reward = float(data.get("reward", 0.0))
        done = bool(data.get("done", False))

        # Get action AND Q-values for explainability
        action_id, q_values, exploration = agent.step_with_explanation(
            state=state,
            valid_actions=valid_actions,
            reward=reward,
            done=done,
        )

        mode = "EVAL" if agent.eval_mode else f"eps={agent.epsilon:.3f}"
        logger.info(
            "[%s] ep=%d %s o=%d valid=%s r=%.2f done=%s -> a=%d",
            agent_id,
            agent.episode,
            mode,
            int(state[:11].argmax()),
            valid_actions,
            reward,
            done,
            action_id,
        )

        # Build explainable response
        response = {
            "action_id": int(action_id),
            "explanation": {
                "q_values": {str(a): float(round(q_values[a], 4)) for a in valid_actions} if q_values is not None else {},
                "selected_q": float(round(q_values[action_id], 4)) if q_values is not None else None,
                "exploration": exploration,  # "greedy" or "epsilon_random"
                "mode": "inference" if agent.eval_mode else "training",
                "epsilon": float(round(agent.epsilon, 4)) if not agent.eval_mode else 0.0,
            }
        }
        return jsonify(response)

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
        "agents": {aid: agent.get_stats() for aid, agent in agents.items()},
    })


@app.route("/stats/<agent_id>", methods=["GET"])
def stats(agent_id: str):
    if agent_id not in agents:
        return jsonify({"error": f"Agent {agent_id} not found"}), 404
    return jsonify(agents[agent_id].get_stats())


@app.route("/save/<agent_id>", methods=["POST"])
def save(agent_id: str):
    if agent_id not in agents:
        return jsonify({"error": f"Agent {agent_id} not found"}), 404

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    path = os.path.join(CHECKPOINT_DIR, f"{agent_id}.pt")
    agents[agent_id].save(path)
    return jsonify({"status": "ok", "path": path})


@app.route("/load/<agent_id>", methods=["POST"])
def load(agent_id: str):
    path = os.path.join(CHECKPOINT_DIR, f"{agent_id}.pt")
    if not os.path.exists(path):
        return jsonify({"error": f"Checkpoint not found: {path}"}), 404

    agent = get_or_create_agent(agent_id)
    agent.load(path)

    # Enable eval mode if requested (inference only, no training)
    data = request.get_json(silent=True) or {}
    if data.get("eval", False):
        agent.set_eval_mode(True)
        logger.info("[%s] Eval mode ENABLED (inference only)", agent_id)

    return jsonify({"status": "ok", "stats": agent.get_stats()})


def main():
    port = int(os.environ.get("PORT", "5000"))
    logger.info("Starting VEsNA RL Service on port %d", port)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
