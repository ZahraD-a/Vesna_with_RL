"""Run evaluation of all 2450 pairs and print paths to console."""
import sys, os, numpy as np, torch
from collections import defaultdict, deque

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "mind", "python"))
from dqn_agent import DQNAgent

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
ID_TO_ROOM = {i: n for i, n in enumerate(ROOMS)}
NUM = len(ROOMS)

EC = [("corridor","reception"),("corridor","open_office"),("corridor","corridor_north"),
      ("corridor","corridor_south"),("corridor_south","lobby")]
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

adj = defaultdict(set)
for a, b in EC + DOORS:
    adj[a].add(b)
    adj[b].add(a)

def bfs(s, g):
    if s == g:
        return 0
    vis = {s}
    q = deque([(s, 0)])
    while q:
        n, d = q.popleft()
        for nb in adj[n]:
            if nb == g:
                return d + 1
            if nb not in vis:
                vis.add(nb)
                q.append((nb, d + 1))
    return -1

def make_state(c, g):
    s = np.zeros(100, dtype=np.float32)
    s[ROOM_TO_ID[c]] = 1.0
    s[50 + ROOM_TO_ID[g]] = 1.0
    return s

# Load agent
agent = DQNAgent(state_size=100, action_size=50, hidden_size=128)
agent.load("checkpoints/alice.pt")
agent.set_eval_mode(True)
print(f"Loaded policy (episode={agent.episode}, epsilon={agent.epsilon:.6f})")
print()

pairs = [(s, g) for s in ROOMS for g in ROOMS if s != g]
total = len(pairs)
optimal = 0
success = 0

for i, (start, goal) in enumerate(pairs):
    bfs_d = bfs(start, goal)
    cur = start
    print(f"========== PAIR {i+1}/{total} ({start} -> {goal})  [BFS optimal: {bfs_d}] ==========")
    print(f"  Step 0: at {cur} -> goal: {goal}")

    done = False
    for step in range(150):
        st = make_state(cur, goal)
        valid = sorted([ROOM_TO_ID[n] for n in adj[cur]])
        with torch.no_grad():
            o = torch.tensor(st, dtype=torch.float32).unsqueeze(0)
            q = agent.policy_net(o).squeeze(0)
            mask = torch.full((50,), float("-inf"))
            mask[valid] = 0.0
            act = int((q + mask).argmax().item())

        nxt = ID_TO_ROOM[act]
        print(f"    -> RL selected: {nxt}")
        cur = nxt

        if cur == goal:
            steps = step + 1
            reward = 100 - steps
            tag = "OPTIMAL" if steps == bfs_d else f"+{steps - bfs_d} extra"
            print(f"  *** GOAL REACHED in {steps} steps (reward: {reward}) [{tag}] ***")
            success += 1
            if steps == bfs_d:
                optimal += 1
            done = True
            break

        print(f"  Step {step+1}: at {cur} -> goal: {goal}")

    if not done:
        print(f"  *** TIMEOUT after 150 steps ***")

    print()

print("=" * 60)
print(f"  SUMMARY: {success}/{total} success ({success/total*100:.1f}%)")
print(f"  Optimal paths: {optimal}/{total} ({optimal/total*100:.1f}%)")
print("=" * 60)
