"""
Pretrain a production Q-table with safety mask + decaying epsilon.

Runs multiple epochs over the processed sensitivity dataset, updates
Q-values with true next-packet transitions, and writes:

  Production/src/q_table_pretrained.npy   (showcase / bootstrap)
  Production/src/q_table.npy              (live runtime copy)

Usage:
    python Model_Experimenting/train_q_table.py
    python Model_Experimenting/train_q_table.py --epochs 10 --seed 42
"""

from __future__ import annotations

import argparse
import pickle
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from repo_paths import (  # noqa: E402
    DATA_PROCESSED,
    Q_TABLE_PATH,
    Q_TABLE_PRETRAINED,
    MODEL_CANDIDATES,
    setup_production_imports,
)

setup_production_imports()

from src.classifiers import AdaptiveQLearner, calculate_reinforcement_reward  # noqa: E402
from src.monitor import FEATURE_COLUMNS  # noqa: E402

TIER_NAMES = {0: "Tier1/ChaCha20", 1: "Tier2/AES", 2: "Tier3/ECDH+AES"}
STATE_NAMES = {
    (0, 0): "public + safe",
    (0, 1): "public + high",
    (1, 0): "sensitive + safe",
    (1, 1): "sensitive + high",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pretrain ACF Q-table for production.")
    parser.add_argument("--epochs", type=int, default=8, help="Passes over the dataset.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epsilon", type=float, default=0.25, help="Starting epsilon.")
    parser.add_argument("--epsilon-min", type=float, default=0.01)
    parser.add_argument("--epsilon-decay", type=float, default=0.9995)
    parser.add_argument(
        "--threat-period",
        type=int,
        default=4,
        help="Every Nth packet is HIGH threat (synthetic, reproducible).",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Optional row cap for a quick smoke train.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    np.random.seed(args.seed)

    dataset = pd.read_csv(DATA_PROCESSED / "sensitivity_dataset.csv")
    if args.max_rows is not None:
        dataset = dataset.head(args.max_rows)

    model_path = next(path for path in MODEL_CANDIDATES if path.exists())
    with model_path.open("rb") as handle:
        sensitivity_model = pickle.load(handle)

    agent = AdaptiveQLearner(
        persist_path=None,  # save once at the end
        load_existing=False,
        safety_mask=True,
        epsilon=args.epsilon,
        epsilon_min=args.epsilon_min,
        epsilon_decay=args.epsilon_decay,
        decay_epsilon=True,
    )

    print(f"Loaded classifier: {model_path.relative_to(REPO_ROOT)}")
    print(
        f"Training Q-table | packets={len(dataset)} | epochs={args.epochs} | "
        f"eps0={args.epsilon} -> min={args.epsilon_min}"
    )

    # Precompute sensitivity labels once
    features = dataset[FEATURE_COLUMNS]
    sens_labels = sensitivity_model.predict(features).astype(int)
    threats = np.array(
        [1 if (i % args.threat_period == 0) else 0 for i in range(len(dataset))],
        dtype=int,
    )

    total_reward = 0.0
    underprotect = 0
    sensitive_n = 0

    for epoch in range(args.epochs):
        epoch_reward = 0.0
        # Shuffle packet order each epoch for better coverage
        order = np.random.permutation(len(dataset))
        for pos, idx in enumerate(order):
            sens = int(sens_labels[idx])
            threat = int(threats[idx])
            next_idx = order[(pos + 1) % len(order)]
            next_sens = int(sens_labels[next_idx])
            next_threat = int(threats[next_idx])

            action = agent.select_action(sens, threat)  # uses decaying epsilon
            reward = calculate_reinforcement_reward(sens, threat, action)
            agent.update_q_values(sens, threat, action, reward, next_sens, next_threat)

            epoch_reward += reward
            if sens == 1:
                sensitive_n += 1
                if action == 0:
                    underprotect += 1

        total_reward += epoch_reward
        print(
            f"  epoch {epoch + 1}/{args.epochs}: "
            f"reward={epoch_reward:.1f} | epsilon={agent.epsilon:.4f}"
        )

    # Persist showcase + live copies
    Q_TABLE_PRETRAINED.parent.mkdir(parents=True, exist_ok=True)
    agent.save(Q_TABLE_PRETRAINED)
    shutil.copy2(Q_TABLE_PRETRAINED, Q_TABLE_PATH)

    prefs = agent.preferred_actions()
    print("\nGreedy policy after training (with safety mask):")
    for state, action in prefs.items():
        print(f"  {STATE_NAMES[state]:18s} -> {TIER_NAMES[action]}")

    under_rate = underprotect / sensitive_n if sensitive_n else 0.0
    print("\nTraining summary")
    print(f"  total_reward:        {total_reward:.1f}")
    print(f"  final_epsilon:       {agent.epsilon:.4f}")
    print(f"  underprotect_events: {underprotect} / {sensitive_n} ({under_rate:.4%})")
    print(f"  wrote: {Q_TABLE_PRETRAINED.relative_to(REPO_ROOT)}")
    print(f"  wrote: {Q_TABLE_PATH.relative_to(REPO_ROOT)}")
    print("\nQ-table tensor:")
    print(agent.q_table)


if __name__ == "__main__":
    main()
