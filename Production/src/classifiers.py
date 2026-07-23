from pathlib import Path

import numpy as np


class AdaptiveQLearner:
    """Q-Learning cipher selector with optional disk persistence."""

    def __init__(
        self,
        actions_count=3,
        learning_rate=0.2,
        discount_factor=0.9,
        persist_path=None,
        load_existing=True,
    ):
        self.q_table = np.zeros((2, 2, actions_count), dtype=float)
        self.alpha = learning_rate
        self.gamma = discount_factor
        self.persist_path = Path(persist_path) if persist_path is not None else None
        self.loaded_from_disk = False

        if load_existing and self.persist_path is not None and self.persist_path.exists():
            self.load()
        else:
            self.initialize_default_policy()

    def initialize_default_policy(self):
        self.q_table[:, :, :] = 0.0
        self.q_table[0, 0, 0] = 5.0
        self.q_table[0, 1, 1] = 5.0
        self.q_table[1, 0, 2] = 5.0
        self.q_table[1, 1, 2] = 10.0
        self.loaded_from_disk = False

    def select_action(self, sensitivity_state, threat_state, epsilon=0.1):
        if np.random.uniform(0, 1) < epsilon:
            return int(np.random.choice([0, 1, 2]))
        return int(np.argmax(self.q_table[sensitivity_state, threat_state]))

    def update_q_values(self, sens, threat, action, reward, next_sens, next_threat):
        old_value = self.q_table[sens, threat, action]
        next_max = np.max(self.q_table[next_sens, next_threat])
        self.q_table[sens, threat, action] = old_value + self.alpha * (
            reward + self.gamma * next_max - old_value
        )
        if self.persist_path is not None:
            self.save()

    def save(self, path=None):
        """Write the current Q-table to disk."""
        target = Path(path) if path is not None else self.persist_path
        if target is None:
            raise ValueError("No persist_path configured for AdaptiveQLearner.save()")
        target.parent.mkdir(parents=True, exist_ok=True)
        np.save(target, self.q_table)

    def load(self, path=None):
        """Load a Q-table from disk. Falls back to defaults if invalid."""
        target = Path(path) if path is not None else self.persist_path
        if target is None or not target.exists():
            self.initialize_default_policy()
            return False

        loaded = np.load(target)
        if loaded.shape != self.q_table.shape:
            self.initialize_default_policy()
            return False

        self.q_table = loaded.astype(float, copy=True)
        self.loaded_from_disk = True
        return True


def calculate_reinforcement_reward(sensitivity, threat_level, action_taken):
    if sensitivity == 1 or threat_level == 1:
        if action_taken == 2:
            return 15
        elif action_taken == 1:
            return 2
        else:
            return -30
    else:
        if action_taken == 0:
            return 10
        elif action_taken == 1:
            return 4
        else:
            return -15
