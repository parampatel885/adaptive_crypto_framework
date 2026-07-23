"""
Ablation study for Adaptive Cryptography Framework cipher routing.

Runs the SAME packets through multiple policies so you can attribute
latency / energy / safety to each component:

  A0  always_tier3          — static max-security baseline
  A1  always_tier1          — static min-cost baseline (unsafe reference)
  A2  always_tier2          — static medium baseline
  A3  rule_based            — if/else on (sens, threat); NO Q-Learning
  A4  classifier_only       — uses ML sensitivity; threat forced SAFE (0)
  A5  threat_only           — uses threat; sensitivity forced PUBLIC (0)
  A6  full_adaptive_rl      — LogReg + threat + Q-Learning (current system)
  A7  full_adaptive_safe    — same as A6 but Tier 1 forbidden when sens=1

This answers: "Does RL beat a simple rule? Does the classifier matter?
Does threat matter? What is the security cost of savings?"

Usage:
    python Model_Experimenting/run_ablation_study.py
    python Model_Experimenting/run_ablation_study.py --max-rows 500 --seeds 3
"""

from __future__ import annotations

import argparse
import csv
import pickle
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from repo_paths import DATA_PROCESSED, MODEL_CANDIDATES, RESULTS_DIR, setup_production_imports  # noqa: E402

setup_production_imports()

from src.classifiers import AdaptiveQLearner, calculate_reinforcement_reward  # noqa: E402
from src.crypto_engines import (  # noqa: E402
    execute_hybrid_ecc_aes,
    execute_lightweight_trivium,
    execute_standard_aes,
)
from src.monitor import FEATURE_COLUMNS  # noqa: E402

ENGINES = (
    execute_lightweight_trivium,  # 0 = Tier 1
    execute_standard_aes,         # 1 = Tier 2
    execute_hybrid_ecc_aes,       # 2 = Tier 3
)


def rule_based_action(sens: int, threat: int) -> int:
    """Deterministic policy mirroring the intended security mapping (no RL)."""
    if sens == 1 or threat == 1:
        return 2  # Tier 3
    return 0      # Tier 1


def safe_mask(action: int, sens: int) -> int:
    """Never allow Tier 1 on sensitive packets."""
    if sens == 1 and action == 0:
        return 2
    return action


@dataclass
class PolicyMetrics:
    name: str
    latency_ms: float = 0.0
    energy_uj: float = 0.0
    tier_counts: dict[int, int] = field(default_factory=lambda: {0: 0, 1: 0, 2: 0})
    # Safety: sensitive packets that received Tier 1 (under-protection)
    underprotected: int = 0
    sensitive_packets: int = 0
    # Efficiency: public+safe packets that received Tier 3 (over-protection)
    overprotected: int = 0
    public_safe_packets: int = 0
    n_packets: int = 0

    def record(self, action: int, latency: float, energy: float, sens: int, threat: int) -> None:
        self.latency_ms += latency
        self.energy_uj += energy
        self.tier_counts[action] += 1
        self.n_packets += 1
        if sens == 1:
            self.sensitive_packets += 1
            if action == 0:
                self.underprotected += 1
        if sens == 0 and threat == 0:
            self.public_safe_packets += 1
            if action == 2:
                self.overprotected += 1

    def to_row(self, baseline_latency: float, baseline_energy: float) -> dict:
        under_rate = (
            self.underprotected / self.sensitive_packets if self.sensitive_packets else 0.0
        )
        over_rate = (
            self.overprotected / self.public_safe_packets if self.public_safe_packets else 0.0
        )
        lat_save = (
            ((baseline_latency - self.latency_ms) / baseline_latency) * 100.0
            if baseline_latency
            else 0.0
        )
        en_save = (
            ((baseline_energy - self.energy_uj) / baseline_energy) * 100.0
            if baseline_energy
            else 0.0
        )
        return {
            "policy": self.name,
            "n_packets": self.n_packets,
            "latency_ms": round(self.latency_ms, 2),
            "energy_uj": round(self.energy_uj, 2),
            "latency_saving_vs_tier3_pct": round(lat_save, 2),
            "energy_saving_vs_tier3_pct": round(en_save, 2),
            "tier1_count": self.tier_counts[0],
            "tier2_count": self.tier_counts[1],
            "tier3_count": self.tier_counts[2],
            "underprotection_count": self.underprotected,
            "underprotection_rate": round(under_rate, 4),
            "overprotection_count": self.overprotected,
            "overprotection_rate": round(over_rate, 4),
        }


