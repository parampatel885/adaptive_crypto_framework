from pathlib import Path

import numpy as np


class AdaptiveQLearner:
    """Q-Learning cipher selector with safety mask, decaying epsilon, and disk persistence."""

    def __init__(
        self,
        actions_count=3,
        learning_rate=0.2,
        discount_factor=0.9,
        persist_path=None,
        load_existing=True,
        safety_mask=True,
        epsilon=0.2,
        epsilon_min=0.01,
        epsilon_decay=0.9995,
        decay_epsilon=True,
    ):
        self.actions_count = actions_count
        self.q_table = np.zeros((2, 2, actions_count), dtype=float)
        self.alpha = learning_rate
        self.gamma = discount_factor
        self.persist_path = Path(persist_path) if persist_path is not None else None
        self.loaded_from_disk = False

        self.safety_mask = safety_mask
        self.epsilon = float(epsilon)
        self.epsilon_min = float(epsilon_min)
        self.epsilon_decay = float(epsilon_decay)
        self.decay_epsilon = decay_epsilon
        self.steps = 0

        if load_existing and self.persist_path is not None and self.persist_path.exists():
            self.load()
        else:
            self.initialize_default_policy()

    def initialize_default_policy(self):
        self.q_table[:, :, :] = 0.0
        self.q_table[0, 0, 0] = 5.0   # public + safe  -> prefer Tier 1
        self.q_table[0, 1, 1] = 5.0   # public + high  -> prefer Tier 2
        self.q_table[1, 0, 2] = 5.0   # sensitive + safe -> prefer Tier 3
        self.q_table[1, 1, 2] = 10.0  # sensitive + high -> prefer Tier 3
        self.loaded_from_disk = False

    def allowed_actions(self, sensitivity_state: int) -> list[int]:
        """Return legal tiers. With safety mask, Tier 1 is banned for sensitive data."""
        actions = list(range(self.actions_count))
        if self.safety_mask and int(sensitivity_state) == 1:
            actions = [a for a in actions if a != 0]
        return actions

    def apply_safety_mask(self, action: int, sensitivity_state: int) -> int:
        if self.safety_mask and int(sensitivity_state) == 1 and int(action) == 0:
            return 2  # escalate to Tier 3
        return int(action)

    def select_action(self, sensitivity_state, threat_state, epsilon=None):
        """
        ε-greedy action selection over allowed actions only.
        If epsilon is None, use the agent's current decaying epsilon.
        """
        sens = int(sensitivity_state)
        threat = int(threat_state)
        allowed = self.allowed_actions(sens)
        eps = self.epsilon if epsilon is None else float(epsilon)

        if np.random.uniform(0, 1) < eps:
            action = int(np.random.choice(allowed))
        else:
            q_row = self.q_table[sens, threat].copy()
            # Mask illegal actions so argmax cannot pick them
            for a in range(self.actions_count):
                if a not in allowed:
                    q_row[a] = -1e9
            action = int(np.argmax(q_row))

        action = self.apply_safety_mask(action, sens)
        self._maybe_decay_epsilon()
        return action

    def _maybe_decay_epsilon(self):
        if not self.decay_epsilon:
            return
        self.steps += 1
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def update_q_values(self, sens, threat, action, reward, next_sens, next_threat):
        sens = int(sens)
        threat = int(threat)
        action = self.apply_safety_mask(int(action), sens)
        next_sens = int(next_sens)
        next_threat = int(next_threat)

        old_value = self.q_table[sens, threat, action]

        # Bootstrap from best *allowed* next action
        next_allowed = self.allowed_actions(next_sens)
        next_q = self.q_table[next_sens, next_threat]
        next_max = float(np.max(next_q[next_allowed]))

        self.q_table[sens, threat, action] = old_value + self.alpha * (
            reward + self.gamma * next_max - old_value
        )
        if self.persist_path is not None:
            self.save()

    def preferred_actions(self) -> dict[tuple[int, int], int]:
        """Greedy action per state after applying safety mask."""
        prefs = {}
        for sens in (0, 1):
            for threat in (0, 1):
                allowed = self.allowed_actions(sens)
                q_row = self.q_table[sens, threat].copy()
                for a in range(self.actions_count):
                    if a not in allowed:
                        q_row[a] = -1e9
                prefs[(sens, threat)] = int(np.argmax(q_row))
        return prefs

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
