"""
Comprehensive evaluation of the trained DQN navigation policy.

Loads the checkpoint, tests ALL 2,450 start-goal pairs (50x49),
compares agent paths against BFS shortest paths, and generates
evaluation metrics + figures for academic reporting.

Safe to run independently — does NOT require the training server.

Usage:
    python evaluate_policy.py
    python evaluate_policy.py --checkpoint checkpoints/alice50.pt
"""

import argparse
import csv
import os
import sys
from collections import defaultdict, deque
from itertools import product

import numpy as np
import torch
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for saving figures

# Add mind/python to path so we can import dqn_agent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "mind", "python"))
from dqn_agent import DQNAgent


# ============================================================
#  GRAPH DEFINITION (from office_map.asl + navigation_rl_bridge.asl)
# ============================================================

ROOMS = [
    "reception", "corridor", "open_office", "outside", "common",
    "meeting_room", "senior_office_1", "senior_office_2", "senior_office_3",
    "boss_office_1", "boss_office_2",
    "corridor_north", "corridor_south",
    "kitchen", "restroom_1", "storage_1",
    "meeting_room_2", "meeting_room_3", "lab_1", "lab_2", "server_room",
    "office_1", "office_2", "office_3", "office_4", "office_5",
    "lobby", "cafeteria", "gym", "restroom_2",
    "office_6", "office_7", "office_8", "office_9", "office_10",
    "archive", "training_room",
    "terrace", "parking", "conference_room", "security_desk",
    "library", "print_room", "mail_room", "executive_suite",
    "phone_booth_1", "phone_booth_2", "supply_closet", "lounge",
    "wellness_room",
]

ROOM_TO_ID = {name: i for i, name in enumerate(ROOMS)}
ID_TO_ROOM = {i: name for i, name in enumerate(ROOMS)}
NUM_ROOMS = len(ROOMS)

# Direct connections (EC = open passage)
EC_EDGES = [
    ("corridor", "reception"),
    ("corridor", "open_office"),
    ("corridor", "corridor_north"),
    ("corridor", "corridor_south"),
    ("corridor_south", "lobby"),
]

# Door connections (PO: room <-> door <-> room)
DOOR_EDGES = [
    ("corridor", "common"),
    ("corridor", "senior_office_1"),
    ("corridor", "senior_office_2"),
    ("corridor", "senior_office_3"),
    ("corridor", "meeting_room"),
    ("corridor", "restroom_1"),
    ("corridor", "storage_1"),
    ("open_office", "boss_office_1"),
    ("open_office", "boss_office_2"),
    ("open_office", "outside"),
    ("open_office", "print_room"),
    ("corridor_north", "meeting_room_2"),
    ("corridor_north", "meeting_room_3"),
    ("corridor_north", "lab_1"),
    ("corridor_north", "lab_2"),
    ("corridor_north", "server_room"),
    ("corridor_north", "office_1"),
    ("corridor_north", "office_2"),
    ("corridor_north", "office_3"),
    ("corridor_north", "office_4"),
    ("corridor_north", "office_5"),
    ("corridor_south", "cafeteria"),
    ("corridor_south", "gym"),
    ("corridor_south", "restroom_2"),
    ("corridor_south", "office_6"),
    ("corridor_south", "office_7"),
    ("corridor_south", "office_8"),
    ("corridor_south", "office_9"),
    ("corridor_south", "office_10"),
    ("corridor_south", "archive"),
    ("corridor_south", "training_room"),
    ("lobby", "parking"),
    ("lobby", "conference_room"),
    ("lobby", "security_desk"),
    ("common", "kitchen"),
    ("common", "library"),
    ("cafeteria", "terrace"),
    ("reception", "mail_room"),
    ("boss_office_1", "executive_suite"),
    ("library", "phone_booth_1"),
    ("gym", "lounge"),
    ("gym", "wellness_room"),
    ("lounge", "phone_booth_2"),
    ("storage_1", "supply_closet"),
]


def build_adjacency():
    """Build adjacency list from EC + door edges (symmetric)."""
    adj = defaultdict(set)
    for a, b in EC_EDGES + DOOR_EDGES:
        adj[a].add(b)
        adj[b].add(a)
    return adj


def bfs_shortest_path(adj, start, goal):
    """BFS shortest path. Returns (path_length, path_list)."""
    if start == goal:
        return 0, [start]
    visited = {start}
    queue = deque([(start, [start])])
    while queue:
        node, path = queue.popleft()
        for neighbor in sorted(adj[node]):
            if neighbor == goal:
                return len(path), path + [goal]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return -1, []  # unreachable


