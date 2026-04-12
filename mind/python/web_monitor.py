"""
VEsNA Web Map Monitor — browser-based visualization of the RL agent.

Serves an interactive HTML5 Canvas map at http://0.0.0.0:8050/map

Modes:
  - DEMO: Runs inference locally with the trained checkpoint
  - LIVE: Polls the running DQN server to show Jason MAS agent in real-time

Features:
  - Switch between 11, 50, and 103 region maps
  - Load different policy checkpoints per region count
  - Side-by-side map + log panel layout

Checkpoints:
  - checkpoints/alice11.pt   (11 regions, hidden_size=64)
  - checkpoints/alice50.pt   (50 regions, hidden_size=128)
  - checkpoints/alice103.pt  (103 regions, hidden_size=128 or 512)

Usage:
    python web_monitor.py
    python web_monitor.py --checkpoint ../../checkpoints/alice103.pt
    python web_monitor.py --port 8050
"""

import argparse
import glob as glob_mod
import json
import os
import re
import sys
import threading
from collections import defaultdict, deque

import numpy as np
from flask import Flask, jsonify, request, Response

# Add mind/python to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import torch
    import torch.nn as nn
    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False

try:
    import requests as http_requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False


# ═══════════════════════════════════════════════════════════════════════════════
# Map configurations for each region count
# ═══════════════════════════════════════════════════════════════════════════════

# --- 11 regions ---
ROOM_ORDER_11 = [
    "reception", "corridor", "open_office", "outside", "common",
    "meeting_room", "senior_office_1", "senior_office_2",
    "senior_office_3", "boss_office_1", "boss_office_2",
]

EC_CONNS_11 = [
    ("corridor", "reception"), ("corridor", "open_office"),
]
DOOR_CONNS_11 = [
    ("corridor", "common"), ("corridor", "senior_office_1"),
    ("corridor", "senior_office_2"), ("corridor", "senior_office_3"),
    ("corridor", "meeting_room"),
    ("open_office", "boss_office_1"), ("open_office", "boss_office_2"),
    ("open_office", "outside"),
]

# --- 50 regions ---
ROOM_ORDER_50 = [
    "reception", "corridor", "open_office", "outside", "common",
    "meeting_room", "senior_office_1", "senior_office_2",
    "senior_office_3", "boss_office_1", "boss_office_2",
    "corridor_north", "corridor_south",
    "kitchen", "restroom_1", "storage_1",
    "meeting_room_2", "meeting_room_3", "lab_1", "lab_2", "server_room",
    "office_1", "office_2", "office_3", "office_4", "office_5",
    "lobby", "cafeteria", "gym", "restroom_2",
    "office_6", "office_7", "office_8", "office_9", "office_10",
    "archive", "training_room",
    "terrace", "parking", "conference_room", "security_desk",
    "library", "print_room", "mail_room", "executive_suite",
    "phone_booth_1", "phone_booth_2", "supply_closet",
    "lounge", "wellness_room",
]

EC_CONNS_50 = [
    ("corridor", "reception"), ("corridor", "open_office"),
    ("corridor", "corridor_north"), ("corridor", "corridor_south"),
    ("corridor_south", "lobby"),
]
DOOR_CONNS_50 = [
    ("corridor", "common"), ("corridor", "senior_office_1"),
    ("corridor", "senior_office_2"), ("corridor", "senior_office_3"),
    ("corridor", "meeting_room"), ("corridor", "restroom_1"), ("corridor", "storage_1"),
    ("open_office", "boss_office_1"), ("open_office", "boss_office_2"),
    ("open_office", "outside"), ("open_office", "print_room"),
    ("corridor_north", "meeting_room_2"), ("corridor_north", "meeting_room_3"),
    ("corridor_north", "lab_1"), ("corridor_north", "lab_2"), ("corridor_north", "server_room"),
    ("corridor_north", "office_1"), ("corridor_north", "office_2"),
    ("corridor_north", "office_3"), ("corridor_north", "office_4"), ("corridor_north", "office_5"),
    ("corridor_south", "cafeteria"), ("corridor_south", "gym"), ("corridor_south", "restroom_2"),
    ("corridor_south", "office_6"), ("corridor_south", "office_7"),
    ("corridor_south", "office_8"), ("corridor_south", "office_9"),
    ("corridor_south", "office_10"),
    ("corridor_south", "archive"), ("corridor_south", "training_room"),
    ("lobby", "parking"), ("lobby", "conference_room"), ("lobby", "security_desk"),
    ("common", "kitchen"), ("common", "library"),
    ("cafeteria", "terrace"), ("reception", "mail_room"),
    ("boss_office_1", "executive_suite"), ("library", "phone_booth_1"),
    ("gym", "lounge"), ("gym", "wellness_room"),
    ("lounge", "phone_booth_2"), ("storage_1", "supply_closet"),
]

# --- 100 regions ---
ROOM_ORDER_100 = [
    "corridor_north","office_1","office_2","office_3","office_4","office_5",
    "meeting_room_2","meeting_room_3","lab_1","lab_2","server_room","mail_room","reception",
    "corridor","open_office","boss_office_1","boss_office_2","print_room","outside",
    "senior_office_1","senior_office_2","senior_office_3","meeting_room","restroom_1","storage_1",
    "executive_suite","supply_closet","common","kitchen","library","phone_booth_1",
    "corridor_south","office_6","office_7","office_8","office_9","office_10",
    "cafeteria","gym","restroom_2","archive","training_room",
    "terrace","lounge","wellness_room","phone_booth_2",
    "lobby","security_desk","conference_room","parking",
    "corridor_east","lab_3","lab_4","lab_5","lab_6",
    "server_room_2","server_room_3","data_center","tech_office_1","tech_office_2",
    "server_maintenance","network_room","backup_power","telecom_room",
    "corridor_west","storage_2","storage_3","storage_4","storage_5","storage_6",
    "workshop","equipment_room","hazmat_storage","loading_bay",
    "recycling_center","courier_station","freight_elevator","dock_office",
    "annex_corridor","wellness_center","meditation_room","fitness_studio","yoga_room",
    "game_room","music_room","art_studio","rooftop_garden","outdoor_seating",
    "bike_storage","shower_room",
    "office_11","office_12","office_13","office_14","office_15",
    "meeting_room_6","meeting_room_7","break_room_2","pantry_2",
    "copy_center","scanner","server_room_4","server_room_5",
]