def choose_action(
    policy: str,
    sens: int,
    threat: int,
    rl_agent: AdaptiveQLearner | None,
    epsilon: float,
) -> int:
    if policy == "always_tier3":
        return 2
    if policy == "always_tier1":
        return 0
    if policy == "always_tier2":
        return 1
    if policy == "rule_based":
        return rule_based_action(sens, threat)
    if policy == "classifier_only":
        return rule_based_action(sens, threat=0)
    if policy == "threat_only":
        return rule_based_action(sens=0, threat=threat)
    if policy == "full_adaptive_rl":
        assert rl_agent is not None
        return int(rl_agent.select_action(sens, threat, epsilon=epsilon))
    if policy == "full_adaptive_safe":
        assert rl_agent is not None
        action = int(rl_agent.select_action(sens, threat, epsilon=epsilon))
        return safe_mask(action, sens)
    raise ValueError(f"Unknown policy: {policy}")


POLICIES = (
    "always_tier3",
    "always_tier1",
    "always_tier2",
    "rule_based",
    "classifier_only",
    "threat_only",
    "full_adaptive_rl",
    "full_adaptive_safe",
)


def run_one_seed(
    dataset: pd.DataFrame,
    sensitivity_model,
    seed: int,
    epsilon: float,
) -> list[PolicyMetrics]:
    rng = np.random.default_rng(seed)
    # Keep threat pattern reproducible but seed-dependent
    threat_offset = int(rng.integers(0, 4))

    metrics = {name: PolicyMetrics(name=name) for name in POLICIES}
    rl_agents = {
        "full_adaptive_rl": AdaptiveQLearner(),
        "full_adaptive_safe": AdaptiveQLearner(),
    }

    for index, row in dataset.iterrows():
        features_df = pd.DataFrame([row[FEATURE_COLUMNS].to_dict()], columns=FEATURE_COLUMNS)
        sens = int(sensitivity_model.predict(features_df)[0])
        threat = 1 if ((int(index) + threat_offset) % 4 == 0) else 0
        payload = str(row.to_dict())

        for name in POLICIES:
            agent = rl_agents.get(name)
            action = choose_action(name, sens, threat, agent, epsilon)
            _, latency, energy = ENGINES[action](payload)
            metrics[name].record(action, latency, energy, sens, threat)

            if agent is not None:
                reward = calculate_reinforcement_reward(sens, threat, action)
                agent.update_q_values(sens, threat, action, reward, sens, threat)

    return [metrics[name] for name in POLICIES]


