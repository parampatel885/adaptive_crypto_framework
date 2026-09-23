"""
Comparative Evaluation of RL Formulations for Adaptive Crypto Routing.

Compares:
  1. Baseline (Hardcoded Heuristic Rewards, 2x2 State)
  2. Multi-Objective Utility (Analytical Physical Reward, 2x2 State)
  3. Multi-Dimensional Q-Table (Analytical Physical Reward, 2x2x2 State with Size Metric)

Outputs:
  - Model_Experimenting/results/reward_formulation_comparison.csv
  - Model_Experimenting/results/reward_formulation_comparison.png
  - Documents/images/reward_formulation_comparison.png
"""

from __future__ import annotations

import argparse
import csv
import pickle
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from repo_paths import (  # noqa: E402
    DATA_PROCESSED,
    DOCUMENTS,
    MODEL_CANDIDATES,
    RESULTS_DIR,
    setup_production_imports,
)

setup_production_imports()

from src.classifiers import AdaptiveQLearner, calculate_reinforcement_reward  # noqa: E402
from src.crypto_engines import (  # noqa: E402
    execute_hybrid_ecc_aes,
    execute_lightweight_trivium,
    execute_standard_aes,
)
from src.monitor import FEATURE_COLUMNS  # noqa: E402

ENGINES = {
    0: ("Tier1/ChaCha20", execute_lightweight_trivium),
    1: ("Tier2/AES-CTR", execute_standard_aes),
    2: ("Tier3/ECDH+AES", execute_hybrid_ecc_aes),
}

# Empirical hardware normalization factors
MAX_LATENCY_MS = 1.0
MAX_ENERGY_UJ = 40.0


def calculate_multi_objective_reward(
    sens: int,
    threat: int,
    action: int,
    size_kb: float,
    elapsed_ms: float,
    energy_uj: float,
    w_sec: float = 0.60,
    w_lat: float = 0.25,
    w_eng: float = 0.15,
) -> float:
    """
    Continuous Multi-Objective Utility balancing security, latency, and energy.
    Range roughly in [-25.0, +10.0] for stable Q-learning gradients.
    """
    sens = int(sens)
    threat = int(threat)
    act = int(action)

    # 1. Security target
    if sens == 1:
        target_action = 2
    elif threat == 1:
        target_action = 1
    else:
        target_action = 0

    if act == target_action:
        s_score = 1.0
    elif act > target_action:
        s_score = 0.5   # safe but over-protected
    else:
        s_score = -2.5  # under-protection breach penalty

    # 2. Normalized physical costs
    norm_lat = min(elapsed_ms / max(MAX_LATENCY_MS * max(size_kb, 0.1), 0.001), 1.0)
    norm_eng = min(energy_uj / max(MAX_ENERGY_UJ * max(size_kb, 0.1), 0.001), 1.0)

    utility = (w_sec * s_score) - (w_lat * norm_lat) - (w_eng * norm_eng)
    return float(utility * 10.0)


class MultiDimQLearner:
    """3D Q-Learner: State is (Sensitivity, Threat, Size_Bucket)."""

    def __init__(
        self,
        actions_count: int = 3,
        learning_rate: float = 0.2,
        discount_factor: float = 0.9,
        safety_mask: bool = True,
        epsilon: float = 0.25,
        epsilon_min: float = 0.01,
        epsilon_decay: float = 0.9995,
    ):
        self.actions_count = actions_count
        # Shape: [sens (2), threat (2), size_bucket (2), actions (3)]
        self.q_table = np.zeros((2, 2, 2, actions_count), dtype=float)
        self.alpha = learning_rate
        self.gamma = discount_factor
        self.safety_mask = safety_mask
        self.epsilon = float(epsilon)
        self.epsilon_min = float(epsilon_min)
        self.epsilon_decay = float(epsilon_decay)

    def allowed_actions(self, sens: int) -> list[int]:
        actions = list(range(self.actions_count))
        if self.safety_mask and int(sens) == 1:
            actions = [a for a in actions if a != 0]
        return actions

    def select_action(self, sens: int, threat: int, size_b: int) -> int:
        allowed = self.allowed_actions(sens)
        if np.random.uniform(0, 1) < self.epsilon:
            action = int(np.random.choice(allowed))
        else:
            q_row = self.q_table[sens, threat, size_b].copy()
            for a in range(self.actions_count):
                if a not in allowed:
                    q_row[a] = -1e9
            action = int(np.argmax(q_row))

        if self.safety_mask and sens == 1 and action == 0:
            action = 2

        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        return action

    def update_q(
        self,
        sens: int,
        threat: int,
        size_b: int,
        action: int,
        reward: float,
        next_sens: int,
        next_threat: int,
        next_size_b: int,
    ) -> None:
        if self.safety_mask and sens == 1 and action == 0:
            action = 2

        old_val = self.q_table[sens, threat, size_b, action]
        next_allowed = self.allowed_actions(next_sens)
        next_max = float(np.max(self.q_table[next_sens, next_threat, next_size_b][next_allowed]))
        self.q_table[sens, threat, size_b, action] = old_val + self.alpha * (
            reward + self.gamma * next_max - old_val
        )


