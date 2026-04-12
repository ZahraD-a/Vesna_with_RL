"""
Interactive evaluation dashboard for VEsNA DQN navigation policy.
Opens in browser with zoomable, hoverable plots.
Also generates a network graph with example paths.
"""

import sys, os, csv, json
import numpy as np
from collections import defaultdict, deque

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import networkx as nx

# ============================================================
#  GRAPH + DATA
# ============================================================

ROOMS = [
    "reception","corridor","open_office","outside","common",
    "meeting_room","senior_office_1","senior_office_2","senior_office_3",
    "boss_office_1","boss_office_2","corridor_north","corridor_south",
    "kitchen","restroom_1","storage_1",
    "meeting_room_2","meeting_room_3","lab_1","lab_2","server_room",
    "office_1","office_2","office_3","office_4","office_5",
    "lobby","cafeteria","gym","restroom_2",
    "office_6","office_7","office_8","office_9","office_10",
    "archive","training_room",
    "terrace","parking","conference_room","security_desk",
    "library","print_room","mail_room","executive_suite",
    "phone_booth_1","phone_booth_2","supply_closet","lounge","wellness_room",
]

ROOM_TO_ID = {n: i for i, n in enumerate(ROOMS)}
NUM = len(ROOMS)

EC = [("corridor","reception"),("corridor","open_office"),
      ("corridor","corridor_north"),("corridor","corridor_south"),
      ("corridor_south","lobby")]
DOORS = [
    ("corridor","common"),("corridor","senior_office_1"),("corridor","senior_office_2"),
    ("corridor","senior_office_3"),("corridor","meeting_room"),("corridor","restroom_1"),
    ("corridor","storage_1"),("open_office","boss_office_1"),("open_office","boss_office_2"),
    ("open_office","outside"),("open_office","print_room"),
    ("corridor_north","meeting_room_2"),("corridor_north","meeting_room_3"),
    ("corridor_north","lab_1"),("corridor_north","lab_2"),("corridor_north","server_room"),
    ("corridor_north","office_1"),("corridor_north","office_2"),("corridor_north","office_3"),
    ("corridor_north","office_4"),("corridor_north","office_5"),
    ("corridor_south","cafeteria"),("corridor_south","gym"),("corridor_south","restroom_2"),
    ("corridor_south","office_6"),("corridor_south","office_7"),("corridor_south","office_8"),
    ("corridor_south","office_9"),("corridor_south","office_10"),("corridor_south","archive"),
    ("corridor_south","training_room"),("lobby","parking"),("lobby","conference_room"),
    ("lobby","security_desk"),("common","kitchen"),("common","library"),
    ("cafeteria","terrace"),("reception","mail_room"),("boss_office_1","executive_suite"),
    ("library","phone_booth_1"),("gym","lounge"),("gym","wellness_room"),
    ("lounge","phone_booth_2"),("storage_1","supply_closet"),
]

ALL_EDGES = EC + DOORS

adj = defaultdict(set)
for a, b in ALL_EDGES:
    adj[a].add(b)
    adj[b].add(a)


def bfs_path(s, g):
    if s == g:
        return [s]
    visited = {s}
    queue = deque([(s, [s])])
    while queue:
        node, path = queue.popleft()
        for nb in sorted(adj[node]):
            if nb == g:
                return path + [g]
            if nb not in visited:
                visited.add(nb)
                queue.append((nb, path + [nb]))
    return []


def load_eval_csv(path):
    results = []
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["bfs_steps"] = int(row["bfs_steps"])
            row["agent_steps"] = int(row["agent_steps"])
            row["reward"] = float(row["reward"])
            row["optimality"] = float(row["optimality"])
            row["success"] = row["success"] == "True"
            results.append(row)
    return results


# ============================================================
#  PLOT 1: Interactive Heatmap (steps per pair)
# ============================================================