EC_CONNS_100 = [
    ("corridor","reception"),("corridor","open_office"),
    ("corridor","corridor_north"),("corridor","corridor_south"),
    ("corridor_south","lobby"),
    ("corridor_north","corridor_east"),("corridor_south","corridor_west"),
    ("corridor","annex_corridor"),
]
DOOR_CONNS_100 = [
    ("corridor","common"),("corridor","senior_office_1"),
    ("corridor","senior_office_2"),("corridor","senior_office_3"),
    ("corridor","meeting_room"),("corridor","restroom_1"),("corridor","storage_1"),
    ("open_office","boss_office_1"),("open_office","boss_office_2"),
    ("open_office","outside"),("open_office","print_room"),
    ("corridor_north","meeting_room_2"),("corridor_north","meeting_room_3"),
    ("corridor_north","lab_1"),("corridor_north","lab_2"),("corridor_north","server_room"),
    ("corridor_north","office_1"),("corridor_north","office_2"),
    ("corridor_north","office_3"),("corridor_north","office_4"),("corridor_north","office_5"),
    ("corridor_south","cafeteria"),("corridor_south","gym"),("corridor_south","restroom_2"),
    ("corridor_south","office_6"),("corridor_south","office_7"),
    ("corridor_south","office_8"),("corridor_south","office_9"),
    ("corridor_south","office_10"),
    ("corridor_south","archive"),("corridor_south","training_room"),
    ("lobby","parking"),("lobby","conference_room"),("lobby","security_desk"),
    ("common","kitchen"),("common","library"),
    ("cafeteria","terrace"),("reception","mail_room"),
    ("boss_office_1","executive_suite"),("library","phone_booth_1"),
    ("gym","lounge"),("gym","wellness_room"),
    ("lounge","phone_booth_2"),("storage_1","supply_closet"),
    ("corridor_east","lab_3"),("corridor_east","lab_4"),
    ("corridor_east","lab_5"),("corridor_east","lab_6"),
    ("corridor_east","server_room_2"),("corridor_east","server_room_3"),
    ("corridor_east","data_center"),
    ("corridor_east","tech_office_1"),("corridor_east","tech_office_2"),
    ("corridor_east","server_maintenance"),("corridor_east","network_room"),
    ("corridor_east","backup_power"),("corridor_east","telecom_room"),
    ("corridor_west","storage_2"),("corridor_west","storage_3"),
    ("corridor_west","storage_4"),("corridor_west","storage_5"),
    ("corridor_west","storage_6"),("corridor_west","workshop"),
    ("corridor_west","equipment_room"),("corridor_west","hazmat_storage"),
    ("corridor_west","loading_bay"),("corridor_west","recycling_center"),
    ("corridor_west","courier_station"),("corridor_west","freight_elevator"),
    ("corridor_west","dock_office"),
    ("annex_corridor","wellness_center"),("annex_corridor","meditation_room"),
    ("annex_corridor","fitness_studio"),("annex_corridor","yoga_room"),
    ("annex_corridor","game_room"),("annex_corridor","music_room"),
    ("annex_corridor","art_studio"),("annex_corridor","rooftop_garden"),
    ("annex_corridor","outdoor_seating"),("annex_corridor","bike_storage"),
    ("annex_corridor","shower_room"),
    ("annex_corridor","office_11"),
    ("office_11","office_12"),("office_12","office_13"),
    ("office_13","office_14"),("office_14","office_15"),
    ("office_11","meeting_room_6"),("office_12","meeting_room_7"),
    ("meeting_room_6","break_room_2"),("meeting_room_7","break_room_2"),
    ("break_room_2","pantry_2"),("break_room_2","copy_center"),
    ("copy_center","scanner"),("scanner","server_room_4"),
    ("server_room_4","server_room_5"),
]

# Map configs keyed by region count
MAP_CONFIGS = {
    11: {"rooms": ROOM_ORDER_11, "ec": EC_CONNS_11, "doors": DOOR_CONNS_11},
    50: {"rooms": ROOM_ORDER_50, "ec": EC_CONNS_50, "doors": DOOR_CONNS_50},
    100: {"rooms": ROOM_ORDER_100, "ec": EC_CONNS_100, "doors": DOOR_CONNS_100},
}


def build_adjacency(rooms, ec_conns, door_conns):
    adj = defaultdict(set)
    room_set = set(rooms)
    for a, b in ec_conns + door_conns:
        if a in room_set and b in room_set:
            adj[a].add(b)
            adj[b].add(a)
    return adj


def bfs_shortest(adj, start, goal):
    if start == goal:
        return [start]
    visited = {start}
    queue = deque([(start, [start])])
    while queue:
        node, path = queue.popleft()
        for nb in sorted(adj[node]):
            if nb == goal:
                return path + [goal]
            if nb not in visited:
                visited.add(nb)
                queue.append((nb, path + [nb]))
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# DQN Inference
# ═══════════════════════════════════════════════════════════════════════════════

if _HAS_TORCH:
    class DQNetwork3Layer(nn.Module):
        def __init__(self, state_size, action_size, hidden_size=128):
            super().__init__()
            self.fc1 = nn.Linear(state_size, hidden_size)
            self.fc2 = nn.Linear(hidden_size, hidden_size)
            self.fc3 = nn.Linear(hidden_size, action_size)

        def forward(self, x):
            return self.fc3(torch.relu(self.fc2(torch.relu(self.fc1(x)))))


# Active map state
active_map = {
    "regions": 103,
    "rooms": ROOM_ORDER_100,
    "room_to_id": {name: i for i, name in enumerate(ROOM_ORDER_100)},
    "id_to_room": {i: name for i, name in enumerate(ROOM_ORDER_100)},
    "adj": build_adjacency(ROOM_ORDER_100, EC_CONNS_100, DOOR_CONNS_100),
    "ec": EC_CONNS_100,
    "doors": DOOR_CONNS_100,
}

# Loaded policies: {region_count: {"net": policy_net, "path": path, "episode": ep}}
loaded_policies = {}
policy_net = None

# Demo state
demo_lock = threading.Lock()
demo_state = {
    "current": None, "goal": None, "path": [], "step": 0,
    "done": True, "reward": 0, "bfs_path": [], "episode": 0,
}


def switch_map(region_count):
    """Switch to a different map configuration."""
    global active_map
    cfg = MAP_CONFIGS[region_count]
    rooms = cfg["rooms"]
    active_map = {
        "regions": region_count,
        "rooms": rooms,
        "room_to_id": {name: i for i, name in enumerate(rooms)},
        "id_to_room": {i: name for i, name in enumerate(rooms)},
        "adj": build_adjacency(rooms, cfg["ec"], cfg["doors"]),
        "ec": cfg["ec"],
        "doors": cfg["doors"],
    }


def load_policy(checkpoint_path, region_count=None):
    """Load a policy checkpoint. Auto-detects region count from weights if not specified."""
    global policy_net
    if not _HAS_TORCH:
        print("WARNING: PyTorch not available, demo mode disabled")
        return False
    if not os.path.exists(checkpoint_path):
        print(f"WARNING: Checkpoint not found: {checkpoint_path}")
        return False

    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    sd = ckpt["policy_net"]

    # Handle both model formats:
    #   DQNetwork3Layer: fc1.weight, fc2.weight, fc3.weight
    #   nn.Sequential:  net.0.weight, net.2.weight, net.4.weight
    if "fc1.weight" in sd:
        inp = sd["fc1.weight"].shape[1]
        hid = sd["fc1.weight"].shape[0]
        out = sd["fc3.weight"].shape[0]
    elif "net.0.weight" in sd:
        inp = sd["net.0.weight"].shape[1]
        hid = sd["net.0.weight"].shape[0]
        out = sd["net.4.weight"].shape[0]
        # Remap keys to DQNetwork3Layer format
        sd = {
            "fc1.weight": sd["net.0.weight"], "fc1.bias": sd["net.0.bias"],
            "fc2.weight": sd["net.2.weight"], "fc2.bias": sd["net.2.bias"],
            "fc3.weight": sd["net.4.weight"], "fc3.bias": sd["net.4.bias"],
        }
    else:
        print(f"WARNING: Unknown model format in {checkpoint_path}: {list(sd.keys())}")
        return False

    net = DQNetwork3Layer(inp, out, hid)
    net.load_state_dict(sd)
    net.eval()

    detected_regions = inp // 2
    if region_count is None:
        region_count = detected_regions

    ep = ckpt.get("episode", "?")
    loaded_policies[region_count] = {
        "net": net,
        "path": checkpoint_path,
        "episode": ep,
        "detected_regions": detected_regions,
    }
    policy_net = net
    print(f"Policy loaded: {detected_regions} rooms, hidden={hid}, ep={ep} -> mapped to {region_count}-region")
    return True


