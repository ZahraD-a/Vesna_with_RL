"""
Read-only training monitor — plots metrics from alice_episodes.csv
Safe to run while training is active (only reads the CSV file).
"""

import csv
import matplotlib.pyplot as plt
import numpy as np
import sys
import os

CSV_PATH = os.path.join(os.path.dirname(__file__), "mind", "logs", "alice_episodes.csv")

def load_episodes(csv_path):
    """Load episodes from CSV (read-only)."""
    episodes, rewards, steps, outcomes = [], [], [], []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            episodes.append(int(row["episode"]))
            rewards.append(float(row["reward"]))
            steps.append(int(row["steps"]))
            outcomes.append(row["outcome"].strip())
    return episodes, rewards, steps, outcomes


def find_current_run(episodes):
    """Find where the latest run starts (last episode counter reset)."""
    last_reset = 0
    for i in range(1, len(episodes)):
        if episodes[i] < episodes[i - 1]:
            last_reset = i
    return last_reset


def rolling_average(data, window=500):
    """Compute rolling average with given window size."""
    arr = np.array(data, dtype=float)
    if len(arr) < window:
        window = max(1, len(arr) // 5)
    cumsum = np.cumsum(arr)
    cumsum = np.insert(cumsum, 0, 0)
    rolling = (cumsum[window:] - cumsum[:-window]) / window
    # Pad the beginning so the array length matches
    pad = np.full(window - 1, np.nan)
    return np.concatenate([pad, rolling])


def rolling_success_rate(outcomes, window=500):
    """Compute rolling success rate (fraction of 'success' in window)."""
    binary = np.array([1.0 if o == "success" else 0.0 for o in outcomes])
    return rolling_average(binary, window) * 100


def plot_training(csv_path):
    print(f"Loading data from: {csv_path}")
    episodes, rewards, steps, outcomes = load_episodes(csv_path)

    # Only plot the current (latest) training run
    start = find_current_run(episodes)
    episodes = episodes[start:]
    rewards = rewards[start:]
    steps = steps[start:]
    outcomes = outcomes[start:]

    n = len(episodes)
    x = np.arange(n)
    ep_nums = np.array(episodes)

    print(f"Current run: {n} episodes (ep {episodes[0]} to {episodes[-1]})")

    window = min(500, n // 10) if n > 50 else 1
    print(f"Rolling window: {window}")

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    fig.suptitle(
        f"VEsNA Extended Regions — Training Monitor\n"
        f"Current run: {n:,} episodes (rolling window = {window})",
        fontsize=13, fontweight="bold",
    )

    # --- Plot 1: Reward ---
    ax1 = axes[0]
    ax1.scatter(ep_nums, rewards, s=1, alpha=0.08, color="steelblue", label="Per episode")
    roll_r = rolling_average(rewards, window)
    ax1.plot(ep_nums, roll_r, color="red", linewidth=1.5, label=f"Rolling avg ({window})")
    ax1.set_ylabel("Reward")
    ax1.set_title("Episode Reward")
    ax1.legend(loc="lower right")
    ax1.grid(True, alpha=0.3)

    # --- Plot 2: Steps ---
    ax2 = axes[1]
    ax2.scatter(ep_nums, steps, s=1, alpha=0.08, color="forestgreen", label="Per episode")
    roll_s = rolling_average(steps, window)
    ax2.plot(ep_nums, roll_s, color="red", linewidth=1.5, label=f"Rolling avg ({window})")
    ax2.set_ylabel("Steps")
    ax2.set_title("Steps per Episode")
    ax2.legend(loc="upper right")
    ax2.grid(True, alpha=0.3)

    # --- Plot 3: Success Rate ---
    ax3 = axes[2]
    roll_sr = rolling_success_rate(outcomes, window)
    ax3.plot(ep_nums, roll_sr, color="darkorange", linewidth=1.5, label=f"Rolling success % ({window})")
    ax3.set_ylabel("Success Rate (%)")
    ax3.set_xlabel("Episode")
    ax3.set_title("Success Rate")
    ax3.set_ylim(-5, 105)
    ax3.legend(loc="lower right")
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()

    out_path = os.path.join(os.path.dirname(csv_path), "training_plot.png")
    plt.savefig(out_path, dpi=150)
    print(f"Plot saved to: {out_path}")
    plt.show()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else CSV_PATH
    plot_training(path)