def plot_heatmap(results, output_dir):
    mat = np.full((NUM, NUM), np.nan)
    for r in results:
        si = ROOM_TO_ID[r["start"]]
        gi = ROOM_TO_ID[r["goal"]]
        mat[si, gi] = r["agent_steps"]

    hover = []
    for si in range(NUM):
        row = []
        for gi in range(NUM):
            r_match = [r for r in results if r["start"] == ROOMS[si] and r["goal"] == ROOMS[gi]]
            if r_match:
                r = r_match[0]
                row.append(
                    f"<b>{r['start']} → {r['goal']}</b><br>"
                    f"Agent steps: {r['agent_steps']}<br>"
                    f"BFS optimal: {r['bfs_steps']}<br>"
                    f"Reward: {r['reward']}<br>"
                    f"Optimal: {'Yes' if r['agent_steps'] == r['bfs_steps'] else 'No'}"
                )
            else:
                row.append("")
        hover.append(row)

    fig = go.Figure(data=go.Heatmap(
        z=mat,
        x=ROOMS, y=ROOMS,
        hovertext=hover, hoverinfo="text",
        colorscale="YlGnBu_r",
        colorbar=dict(title="Steps"),
        zmin=1, zmax=7,
    ))
    fig.update_layout(
        title="Agent Path Length per Start-Goal Pair (hover for details)",
        xaxis_title="Goal Room", yaxis_title="Start Room",
        width=1200, height=1000,
        font=dict(size=10),
    )
    path = os.path.join(output_dir, "interactive_heatmap.html")
    fig.write_html(path)
    print(f"  Saved: {path}")


# ============================================================
#  PLOT 2: Network Graph with Example Paths
# ============================================================

def plot_network_graph(results, output_dir):
    G = nx.Graph()
    G.add_nodes_from(ROOMS)
    G.add_edges_from(ALL_EDGES)

    # Use spring layout with hierarchy hints
    pos = nx.spring_layout(G, seed=42, k=2.5, iterations=100)

    # Example paths to highlight (diverse distances)
    example_routes = [
        ("wellness_room", "executive_suite", "#e74c3c", "wellness_room → executive_suite (6 hops)"),
        ("phone_booth_2", "phone_booth_1", "#2ecc71", "phone_booth_2 → phone_booth_1 (7 hops)"),
        ("parking", "server_room", "#3498db", "parking → server_room (5 hops)"),
        ("kitchen", "office_8", "#f39c12", "kitchen → office_8 (4 hops)"),
    ]

    fig = go.Figure()

    # Draw all edges (grey)
    for a, b in ALL_EDGES:
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        fig.add_trace(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode="lines",
            line=dict(width=1, color="#cccccc"),
            hoverinfo="none",
            showlegend=False,
        ))

    # Draw example paths
    for start, goal, color, label in example_routes:
        path = bfs_path(start, goal)
        xs, ys = [], []
        for room in path:
            x, y = pos[room]
            xs.append(x)
            ys.append(y)
        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="lines+markers",
            line=dict(width=4, color=color),
            marker=dict(size=10, color=color),
            name=label,
            text=path,
            hoverinfo="text",
        ))

    # Draw all nodes
    node_x = [pos[r][0] for r in ROOMS]
    node_y = [pos[r][1] for r in ROOMS]
    node_degree = [len(adj[r]) for r in ROOMS]
    node_text = [f"<b>{r}</b><br>Connections: {len(adj[r])}<br>Neighbors: {', '.join(sorted(adj[r]))}" for r in ROOMS]

    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        marker=dict(
            size=[8 + d * 3 for d in node_degree],
            color=node_degree,
            colorscale="Viridis",
            colorbar=dict(title="Connections", x=1.02),
            line=dict(width=1, color="white"),
        ),
        text=ROOMS,
        textposition="top center",
        textfont=dict(size=7),
        hovertext=node_text,
        hoverinfo="text",
        name="Rooms",
    ))

    fig.update_layout(
        title="VEsNA Office Navigation Graph — 50 Rooms with Example Optimal Paths",
        showlegend=True,
        width=1400, height=900,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="white",
        legend=dict(x=0, y=1, bgcolor="rgba(255,255,255,0.8)"),
    )

    path = os.path.join(output_dir, "network_graph_paths.html")
    fig.write_html(path)
    print(f"  Saved: {path}")


