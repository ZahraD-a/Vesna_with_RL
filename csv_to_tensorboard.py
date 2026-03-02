"""
Convert alice_episodes.csv into TensorBoard event files.

Read-only on the CSV — safe to run while training is active.
Writes TensorBoard events to runs/csv_import/ so you can view
the current run's metrics in TensorBoard immediately.

Usage:
    python csv_to_tensorboard.py                    # default paths
    python csv_to_tensorboard.py --csv <path>       # custom CSV
    tensorboard --logdir runs                        # then open browser
"""

import argparse
import csv
import os
from collections import deque

from torch.utils.tensorboard import SummaryWriter


def convert(csv_path: str, log_dir: str) -> None:
    print(f"Reading: {csv_path}")

    episodes = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            episodes.append(row)

    # Find the last episode-counter reset (start of current run)
    ep_nums = [int(row["episode"]) for row in episodes]
    last_reset = 0
    for i in range(1, len(ep_nums)):
        if ep_nums[i] < ep_nums[i - 1]:
            last_reset = i

    episodes = episodes[last_reset:]
    print(f"Current run: {len(episodes)} episodes (skipped {last_reset} from older runs)")

    writer = SummaryWriter(log_dir=log_dir)

    recent_rewards = deque(maxlen=100)
    recent_steps = deque(maxlen=100)
    recent_successes = deque(maxlen=100)

    for row in episodes:
        ep = int(row["episode"])
        reward = float(row["reward"])
        steps = int(row["steps"])
        outcome = row["outcome"].strip()
        is_success = 1.0 if outcome == "success" else 0.0

        # Per-episode metrics
        writer.add_scalar("episode/reward", reward, ep)
        writer.add_scalar("episode/steps", steps, ep)

        # Rolling averages
        recent_rewards.append(reward)
        recent_steps.append(steps)
        recent_successes.append(is_success)

        if len(recent_rewards) >= 10:
            writer.add_scalar(
                "rolling/avg_reward",
                sum(recent_rewards) / len(recent_rewards), ep)
            writer.add_scalar(
                "rolling/avg_steps",
                sum(recent_steps) / len(recent_steps), ep)
            writer.add_scalar(
                "rolling/success_rate",
                sum(recent_successes) / len(recent_successes) * 100, ep)

    writer.flush()
    writer.close()

    print(f"Wrote TensorBoard events to: {log_dir}")
    print(f"\nTo view, run:")
    print(f"  tensorboard --logdir {os.path.dirname(log_dir)}")
    print(f"  Then open http://localhost:6006")


if __name__ == "__main__":
    project_root = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser(description="Convert training CSV to TensorBoard")
    parser.add_argument("--csv", default=os.path.join(project_root, "mind", "logs", "alice_episodes.csv"))
    parser.add_argument("--logdir", default=os.path.join(project_root, "runs", "csv_import"))
    args = parser.parse_args()

    convert(args.csv, args.logdir)
