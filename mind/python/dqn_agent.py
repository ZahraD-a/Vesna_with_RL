"""
DQN Agent with Action Masking for VEsNA RL Service.

Important contract:
- This module has NO reward function and NO goal detection.
- It receives:
    o_t (observation vector), valid_actions A(o_t),
    reward r_t and done flag from the PREVIOUS transition.
- It returns the next action a_t in A(o_t).

Masking: invalid actions get -inf so argmax never selects them. :contentReference[oaicite:7]{index=7}
"""

import gc
import logging
import random
from collections import deque
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

try:
    from torch.utils.tensorboard import SummaryWriter
    _HAS_TB = True
except ImportError:
    _HAS_TB = False

logger = logging.getLogger("vesna-rl-service")


class DQNetwork(nn.Module):
    def __init__(self, obs_size: int, action_size: int, hidden_size: int = 64):
        super().__init__()
        self.fc1 = nn.Linear(obs_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, action_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)


@dataclass(frozen=True)
class Transition:
    o: np.ndarray
    a: int
    r: float
    o2: np.ndarray
    valid_actions_o2: List[int]
    done: bool


class ReplayBuffer:
    def __init__(self, capacity: int = 10_000):
        self.buffer = deque(maxlen=capacity)

    def push(self, t: Transition) -> None:
        self.buffer.append(t)

    def sample(self, batch_size: int) -> List[Transition]:
        return random.sample(self.buffer, batch_size)

    def __len__(self) -> int:
        return len(self.buffer)