# ============================================================
#  PLOT 3: Interactive Training Curves (from CSV)
# ============================================================

def plot_training_curves(output_dir):
    csv_path = os.path.join(os.path.dirname(__file__), "mind", "logs", "alice_episodes.csv")
    if not os.path.exists(csv_path):
        print("  Skipping training curves (CSV not found)")
        return

    episodes, rewards, steps, outcomes = [], [], [], []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            episodes.append(int(row["episode"]))
            rewards.append(float(row["reward"]))
            steps.append(int(row["steps"]))
            outcomes.append(row["outcome"].strip())

    # Find current run
    last_reset = 0
    for i in range(1, len(episodes)):
        if episodes[i] < episodes[i - 1]:
            last_reset = i
    episodes = episodes[last_reset:]
    rewards = rewards[last_reset:]
    steps = steps[last_reset:]
    outcomes = outcomes[last_reset:]

    ep = np.array(episodes)
    rew = np.array(rewards)
    stp = np.array(steps)
    succ = np.array([1.0 if o == "success" else 0.0 for o in outcomes])

    # Rolling averages
    w = 200
    def rolling(arr, window=w):
        cs = np.cumsum(arr)
        cs = np.insert(cs, 0, 0)
        r = (cs[window:] - cs[:-window]) / window
        return np.concatenate([np.full(window - 1, np.nan), r])

    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=("Episode Reward", "Steps per Episode", "Success Rate (%)"),
        vertical_spacing=0.08,
    )

    # Reward
    fig.add_trace(go.Scattergl(x=ep, y=rew, mode="markers", marker=dict(size=1, color="rgba(70,130,180,0.1)"),
                                name="Reward (raw)", showlegend=True), row=1, col=1)
    r_avg = rolling(rew)
    fig.add_trace(go.Scatter(x=ep, y=r_avg, mode="lines", line=dict(color="red", width=2),
                              name=f"Reward (avg {w})"), row=1, col=1)

    # Steps
    fig.add_trace(go.Scattergl(x=ep, y=stp, mode="markers", marker=dict(size=1, color="rgba(34,139,34,0.1)"),
                                name="Steps (raw)", showlegend=True), row=2, col=1)
    s_avg = rolling(stp)
    fig.add_trace(go.Scatter(x=ep, y=s_avg, mode="lines", line=dict(color="red", width=2),
                              name=f"Steps (avg {w})"), row=2, col=1)

    # Success rate
    sr = rolling(succ) * 100
    fig.add_trace(go.Scatter(x=ep, y=sr, mode="lines", line=dict(color="darkorange", width=2),
                              name=f"Success % (avg {w})"), row=3, col=1)

    fig.update_layout(
        title="VEsNA DQN Training Curves — Interactive (zoom, pan, hover)",
        height=900, width=1200,
        template="plotly_white",
    )
    fig.update_yaxes(title_text="Reward", row=1, col=1)
    fig.update_yaxes(title_text="Steps", row=2, col=1)
    fig.update_yaxes(title_text="Success %", range=[0, 105], row=3, col=1)
    fig.update_xaxes(title_text="Episode", row=3, col=1)

    path = os.path.join(output_dir, "training_curves_interactive.html")
    fig.write_html(path)
    print(f"  Saved: {path}")


# ============================================================
#  PLOT 4: Evaluation Dashboard
# ============================================================

