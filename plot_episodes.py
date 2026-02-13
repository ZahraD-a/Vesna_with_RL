"""
Plot evaluation results from logs/alice_episodes.csv

Usage:
    python plot_episodes.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

CSV_PATH = "logs/alice_episodes.csv"

def main():
    if not os.path.exists(CSV_PATH):
        print(f"No log file found at {CSV_PATH}")
        print("Run episodes first with eval_mode(true) to generate data.")
        sys.exit(1)

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} episodes from {CSV_PATH}")
    print(f"  Success: {(df['outcome'] == 'success').sum()}")
    print(f"  Timeout: {(df['outcome'] == 'timeout').sum()}")
    print(f"  Avg reward: {df['reward'].mean():.1f}")
    print(f"  Avg steps (success only): {df[df['outcome'] == 'success']['steps'].mean():.1f}")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("RL Policy Evaluation Results", fontsize=14, fontweight="bold")

    # --- 1. Reward per episode ---
    ax = axes[0, 0]
    ax.plot(df["episode"], df["reward"], alpha=0.3, linewidth=0.5, color="steelblue")
    # Rolling average
    window = min(50, len(df) // 5) if len(df) > 10 else len(df)
    if window > 1:
        rolling = df["reward"].rolling(window=window, min_periods=1).mean()
        ax.plot(df["episode"], rolling, color="darkblue", linewidth=2, label=f"Rolling avg ({window} eps)")
        ax.legend()
    ax.set_xlabel("Episode")
    ax.set_ylabel("Total Reward")
    ax.set_title("Reward per Episode")
    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5)

    # --- 2. Steps per episode ---
    ax = axes[0, 1]
    ax.plot(df["episode"], df["steps"], alpha=0.3, linewidth=0.5, color="coral")
    if window > 1:
        rolling_steps = df["steps"].rolling(window=window, min_periods=1).mean()
        ax.plot(df["episode"], rolling_steps, color="darkred", linewidth=2, label=f"Rolling avg ({window} eps)")
        ax.legend()
    ax.set_xlabel("Episode")
    ax.set_ylabel("Steps")
    ax.set_title("Steps per Episode")

    # --- 3. Success rate (rolling window) ---
    ax = axes[1, 0]
    df["is_success"] = (df["outcome"] == "success").astype(int)
    if window > 1:
        success_rate = df["is_success"].rolling(window=window, min_periods=1).mean() * 100
        ax.plot(df["episode"], success_rate, color="green", linewidth=2)
    else:
        ax.plot(df["episode"], df["is_success"] * 100, color="green", linewidth=2)
    ax.set_xlabel("Episode")
    ax.set_ylabel("Success Rate (%)")
    ax.set_title(f"Success Rate (rolling {window} episodes)")
    ax.set_ylim(-5, 105)
    ax.axhline(y=100, color="gray", linestyle="--", alpha=0.3)

    # --- 4. Hardest start-goal pairs ---
    ax = axes[1, 1]
    df["pair"] = df["start"] + " -> " + df["goal"]
    pair_stats = df.groupby("pair").agg(
        total=("outcome", "count"),
        failures=("is_success", lambda x: (x == 0).sum()),
        avg_steps=("steps", "mean")
    ).reset_index()
    pair_stats["failure_rate"] = pair_stats["failures"] / pair_stats["total"] * 100

    # Show top 10 hardest pairs (by failure rate, min 2 attempts)
    hard = pair_stats[pair_stats["total"] >= 2].nlargest(10, "failure_rate")
    if len(hard) > 0:
        bars = ax.barh(hard["pair"], hard["failure_rate"], color="salmon")
        ax.set_xlabel("Failure Rate (%)")
        ax.set_title("Hardest Start-Goal Pairs")
        ax.set_xlim(0, 105)
        # Add attempt count labels
        for bar, total in zip(bars, hard["total"]):
            ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                    f"n={total}", va="center", fontsize=8)
    else:
        ax.text(0.5, 0.5, "Not enough data\n(need 2+ attempts per pair)",
                ha="center", va="center", transform=ax.transAxes)
        ax.set_title("Hardest Start-Goal Pairs")

    plt.tight_layout()
    plt.savefig("logs/evaluation_results.png", dpi=150, bbox_inches="tight")
    print(f"\nPlot saved to logs/evaluation_results.png")
    plt.show()

if __name__ == "__main__":
    main()