def run_experiment(epochs: int = 8, seed: int = 42) -> dict:
    np.random.seed(seed)

    # 1. Load dataset & model
    dataset = pd.read_csv(DATA_PROCESSED / "sensitivity_dataset.csv")
    model_path = next(p for p in MODEL_CANDIDATES if p.exists())
    with model_path.open("rb") as handle:
        sensitivity_model = pickle.load(handle)

    features = dataset[FEATURE_COLUMNS]
    sens_labels = sensitivity_model.predict(features).astype(int)
    sizes_kb = dataset["Size_KB"].values if "Size_KB" in dataset.columns else np.ones(len(dataset))
    size_median = float(np.median(sizes_kb))
    size_buckets = (sizes_kb > size_median).astype(int)
    threats = np.array([1 if (i % 4 == 0) else 0 for i in range(len(dataset))], dtype=int)

    # Convert payloads for actual crypto execution
    payloads = [str(dict(row)) for _, row in dataset.iterrows()]

    # 2. Instantiate Agents
    agent_baseline = AdaptiveQLearner(load_existing=False, safety_mask=True, epsilon=0.25)
    agent_multiobj = AdaptiveQLearner(load_existing=False, safety_mask=True, epsilon=0.25)
    agent_3d_state = MultiDimQLearner(safety_mask=True, epsilon=0.25)

    history = {
        "baseline_rewards": [],
        "multiobj_rewards": [],
        "3d_state_rewards": [],
    }

    print("\n" + "=" * 65)
    print("  TRAINING 3 RL FORMULATIONS ON SENSITIVITY DATASET")
    print("=" * 65)

    for epoch in range(epochs):
        order = np.random.permutation(len(dataset))
        r_base_epoch, r_multi_epoch, r_3d_epoch = 0.0, 0.0, 0.0

        for pos, idx in enumerate(order):
            s = int(sens_labels[idx])
            t = int(threats[idx])
            sz_b = int(size_buckets[idx])
            sz_kb = float(sizes_kb[idx])
            payload = payloads[idx]

            nxt_idx = order[(pos + 1) % len(order)]
            nxt_s = int(sens_labels[nxt_idx])
            nxt_t = int(threats[nxt_idx])
            nxt_sz_b = int(size_buckets[nxt_idx])

            # Agent 1: Baseline (Heuristic reward, 2x2 state)
            act_b = agent_baseline.select_action(s, t)
            _, elap_b, eng_b = ENGINES[act_b][1](payload)
            rew_b = calculate_reinforcement_reward(s, t, act_b)
            agent_baseline.update_q_values(s, t, act_b, rew_b, nxt_s, nxt_t)
            r_base_epoch += rew_b

            # Agent 2: Multi-Objective (Analytical reward, 2x2 state)
            act_m = agent_multiobj.select_action(s, t)
            _, elap_m, eng_m = ENGINES[act_m][1](payload)
            rew_m = calculate_multi_objective_reward(s, t, act_m, sz_kb, elap_m, eng_m)
            agent_multiobj.update_q_values(s, t, act_m, rew_m, nxt_s, nxt_t)
            r_multi_epoch += rew_m

            # Agent 3: 3D State + Multi-Objective (Analytical reward, 2x2x2 state)
            act_3d = agent_3d_state.select_action(s, t, sz_b)
            _, elap_3d, eng_3d = ENGINES[act_3d][1](payload)
            rew_3d = calculate_multi_objective_reward(s, t, act_3d, sz_kb, elap_3d, eng_3d)
            agent_3d_state.update_q(s, t, sz_b, act_3d, rew_3d, nxt_s, nxt_t, nxt_sz_b)
            r_3d_epoch += rew_3d

        history["baseline_rewards"].append(r_base_epoch)
        history["multiobj_rewards"].append(r_multi_epoch)
        history["3d_state_rewards"].append(r_3d_epoch)
        print(
            f"Epoch {epoch+1:02d}/{epochs:02d} | "
            f"Baseline Rew: {r_base_epoch:7.1f} | "
            f"Multi-Obj Rew: {r_multi_epoch:7.1f} | "
            f"3D-State Rew: {r_3d_epoch:7.1f}"
        )

    # 3. Final Evaluation Test Run (Greedy Mode: Epsilon = 0)
    print("\n" + "=" * 65)
    print("  EVALUATION BENCHMARK (GREEDY INFERENCE ON TEST STREAM)")
    print("=" * 65)

    def evaluate_policy(name: str, get_action_fn) -> dict:
        total_lat = 0.0
        total_eng = 0.0
        tier_counts = {0: 0, 1: 0, 2: 0}
        violations = 0
        total_utility = 0.0

        for idx in range(len(dataset)):
            s = int(sens_labels[idx])
            t = int(threats[idx])
            sz_b = int(size_buckets[idx])
            sz_kb = float(sizes_kb[idx])
            payload = payloads[idx]

            action = get_action_fn(s, t, sz_b)
            tier_counts[action] += 1

            _, elap, eng = ENGINES[action][1](payload)
            total_lat += elap
            total_eng += eng

            util = calculate_multi_objective_reward(s, t, action, sz_kb, elap, eng)
            total_utility += util

            if s == 1 and action == 0:
                violations += 1

        return {
            "name": name,
            "total_latency_ms": round(total_lat, 2),
            "avg_latency_ms": round(total_lat / len(dataset), 4),
            "total_energy_uj": round(total_eng, 2),
            "avg_energy_uj": round(total_eng / len(dataset), 4),
            "tier1_pct": round(tier_counts[0] / len(dataset) * 100, 1),
            "tier2_pct": round(tier_counts[1] / len(dataset) * 100, 1),
            "tier3_pct": round(tier_counts[2] / len(dataset) * 100, 1),
            "violations": violations,
            "mean_utility": round(total_utility / len(dataset), 3),
        }

    eval_results = [
        evaluate_policy("1. Static Tier 3 (Always ECDH+AES)", lambda s, t, sz: 2),
        evaluate_policy("2. Static Tier 1 (Always ChaCha20)", lambda s, t, sz: 0),
        evaluate_policy(
            "3. Baseline RL (Heuristic, 2x2 State)",
            lambda s, t, sz: agent_baseline.select_action(s, t, epsilon=0.0),
        ),
        evaluate_policy(
            "4. Multi-Objective RL (Utility, 2x2 State)",
            lambda s, t, sz: agent_multiobj.select_action(s, t, epsilon=0.0),
        ),
        evaluate_policy(
            "5. Multi-Dim RL (Utility, 2x2x2 State with Size)",
            lambda s, t, sz: int(np.argmax(agent_3d_state.q_table[s, t, sz])),
        ),
    ]

    # Print Summary Table
    print(
        f"{'Model':<44} | {'Lat (ms)':<8} | {'Energy(uJ)':<10} | "
        f"{'T1%':<5} {'T2%':<5} {'T3%':<5} | {'Violations':<10} | {'Mean Util'}"
    )
    print("-" * 110)
    for r in eval_results:
        print(
            f"{r['name']:<44} | {r['total_latency_ms']:<8.2f} | {r['total_energy_uj']:<10.2f} | "
            f"{r['tier1_pct']:<5.1f} {r['tier2_pct']:<5.1f} {r['tier3_pct']:<5.1f} | "
            f"{r['violations']:<10} | {r['mean_utility']:.3f}"
        )
    print("-" * 110)

    # 4. Save Results to CSV
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    csv_out = RESULTS_DIR / "reward_formulation_comparison.csv"
    with csv_out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(eval_results[0].keys()))
        writer.writeheader()
        writer.writerows(eval_results)
    print(f"\n[Saved CSV]: {csv_out}")

    # 5. Plot Comparison Figures
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Plot (a): Learning Convergence
    ax0 = axes[0]
    ep_range = list(range(1, epochs + 1))
    ax0.plot(ep_range, history["baseline_rewards"], "o--", color="#6c757d", label="Baseline (Heuristic)")
    ax0.plot(ep_range, history["multiobj_rewards"], "s-", color="#0d6efd", label="Multi-Objective (2x2)")
    ax0.plot(ep_range, history["3d_state_rewards"], "^-", color="#198754", label="Multi-Dim State (2x2x2)")
    ax0.set_title("(a) Training Episode Utility", fontsize=11, fontweight="bold")
    ax0.set_xlabel("Epoch")
    ax0.set_ylabel("Cumulative Epoch Reward")
    ax0.grid(True, linestyle=":", alpha=0.6)
    ax0.legend(fontsize=9)

    # Plot (b): Latency vs Energy Trade-off
    ax1 = axes[1]
    names = ["Static T3", "Static T1", "Baseline RL", "Multi-Obj (2x2)", "Multi-Dim (2x2x2)"]
    lats = [r["total_latency_ms"] for r in eval_results]
    engs = [r["total_energy_uj"] for r in eval_results]
    x = np.arange(len(names))
    width = 0.35

    ax1.bar(x - width / 2, lats, width, label="Latency (ms)", color="#0dcaf0")
    ax1_twin = ax1.twinx()
    ax1_twin.bar(x + width / 2, engs, width, label="Energy (uJ)", color="#ffc107")

    ax1.set_xticks(x)
    ax1.set_xticklabels(names, rotation=25, ha="right", fontsize=9)
    ax1.set_ylabel("Latency (ms)", color="#0aa2c0")
    ax1_twin.set_ylabel("Modeled Energy (uJ)", color="#d39e00")
    ax1.set_title("(b) Latency & Energy Consumption", fontsize=11, fontweight="bold")
    ax1.grid(True, linestyle=":", alpha=0.4)

    # Plot (c): Tier Action Distribution
    ax2 = axes[2]
    t1_bars = [r["tier1_pct"] for r in eval_results]
    t2_bars = [r["tier2_pct"] for r in eval_results]
    t3_bars = [r["tier3_pct"] for r in eval_results]

    ax2.bar(names, t1_bars, label="Tier 1 (ChaCha20)", color="#20c997")
    ax2.bar(names, t2_bars, bottom=t1_bars, label="Tier 2 (AES-CTR)", color="#fd7e14")
    ax2.bar(names, t3_bars, bottom=np.array(t1_bars) + np.array(t2_bars), label="Tier 3 (ECDH+AES)", color="#dc3545")
    ax2.set_xticklabels(names, rotation=25, ha="right", fontsize=9)
    ax2.set_ylabel("Action Allocation (%)")
    ax2.set_title("(c) Cipher Tier Allocation Distribution", fontsize=11, fontweight="bold")
    ax2.legend(loc="upper right", fontsize=8)
    ax2.grid(True, linestyle=":", alpha=0.4)

    fig.tight_layout()
    img_out = RESULTS_DIR / "reward_formulation_comparison.png"
    fig.savefig(img_out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"[Saved Plot]: {img_out}")

    # Copy to Documents/images for presentation
    doc_img_dir = DOCUMENTS / "images"
    doc_img_dir.mkdir(parents=True, exist_ok=True)
    doc_img_out = doc_img_dir / "reward_formulation_comparison.png"
    import shutil
    shutil.copy2(img_out, doc_img_out)
    print(f"[Saved Presentation Image]: {doc_img_out}")

    return {
        "results": eval_results,
        "csv_path": str(csv_out),
        "img_path": str(img_out),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    run_experiment(epochs=args.epochs, seed=args.seed)