def plot_eval_dashboard(results, output_dir):
    successes = [r for r in results if r["success"]]

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Agent Steps vs BFS Optimal",
            "Reward Distribution",
            "Performance by Path Distance",
            "Path Count by Distance",
        ),
        vertical_spacing=0.12, horizontal_spacing=0.1,
    )

    # 1. Scatter: agent vs BFS
    bfs_s = [r["bfs_steps"] for r in successes]
    agt_s = [r["agent_steps"] for r in successes]
    hover_s = [f"{r['start']} → {r['goal']}<br>BFS: {r['bfs_steps']}, Agent: {r['agent_steps']}" for r in successes]

    fig.add_trace(go.Scatter(
        x=bfs_s, y=agt_s, mode="markers",
        marker=dict(size=6, color=bfs_s, colorscale="Viridis", opacity=0.7),
        text=hover_s, hoverinfo="text", name="Pairs",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=[0, 8], y=[0, 8], mode="lines",
        line=dict(color="red", dash="dash", width=2), name="Optimal (y=x)",
    ), row=1, col=1)

    # 2. Reward histogram
    rewards = [r["reward"] for r in results]
    fig.add_trace(go.Histogram(
        x=rewards, nbinsx=30, marker_color="steelblue",
        name="Rewards", hoverinfo="x+y",
    ), row=1, col=2)

    # 3. Grouped bar: avg steps by distance
    by_dist = defaultdict(list)
    for r in results:
        by_dist[r["bfs_steps"]].append(r)
    dists = sorted(by_dist.keys())
    bfs_avg = [d for d in dists]
    agt_avg = [np.mean([r["agent_steps"] for r in by_dist[d] if r["success"]]) for d in dists]

    fig.add_trace(go.Bar(x=dists, y=bfs_avg, name="BFS Optimal", marker_color="forestgreen"), row=2, col=1)
    fig.add_trace(go.Bar(x=dists, y=agt_avg, name="DQN Agent", marker_color="steelblue"), row=2, col=1)

    # 4. Pair count per distance
    counts = [len(by_dist[d]) for d in dists]
    fig.add_trace(go.Bar(
        x=dists, y=counts, marker_color="darkorange", name="Pair count",
        text=counts, textposition="auto",
    ), row=2, col=2)

    fig.update_layout(
        title="VEsNA DQN Evaluation Dashboard — All 2,450 Start-Goal Pairs",
        height=800, width=1200,
        template="plotly_white",
        barmode="group",
    )
    fig.update_xaxes(title_text="BFS Steps", row=1, col=1)
    fig.update_yaxes(title_text="Agent Steps", row=1, col=1)
    fig.update_xaxes(title_text="Reward", row=1, col=2)
    fig.update_yaxes(title_text="Count", row=1, col=2)
    fig.update_xaxes(title_text="BFS Distance", row=2, col=1)
    fig.update_yaxes(title_text="Avg Steps", row=2, col=1)
    fig.update_xaxes(title_text="BFS Distance", row=2, col=2)
    fig.update_yaxes(title_text="Number of Pairs", row=2, col=2)

    path = os.path.join(output_dir, "eval_dashboard.html")
    fig.write_html(path)
    print(f"  Saved: {path}")


# ============================================================
#  MAIN
# ============================================================

def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    eval_csv = os.path.join(project_root, "evaluation", "eval_results.csv")
    output_dir = os.path.join(project_root, "evaluation")
    os.makedirs(output_dir, exist_ok=True)

    print("Loading evaluation results...")
    results = load_eval_csv(eval_csv)
    print(f"  {len(results)} pairs loaded")
    print()

    print("Generating interactive plots (HTML — open in browser)...")
    plot_heatmap(results, output_dir)
    plot_network_graph(results, output_dir)
    plot_training_curves(output_dir)
    plot_eval_dashboard(results, output_dir)

    print()
    print("=" * 60)
    print("  All interactive plots saved to evaluation/")
    print("  Open these in your browser:")
    print(f"    - interactive_heatmap.html")
    print(f"    - network_graph_paths.html")
    print(f"    - training_curves_interactive.html")
    print(f"    - eval_dashboard.html")
    print("=" * 60)


if __name__ == "__main__":
    main()