def aggregate_rows(all_seed_rows: list[list[dict]]) -> list[dict]:
    """Mean ± std across seeds for numeric fields."""
    by_policy: dict[str, list[dict]] = {name: [] for name in POLICIES}
    for seed_rows in all_seed_rows:
        for row in seed_rows:
            by_policy[row["policy"]].append(row)

    numeric = [
        "latency_ms",
        "energy_uj",
        "latency_saving_vs_tier3_pct",
        "energy_saving_vs_tier3_pct",
        "tier1_count",
        "tier2_count",
        "tier3_count",
        "underprotection_count",
        "underprotection_rate",
        "overprotection_count",
        "overprotection_rate",
    ]
    aggregated: list[dict] = []
    for name in POLICIES:
        rows = by_policy[name]
        out: dict = {
            "policy": name,
            "n_packets": rows[0]["n_packets"],
            "n_seeds": len(rows),
        }
        for key in numeric:
            vals = np.array([r[key] for r in rows], dtype=float)
            out[f"{key}_mean"] = round(float(vals.mean()), 4)
            out[f"{key}_std"] = round(float(vals.std(ddof=0)), 4)
        aggregated.append(out)
    return aggregated


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ACF cipher-routing ablation study.")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Optional cap on dataset rows (faster smoke test).",
    )
    parser.add_argument("--seeds", type=int, default=3, help="Number of random seeds.")
    parser.add_argument("--epsilon", type=float, default=0.05, help="Epsilon for RL policies.")
    parser.add_argument(
        "--output",
        default=str(RESULTS_DIR / "ablation_summary.csv"),
        help="Aggregated mean±std CSV path.",
    )
    parser.add_argument(
        "--per-seed-output",
        default=str(RESULTS_DIR / "ablation_per_seed.csv"),
        help="Per-seed raw CSV path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset = pd.read_csv(DATA_PROCESSED / "sensitivity_dataset.csv")
    if args.max_rows is not None:
        dataset = dataset.head(args.max_rows)

    model_path = next(path for path in MODEL_CANDIDATES if path.exists())
    with model_path.open("rb") as handle:
        sensitivity_model = pickle.load(handle)
    print(f"Loaded model: {model_path.relative_to(REPO_ROOT)}")
    print(f"Packets: {len(dataset)} | Seeds: {args.seeds} | epsilon={args.epsilon}")

    per_seed_rows: list[dict] = []
    seed_metric_sets: list[list[dict]] = []

    for seed in range(args.seeds):
        print(f"\n-- Seed {seed} --")
        metrics_list = run_one_seed(dataset, sensitivity_model, seed, args.epsilon)
        baseline = next(m for m in metrics_list if m.name == "always_tier3")
        seed_rows = [m.to_row(baseline.latency_ms, baseline.energy_uj) for m in metrics_list]
        for row in seed_rows:
            row["seed"] = seed
            per_seed_rows.append(row)
        seed_metric_sets.append(seed_rows)

        # Compact console table for this seed
        print(f"{'policy':<22} {'lat_save%':>10} {'en_save%':>10} {'under%':>10} {'over%':>10}")
        for row in seed_rows:
            print(
                f"{row['policy']:<22} "
                f"{row['latency_saving_vs_tier3_pct']:>10.2f} "
                f"{row['energy_saving_vs_tier3_pct']:>10.2f} "
                f"{row['underprotection_rate'] * 100:>9.2f}% "
                f"{row['overprotection_rate'] * 100:>9.2f}%"
            )

    summary = aggregate_rows(seed_metric_sets)

    out = Path(args.output)
    per_seed_out = Path(args.per_seed_output)
    if not out.is_absolute():
        out = REPO_ROOT / out
    if not per_seed_out.is_absolute():
        per_seed_out = REPO_ROOT / per_seed_out

    write_csv(per_seed_rows, per_seed_out)
    write_csv(summary, out)

    print("\n" + "=" * 72)
    print("ABLATION SUMMARY (mean across seeds, vs always_tier3)")
    print("=" * 72)
    print(
        f"{'policy':<22} {'lat_save%':>10} {'en_save%':>10} "
        f"{'under%':>10} {'over%':>10}"
    )
    print("-" * 72)
    for row in summary:
        print(
            f"{row['policy']:<22} "
            f"{row['latency_saving_vs_tier3_pct_mean']:>10.2f} "
            f"{row['energy_saving_vs_tier3_pct_mean']:>10.2f} "
            f"{row['underprotection_rate_mean'] * 100:>9.2f}% "
            f"{row['overprotection_rate_mean'] * 100:>9.2f}%"
        )
    print("-" * 72)
    print("How to read this:")
    print("  * rule_based vs full_adaptive_rl  -> does RL beat a simple if/else?")
    print("  * classifier_only vs threat_only  -> which signal matters more?")
    print("  * underprotection_rate            -> security cost of speed")
    print("  * full_adaptive_safe              -> RL with hard Tier-1 ban on sensitive")
    print(f"\nWrote: {per_seed_out.relative_to(REPO_ROOT)}")
    print(f"Wrote: {out.relative_to(REPO_ROOT)}")
    print("Note: energy is still the modeled proxy (latency x tier multiplier).")


if __name__ == "__main__":
    main()
