"""
gRPC Server for VEsNA RL Service — Parallel multi-agent training.

ONE shared DQNAgent handles all Java agents (alice_1..alice_8) simultaneously.
Each agent sends its own agent_id; the shared agent tracks per-agent episode
state internally while sharing one neural network and one replay buffer.

A single background thread runs train_batch() in a tight loop so SelectAction
calls always return immediately without blocking on training.

Run with: python dqn_server_grpc.py
"""

import logging
import os
import threading
import time
from concurrent import futures
from typing import Optional

import grpc
import numpy as np
import torch

import rl_service_pb2
import rl_service_pb2_grpc
from dqn_agent_grpc import DQNAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vesna-rl-grpc")

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHECKPOINT_DIR = os.environ.get("CHECKPOINT_DIR", os.path.join(_PROJECT_ROOT, "checkpoints"))
LOG_DIR = os.environ.get("LOG_DIR", os.path.join(_PROJECT_ROOT, "runs"))

# Configuration from environment variables
STATE_SIZE = int(os.environ.get("STATE_SIZE", "206"))
ACTION_SIZE = int(os.environ.get("ACTION_SIZE", "103"))
HIDDEN_SIZE = int(os.environ.get("HIDDEN_SIZE", "512"))
BUFFER_SIZE = int(os.environ.get("BUFFER_SIZE", "200000"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "512"))
EPSILON_DECAY = float(os.environ.get("EPSILON_DECAY", "0.99995"))
TARGET_UPDATE = int(os.environ.get("TARGET_UPDATE", "200"))
TRAIN_STEPS_PER_ACTION = int(os.environ.get("TRAIN_STEPS_PER_ACTION", "8"))

# Single shared agent — all Java agents connect to this one instance
shared_agent: Optional[DQNAgent] = None
_agent_lock = threading.Lock()
_trainer_started = False


def get_shared_agent() -> DQNAgent:
    """Return (or lazily create) the one shared DQNAgent and start the trainer."""
    global shared_agent, _trainer_started
    if shared_agent is None:
        with _agent_lock:
            if shared_agent is None:
                log_dir = os.path.join(LOG_DIR, "shared")
                logger.info(
                    "Creating shared DQNAgent — state=%d actions=%d hidden=%d "
                    "batch=%d buffer=%d eps_decay=%.6f target_update=%d",
                    STATE_SIZE, ACTION_SIZE, HIDDEN_SIZE,
                    BATCH_SIZE, BUFFER_SIZE, EPSILON_DECAY, TARGET_UPDATE,
                )
                shared_agent = DQNAgent(
                    state_size=STATE_SIZE,
                    action_size=ACTION_SIZE,
                    hidden_size=HIDDEN_SIZE,
                    buffer_size=BUFFER_SIZE,
                    batch_size=BATCH_SIZE,
                    epsilon_decay=EPSILON_DECAY,
                    target_update=TARGET_UPDATE,
                    log_dir=log_dir,
                )
                _start_background_trainer()
    return shared_agent


# ── Background training loop ─────────────────────────────────────────────────

def _log_gpu_util(train_count: int) -> None:
    if not torch.cuda.is_available():
        return
    try:
        alloc_mb = torch.cuda.memory_allocated() / 1024 ** 2
        reserved_mb = torch.cuda.memory_reserved() / 1024 ** 2
        logger.info(
            "[trainer] step=%d | GPU mem: alloc=%.0f MB reserved=%.0f MB",
            train_count, alloc_mb, reserved_mb,
        )
    except Exception:
        pass


def _background_trainer_loop() -> None:
    """
    Tight training loop — calls train_batch() as fast as possible once the
    replay buffer is sufficiently filled.  Yields briefly while the buffer is
    still warming up to avoid burning CPU at 100% for no benefit.
    """
    logger.info(
        "Background trainer started (TRAIN_STEPS_PER_ACTION=%d, "
        "will spin after buffer reaches %d)",
        TRAIN_STEPS_PER_ACTION, BATCH_SIZE,
    )
    train_count = 0
    while True:
        agent = shared_agent
        if agent is None:
            time.sleep(0.01)
            continue
        try:
            if len(agent.memory) < agent.batch_size:
                # Buffer not ready — yield briefly to avoid 100% CPU spin
                time.sleep(0.01)
                continue
            loss = agent.train_batch()
            if loss is not None:
                train_count += 1
                if train_count % 1000 == 0:
                    _log_gpu_util(train_count)
        except Exception:
            logger.exception("Unhandled error in background trainer")


def _start_background_trainer() -> None:
    global _trainer_started
    if _trainer_started:
        return
    _trainer_started = True
    t = threading.Thread(
        target=_background_trainer_loop, daemon=True, name="bg-trainer"
    )
    t.start()
    logger.info("Background trainer thread launched")


# ── gRPC servicer ────────────────────────────────────────────────────────────