def build_state(current_id, goal_id, num_rooms=50):
    """Build one-hot state vector [current | goal]."""
    state = np.zeros(num_rooms * 2, dtype=np.float32)
    state[current_id] = 1.0
    state[num_rooms + goal_id] = 1.0
    return state


def get_valid_actions(adj, room_name):
    """Get valid action IDs for a room."""
    return sorted([ROOM_TO_ID[n] for n in adj[room_name]])


def evaluate_agent(agent, adj, max_steps=150):
    """Evaluate agent on ALL start-goal pairs. Returns list of result dicts."""
    agent.set_eval_mode(True)
    results = []
    pairs = [(s, g) for s in ROOMS for g in ROOMS if s != g]

    for i, (start, goal) in enumerate(pairs):
        # BFS optimal
        bfs_len, bfs_path = bfs_shortest_path(adj, start, goal)

        # Agent rollout
        current = start
        agent_path = [current]
        steps = 0
        success = False

        for step in range(max_steps):
            state = build_state(ROOM_TO_ID[current], ROOM_TO_ID[goal])
            valid = get_valid_actions(adj, current)
            with torch.no_grad():
                o = torch.tensor(state, dtype=torch.float32, device=agent.device).unsqueeze(0)
                q = agent.policy_net(o).squeeze(0)
                # Masked argmax
                mask = torch.full((agent.action_size,), float("-inf"), device=q.device)
                mask[valid] = 0.0
                action = int((q + mask).argmax().item())

            next_room = ID_TO_ROOM[action]
            agent_path.append(next_room)
            steps += 1
            current = next_room

            if current == goal:
                success = True
                break

        reward = (100 - steps) if success else (-steps - 10)
        optimality = bfs_len / steps if (success and steps > 0) else 0.0

        results.append({
            "start": start,
            "goal": goal,
            "bfs_steps": bfs_len,
            "agent_steps": steps,
            "success": success,
            "reward": reward,
            "optimality": optimality,
            "agent_path": " -> ".join(agent_path),
            "bfs_path": " -> ".join(bfs_path),
        })

        if (i + 1) % 500 == 0:
            print(f"  Evaluated {i+1}/{len(pairs)} pairs...")

    return results


def print_summary(results):
    """Print evaluation summary statistics."""
    total = len(results)
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]

    success_rate = len(successes) / total * 100
    avg_agent_steps = np.mean([r["agent_steps"] for r in successes]) if successes else 0
    avg_bfs_steps = np.mean([r["bfs_steps"] for r in successes]) if successes else 0
    avg_optimality = np.mean([r["optimality"] for r in successes]) if successes else 0
    avg_reward = np.mean([r["reward"] for r in results])

    optimal_count = sum(1 for r in successes if r["agent_steps"] == r["bfs_steps"])
    optimal_pct = optimal_count / total * 100

    near_optimal = sum(1 for r in successes if r["agent_steps"] <= r["bfs_steps"] + 1)
    near_optimal_pct = near_optimal / total * 100

    print("\n" + "=" * 60)
    print("  EVALUATION RESULTS — DQN Navigation Policy")
    print("=" * 60)
    print(f"  Total pairs tested:      {total}")
    print(f"  Success rate:            {success_rate:.1f}% ({len(successes)}/{total})")
    print(f"  Failures (timeout):      {len(failures)}")
    print(f"")
    print(f"  Avg agent steps:         {avg_agent_steps:.2f}")
    print(f"  Avg BFS shortest path:   {avg_bfs_steps:.2f}")
    print(f"  Avg optimality ratio:    {avg_optimality:.4f} (1.0 = perfect)")
    print(f"  Avg reward:              {avg_reward:.2f}")
    print(f"")
    print(f"  Exactly optimal paths:   {optimal_pct:.1f}% ({optimal_count}/{total})")
    print(f"  Near-optimal (opt+1):    {near_optimal_pct:.1f}% ({near_optimal}/{total})")
    print("=" * 60)

    # Breakdown by BFS distance
    print("\n  Breakdown by shortest path length:")
    print(f"  {'BFS Dist':<10} {'Pairs':<8} {'Success%':<10} {'Avg Steps':<12} {'Optimal%':<10}")
    print(f"  {'-'*50}")

    by_dist = defaultdict(list)
    for r in results:
        by_dist[r["bfs_steps"]].append(r)

    for dist in sorted(by_dist.keys()):
        group = by_dist[dist]
        n = len(group)
        s = sum(1 for r in group if r["success"])
        o = sum(1 for r in group if r["success"] and r["agent_steps"] == r["bfs_steps"])
        avg_s = np.mean([r["agent_steps"] for r in group if r["success"]]) if s > 0 else 0
        print(f"  {dist:<10} {n:<8} {s/n*100:<10.1f} {avg_s:<12.2f} {o/n*100:<10.1f}")

    # Worst 10 pairs
    if successes:
        worst = sorted(successes, key=lambda r: r["optimality"])[:10]
        print(f"\n  10 Hardest pairs (lowest optimality):")
        print(f"  {'Start':<20} {'Goal':<20} {'BFS':<5} {'Agent':<7} {'Ratio':<6}")
        print(f"  {'-'*58}")
        for r in worst:
            print(f"  {r['start']:<20} {r['goal']:<20} {r['bfs_steps']:<5} {r['agent_steps']:<7} {r['optimality']:<6.3f}")

    return {
        "total_pairs": total,
        "success_rate": success_rate,
        "avg_agent_steps": avg_agent_steps,
        "avg_bfs_steps": avg_bfs_steps,
        "avg_optimality": avg_optimality,
        "optimal_pct": optimal_pct,
        "near_optimal_pct": near_optimal_pct,
        "avg_reward": avg_reward,
    }


