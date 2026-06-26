import pickle
import os
import pandas as pd
import numpy as np
from src.monitor import extract_file_features

class AdaptiveQLearner:
    def __init__(self, actions_count=3, learning_rate=0.2, discount_factor=0.9):
        self.q_table = np.zeros((2, 2, actions_count))
        self.alpha = learning_rate
        self.gamma = discount_factor
        self.initialize_default_policy()

    def initialize_default_policy(self):
        self.q_table[0, 0, 0] = 5.0
        self.q_table[0, 1, 1] = 5.0
        self.q_table[1, 0, 2] = 5.0
        self.q_table[1, 1, 2] = 10.0

    def select_action(self, sensitivity_state, threat_state, epsilon=0.1):
        if np.random.uniform(0, 1) < epsilon:
            return np.random.choice([0, 1, 2])
        return np.argmax(self.q_table[sensitivity_state, threat_state])

    def update_q_values(self, sens, threat, action, reward, next_sens, next_threat):
        old_value = self.q_table[sens, threat, action]
        next_max = np.max(self.q_table[next_sens, next_threat])
        self.q_table[sens, threat, action] = old_value + self.alpha * (reward + self.gamma * next_max - old_value)

def calculate_reinforcement_reward(sensitivity, threat_level, action_taken):
    if sensitivity == 1 or threat_level == 1:
        if action_taken == 2: return 15
        elif action_taken == 1: return 2
        else: return -30
    else:
        if action_taken == 0: return 10
        elif action_taken == 1: return 4
        else: return -15