class RLServicer(rl_service_pb2_grpc.RLServiceServicer):
    """gRPC service — one shared agent, N parallel Java callers."""

    def SelectAction(self, request, context):
        try:
            agent_id = request.agent_id
            state = np.array(request.state, dtype=np.float32)
            valid_actions = list(request.valid_actions)
            reward = float(request.reward)
            done = bool(request.done)

            if not valid_actions:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("valid_actions cannot be empty")
                return rl_service_pb2.ActionResponse()

            agent = get_shared_agent()

            # Never blocks on training — background thread handles that
            action_id, q_values, exploration = agent.step_with_explanation(
                state=state,
                valid_actions=valid_actions,
                reward=reward,
                done=done,
                agent_id=agent_id,
            )

            response = rl_service_pb2.ActionResponse(
                action_id=int(action_id),
                mode="training",
                exploration=exploration,
                epsilon=float(round(agent.epsilon, 4)),
                step_count=int(agent.steps),
            )

            if q_values is not None:
                if action_id < len(q_values):
                    response.selected_q = float(round(float(q_values[action_id]), 4))
                for a in valid_actions:
                    if a < len(q_values):
                        response.q_values[a] = float(round(float(q_values[a]), 4))

            if done:
                logger.info(
                    "[%s] DONE | ep=%d eps=%.4f buf=%d r=%.2f -> a=%d",
                    agent_id, agent.episode, agent.epsilon,
                    len(agent.memory), reward, action_id,
                )

            return response

        except Exception as exc:
            logger.exception("Error in SelectAction for agent_id=%s", request.agent_id)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return rl_service_pb2.ActionResponse()

    def ResetAgent(self, request, context):
        try:
            agent = get_shared_agent()
            agent.reset_episode(agent_id=request.agent_id)
            return rl_service_pb2.ResetResponse(success=True, message="Reset successful")
        except Exception as exc:
            return rl_service_pb2.ResetResponse(success=False, message=str(exc))

    def SaveModel(self, request, context):
        try:
            agent = get_shared_agent()
            os.makedirs(CHECKPOINT_DIR, exist_ok=True)
            path = request.checkpoint_path or os.path.join(CHECKPOINT_DIR, "shared_agent.pt")
            agent.save(path)
            logger.info("Model saved → %s", path)
            return rl_service_pb2.SaveResponse(success=True, saved_path=path, message="Saved")
        except Exception as exc:
            return rl_service_pb2.SaveResponse(success=False, message=str(exc))

    def LoadModel(self, request, context):
        try:
            agent = get_shared_agent()
            path = request.checkpoint_path or os.path.join(CHECKPOINT_DIR, "shared_agent.pt")
            if not os.path.exists(path):
                return rl_service_pb2.LoadResponse(
                    success=False, message=f"Checkpoint not found: {path}"
                )
            agent.load(path)
            logger.info("Model loaded ← %s", path)
            return rl_service_pb2.LoadResponse(
                success=True,
                message="Loaded",
                episode=int(agent.episode),
                step=int(agent.steps),
            )
        except Exception as exc:
            return rl_service_pb2.LoadResponse(success=False, message=str(exc))

    def GetStats(self, request, context):
        try:
            agent = get_shared_agent()
            stats = agent.get_stats()
            return rl_service_pb2.StatsResponse(
                episode=int(stats.get("episode", 0)),
                step=int(stats.get("steps", 0)),
                epsilon=float(stats.get("epsilon", 0.0)),
                buffer_size=int(stats.get("buffer_size", 0)),
            )
        except Exception:
            logger.exception("Error in GetStats")
            return rl_service_pb2.StatsResponse()


# ── Entry point ───────────────────────────────────────────────────────────────

def serve() -> None:
    port = int(os.environ.get("GRPC_PORT", "50051"))

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=16),
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
            ("grpc.so_reuseport", 0),
        ],
    )

    rl_service_pb2_grpc.add_RLServiceServicer_to_server(RLServicer(), server)
    server.add_insecure_port(f"[::]:{port}")

    logger.info("VEsNA gRPC RL Service starting on port %d", port)
    logger.info(
        "Config: state=%d actions=%d hidden=%d batch=%d buffer=%d "
        "eps_decay=%.6f target_update=%d",
        STATE_SIZE, ACTION_SIZE, HIDDEN_SIZE,
        BATCH_SIZE, BUFFER_SIZE, EPSILON_DECAY, TARGET_UPDATE,
    )
    logger.info("TensorBoard logs → %s", os.path.join(LOG_DIR, "shared"))
    logger.info("Checkpoints → %s", CHECKPOINT_DIR)
    logger.info("gRPC thread pool: 16 workers (supports 8 parallel agents)")

    server.start()

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down…")
        if shared_agent is not None:
            shared_agent.close()


if __name__ == "__main__":
    serve()
