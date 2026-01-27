"""
Office Graph Environment for pure Python RL training.

Mirrors the adjacency graph from symbolic_execution_engine.asl.
No Godot, no physics, no WebSocket -- just graph transitions.

State: 22-dim numpy array [current_one_hot(11) | goal_one_hot(11)]
Action: region ID (0-10), must be a valid neighbor
Rewards: -1 per step, +100 goal reached, -10 timeout
"""

import random
from typing import Dict, List, Tuple

import numpy as np

# Region ID encoding (mirrors symbolic_execution_engine.asl)
REGION_IDS: Dict[str, int] = {
    "reception": 0,
    "corridor": 1,
    "open_office": 2,
    "outside": 3,
    "common": 4,
    "meeting_room": 5,
    "senior_office_1": 6,
    "senior_office_2": 7,
    "senior_office_3": 8,
    "boss_office_1": 9,
    "boss_office_2": 10,
}

ID_TO_REGION: Dict[int, str] = {v: k for k, v in REGION_IDS.items()}

NUM_REGIONS = len(REGION_IDS)

# Adjacency graph (mirrors symbolic_execution_engine.asl neighbor/2 facts)
ADJACENCY: Dict[int, List[int]] = {
    0: [1],              # reception ↔ corridor
    1: [0, 2, 4, 5, 6, 7, 8],  # corridor ↔ reception, open_office, common, meeting_room, senior_offices
    2: [1, 3, 9, 10],   # open_office ↔ corridor, outside, boss_office_1, boss_office_2
    3: [2],              # outside ↔ open_office
    4: [1],              # common ↔ corridor
    5: [1],              # meeting_room ↔ corridor
    6: [1],              # senior_office_1 ↔ corridor
    7: [1],              # senior_office_2 ↔ corridor
    8: [1],              # senior_office_3 ↔ corridor
    9: [2],              # boss_office_1 ↔ open_office
    10: [2],             # boss_office_2 ↔ open_office
}


class OfficeGraphEnv:
    """Goal-conditioned graph environment for the office map."""

    def __init__(self, max_steps: int = 50):
        self.num_regions = NUM_REGIONS
        self.state_size = NUM_REGIONS * 2  # 22 (current + goal one-hot)
        self.action_size = NUM_REGIONS     # 11
        self.max_steps = max_steps

        self.current: int = 0
        self.goal: int = 0
        self.steps: int = 0

    def _one_hot(self, region_id: int) -> np.ndarray:
        vec = np.zeros(self.num_regions, dtype=np.float32)
        vec[region_id] = 1.0
        return vec

    def _state(self) -> np.ndarray:
        return np.concatenate([self._one_hot(self.current), self._one_hot(self.goal)])

    def _valid_actions(self) -> List[int]:
        return ADJACENCY[self.current]

    def reset(self) -> Tuple[np.ndarray, List[int]]:
        """Random start and goal (guaranteed different). Returns (state, valid_actions)."""
        ids = list(range(self.num_regions))
        random.shuffle(ids)
        self.current = ids[0]
        self.goal = ids[1]
        self.steps = 0
        return self._state(), self._valid_actions()

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, List[int]]:
        """Take action (region ID). Returns (next_state, reward, done, valid_actions)."""
        assert action in ADJACENCY[self.current], (
            f"Invalid action {action} from region {self.current}. "
            f"Valid: {ADJACENCY[self.current]}"
        )

        self.current = action
        self.steps += 1

        if self.current == self.goal:
            return self._state(), 100.0, True, self._valid_actions()

        if self.steps >= self.max_steps:
            return self._state(), -10.0, True, self._valid_actions()

        return self._state(), -1.0, False, self._valid_actions()