def activate_policy(region_count):
    """Set the active policy_net to the one loaded for region_count."""
    global policy_net
    if region_count in loaded_policies:
        policy_net = loaded_policies[region_count]["net"]
        return True
    return False


def inference_action(current, goal):
    """Get action from policy for current->goal."""
    room_to_id = active_map["room_to_id"]
    id_to_room = active_map["id_to_room"]
    adj = active_map["adj"]
    num_rooms = len(active_map["rooms"])

    neighbors = sorted(adj[current])
    valid_ids = [room_to_id[n] for n in neighbors]

    # Build state vector matching the active policy's input size
    policy_rooms = policy_net.fc1.weight.shape[1] // 2

    state = np.zeros(policy_rooms * 2, dtype=np.float32)
    cur_id = room_to_id.get(current)
    goal_id = room_to_id.get(goal)
    if cur_id is not None and cur_id < policy_rooms:
        state[cur_id] = 1.0
    if goal_id is not None and goal_id < policy_rooms:
        state[policy_rooms + goal_id] = 1.0

    with torch.no_grad():
        q = policy_net(torch.FloatTensor(state).unsqueeze(0)).squeeze(0).numpy()

    masked = np.full(len(q), -np.inf)
    for vid in valid_ids:
        if vid < len(q):
            masked[vid] = q[vid]

    action = int(np.argmax(masked))
    action_room = id_to_room.get(action, current)
    q_info = {}
    for a in valid_ids:
        if a < len(q):
            q_info[id_to_room[a]] = float(round(q[a], 2))
    return action_room, q_info


# ═══════════════════════════════════════════════════════════════════════════════
# Checkpoint Discovery
# ═══════════════════════════════════════════════════════════════════════════════

def discover_checkpoints(project_root):
    """Find all available checkpoints organized by region count."""
    ckpt_dirs = [
        os.path.join(project_root, "checkpoints"),
        os.path.join(project_root, "checkpoints", "checkpoints"),
    ]
    found = {}  # {region_count: [{"path": ..., "episode": ..., "filename": ...}]}

    # Mapping: filename pattern -> region count
    NAME_MAP = {
        "alice11.pt": 11,
        "alice50.pt": 50,
        "alice103.pt": 103,
    }

    for ckpt_dir in ckpt_dirs:
        if not os.path.isdir(ckpt_dir):
            continue
        for f in sorted(os.listdir(ckpt_dir)):
            if not f.endswith(".pt"):
                continue
            path = os.path.join(ckpt_dir, f)

            # New naming: alice11.pt, alice50.pt, alice103.pt
            if f in NAME_MAP:
                regions = NAME_MAP[f]
                # Extract episode from checkpoint metadata
                episode = 0
                try:
                    ckpt = torch.load(path, map_location="cpu", weights_only=False)
                    episode = ckpt.get("episode", 0)
                except Exception:
                    pass
            # Legacy naming: alice_navigation_rl_100_ep30000.pt
            else:
                m = re.match(r"alice_navigation_rl_(\d+)_ep(\d+)\.pt", f)
                if m:
                    regions = int(m.group(1))
                    episode = int(m.group(2))
                else:
                    continue

            found.setdefault(regions, []).append({
                "path": path,
                "episode": episode,
                "filename": f,
            })

    # Sort by episode descending within each region count
    for r in found:
        found[r].sort(key=lambda x: x["episode"], reverse=True)

    return found


# ═══════════════════════════════════════════════════════════════════════════════
# Flask App
# ═══════════════════════════════════════════════════════════════════════════════

app = Flask(__name__)
checkpoint_registry = {}  # populated at startup


@app.route("/")
def index():
    return Response(MAP_HTML, mimetype="text/html")

@app.route("/map")
def serve_map():
    return Response(MAP_HTML, mimetype="text/html")


@app.route("/api/rooms")
def api_rooms():
    """Return room list, grid positions, connections for the JS client."""
    return jsonify({
        "rooms": active_map["rooms"],
        "room_to_id": active_map["room_to_id"],
        "ec_conns": active_map["ec"],
        "door_conns": active_map["doors"],
        "regions": active_map["regions"],
    })


@app.route("/api/maps")
def api_maps():
    """Return available maps and checkpoints."""
    policies = {}
    for rc, ckpts in checkpoint_registry.items():
        policies[str(rc)] = [{"filename": c["filename"], "episode": c["episode"]} for c in ckpts]
    return jsonify({
        "available_maps": [11, 50, 100],
        "current_map": active_map["regions"],
        "policies": policies,
        "loaded_policies": {str(k): {"episode": v["episode"], "detected_regions": v["detected_regions"]}
                           for k, v in loaded_policies.items()},
    })


@app.route("/api/switch", methods=["POST"])
def api_switch():
    """Switch map and/or policy."""
    data = request.get_json(silent=True) or {}
    regions = data.get("regions")
    policy_regions = data.get("policy_regions")
    checkpoint_file = data.get("checkpoint")

    result = {}

    if regions and int(regions) in MAP_CONFIGS:
        switch_map(int(regions))
        result["map_switched"] = int(regions)
        # Reset demo state
        with demo_lock:
            demo_state["current"] = None
            demo_state["goal"] = None
            demo_state["path"] = []
            demo_state["step"] = 0
            demo_state["done"] = True
        # Auto-activate matching policy if no explicit policy_regions given
        if policy_regions is None and int(regions) in loaded_policies:
            activate_policy(int(regions))
            result["policy_activated"] = int(regions)

    if policy_regions is not None:
        pr = int(policy_regions)
        if pr in loaded_policies:
            activate_policy(pr)
            result["policy_activated"] = pr
        elif checkpoint_file:
            # Find and load the specific checkpoint
            for rc, ckpts in checkpoint_registry.items():
                for c in ckpts:
                    if c["filename"] == checkpoint_file:
                        load_policy(c["path"], region_count=pr)
                        activate_policy(pr)
                        result["policy_loaded"] = checkpoint_file
                        break

    if not result:
        return jsonify({"error": "No valid switch parameters"}), 400

    return jsonify(result)


@app.route("/api/demo/start", methods=["POST"])
def demo_start():
    """Start a new demo episode."""
    if policy_net is None:
        return jsonify({"error": "No policy loaded"}), 400

    data = request.get_json(silent=True) or {}
    rooms = active_map["rooms"]
    non_corridors = [r for r in rooms if "corridor" not in r]

    start = data.get("start") or np.random.choice(non_corridors)
    goal = data.get("goal") or np.random.choice([r for r in non_corridors if r != start])
    bfs_path = bfs_shortest(active_map["adj"], start, goal)

    with demo_lock:
        demo_state["current"] = start
        demo_state["goal"] = goal
        demo_state["path"] = [start]
        demo_state["step"] = 0
        demo_state["done"] = False
        demo_state["reward"] = 0
        demo_state["bfs_path"] = bfs_path
        demo_state["episode"] += 1

    return jsonify({
        "current": start, "goal": goal,
        "bfs_path": bfs_path, "bfs_steps": len(bfs_path) - 1,
        "episode": demo_state["episode"],
    })


@app.route("/api/demo/step", methods=["POST"])
def demo_step():
    """Execute one inference step."""
    with demo_lock:
        if demo_state["done"] or demo_state["current"] is None:
            return jsonify({"error": "No active episode. Call /api/demo/start first"}), 400

        current = demo_state["current"]
        goal = demo_state["goal"]

        if current == goal:
            demo_state["done"] = True
            demo_state["reward"] = 100 - demo_state["step"]
            return jsonify({**demo_state, "status": "goal_reached"})

        if demo_state["step"] >= 300:
            demo_state["done"] = True
            return jsonify({**demo_state, "status": "timeout"})

        next_room, q_info = inference_action(current, goal)
        demo_state["current"] = next_room
        demo_state["path"].append(next_room)
        demo_state["step"] += 1

        if next_room == goal:
            demo_state["done"] = True
            demo_state["reward"] = 100 - demo_state["step"]
            status = "goal_reached"
        else:
            status = "moving"

        return jsonify({
            **demo_state,
            "action": next_room,
            "q_values": q_info,
            "status": status,
        })


