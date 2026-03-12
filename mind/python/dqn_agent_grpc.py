"""
DQN Agent with Action Masking for VEsNA RL Service - gRPC version.

Supports parallel multi-agent training: multiple Java agents (alice_1..alice_8)
share ONE DQNAgent (same neural network + replay buffer) while each tracking
their own prev_state/prev_action/episode metrics independently.

Training runs in a background thread; gRPC calls never block on it.

Contract:
- No reward function, no goal detection here.
- Receives: o_t, valid_actions A(o_t), reward r_t and done flag for the
  PREVIOUS transition, returns next action a_t in A(o_t).
- Masking: invalid actions get -inf so argmax never selects them.
"""

import logging
import random
import threading
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

try:
    from torch.utils.tensorboard import SummaryWriter
    _HAS_TB = True
except ImportError:
    _HAS_TB = False

logger = logging.getLogger("vesna-rl-grpc")


class DQNetwork(nn.Module):
    def __init__(self, obs_size: int, action_size: int, hidden_size: int = 512):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, action_size),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


@dataclass(frozen=True)
class Transition:
    o: np.ndarray
    a: int
    r: float
    o2: np.ndarray
    valid_actions_o2: List[int]
    done: bool


class ReplayBuffer:
    """Thread-safe experience replay buffer."""

    def __init__(self, capacity: int = 200_000):
        self._buffer: deque = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def push(self, t: Transition) -> None:
        with self._lock:
            self._buffer.append(t)

    def sample(self, batch_size: int) -> List[Transition]:
        with self._lock:
            return random.sample(self._buffer, batch_size)

    def __len__(self) -> int:
        with self._lock:
            return len(self._buffer)