class DQNAgent:
    def __init__(
        self,
        state_size: int = 11,
        action_size: int = 11,
        hidden_size: int = 64,
        learning_rate: float = 5e-4,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.01,
        epsilon_decay: float = 0.9999,  # Slower decay for long training
        batch_size: int = 64,
        buffer_size: int = 10_000,
        target_update: int = 10,
        grad_clip_norm: float = 10.0,
        device: Optional[str] = None,
        seed: Optional[int] = None,
        log_dir: Optional[str] = None,
    ):
        self.state_size = state_size
        self.action_size = action_size
        self.gamma = gamma

        self.epsilon = epsilon_start
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

        self.policy_net = DQNetwork(state_size, action_size, hidden_size).to(self.device)
        self.target_net = DQNetwork(state_size, action_size, hidden_size).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=learning_rate)
        self.loss_fn = nn.SmoothL1Loss()  # Huber loss

        self.memory = ReplayBuffer(buffer_size)

        self.episode = 0
        self.steps = 0
        self.eval_mode = False

        # previous (o_{t-1}, a_{t-1}) so we can store transition when r_t arrives
        self.prev_state: Optional[np.ndarray] = None
        self.prev_action: Optional[int] = None

        # --- TensorBoard logging ---
        self._writer = None
        if log_dir and _HAS_TB:
            self._writer = SummaryWriter(log_dir=log_dir)
            logger.info("TensorBoard logging enabled → %s", log_dir)
        elif log_dir and not _HAS_TB:
            logger.warning("tensorboard not installed — pip install tensorboard")

        # Episode-level metric accumulators
        self._ep_reward = 0.0
        self._ep_steps = 0
        self._train_step = 0  # global training batch counter

        # Rolling windows for smoothed metrics (100-episode window)
        self._recent_rewards: deque = deque(maxlen=100)
        self._recent_steps: deque = deque(maxlen=100)
        self._recent_successes: deque = deque(maxlen=100)

    def _masked_argmax(self, q_values: torch.Tensor, valid_actions: List[int]) -> int:
        mask = torch.full((self.action_size,), float("-inf"), device=q_values.device)
        mask[valid_actions] = 0.0
        return int((q_values + mask).argmax().item())

    def select_action(self, state: np.ndarray, valid_actions: List[int]) -> int:
        if not valid_actions:
            raise ValueError("valid_actions is empty")

        # Explore uniformly among valid actions
        if random.random() < self.epsilon:
            return int(random.choice(valid_actions))

        with torch.no_grad():
            o = torch.tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0)
            q = self.policy_net(o).squeeze(0)
            return self._masked_argmax(q, valid_actions)

    def set_eval_mode(self, enabled: bool = True) -> None:
        """Switch between inference (eval) and training mode."""
        self.eval_mode = enabled
        if enabled:
            self.policy_net.eval()
        else:
            self.policy_net.train()

    def step(self, state: np.ndarray, valid_actions: List[int], reward: float, done: bool) -> int:
        """
        Called with the CURRENT observation o_t and the reward/done that correspond
        to the PREVIOUS action (transition into o_t).
        """
        action, _, _ = self.step_with_explanation(state, valid_actions, reward, done)
        return action

    def step_with_explanation(
        self, state: np.ndarray, valid_actions: List[int], reward: float, done: bool
    ) -> Tuple[int, Optional[np.ndarray], str]:
        """
        Same as step() but returns (action, q_values, exploration_type) for explainability.

        Returns:
            action: The selected action ID
            q_values: numpy array of Q-values for all actions (or None if random)
            exploration: "greedy", "epsilon_random", or "done"
        """
        # Eval mode: pure greedy inference, no training
        if self.eval_mode:
            if done:
                return int(valid_actions[0]), None, "done"
            with torch.no_grad():
                o = torch.tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0)
                q = self.policy_net(o).squeeze(0)
                q_numpy = q.cpu().numpy()
                action = self._masked_argmax(q, valid_actions)
                return int(action), q_numpy, "greedy"

        # Training mode: store transitions and learn
        # If we have (o_{t-1}, a_{t-1}), we can store transition using r_t and o_t
        if self.prev_state is not None and self.prev_action is not None:
            self._ep_reward += reward
            self._ep_steps += 1
            self.memory.push(Transition(
                o=self.prev_state,
                a=int(self.prev_action),
                r=float(reward),
                o2=state.copy(),
                valid_actions_o2=list(valid_actions),
                done=bool(done),
            ))

        if len(self.memory) >= self.batch_size:
            self._train_batch()

        if done:
            # Log episode metrics before resetting
            self._log_episode_metrics()

            self.episode += 1
            self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

            if self.episode % self.target_update == 0:
                self.target_net.load_state_dict(self.policy_net.state_dict())

            # Aggressive garbage collection every 10 episodes to prevent memory buildup
            if self.episode % 10 == 0:
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

            self.prev_state = None
            self.prev_action = None
            self._ep_reward = 0.0
            self._ep_steps = 0
            return int(valid_actions[0]), None, "done"

        # Epsilon-greedy action selection with explanation
        if random.random() < self.epsilon:
            # Random exploration
            action = int(random.choice(valid_actions))
            self.prev_state = state.copy()
            self.prev_action = int(action)
            self.steps += 1
            return int(action), None, "epsilon_random"
        else:
            # Greedy action with Q-values
            with torch.no_grad():
                o = torch.tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0)
                q = self.policy_net(o).squeeze(0)
                q_numpy = q.cpu().numpy()
                action = self._masked_argmax(q, valid_actions)
            self.prev_state = state.copy()
            self.prev_action = int(action)
            self.steps += 1
            return int(action), q_numpy, "greedy"

    def _train_batch(self) -> None:
        batch = self.memory.sample(self.batch_size)

        states = torch.tensor(np.stack([t.o for t in batch]), dtype=torch.float32, device=self.device)
        actions = torch.tensor([t.a for t in batch], dtype=torch.long, device=self.device)
        rewards = torch.tensor([t.r for t in batch], dtype=torch.float32, device=self.device)
        next_states = torch.tensor(np.stack([t.o2 for t in batch]), dtype=torch.float32, device=self.device)
        dones = torch.tensor([t.done for t in batch], dtype=torch.float32, device=self.device)

        # Q(o,a)
        q_all = self.policy_net(states)
        q_sa = q_all.gather(1, actions.unsqueeze(1)).squeeze(1)

        with torch.no_grad():
            next_q_all = self.target_net(next_states)  # Q^-(o2, .)
            max_next_q = torch.zeros(self.batch_size, device=self.device)

            for i, t in enumerate(batch):
                if t.valid_actions_o2:
                    max_next_q[i] = next_q_all[i, t.valid_actions_o2].max()
                else:
                    max_next_q[i] = 0.0

            target = rewards + self.gamma * max_next_q * (1.0 - dones)

        loss = self.loss_fn(q_sa, target)
        self.optimizer.zero_grad()
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(
            self.policy_net.parameters(), self.grad_clip_norm
        )
        self.optimizer.step()

        # Save values for logging before freeing memory
        loss_value = loss.item()
        avg_q_value = q_sa.mean().item()
        max_q_value = q_sa.max().item()

        # Free memory from training tensors
        del states, actions, rewards, next_states, dones, q_all, q_sa, next_q_all, max_next_q, target, loss
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # TensorBoard: log training metrics every 50 batches
        self._train_step += 1
        if self._writer and self._train_step % 50 == 0:
            gn = grad_norm.item() if isinstance(grad_norm, torch.Tensor) else float(grad_norm)
            self._writer.add_scalar("training/loss", loss_value, self._train_step)
            self._writer.add_scalar("training/avg_q", avg_q_value, self._train_step)
            self._writer.add_scalar("training/max_q", max_q_value, self._train_step)
            self._writer.add_scalar("training/grad_norm", gn, self._train_step)
            self._writer.add_scalar("training/lr",
                                    self.optimizer.param_groups[0]["lr"], self._train_step)

    def _log_episode_metrics(self) -> None:
        """Write episode-level scalars to TensorBoard."""
        self._recent_rewards.append(self._ep_reward)
        self._recent_steps.append(self._ep_steps)
        self._recent_successes.append(1.0 if self._ep_reward > 0 else 0.0)

        if not self._writer:
            return

        ep = self.episode
        self._writer.add_scalar("episode/reward", self._ep_reward, ep)
        self._writer.add_scalar("episode/steps", self._ep_steps, ep)
        self._writer.add_scalar("episode/epsilon", self.epsilon, ep)
        self._writer.add_scalar("episode/buffer_size", len(self.memory), ep)

        if len(self._recent_rewards) >= 10:
            self._writer.add_scalar(
                "rolling/avg_reward",
                sum(self._recent_rewards) / len(self._recent_rewards), ep)
            self._writer.add_scalar(
                "rolling/avg_steps",
                sum(self._recent_steps) / len(self._recent_steps), ep)
            self._writer.add_scalar(
                "rolling/success_rate",
                sum(self._recent_successes) / len(self._recent_successes) * 100, ep)

    def reset_episode(self) -> None:
        self.prev_state = None
        self.prev_action = None

    def close(self) -> None:
        """Flush and close TensorBoard writer."""
        if self._writer:
            self._writer.flush()
            self._writer.close()
            self._writer = None

    def get_stats(self) -> dict:
        return {
            "episode": int(self.episode),
            "epsilon": float(round(self.epsilon, 4)),
            "steps": int(self.steps),
            "buffer_size": int(len(self.memory)),
            "eval_mode": bool(self.eval_mode),
        }

    def save(self, path: str) -> None:
        torch.save({
            "policy_net": self.policy_net.state_dict(),
            "target_net": self.target_net.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "episode": self.episode,
            "epsilon": self.epsilon,
            "steps": self.steps,
            "train_step": self._train_step,
        }, path)

    def load(self, path: str) -> None:
        ckpt = torch.load(path, map_location=self.device, weights_only=False)

        # Check if checkpoint uses compiled model format (_orig_mod.net.X)
        # vs non-compiled format (fc1, fc2, fc3)
        policy_state = ckpt["policy_net"]
        target_state = ckpt["target_net"]

        if any(k.startswith('_orig_mod') for k in policy_state.keys()):
            # Remap compiled keys to non-compiled keys
            key_map = {
                '_orig_mod.net.0.weight': 'fc1.weight',
                '_orig_mod.net.0.bias': 'fc1.bias',
                '_orig_mod.net.2.weight': 'fc2.weight',
                '_orig_mod.net.2.bias': 'fc2.bias',
                '_orig_mod.net.4.weight': 'fc3.weight',
                '_orig_mod.net.4.bias': 'fc3.bias',
                '_orig_mod.net.6.weight': 'fc4.weight',
                '_orig_mod.net.6.bias': 'fc4.bias',
            }
            policy_remapped = {key_map.get(k, k): v for k, v in policy_state.items()}
            target_remapped = {key_map.get(k, k): v for k, v in target_state.items()}
            self.policy_net.load_state_dict(policy_remapped, strict=False)
            self.target_net.load_state_dict(target_remapped, strict=False)
        else:
            self.policy_net.load_state_dict(policy_state)
            self.target_net.load_state_dict(target_state)

        self.optimizer.load_state_dict(ckpt["optimizer"])
        self.episode = int(ckpt.get("episode", 0))
        self.epsilon = float(ckpt.get("epsilon", 1.0))
        self.steps = int(ckpt.get("steps", 0))
        self._train_step = int(ckpt.get("train_step", 0))
