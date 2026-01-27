"""
Pure Python trainer for the office navigation DQN.

Runs the DQN agent directly on the graph environment --
no Godot, no Jason, no WebSocket. Training completes in seconds.

Usage:
    python train.py                          # 5000 episodes, saves as 'alice'
    python train.py --episodes 10000 --name bob
"""

import argparse
import logging
import time
from collections import deque
from pathlib import Path

import numpy as np

from dqn_agent import DQNAgent
from office_graph_env import OfficeGraphEnv

CHECKPOINT_DIR = Path(__file__).parent.parent.parent / "checkpoints"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("train")


def train(episodes: int, name: str) -> None:
    env = OfficeGraphEnv(max_steps=50)
    agent = DQNAgent(state_size=22, action_size=11)

    # Rolling metrics (last 100 episodes)
    recent_rewards = deque(maxlen=100)
    recent_steps = deque(maxlen=100)
    recent_successes = deque(maxlen=100)
    total_successes = 0

    start_time = time.time()

    for ep in range(episodes):
        state, valid_actions = env.reset()
        agent.reset_episode()

        # First call: no previous transition (reward=0, done=False)
        action = agent.step(state, valid_actions, reward=0.0, done=False)

        episode_reward = 0.0
        done = False

        while not done:
            next_state, reward, done, next_valid = env.step(action)
            episode_reward += reward

            action = agent.step(next_state, next_valid, reward, done)

            state = next_state
            valid_actions = next_valid

        success = episode_reward > 0  # Goal (+100) minus steps > 0
        total_successes += int(success)
        recent_rewards.append(episode_reward)
        recent_steps.append(env.steps)
        recent_successes.append(int(success))

        if (ep + 1) % 100 == 0:
            avg_r = np.mean(recent_rewards)
            avg_s = np.mean(recent_steps)
            sr = np.mean(recent_successes) * 100
            elapsed = time.time() - start_time
            logger.info(
                "Episode %5d | SuccessRate=%5.1f%% | AvgReward=%7.1f | AvgSteps=%5.1f | Epsilon=%.3f | %.1fs",
                ep + 1, sr, avg_r, avg_s, agent.epsilon, elapsed,
            )

    # Save checkpoint
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    path = CHECKPOINT_DIR / f"{name}.pt"
    agent.save(str(path))

    elapsed = time.time() - start_time
    logger.info("")
    logger.info("=" * 60)
    logger.info("TRAINING COMPLETE")
    logger.info("  Episodes:     %d", episodes)
    logger.info("  Successes:    %d / %d (%.1f%%)", total_successes, episodes, total_successes / episodes * 100)
    logger.info("  Final epsilon: %.4f", agent.epsilon)
    logger.info("  Time:         %.1fs", elapsed)
    logger.info("  Saved:        %s", path)
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Train DQN on office graph")
    parser.add_argument("--episodes", type=int, default=5000, help="Number of episodes")
    parser.add_argument("--name", type=str, default="alice", help="Agent name for checkpoint")
    args = parser.parse_args()

    train(args.episodes, args.name)


if __name__ == "__main__":
    main()