@app.route("/api/demo/state")
def demo_get_state():
    with demo_lock:
        return jsonify(demo_state)


@app.route("/api/live")
def live_proxy():
    """Proxy to the running DQN server's monitor endpoint."""
    server = request.args.get("server", "http://localhost:5000")
    agent_id = request.args.get("agent", "alice103")
    try:
        resp = http_requests.get(f"{server}/monitor/{agent_id}", timeout=1)
        data = resp.json()
        id_to_room = active_map["id_to_room"]
        data["current_name"] = id_to_room.get(data.get("current", 0), "?")
        data["goal_name"] = id_to_room.get(data.get("goal", 0), "?")
        path_ids = data.get("path", [])
        data["path_names"] = [id_to_room.get(p, "?") for p in path_ids]
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 502


# ═══════════════════════════════════════════════════════════════════════════════
# HTML/CSS/JS — Single-page map viewer
# ═══════════════════════════════════════════════════════════════════════════════

MAP_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>VEsNA — Live Navigation Monitor</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #1e2330; color: #ddd; font-family: 'Consolas', 'Monaco', monospace; overflow: hidden; }
#top-bar {
    background: #161a25; padding: 8px 16px; display: flex; align-items: center;
    gap: 12px; border-bottom: 1px solid #333; height: 44px; flex-wrap: nowrap;
}
#top-bar h1 { font-size: 15px; color: #f0c040; white-space: nowrap; }
#top-bar .info { font-size: 12px; color: #aaa; }
#top-bar .info b { color: #eee; }
#top-bar .info .optimal { color: #4f4; }
#top-bar .info .suboptimal { color: #fa4; }
.btn {
    padding: 5px 14px; border: 1px solid #555; background: #2a2f40;
    color: #ddd; cursor: pointer; font-size: 12px; font-family: inherit;
    border-radius: 4px; white-space: nowrap;
}
.btn:hover { background: #3a4060; border-color: #888; }
.btn.active { background: #405020; border-color: #6a4; color: #6f4; }
.btn.primary { background: #304060; border-color: #58a; color: #8cf; }
select, input[type=range] { background: #2a2f40; color: #ddd; border: 1px solid #555; font-family: inherit; font-size: 12px; border-radius: 3px; }
select { padding: 4px 6px; }

/* Main layout: map on left, log on right */
#main-wrap {
    display: flex; width: 100vw; height: calc(100vh - 44px);
}
#canvas-wrap { position: relative; flex: 1; min-width: 0; }
canvas { display: block; width: 100%; height: 100%; }

#right-panel {
    width: 340px; min-width: 280px; max-width: 400px;
    background: #161a25; border-left: 1px solid #333;
    display: flex; flex-direction: column;
}
#right-panel-header {
    padding: 10px 12px 8px; border-bottom: 1px solid #333;
    font-size: 13px; color: #f0c040; font-weight: bold;
}
#log-panel {
    flex: 1; padding: 8px 12px; font-size: 11px; overflow-y: auto; line-height: 1.6;
}
#log-panel .step-log { color: #bbb; }
#log-panel .step-log .room { color: #8cf; }
#log-panel .step-log .q { color: #aaa; }
#log-panel .success { color: #4f4; font-weight: bold; }
#log-panel .fail { color: #f44; font-weight: bold; }

#legend {
    position: absolute; bottom: 10px; left: 10px; background: rgba(20,24,35,0.92);
    border: 1px solid #444; border-radius: 6px; padding: 10px; font-size: 11px;
}
#legend .item { display: flex; align-items: center; gap: 8px; margin: 3px 0; }
#legend .swatch { width: 14px; height: 14px; border-radius: 3px; border: 1px solid #555; }