class DQNAgent:
    """
    Shared DQN agent for parallel multi-agent training.

    Multiple agents (identified by agent_id) share one network and one replay
    buffer.  Per-agent episode state (prev_state, prev_action, running reward
    and step count) is stored in self._contexts keyed by agent_id.

    Thread-safety:
      _lock        — guards shared counters (episode, steps, _train_step,
                     epsilon, rolling metric deques)
      _model_lock  — guards policy_net / target_net reads and writes so that
                     concurrent inference and background training don't race
      _ctx_lock    — guards structural changes to the _contexts dict
      memory       — ReplayBuffer has its own internal lock
    """

    def __init__(
        self,
        state_size: int,
        action_size: int,
        hidden_size: int = 512,
        learning_rate: float = 5e-4,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.01,
        epsilon_decay: float = 0.9999,
        batch_size: int = 512,
        buffer_size: int = 200_000,
        target_update: int = 200,
        grad_clip_norm: float = 10.0,
        device: Optional[str] = None,
        seed: Optional[int] = None,
        log_dir: Optional[str] = None,
    ):
        self.state_size = state_size
        self.action_size = action_size
        self.gamma = gamma
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update = target_update
        self.grad_clip_norm = grad_clip_norm

        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
            torch.manual_seed(seed)

        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        logger.info("DQNAgent using device: %s", self.device)

        if self.device.type == "cuda":
            torch.set_float32_matmul_precision("high")
            logger.info("TF32 matmul precision enabled")

        self.policy_net = DQNetwork(state_size, action_size, hidden_size).to(self.device)
        self.target_net = DQNetwork(state_size, action_size, hidden_size).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        if hasattr(torch, "compile"):
            try:
                # "default" mode is thread-safe; "reduce-overhead" uses CUDA graphs
                # which segfault under multi-threaded inference + training
                self.policy_net = torch.compile(self.policy_net, mode="default")
                logger.info("torch.compile(policy_net, mode='default') succeeded")
            except Exception as exc:
                logger.warning("torch.compile(policy_net) failed: %s", exc)
            try:
                self.target_net = torch.compile(self.target_net, mode="default")
                logger.info("torch.compile(target_net, mode='default') succeeded")
            except Exception as exc:
                logger.warning("torch.compile(target_net) failed: %s", exc)

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=learning_rate)
        self.loss_fn = nn.SmoothL1Loss()

        self.memory = ReplayBuffer(buffer_size)

        # Shared counters — all protected by _lock
        self._lock = threading.Lock()
        self.episode: int = 0
        self.steps: int = 0
        self._train_step: int = 0
        self.epsilon: float = epsilon_start
        self._recent_rewards: deque = deque(maxlen=100)
        self._recent_steps: deque = deque(maxlen=100)
        self._recent_successes: deque = deque(maxlen=100)

        # Model read/write guard (inference vs. background training)
        self._model_lock = threading.Lock()

        # Per-agent episode contexts
        self._contexts: Dict[str, dict] = {}
        self._ctx_lock = threading.Lock()

        # Pre-allocated Q-mask reused exclusively by the single trainer thread
        self._q_mask = torch.full(
            (batch_size, action_size), float("-inf"), device=self.device
        )

        self._writer = None
        if log_dir and _HAS_TB:
            self._writer = SummaryWriter(log_dir=log_dir)
            logger.info("TensorBoard logging → %s", log_dir)
        elif log_dir and not _HAS_TB:
            logger.warning("tensorboard not installed — pip install tensorboard")

    # ── Per-agent context ────────────────────────────────────────────────────

    def _get_or_create_context(self, agent_id: str) -> dict:
        with self._ctx_lock:
            if agent_id not in self._contexts:
                self._contexts[agent_id] = {
                    "prev_state": None,
                    "prev_action": None,
                    "episode_reward": 0.0,
                    "episode_steps": 0,
                }
            return self._contexts[agent_id]

    def reset_episode(self, agent_id: Optional[str] = None) -> None:
        """Reset per-agent episode state (call at episode start or after done)."""
        if agent_id is None:
            return
        ctx = self._get_or_create_context(agent_id)
        ctx["prev_state"] = None
        ctx["prev_action"] = None
        ctx["episode_reward"] = 0.0
        ctx["episode_steps"] = 0

    # ── Action selection (inference) ───────────────────────────────────────────

    def _masked_argmax(self, q_values: torch.Tensor, valid_actions: List[int]) -> int:
        mask = torch.full((self.action_size,), float("-inf"), device=q_values.device)
        mask[valid_actions] = 0.0
        return int((q_values + mask).argmax().item())

    def select_action(
        self,
        state: np.ndarray,
        valid_actions: List[int],
        reward: float,
        done: bool,
        agent_id: str = "default",
    ) -> int:
        """Select action for a specific agent (thread-safe)."""
        action, _, _ = self.step_with_explanation(
            state, valid_actions, reward, done, agent_id
        )
        return action

    def step_with_explanation(
        self,
        state: np.ndarray,
        valid_actions: List[int],
        reward: float,
        done: bool,
        agent_id: str = "default",
    ) -> Tuple[int, Optional[np.ndarray], str]:
        """
        Process transition and return action with explanation.
        Thread-safe for multi-agent use.
        """
        if not valid_actions:
            raise ValueError("valid_actions cannot be empty")

        ctx = self._get_or_create_context(agent_id)

        # Store transition from PREVIOUS step (if any)
        if ctx["prev_state"] is not None and ctx["prev_action"] is not None:
            ctx["episode_reward"] += reward
            ctx["episode_steps"] += 1
            self.memory.push(
                Transition(
                    o=ctx["prev_state"],
                    a=int(ctx["prev_action"]),
                    r=float(reward),
                    o2=state.copy(),
                    valid_actions_o2=list(valid_actions),
                    done=bool(done),
                )
            )

        # Episode end handling
        if done:
            with self._lock:
                self._recent_rewards.append(ctx["episode_reward"])
                self._recent_steps.append(ctx["episode_steps"])
                self._recent_successes.append(1.0 if ctx["episode_reward"] > 0 else 0.0)

                ep_before = self.episode
                self.episode += 1
                ep_after = self.episode

                self.epsilon = max(
                    self.epsilon_end, self.epsilon * self.epsilon_decay
                )

                if ep_after % self.target_update == 0:
                    with self._model_lock:
                        self.target_net.load_state_dict(self.policy_net.state_dict())
                    logger.info("Target network updated at episode %d", ep_after)

                # TensorBoard logging
                if self._writer:
                    self._writer.add_scalar(
                        "episode/reward", ctx["episode_reward"], ep_after
                    )
                    self._writer.add_scalar("episode/epsilon", self.epsilon, ep_after)
                    if len(self._recent_rewards) >= 10:
                        self._writer.add_scalar(
                            "rolling/avg_reward",
                            sum(self._recent_rewards) / len(self._recent_rewards),
                            ep_after,
                        )

            self.reset_episode(agent_id)
            return int(valid_actions[0]), None, "done"

        # Epsilon-greedy action selection
        with self._lock:
            current_epsilon = self.epsilon

        if random.random() < current_epsilon:
            action = int(random.choice(valid_actions))
            exploration = "epsilon_random"
            q_values = None
        else:
            with self._model_lock:
                o = torch.tensor(
                    state, dtype=torch.float32, device=self.device
                ).unsqueeze(0)
                q = self.policy_net(o).squeeze(0)
                q_values = q.detach().cpu().numpy()
                action = self._masked_argmax(q, valid_actions)
            exploration = "greedy"

        # Update context for next step
        ctx["prev_state"] = state.copy()
        ctx["prev_action"] = int(action)

        with self._lock:
            self.steps += 1

        return int(action), q_values, exploration

    # ── Training ───────────────────────────────────────────────────────────────

    def train_batch(self) -> Optional[float]:
        """Run one gradient update. Returns loss or None if buffer too small."""
        if len(self.memory) < self.batch_size:
            return None

        batch = self.memory.sample(self.batch_size)

        states = torch.tensor(
            np.stack([t.o for t in batch]), dtype=torch.float32, device=self.device
        )
        actions = torch.tensor(
            [t.a for t in batch], dtype=torch.long, device=self.device
        )
        rewards = torch.tensor(
            [t.r for t in batch], dtype=torch.float32, device=self.device
        )
        next_states = torch.tensor(
            np.stack([t.o2 for t in batch]), dtype=torch.float32, device=self.device
        )
        dones = torch.tensor(
            [t.done for t in batch], dtype=torch.float32, device=self.device
        )

        # Q(s, a)
        with self._model_lock:
            q_all = self.policy_net(states)
        q_sa = q_all.gather(1, actions.unsqueeze(1)).squeeze(1)

        # Target: r + γ * max_{a'∈valid} Q^-(s', a')
        with torch.no_grad():
            with self._model_lock:
                next_q_all = self.target_net(next_states)

            # Reuse pre-allocated mask
            self._q_mask.fill_(float("-inf"))

            max_next_q = torch.zeros(self.batch_size, device=self.device)
            for i, t in enumerate(batch):
                if t.valid_actions_o2:
                    self._q_mask[i, t.valid_actions_o2] = 0.0
                    max_next_q[i] = (next_q_all[i] + self._q_mask[i]).max()

            target = rewards + self.gamma * max_next_q * (1.0 - dones)

        loss = self.loss_fn(q_sa, target)

        with self._model_lock:
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                self.policy_net.parameters(), self.grad_clip_norm
            )
            self.optimizer.step()

        with self._lock:
            self._train_step += 1
            step = self._train_step

        # TensorBoard logging
        if self._writer and step % 50 == 0:
            self._writer.add_scalar("training/loss", loss.item(), step)
            self._writer.add_scalar("training/avg_q", q_sa.mean().item(), step)

        return loss.item()

    # ── Utility methods ────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "episode": int(self.episode),
                "epsilon": float(round(self.epsilon, 4)),
                "steps": int(self.steps),
                "buffer_size": int(len(self.memory)),
            }

    def save(self, path: str) -> None:
        with self._lock:
            ep = self.episode
            eps = self.epsilon
            steps = self.steps
            ts = self._train_step
        with self._model_lock:
            torch.save(
                {
                    "policy_net": self.policy_net.state_dict(),
                    "target_net": self.target_net.state_dict(),
                    "optimizer": self.optimizer.state_dict(),
                    "episode": ep,
                    "epsilon": eps,
                    "steps": steps,
                    "train_step": ts,
                },
                path,
            )

    def load(self, path: str) -> None:
        ckpt = torch.load(path, map_location=self.device)
        with self._model_lock:
            self.policy_net.load_state_dict(ckpt["policy_net"])
            self.target_net.load_state_dict(ckpt["target_net"])
            self.optimizer.load_state_dict(ckpt["optimizer"])
        with self._lock:
            self.episode = int(ckpt.get("episode", 0))
            self.epsilon = float(ckpt.get("epsilon", 1.0))
            self.steps = int(ckpt.get("steps", 0))
            self._train_step = int(ckpt.get("train_step", 0))

    def close(self) -> None:
        if self._writer:
            self._writer.flush()
            self._writer.close()
            self._writer = None
