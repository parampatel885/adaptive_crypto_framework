"""
Plot ablation study results for the Adaptive Cryptography Framework.

Reads:
  Model_Experimenting/results/ablation_summary.csv
  Model_Experimenting/results/ablation_per_seed.csv  (optional error bars)

Writes:
  Model_Experimenting/results/ablation_dashboard.png
  Model_Experimenting/results/ablation_tradeoff.png

Usage:
    python Model_Experimenting/plot_ablation_results.py
    python Model_Experimenting/plot_ablation_results.py --summary Model_Experimenting/results/ablation_summary.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from repo_paths import RESULTS_DIR  # noqa: E402

# Short labels for readable charts
POLICY_LABELS = {
    "always_tier3": "Always T3",
    "always_tier1": "Always T1",
    "always_tier2": "Always T2",
    "rule_based": "Rule-based",
    "classifier_only": "Classifier only",
    "threat_only": "Threat only",
    "full_adaptive_rl": "Full RL",
    "full_adaptive_safe": "Full RL + safe",
}

# Focus policies for the main research story (exclude trivial always-T1/T2 if desired)
MAIN_POLICIES = [
    "always_tier3",
    "rule_based",
    "classifier_only",
    "threat_only",
    "full_adaptive_rl",
    "full_adaptive_safe",
]

COLORS = {
    "always_tier3": "#7f8c8d",
    "always_tier1": "#c0392b",
    "always_tier2": "#e67e22",
    "rule_based": "#2980b9",
    "classifier_only": "#16a085",
    "threat_only": "#8e44ad",
    "full_adaptive_rl": "#27ae60",
    "full_adaptive_safe": "#1abc9c",
}


def load_summary(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "policy" not in df.columns:
        raise ValueError(f"Expected 'policy' column in {path}")
    return df


def _col(df: pd.DataFrame, base: str) -> tuple[np.ndarray, np.ndarray | None]:
    """Return mean column and optional std column."""
    mean_key = f"{base}_mean" if f"{base}_mean" in df.columns else base
    std_key = f"{base}_std"
    means = df[mean_key].to_numpy(dtype=float)
    stds = df[std_key].to_numpy(dtype=float) if std_key in df.columns else None
    return means, stds


def plot_dashboard(df: pd.DataFrame, output: Path) -> None:
    """4-panel dashboard: latency save, energy save, underprotect, overprotect."""
    # Prefer main research policies; fall back to all if missing
    present = [p for p in MAIN_POLICIES if p in set(df["policy"])]
    if not present:
        present = list(df["policy"])
    sub = df.set_index("policy").loc[present].reset_index()

    labels = [POLICY_LABELS.get(p, p) for p in sub["policy"]]
    x = np.arange(len(labels))
    colors = [COLORS.get(p, "#34495e") for p in sub["policy"]]

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle(
        "Ablation Study: Same Dataset, Different Cipher Policies",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    # A) Latency savings
    lat, lat_std = _col(sub, "latency_saving_vs_tier3_pct")
    axes[0, 0].bar(x, lat, color=colors, yerr=lat_std, capsize=4, edgecolor="white")
    axes[0, 0].set_title("A. Latency Saving vs Always Tier 3")
    axes[0, 0].set_ylabel("Latency saving (%)")
    axes[0, 0].set_xticks(x)
    axes[0, 0].set_xticklabels(labels, rotation=25, ha="right")
    axes[0, 0].axhline(0, color="black", linewidth=0.8)
    axes[0, 0].grid(axis="y", alpha=0.3)

    # B) Energy savings (modeled)
    en, en_std = _col(sub, "energy_saving_vs_tier3_pct")
    axes[0, 1].bar(x, en, color=colors, yerr=en_std, capsize=4, edgecolor="white")
    axes[0, 1].set_title("B. Energy Saving vs Always Tier 3 (modeled)")
    axes[0, 1].set_ylabel("Energy saving (%)")
    axes[0, 1].set_xticks(x)
    axes[0, 1].set_xticklabels(labels, rotation=25, ha="right")
    axes[0, 1].axhline(0, color="black", linewidth=0.8)
    axes[0, 1].grid(axis="y", alpha=0.3)

    # C) Underprotection
    under, under_std = _col(sub, "underprotection_rate")
    under_pct = under * 100.0
    under_std_pct = under_std * 100.0 if under_std is not None else None
    axes[1, 0].bar(
        x, under_pct, color=colors, yerr=under_std_pct, capsize=4, edgecolor="white"
    )
    axes[1, 0].set_title("C. Underprotection Rate (sensitive got Tier 1)")
    axes[1, 0].set_ylabel("Underprotection (%)")
    axes[1, 0].set_xticks(x)
    axes[1, 0].set_xticklabels(labels, rotation=25, ha="right")
    axes[1, 0].grid(axis="y", alpha=0.3)

    # D) Overprotection
    over, over_std = _col(sub, "overprotection_rate")
    over_pct = over * 100.0
    over_std_pct = over_std * 100.0 if over_std is not None else None
    axes[1, 1].bar(
        x, over_pct, color=colors, yerr=over_std_pct, capsize=4, edgecolor="white"
    )
    axes[1, 1].set_title("D. Overprotection Rate (public+safe got Tier 3)")
    axes[1, 1].set_ylabel("Overprotection (%)")
    axes[1, 1].set_xticks(x)
    axes[1, 1].set_xticklabels(labels, rotation=25, ha="right")
    axes[1, 1].grid(axis="y", alpha=0.3)

    n_packets = int(sub["n_packets"].iloc[0]) if "n_packets" in sub.columns else "?"
    n_seeds = int(sub["n_seeds"].iloc[0]) if "n_seeds" in sub.columns else "?"
    fig.text(
        0.5,
        0.01,
        f"Packets={n_packets} | Seeds={n_seeds} | Energy is modeled (latency x tier multiplier)",
        ha="center",
        fontsize=9,
        color="#555555",
    )

    plt.tight_layout(rect=[0, 0.04, 1, 0.96])
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output}")


def plot_tradeoff(df: pd.DataFrame, output: Path) -> None:
    """Scatter: latency saving vs underprotection (efficiency vs safety)."""
    present = [p for p in MAIN_POLICIES if p in set(df["policy"])]
    if not present:
        present = list(df["policy"])
    sub = df.set_index("policy").loc[present].reset_index()

    lat, _ = _col(sub, "latency_saving_vs_tier3_pct")
    under, _ = _col(sub, "underprotection_rate")
    under_pct = under * 100.0

    fig, ax = plt.subplots(figsize=(8.5, 6.5))
    for i, policy in enumerate(sub["policy"]):
        ax.scatter(
            under_pct[i],
            lat[i],
            s=160,
            color=COLORS.get(policy, "#34495e"),
            edgecolors="black",
            linewidths=0.6,
            zorder=3,
        )
        ax.annotate(
            POLICY_LABELS.get(policy, policy),
            (under_pct[i], lat[i]),
            textcoords="offset points",
            xytext=(8, 6),
            fontsize=9,
        )

    ax.set_xlabel("Underprotection rate (%)  [lower is safer]")
    ax.set_ylabel("Latency saving vs Always Tier 3 (%)  [higher is faster]")
    ax.set_title("Efficiency–Safety Tradeoff Across Policies")
    ax.grid(True, alpha=0.3)
    ax.axvline(0, color="#27ae60", linestyle="--", linewidth=1, alpha=0.7)
    ax.set_xlim(left=-2)

    # Ideal corner annotation
    ax.text(
        0.98,
        0.02,
        "Ideal: high savings, near-zero underprotect (top-left)",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=8,
        color="#555555",
    )

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output}")


def plot_tier_mix(df: pd.DataFrame, output: Path) -> None:
    """Stacked bar of tier usage per policy."""
    present = [p for p in MAIN_POLICIES if p in set(df["policy"])]
    if not present:
        present = list(df["policy"])
    sub = df.set_index("policy").loc[present].reset_index()

    labels = [POLICY_LABELS.get(p, p) for p in sub["policy"]]
    x = np.arange(len(labels))

    t1, _ = _col(sub, "tier1_count")
    t2, _ = _col(sub, "tier2_count")
    t3, _ = _col(sub, "tier3_count")

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(x, t1, label="Tier 1 (ChaCha20)", color="#2ecc71")
    ax.bar(x, t2, bottom=t1, label="Tier 2 (AES-CTR)", color="#f39c12")
    ax.bar(x, t3, bottom=t1 + t2, label="Tier 3 (ECDH+AES)", color="#e74c3c")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_ylabel("Packet count")
    ax.set_title("Cipher Tier Mix by Policy")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot ACF ablation results.")
    parser.add_argument(
        "--summary",
        default=str(RESULTS_DIR / "ablation_summary.csv"),
        help="Path to ablation_summary.csv",
    )
    parser.add_argument(
        "--outdir",
        default=str(RESULTS_DIR),
        help="Directory for PNG outputs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary_path = Path(args.summary)
    outdir = Path(args.outdir)
    if not summary_path.is_absolute():
        summary_path = REPO_ROOT / summary_path
    if not outdir.is_absolute():
        outdir = REPO_ROOT / outdir

    if not summary_path.exists():
        raise FileNotFoundError(
            f"Missing {summary_path}. Run:\n"
            "  python Model_Experimenting/run_ablation_study.py"
        )

    df = load_summary(summary_path)
    plot_dashboard(df, outdir / "ablation_dashboard.png")
    plot_tradeoff(df, outdir / "ablation_tradeoff.png")
    plot_tier_mix(df, outdir / "ablation_tier_mix.png")
    print("Done. Use ablation_dashboard.png and ablation_tradeoff.png in the report.")


if __name__ == "__main__":
    main()