.dropdown-group { display: flex; align-items: center; gap: 4px; }
.dropdown-group label { font-size: 11px; color: #aaa; white-space: nowrap; }
</style>
</head>
<body>

<div id="top-bar">
    <h1>VEsNA Navigation Monitor</h1>

    <div class="dropdown-group">
        <label>Map:</label>
        <select id="sel-map">
            <option value="11">11 Regions (11 rooms)</option>
            <option value="50">50 Regions (50 rooms)</option>
            <option value="103" selected>103 Regions (103 rooms)</option>
        </select>
    </div>

    <div class="dropdown-group">
        <label>Policy:</label>
        <select id="sel-policy"></select>
    </div>

    <button class="btn primary" id="btn-start">New Episode</button>
    <button class="btn" id="btn-step">Step</button>
    <button class="btn" id="btn-auto">Auto-play</button>
    <label style="font-size:12px; color:#aaa;">Speed:
        <input type="range" id="speed" min="50" max="1500" value="400" style="width:80px; vertical-align:middle;">
    </label>
    <label style="font-size:12px; color:#aaa;">Start:
        <select id="sel-start"><option value="">Random</option></select>
    </label>
    <label style="font-size:12px; color:#aaa;">Goal:
        <select id="sel-goal"><option value="">Random</option></select>
    </label>
    <span class="info" id="status-info">Ready</span>
</div>

<div id="main-wrap">
    <div id="canvas-wrap">
        <canvas id="map"></canvas>
        <div id="legend">
            <div class="item"><div class="swatch" style="background:#ff3c3c"></div> Agent</div>
            <div class="item"><div class="swatch" style="background:#32e632"></div> Goal</div>
            <div class="item"><div class="swatch" style="background:#b06ce6"></div> Path taken</div>
            <div class="item"><div class="swatch" style="background:#28af41"></div> Open passage</div>
            <div class="item"><div class="swatch" style="background:#606878"></div> Door</div>
        </div>
    </div>

    <div id="right-panel">
        <div id="right-panel-header">Episode Log</div>
        <div id="log-panel"></div>
    </div>
</div>

<script>
// ══════════════════════════════════════════════════════════════
// Grid layouts for each map size
// ══════════════════════════════════════════════════════════════

const GRIDS = {
    11: {
        corridor:[[1,1],[2,1],[3,1],[4,1]],
        reception:[[0,1]],
        open_office:[[2,2],[3,2]],
        common:[[0,2]],
        meeting_room:[[1,0]],
        senior_office_1:[[2,0]],
        senior_office_2:[[3,0]],
        senior_office_3:[[4,0]],
        boss_office_1:[[2,3]],
        boss_office_2:[[3,3]],
        outside:[[4,3]],
    },
    50: {
        corridor_north:[[0,0],[1,0],[2,0],[3,0],[4,0],[5,0],[6,0],[7,0],[8,0],[9,0]],
        office_1:[[0,1]],office_2:[[1,1]],office_3:[[2,1]],office_4:[[3,1]],office_5:[[4,1]],
        meeting_room_2:[[6,1]],meeting_room_3:[[7,1]],lab_1:[[8,1]],lab_2:[[9,1]],
        server_room:[[0,2]],mail_room:[[1,2]],reception:[[2,2]],
        corridor:[[0,3],[1,3],[2,3],[3,3],[4,3],[5,3],[6,3],[7,3],[8,3],[9,3]],
        open_office:[[0,4],[1,4],[2,4],[3,4]],
        boss_office_1:[[4,4]],boss_office_2:[[5,4]],print_room:[[6,4]],outside:[[7,4]],
        senior_office_1:[[0,5]],senior_office_2:[[1,5]],senior_office_3:[[2,5]],
        meeting_room:[[3,5]],restroom_1:[[4,5]],storage_1:[[5,5]],
        executive_suite:[[6,5]],supply_closet:[[7,5]],
        common:[[0,6]],kitchen:[[1,6]],library:[[2,6]],phone_booth_1:[[3,6]],
        corridor_south:[[0,7],[1,7],[2,7],[3,7],[4,7],[5,7],[6,7],[7,7],[8,7],[9,7]],
        office_6:[[0,8]],office_7:[[1,8]],office_8:[[2,8]],office_9:[[3,8]],office_10:[[4,8]],
        cafeteria:[[5,8]],gym:[[6,8],[7,8]],restroom_2:[[8,8]],archive:[[9,8]],
        training_room:[[0,9]],terrace:[[1,9]],lounge:[[2,9]],wellness_room:[[3,9]],phone_booth_2:[[4,9]],
        lobby:[[0,10],[1,10],[2,10],[3,10]],security_desk:[[4,10]],conference_room:[[5,10]],parking:[[6,10]],
    },
    100: {
        corridor_north:[[0,0],[1,0],[2,0],[3,0],[4,0],[5,0],[6,0],[7,0],[8,0],[9,0]],
        office_1:[[0,1]],office_2:[[1,1]],office_3:[[2,1]],office_4:[[3,1]],office_5:[[4,1]],
        meeting_room_2:[[6,1]],meeting_room_3:[[7,1]],lab_1:[[8,1]],lab_2:[[9,1]],
        server_room:[[0,2]],mail_room:[[1,2]],reception:[[2,2]],
        corridor:[[0,3],[1,3],[2,3],[3,3],[4,3],[5,3],[6,3],[7,3],[8,3],[9,3]],
        open_office:[[0,4],[1,4],[2,4],[3,4]],
        boss_office_1:[[4,4]],boss_office_2:[[5,4]],print_room:[[6,4]],outside:[[7,4]],
        senior_office_1:[[0,5]],senior_office_2:[[1,5]],senior_office_3:[[2,5]],
        meeting_room:[[3,5]],restroom_1:[[4,5]],storage_1:[[5,5]],
        executive_suite:[[6,5]],supply_closet:[[7,5]],
        common:[[0,6]],kitchen:[[1,6]],library:[[2,6]],phone_booth_1:[[3,6]],
        corridor_south:[[0,7],[1,7],[2,7],[3,7],[4,7],[5,7],[6,7],[7,7],[8,7],[9,7]],
        office_6:[[0,8]],office_7:[[1,8]],office_8:[[2,8]],office_9:[[3,8]],office_10:[[4,8]],
        cafeteria:[[5,8]],gym:[[6,8],[7,8]],restroom_2:[[8,8]],archive:[[9,8]],
        training_room:[[0,9]],terrace:[[1,9]],lounge:[[2,9]],wellness_room:[[3,9]],phone_booth_2:[[4,9]],
        lobby:[[0,10],[1,10],[2,10],[3,10]],security_desk:[[4,10]],conference_room:[[5,10]],parking:[[6,10]],
        corridor_east:[[11,0],[11,1],[11,2],[11,3],[11,4]],
        lab_3:[[12,0]],lab_4:[[13,0]],lab_5:[[14,0]],
        lab_6:[[12,1]],server_room_2:[[13,1]],server_room_3:[[14,1]],
        data_center:[[12,2]],tech_office_1:[[13,2]],tech_office_2:[[14,2]],
        server_maintenance:[[12,3]],network_room:[[13,3]],backup_power:[[14,3]],
        telecom_room:[[12,4]],
        corridor_west:[[16,0],[16,1],[16,2],[16,3],[16,4]],
        storage_2:[[17,0]],storage_3:[[18,0]],storage_4:[[19,0]],
        storage_5:[[17,1]],storage_6:[[18,1]],workshop:[[19,1]],
        equipment_room:[[17,2]],hazmat_storage:[[18,2]],loading_bay:[[19,2]],
        recycling_center:[[17,3]],courier_station:[[18,3]],freight_elevator:[[19,3]],
        dock_office:[[17,4]],
        annex_corridor:[[11,5],[11,6],[11,7],[11,8]],
        wellness_center:[[12,5]],meditation_room:[[13,5]],fitness_studio:[[14,5]],
        yoga_room:[[12,6]],game_room:[[13,6]],music_room:[[14,6]],
        art_studio:[[12,7]],rooftop_garden:[[13,7]],outdoor_seating:[[14,7]],
        bike_storage:[[12,8]],shower_room:[[13,8]],
        office_11:[[11,10]],office_12:[[12,10]],office_13:[[13,10]],
        office_14:[[14,10]],office_15:[[15,10]],
        meeting_room_6:[[11,11]],meeting_room_7:[[12,11]],
        break_room_2:[[13,11]],pantry_2:[[14,11]],
        copy_center:[[11,12]],scanner:[[12,12]],server_room_4:[[13,12]],server_room_5:[[14,12]],
    }
};

const EC_MAP = {
    11: [
        ["corridor","reception"],["corridor","open_office"],
    ],
    50: [
        ["corridor","reception"],["corridor","open_office"],
        ["corridor","corridor_north"],["corridor","corridor_south"],
        ["corridor_south","lobby"],
    ],
    100: [
        ["corridor","reception"],["corridor","open_office"],
        ["corridor","corridor_north"],["corridor","corridor_south"],
        ["corridor_south","lobby"],
        ["corridor_north","corridor_east"],["corridor_south","corridor_west"],
        ["corridor","annex_corridor"],
    ]
};

const DOOR_MAP = {
    11: [
        ["corridor","common"],["corridor","senior_office_1"],["corridor","senior_office_2"],
        ["corridor","senior_office_3"],["corridor","meeting_room"],
        ["open_office","boss_office_1"],["open_office","boss_office_2"],
        ["open_office","outside"],
    ],
    50: [
        ["corridor","common"],["corridor","senior_office_1"],["corridor","senior_office_2"],
        ["corridor","senior_office_3"],["corridor","meeting_room"],["corridor","restroom_1"],
        ["corridor","storage_1"],["open_office","boss_office_1"],["open_office","boss_office_2"],
        ["open_office","outside"],["open_office","print_room"],
        ["corridor_north","meeting_room_2"],["corridor_north","meeting_room_3"],
        ["corridor_north","lab_1"],["corridor_north","lab_2"],["corridor_north","server_room"],
        ["corridor_north","office_1"],["corridor_north","office_2"],
        ["corridor_north","office_3"],["corridor_north","office_4"],["corridor_north","office_5"],
        ["corridor_south","cafeteria"],["corridor_south","gym"],["corridor_south","restroom_2"],
        ["corridor_south","office_6"],["corridor_south","office_7"],
        ["corridor_south","office_8"],["corridor_south","office_9"],
        ["corridor_south","office_10"],["corridor_south","archive"],["corridor_south","training_room"],
        ["lobby","parking"],["lobby","conference_room"],["lobby","security_desk"],
        ["common","kitchen"],["common","library"],["cafeteria","terrace"],["reception","mail_room"],
        ["boss_office_1","executive_suite"],["library","phone_booth_1"],
        ["gym","lounge"],["gym","wellness_room"],["lounge","phone_booth_2"],
        ["storage_1","supply_closet"],
    ],
    100: [
        ["corridor","common"],["corridor","senior_office_1"],["corridor","senior_office_2"],
        ["corridor","senior_office_3"],["corridor","meeting_room"],["corridor","restroom_1"],
        ["corridor","storage_1"],["open_office","boss_office_1"],["open_office","boss_office_2"],
        ["open_office","outside"],["open_office","print_room"],
        ["corridor_north","meeting_room_2"],["corridor_north","meeting_room_3"],
        ["corridor_north","lab_1"],["corridor_north","lab_2"],["corridor_north","server_room"],
        ["corridor_north","office_1"],["corridor_north","office_2"],
        ["corridor_north","office_3"],["corridor_north","office_4"],["corridor_north","office_5"],
        ["corridor_south","cafeteria"],["corridor_south","gym"],["corridor_south","restroom_2"],
        ["corridor_south","office_6"],["corridor_south","office_7"],
        ["corridor_south","office_8"],["corridor_south","office_9"],
        ["corridor_south","office_10"],["corridor_south","archive"],["corridor_south","training_room"],
        ["lobby","parking"],["lobby","conference_room"],["lobby","security_desk"],
        ["common","kitchen"],["common","library"],["cafeteria","terrace"],["reception","mail_room"],
        ["boss_office_1","executive_suite"],["library","phone_booth_1"],
        ["gym","lounge"],["gym","wellness_room"],["lounge","phone_booth_2"],
        ["storage_1","supply_closet"],
        ["corridor_east","lab_3"],["corridor_east","lab_4"],["corridor_east","lab_5"],
        ["corridor_east","lab_6"],["corridor_east","server_room_2"],["corridor_east","server_room_3"],
        ["corridor_east","data_center"],["corridor_east","tech_office_1"],
        ["corridor_east","tech_office_2"],["corridor_east","server_maintenance"],
        ["corridor_east","network_room"],["corridor_east","backup_power"],["corridor_east","telecom_room"],
        ["corridor_west","storage_2"],["corridor_west","storage_3"],["corridor_west","storage_4"],
        ["corridor_west","storage_5"],["corridor_west","storage_6"],["corridor_west","workshop"],
        ["corridor_west","equipment_room"],["corridor_west","hazmat_storage"],
        ["corridor_west","loading_bay"],["corridor_west","recycling_center"],
        ["corridor_west","courier_station"],["corridor_west","freight_elevator"],
        ["corridor_west","dock_office"],
        ["annex_corridor","wellness_center"],["annex_corridor","meditation_room"],
        ["annex_corridor","fitness_studio"],["annex_corridor","yoga_room"],
        ["annex_corridor","game_room"],["annex_corridor","music_room"],
        ["annex_corridor","art_studio"],["annex_corridor","rooftop_garden"],
        ["annex_corridor","outdoor_seating"],["annex_corridor","bike_storage"],
        ["annex_corridor","shower_room"],
        ["annex_corridor","office_11"],
        ["office_11","office_12"],["office_12","office_13"],
        ["office_13","office_14"],["office_14","office_15"],
        ["office_11","meeting_room_6"],["office_12","meeting_room_7"],
        ["meeting_room_6","break_room_2"],["meeting_room_7","break_room_2"],
        ["break_room_2","pantry_2"],["break_room_2","copy_center"],
        ["copy_center","scanner"],["scanner","server_room_4"],["server_room_4","server_room_5"],
    ]
};

const WINGS_MAP = {
    11: [
        {label:"CORRIDOR HUB",c1:0,r1:0,c2:4,r2:1,color:"rgba(255,220,100,0.08)"},
        {label:"OFFICES",c1:0,r1:2,c2:4,r2:3,color:"rgba(100,180,180,0.08)"},
    ],
    50: [
        {label:"NORTH WING",c1:0,r1:0,c2:9,r2:2,color:"rgba(255,220,100,0.08)"},
        {label:"CENTRAL HUB",c1:0,r1:3,c2:9,r2:6,color:"rgba(100,180,180,0.08)"},
        {label:"SOUTH WING",c1:0,r1:7,c2:9,r2:9,color:"rgba(200,100,100,0.08)"},
        {label:"LOBBY",c1:0,r1:10,c2:6,r2:10,color:"rgba(100,150,200,0.08)"},
    ],
    100: [
        {label:"NORTH WING",c1:0,r1:0,c2:9,r2:2,color:"rgba(255,220,100,0.08)"},
        {label:"CENTRAL HUB",c1:0,r1:3,c2:9,r2:6,color:"rgba(100,180,180,0.08)"},
        {label:"SOUTH WING",c1:0,r1:7,c2:9,r2:9,color:"rgba(200,100,100,0.08)"},
        {label:"LOBBY",c1:0,r1:10,c2:6,r2:10,color:"rgba(100,150,200,0.08)"},
        {label:"EAST WING",c1:11,r1:0,c2:14,r2:4,color:"rgba(100,200,220,0.08)"},
        {label:"WEST WING",c1:16,r1:0,c2:19,r2:4,color:"rgba(180,100,220,0.08)"},
        {label:"ANNEX",c1:11,r1:5,c2:14,r2:8,color:"rgba(100,200,100,0.08)"},
        {label:"EXTENDED",c1:11,r1:10,c2:15,r2:12,color:"rgba(255,180,100,0.08)"},
    ]
};

// ── Active map state ──
let currentMapSize = 100;
let GRID = GRIDS[100];
let EC = EC_MAP[100];
let DOORS = DOOR_MAP[100];
let WINGS = WINGS_MAP[100];

// ── Room colors ──
function roomColor(name) {
    if (name.includes("corridor")) return "#f0da73";
    if (name.match(/office|senior|boss|executive/)) return "#8cc6e1";
    if (name.match(/meeting|conference|training/)) return "#c3a5da";
    if (name.match(/lab|server|tech|data|network|backup|telecom|maintenance|scanner/)) return "#e4aa64";
    if (["common","kitchen","cafeteria","break_room_2","pantry_2"].includes(name)) return "#91d291";
    if (["outside","terrace","parking","rooftop_garden","outdoor_seating"].includes(name)) return "#73c88c";
    if (["lobby","reception"].includes(name)) return "#e89e78";
    if (name.match(/restroom|storage|supply|archive|mail|print|security|copy|hazmat|loading|recycling|courier|freight|dock|equipment|workshop/)) return "#c0c0c0";
    if (name.match(/gym|lounge|wellness|phone|library|game|music|art|yoga|meditation|fitness|bike|shower/)) return "#e4a2bc";
    return "#b4b4b4";
}

// ── Pre-compute room bounding boxes ──
let roomRects = {};
function recomputeRects() {
    roomRects = {};
    for (const [name, cells] of Object.entries(GRID)) {
        const cs = cells.map(c=>c[0]), rs = cells.map(c=>c[1]);
        roomRects[name] = {
            c: Math.min(...cs), r: Math.min(...rs),
            w: Math.max(...cs) - Math.min(...cs) + 1,
            h: Math.max(...rs) - Math.min(...rs) + 1,
        };
    }
}
recomputeRects();

function roomCenter(name) {
    const r = roomRects[name];
    if (!r) return null;
    return { x: r.c + r.w/2, y: r.r + r.h/2 };
}

// ── Canvas setup ──
const canvas = document.getElementById("map");
const ctx = canvas.getContext("2d");
let CELL = 62;
let PAD = 50;

function resizeCanvas() {
    const wrap = document.getElementById("canvas-wrap");
    canvas.width = wrap.clientWidth * devicePixelRatio;
    canvas.height = wrap.clientHeight * devicePixelRatio;
    canvas.style.width = wrap.clientWidth + "px";
    canvas.style.height = wrap.clientHeight + "px";
    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
}
window.addEventListener("resize", resizeCanvas);
resizeCanvas();

// ── State ──
let state = { current: null, goal: null, path: [], step: 0, done: true, reward: 0, bfs_path: [], episode: 0 };
let autoPlay = false;
let autoTimer = null;

// ── Populate selects ──
function populateRoomSelects() {
    const selStart = document.getElementById("sel-start");
    const selGoal = document.getElementById("sel-goal");
    // Clear existing options
    selStart.innerHTML = '<option value="">Random</option>';
    selGoal.innerHTML = '<option value="">Random</option>';
    const rooms = Object.keys(GRID).sort();
    rooms.forEach(r => {
        selStart.add(new Option(r.replace(/_/g," "), r));
        selGoal.add(new Option(r.replace(/_/g," "), r));
    });
}
populateRoomSelects();

// ── Map switching ──
async function switchMap(size) {
    currentMapSize = size;
    GRID = GRIDS[size];
    EC = EC_MAP[size];
    DOORS = DOOR_MAP[size];
    WINGS = WINGS_MAP[size];
    recomputeRects();
    populateRoomSelects();

    // Adjust cell size based on map complexity
    if (size === 11) {
        CELL = 100; PAD = 80;
    } else if (size === 50) {
        CELL = 62; PAD = 50;
    } else {
        CELL = 62; PAD = 50;
    }

    // Notify server — switch both map AND policy together
    await fetch("/api/switch", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({regions: size, policy_regions: size}),
    });

    // Reset state
    state = { current: null, goal: null, path: [], step: 0, done: true, reward: 0, bfs_path: [], episode: 0 };
    stopAuto();
    document.getElementById("log-panel").innerHTML = "";
    addLog(`Switched to <b>${size}-region</b> map`, "step-log");
    updateStatus();
    resizeCanvas();
}