def plot_evaluation(results, output_dir):
    """Generate evaluation figures for the paper."""
    os.makedirs(output_dir, exist_ok=True)
    successes = [r for r in results if r["success"]]

    # --- Figure 1: Optimality heatmap (50x50) ---
    fig, ax = plt.subplots(figsize=(14, 12))
    heatmap = np.full((NUM_ROOMS, NUM_ROOMS), np.nan)
    for r in results:
        si = ROOM_TO_ID[r["start"]]
        gi = ROOM_TO_ID[r["goal"]]
        heatmap[si, gi] = r["optimality"] if r["success"] else 0.0

    im = ax.imshow(heatmap, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(NUM_ROOMS))
    ax.set_yticks(range(NUM_ROOMS))
    ax.set_xticklabels(ROOMS, rotation=90, fontsize=5)
    ax.set_yticklabels(ROOMS, fontsize=5)
    ax.set_xlabel("Goal Room")
    ax.set_ylabel("Start Room")
    ax.set_title("Optimality Ratio per Start-Goal Pair (green=optimal, red=suboptimal)")
    plt.colorbar(im, ax=ax, label="Optimality (BFS / Agent steps)")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "optimality_heatmap.png"), dpi=200)
    plt.close()
    print(f"  Saved: optimality_heatmap.png")

    # --- Figure 2: Agent steps vs BFS steps scatter ---
    fig, ax = plt.subplots(figsize=(8, 8))
    bfs = [r["bfs_steps"] for r in successes]
    agent = [r["agent_steps"] for r in successes]
    ax.scatter(bfs, agent, alpha=0.15, s=15, color="steelblue")
    max_val = max(max(bfs), max(agent)) + 1
    ax.plot([0, max_val], [0, max_val], "r--", linewidth=1.5, label="Optimal (y=x)")
    ax.set_xlabel("BFS Shortest Path (steps)")
    ax.set_ylabel("Agent Path (steps)")
    ax.set_title("Agent Steps vs Optimal Steps")
    ax.legend()
    ax.set_xlim(0, max_val)
    ax.set_ylim(0, max_val)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "agent_vs_bfs_scatter.png"), dpi=150)
    plt.close()
    print(f"  Saved: agent_vs_bfs_scatter.png")

    # --- Figure 3: Distribution of optimality ratios ---
    fig, ax = plt.subplots(figsize=(10, 5))
    opts = [r["optimality"] for r in successes]
    ax.hist(opts, bins=50, color="steelblue", edgecolor="white", alpha=0.8)
    ax.axvline(x=1.0, color="red", linestyle="--", linewidth=1.5, label="Optimal (1.0)")
    ax.axvline(x=np.mean(opts), color="orange", linestyle="--", linewidth=1.5,
               label=f"Mean ({np.mean(opts):.3f})")
    ax.set_xlabel("Optimality Ratio (BFS / Agent steps)")
    ax.set_ylabel("Count")
    ax.set_title("Distribution of Path Optimality")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "optimality_distribution.png"), dpi=150)
    plt.close()
    print(f"  Saved: optimality_distribution.png")

    # --- Figure 4: Performance by BFS distance ---
    by_dist = defaultdict(list)
    for r in results:
        by_dist[r["bfs_steps"]].append(r)

    dists = sorted(by_dist.keys())
    avg_agent = []
    avg_optimal = []
    success_rates = []
    for d in dists:
        group = by_dist[d]
        s = [r for r in group if r["success"]]
        avg_agent.append(np.mean([r["agent_steps"] for r in s]) if s else 0)
        avg_optimal.append(d)
        success_rates.append(len(s) / len(group) * 100)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    x = np.arange(len(dists))
    width = 0.35
    ax1.bar(x - width/2, avg_optimal, width, label="BFS Optimal", color="forestgreen", alpha=0.8)
    ax1.bar(x + width/2, avg_agent, width, label="DQN Agent", color="steelblue", alpha=0.8)
    ax1.set_xticks(x)
    ax1.set_xticklabels(dists)
    ax1.set_xlabel("BFS Shortest Path Distance")
    ax1.set_ylabel("Average Steps")
    ax1.set_title("Average Steps by Path Distance")
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis="y")

    ax2.bar(dists, success_rates, color="darkorange", alpha=0.8)
    ax2.set_xlabel("BFS Shortest Path Distance")
    ax2.set_ylabel("Success Rate (%)")
    ax2.set_title("Success Rate by Path Distance")
    ax2.set_ylim(0, 105)
    ax2.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "performance_by_distance.png"), dpi=150)
    plt.close()
    print(f"  Saved: performance_by_distance.png")

    # --- Figure 5: Reward distribution ---
    fig, ax = plt.subplots(figsize=(10, 5))
    rewards = [r["reward"] for r in results]
    ax.hist(rewards, bins=50, color="steelblue", edgecolor="white", alpha=0.8)
    ax.axvline(x=np.mean(rewards), color="red", linestyle="--",
               label=f"Mean reward ({np.mean(rewards):.1f})")
    ax.set_xlabel("Episode Reward")
    ax.set_ylabel("Count")
    ax.set_title("Reward Distribution Across All Start-Goal Pairs")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "reward_distribution.png"), dpi=150)
    plt.close()
    print(f"  Saved: reward_distribution.png")


