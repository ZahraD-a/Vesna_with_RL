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

import random
from collections import deque
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim


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
        learning_rate: float = 1e-3,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.01,
        epsilon_decay: float = 0.995,
        batch_size: int = 32,
        buffer_size: int = 10_000,
        target_update: int = 10,
        grad_clip_norm: float = 10.0,
        device: Optional[str] = None,
        seed: Optional[int] = None,
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
            self.episode += 1
            self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

            if self.episode % self.target_update == 0:
                self.target_net.load_state_dict(self.policy_net.state_dict())

            self.prev_state = None
            self.prev_action = None
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
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), self.grad_clip_norm)
        self.optimizer.step()

    def reset_episode(self) -> None:
        self.prev_state = None
        self.prev_action = None

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
        }, path)

    def load(self, path: str) -> None:
        ckpt = torch.load(path, map_location=self.device)  # :contentReference[oaicite:8]{index=8}
        self.policy_net.load_state_dict(ckpt["policy_net"])
        self.target_net.load_state_dict(ckpt["target_net"])
        self.optimizer.load_state_dict(ckpt["optimizer"])
        self.episode = int(ckpt.get("episode", 0))
        self.epsilon = float(ckpt.get("epsilon", 1.0))
        self.steps = int(ckpt.get("steps", 0))