async function switchPolicy(policyRegions) {
    const resp = await fetch("/api/switch", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({policy_regions: policyRegions}),
    });
    const data = await resp.json();
    addLog(`Loaded <b>${policyRegions}-region</b> policy`, "step-log");
    updateStatus();
}

// ── Load available policies ──
async function loadPolicyOptions() {
    const resp = await fetch("/api/maps");
    const data = await resp.json();
    const sel = document.getElementById("sel-policy");
    sel.innerHTML = "";

    // Add loaded policies
    const loaded = data.loaded_policies || {};
    for (const [rc, info] of Object.entries(loaded)) {
        const opt = new Option(`${rc}-region (ep ${info.episode})`, rc);
        sel.add(opt);
    }

    // If current map has a matching policy, select it
    if (loaded[String(currentMapSize)]) {
        sel.value = String(currentMapSize);
    }
}

// ── Drawing ──
function draw() {
    const W = canvas.width / devicePixelRatio;
    const H = canvas.height / devicePixelRatio;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = "#1e2330";
    ctx.fillRect(0, 0, W, H);

    const pathSet = new Set(state.path || []);
    const t = Date.now() / 1000;

    // Wing backgrounds
    for (const w of WINGS) {
        ctx.fillStyle = w.color;
        ctx.fillRect(PAD + w.c1*CELL - 4, PAD + w.r1*CELL - 4,
                     (w.c2 - w.c1 + 1)*CELL + 8, (w.r2 - w.r1 + 1)*CELL + 8);
        ctx.fillStyle = "rgba(200,200,200,0.25)";
        ctx.font = "10px Consolas";
        ctx.fillText(w.label, PAD + w.c1*CELL, PAD + w.r1*CELL - 6);
    }

    // Connections — open passages (green)
    for (const [a,b] of EC) {
        const ca = roomCenter(a), cb = roomCenter(b);
        if (!ca || !cb) continue;
        ctx.strokeStyle = "#28af41"; ctx.lineWidth = 2.5; ctx.globalAlpha = 0.6;
        ctx.beginPath();
        ctx.moveTo(PAD + ca.x*CELL, PAD + ca.y*CELL);
        ctx.lineTo(PAD + cb.x*CELL, PAD + cb.y*CELL);
        ctx.stroke();
    }
    // Connections — doors (gray)
    for (const [a,b] of DOORS) {
        const ca = roomCenter(a), cb = roomCenter(b);
        if (!ca || !cb) continue;
        ctx.strokeStyle = "#464e5a"; ctx.lineWidth = 1; ctx.globalAlpha = 0.5;
        ctx.beginPath();
        ctx.moveTo(PAD + ca.x*CELL, PAD + ca.y*CELL);
        ctx.lineTo(PAD + cb.x*CELL, PAD + cb.y*CELL);
        ctx.stroke();
    }
    ctx.globalAlpha = 1;

    // Rooms
    for (const [name, rect] of Object.entries(roomRects)) {
        const x = PAD + rect.c * CELL + 1;
        const y = PAD + rect.r * CELL + 1;
        const w = rect.w * CELL - 2;
        const h = rect.h * CELL - 2;

        let fill = roomColor(name);
        let border = "#555";
        let bw = 1;

        if (name === state.current) {
            fill = "#ff3c3c"; border = "#fff"; bw = 3;
        } else if (name === state.goal) {
            fill = "#32e632"; border = "#fff"; bw = 3;
        } else if (pathSet.has(name)) {
            fill = "#7b4fa0"; border = "#b06ce6"; bw = 2;
        }

        ctx.fillStyle = fill;
        ctx.fillRect(x, y, w, h);
        ctx.strokeStyle = border; ctx.lineWidth = bw;
        ctx.strokeRect(x, y, w, h);

        // Label
        if (w > 28 && h > 14) {
            let label = name.replace(/_/g," ").replace(/room/g,"rm");
            if (label.length > 14) label = label.substring(0, 12) + "..";
            const brightness = parseInt(fill.substr(1,2),16)*0.299 +
                               parseInt(fill.substr(3,2),16)*0.587 +
                               parseInt(fill.substr(5,2),16)*0.114;
            ctx.fillStyle = brightness > 140 ? "#222" : "#eee";
            ctx.font = w > 50 ? "10px Consolas" : "8px Consolas";
            ctx.textAlign = "center"; ctx.textBaseline = "middle";
            ctx.fillText(label, x + w/2, y + h/2);
        }
    }

    // Path trace — PURPLE
    if (state.path && state.path.length > 1) {
        ctx.strokeStyle = "#b06ce6"; ctx.lineWidth = 3; ctx.globalAlpha = 0.85;
        ctx.beginPath();
        for (let i = 0; i < state.path.length; i++) {
            const c = roomCenter(state.path[i]);
            if (!c) continue;
            if (i === 0) ctx.moveTo(PAD + c.x*CELL, PAD + c.y*CELL);
            else ctx.lineTo(PAD + c.x*CELL, PAD + c.y*CELL);
        }
        ctx.stroke();
        ctx.globalAlpha = 1;
    }

    // Agent marker (pulsing)
    if (state.current && roomCenter(state.current)) {
        const c = roomCenter(state.current);
        const px = PAD + c.x*CELL, py = PAD + c.y*CELL;
        const pulse = 3 * Math.abs(Math.sin(t * 3));
        ctx.beginPath(); ctx.arc(px, py, 16+pulse, 0, Math.PI*2);
        ctx.strokeStyle = "#fff"; ctx.lineWidth = 2.5; ctx.stroke();
        ctx.beginPath(); ctx.arc(px, py, 13, 0, Math.PI*2);
        ctx.fillStyle = "#ff3030"; ctx.fill();
        ctx.fillStyle = "#fff"; ctx.font = "bold 14px Consolas";
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillText("A", px, py);
    }

    // Goal marker
    if (state.goal && roomCenter(state.goal) && state.goal !== state.current) {
        const c = roomCenter(state.goal);
        const px = PAD + c.x*CELL, py = PAD + c.y*CELL;
        const pulse = 2 * Math.abs(Math.sin(t * 2 + 1));
        ctx.beginPath(); ctx.arc(px, py, 14+pulse, 0, Math.PI*2);
        ctx.strokeStyle = "#fff"; ctx.lineWidth = 2.5; ctx.stroke();
        ctx.beginPath(); ctx.arc(px, py, 11, 0, Math.PI*2);
        ctx.fillStyle = "#20c820"; ctx.fill();
        ctx.fillStyle = "#fff"; ctx.font = "bold 14px Consolas";
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillText("G", px, py);
    }

    requestAnimationFrame(draw);
}