def save_results_csv(results, output_path):
    """Save full results to CSV for further analysis."""
    fields = ["start", "goal", "bfs_steps", "agent_steps", "success",
              "reward", "optimality", "agent_path", "bfs_path"]
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    print(f"  Saved: {output_path}")


def main():
    project_root = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser(description="Evaluate trained DQN navigation policy")
    parser.add_argument("--checkpoint", default=os.path.join(project_root, "checkpoints", "alice50.pt"))
    parser.add_argument("--output-dir", default=os.path.join(project_root, "evaluation"))
    args = parser.parse_args()

    print("=" * 60)
    print("  VEsNA DQN Policy Evaluation")
    print("=" * 60)

    # Build graph
    adj = build_adjacency()
    print(f"\nGraph: {NUM_ROOMS} rooms, {sum(len(v) for v in adj.values()) // 2} edges")
    print(f"Total pairs to evaluate: {NUM_ROOMS * (NUM_ROOMS - 1)}")

    # Verify graph connectivity
    visited = set()
    queue = deque([ROOMS[0]])
    visited.add(ROOMS[0])
    while queue:
        node = queue.popleft()
        for n in adj[node]:
            if n not in visited:
                visited.add(n)
                queue.append(n)
    print(f"Graph connectivity: {len(visited)}/{NUM_ROOMS} rooms reachable")
    assert len(visited) == NUM_ROOMS, "Graph is not fully connected!"

    # Load agent
    print(f"\nLoading checkpoint: {args.checkpoint}")
    agent = DQNAgent(
        state_size=NUM_ROOMS * 2,
        action_size=NUM_ROOMS,
        hidden_size=128,
    )
    agent.load(args.checkpoint)
    print(f"  Episode: {agent.episode}, Epsilon: {agent.epsilon:.6f}, Steps: {agent.steps}")

    # Evaluate
    print(f"\nEvaluating all {NUM_ROOMS * (NUM_ROOMS - 1)} pairs...")
    results = evaluate_agent(agent, adj)

    # Print summary
    summary = print_summary(results)

    # Save results
    os.makedirs(args.output_dir, exist_ok=True)
    csv_path = os.path.join(args.output_dir, "eval_results.csv")
    save_results_csv(results, csv_path)

    # Generate plots
    print(f"\nGenerating evaluation figures...")
    plot_evaluation(results, args.output_dir)

    print(f"\nAll outputs saved to: {args.output_dir}/")
    print("Done!")


if __name__ == "__main__":
    main()