// ── Status bar update ──
function updateStatus() {
    const info = document.getElementById("status-info");
    if (!state.current) { info.innerHTML = "Ready — click <b>New Episode</b>"; return; }
    const bfsSteps = state.bfs_path ? state.bfs_path.length - 1 : "?";
    const agentSteps = state.step;
    let optStr = `BFS: ${bfsSteps} | Agent: ${agentSteps}`;
    if (state.done && agentSteps === bfsSteps) {
        optStr += ' <span class="optimal">OPTIMAL</span>';
    } else if (state.done && agentSteps > bfsSteps) {
        optStr += ' <span class="suboptimal">+' + (agentSteps - bfsSteps) + '</span>';
    }
    const doneStr = state.done ? (state.reward > 0 ? " | GOAL REACHED" : " | TIMEOUT") : "";
    info.innerHTML = `Ep: <b>${state.episode}</b> | Step: <b>${agentSteps}</b> | ` +
                     `<b>${state.current}</b> → <b>${state.goal}</b> | ${optStr}${doneStr}`;
}

// ── Log panel ──
function addLog(msg, cls="step-log") {
    const panel = document.getElementById("log-panel");
    const div = document.createElement("div");
    div.className = cls;
    div.innerHTML = msg;
    panel.appendChild(div);
    panel.scrollTop = panel.scrollHeight;
    while (panel.children.length > 100) panel.removeChild(panel.firstChild);
}

// ── API calls ──
async function startEpisode() {
    const selStart = document.getElementById("sel-start");
    const selGoal = document.getElementById("sel-goal");
    const start = selStart.value || undefined;
    const goal = selGoal.value || undefined;
    const body = {};
    if (start) body.start = start;
    if (goal) body.goal = goal;

    const resp = await fetch("/api/demo/start", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body),
    });
    const data = await resp.json();
    if (data.error) { addLog(`Error: ${data.error}`, "fail"); return; }

    state.current = data.current;
    state.goal = data.goal;
    state.path = [data.current];
    state.step = 0;
    state.done = false;
    state.reward = 0;
    state.bfs_path = data.bfs_path;
    state.episode = data.episode;

    document.getElementById("log-panel").innerHTML = "";
    addLog(`<b>Episode ${data.episode}</b>: <span class="room">${data.current}</span> → <span class="room">${data.goal}</span> (BFS optimal: ${data.bfs_steps} steps)`);
    updateStatus();
}

async function doStep() {
    if (state.done) return;
    const resp = await fetch("/api/demo/step", { method: "POST" });
    const data = await resp.json();
    if (data.error) return;

    state.current = data.current;
    state.path = data.path;
    state.step = data.step;
    state.done = data.done;
    state.reward = data.reward;

    if (data.status === "goal_reached") {
        const bfsSteps = state.bfs_path ? state.bfs_path.length - 1 : "?";
        const opt = state.step === bfsSteps ? " (OPTIMAL)" : ` (BFS=${bfsSteps})`;
        addLog(`GOAL reached in ${state.step} steps!${opt}`, "success");
        stopAuto();
    } else if (data.status === "timeout") {
        addLog(`TIMEOUT after ${state.step} steps`, "fail");
        stopAuto();
    } else {
        const prev = state.path.length >= 2 ? state.path[state.path.length - 2] : "?";
        const qStr = data.q_values ? Object.entries(data.q_values).map(([r,q]) =>
            `${r.replace(/_/g," ")}:${q.toFixed(1)}`).join(", ") : "";
        addLog(`Step ${state.step}: <span class="room">${prev}</span> → <span class="room">${data.current}</span> <span class="q">[${qStr}]</span>`);
    }
    updateStatus();
}

function startAuto() {
    autoPlay = true;
    document.getElementById("btn-auto").classList.add("active");
    document.getElementById("btn-auto").textContent = "Stop";
    autoTick();
}
function stopAuto() {
    autoPlay = false;
    if (autoTimer) clearTimeout(autoTimer);
    autoTimer = null;
    document.getElementById("btn-auto").classList.remove("active");
    document.getElementById("btn-auto").textContent = "Auto-play";
}
async function autoTick() {
    if (!autoPlay || state.done) { stopAuto(); return; }
    await doStep();
    const delay = parseInt(document.getElementById("speed").value);
    autoTimer = setTimeout(autoTick, delay);
}

// ── Button handlers ──
document.getElementById("btn-start").onclick = async () => {
    stopAuto();
    await startEpisode();
};
document.getElementById("btn-step").onclick = async () => {
    if (state.done) await startEpisode();
    else await doStep();
};
document.getElementById("btn-auto").onclick = async () => {
    if (autoPlay) { stopAuto(); return; }
    if (state.done) await startEpisode();
    startAuto();
};

// Map dropdown
document.getElementById("sel-map").onchange = async (e) => {
    const size = parseInt(e.target.value);
    await switchMap(size);
    await loadPolicyOptions();
};

// Policy dropdown
document.getElementById("sel-policy").onchange = async (e) => {
    const policyRegions = parseInt(e.target.value);
    await switchPolicy(policyRegions);
};

// Keyboard
document.addEventListener("keydown", async (e) => {
    if (e.key === " ") { e.preventDefault(); if (state.done) await startEpisode(); else stopAuto(); }
    if (e.key === "s" || e.key === "S") { if (!state.done) await doStep(); }
    if (e.key === "a" || e.key === "A") {
        if (autoPlay) stopAuto(); else { if (state.done) await startEpisode(); startAuto(); }
    }
});

// Start
loadPolicyOptions();
draw();
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    parser = argparse.ArgumentParser(description="VEsNA Web Map Monitor")
    parser.add_argument("--checkpoint", default=None, help="Default checkpoint to load")
    parser.add_argument("--port", type=int, default=8050)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    # Discover all checkpoints
    global checkpoint_registry
    checkpoint_registry = discover_checkpoints(project_root)

    print(f"\nDiscovered checkpoints:")
    for rc, ckpts in sorted(checkpoint_registry.items()):
        for c in ckpts:
            print(f"  {rc}-region: {c['filename']} (ep {c['episode']})")

    # Auto-load the best checkpoint for each available region count
    for rc, ckpts in checkpoint_registry.items():
        best = ckpts[0]  # sorted by episode descending
        load_policy(best["path"], region_count=rc)

    # If explicit checkpoint provided, load it too
    if args.checkpoint and os.path.exists(args.checkpoint):
        load_policy(args.checkpoint)

    # Default to 100-region policy if available
    if 100 in loaded_policies:
        activate_policy(100)
    elif loaded_policies:
        activate_policy(next(iter(loaded_policies)))

    print(f"\n{'='*60}")
    print(f"  VEsNA Web Map Monitor")
    print(f"  Open in browser: http://localhost:{args.port}/map")
    print(f"  Available policies: {sorted(loaded_policies.keys())}")
    print(f"{'='*60}\n")

    app.run(host=args.host, port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
