"""
Generate the LogReg-era ACF performance dashboard for the report.

Reads:
  Model_Experimenting/results/classifier_lofo_summary.csv
  Model_Experimenting/results/benchmark_logreg_summary.csv  (or .json)

Writes:
  Model_Experimenting/results/benchmark_results_dashboard.png
  Documents/images/benchmark_results_dashboard.png

Usage:
    python Model_Experimenting/dashboards/generate_report_dashboard.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
from repo_paths import DOCUMENTS, RESULTS_DIR  # noqa: E402

LOFO_LABELS = {
    "logistic_regression": "LogReg",
    "random_forest_constrained": "RF (cstr)",
    "random_forest": "RF",
    "knn": "KNN",
}


def load_lofo(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Prefer a stable display order
    order = ["logistic_regression", "random_forest_constrained", "random_forest", "knn"]
    present = [m for m in order if m in set(df["model"])]
    return df.set_index("model").loc[present].reset_index()


def load_benchmarks(csv_path: Path, json_path: Path) -> list[dict]:
    if json_path.exists():
        return json.loads(json_path.read_text(encoding="utf-8"))
    if csv_path.exists():
        return pd.read_csv(csv_path).to_dict(orient="records")
    raise FileNotFoundError(
        "Missing benchmark results. Run:\n"
        "  python Model_Experimenting/run_benchmarks.py"
    )


def pick_scenario(rows: list[dict], prefix: str) -> dict | None:
    for row in rows:
        if str(row.get("scenario", "")).startswith(prefix):
            return row
    return None


def generate_dashboard(
    lofo: pd.DataFrame,
    local: dict,
    hf: dict | None,
    outputs: list[Path],
) -> None:
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        "Adaptive Cryptographic Framework (ACF) — LogReg Performance Dashboard",
        fontsize=15,
        fontweight="bold",
        y=0.97,
    )

    # ── Panel A: LOFO classifier comparison ───────────────────────────
    models = [LOFO_LABELS.get(m, m) for m in lofo["model"]]
    acc = (lofo["accuracy"] * 100.0).to_numpy()
    f1 = (lofo["macro_f1"] * 100.0).to_numpy()
    x = np.arange(len(models))
    width = 0.35
    bars_acc = axs[0, 0].bar(x - width / 2, acc, width, label="Accuracy", color="#2980b9")
    bars_f1 = axs[0, 0].bar(x + width / 2, f1, width, label="Macro-F1", color="#1abc9c")
    axs[0, 0].set_title("A. Leave-One-File-Out Classifier Comparison", fontweight="bold")
    axs[0, 0].set_ylabel("Score (%)")
    axs[0, 0].set_xticks(x)
    axs[0, 0].set_xticklabels(models, rotation=15, ha="right")
    axs[0, 0].set_ylim(0, 110)
    axs[0, 0].legend(frameon=False, loc="upper right")
    axs[0, 0].grid(axis="y", linestyle="--", alpha=0.4)
    for bar in list(bars_acc) + list(bars_f1):
        h = bar.get_height()
        axs[0, 0].text(
            bar.get_x() + bar.get_width() / 2.0,
            h + 1.5,
            f"{h:.1f}",
            ha="center",
            va="bottom",
            fontsize=8,
            fontweight="bold",
        )

    # ── Panel B: Local latency ────────────────────────────────────────
    categories = ["Static Baseline\n(Always Tier 3)", "Adaptive Framework\n(LogReg + Q-Learning)"]
    lat_vals = [local["static_latency_ms"], local["adaptive_latency_ms"]]
    bars_b = axs[0, 1].bar(categories, lat_vals, color=["#e74c3c", "#2ecc71"], width=0.45)
    n_local = int(local["n_packets"])
    axs[0, 1].set_title(
        f"B. Local Dataset Latency ({n_local:,} Packets)", fontweight="bold"
    )
    axs[0, 1].set_ylabel("Total Encryption Time (ms)")
    axs[0, 1].grid(axis="y", linestyle="--", alpha=0.4)
    for bar in bars_b:
        h = bar.get_height()
        axs[0, 1].text(
            bar.get_x() + bar.get_width() / 2.0,
            h + max(lat_vals) * 0.02,
            f"{h:.2f} ms",
            ha="center",
            va="bottom",
            fontweight="bold",
        )
    axs[0, 1].text(
        0.5,
        max(lat_vals) * 0.55,
        f"{local['latency_saving_pct']:.2f}% Latency\nReduction",
        ha="center",
        color="white",
        fontweight="bold",
        bbox=dict(facecolor="black", alpha=0.65, boxstyle="round,pad=0.45"),
    )

    # ── Panel C: Local modeled energy ─────────────────────────────────
    en_vals = [local["static_energy_uj"], local["adaptive_energy_uj"]]
    bars_c = axs[1, 0].bar(categories, en_vals, color=["#e74c3c", "#34495e"], width=0.45)
    axs[1, 0].set_title(
        f"C. Local Modeled Energy ({n_local:,} Packets)", fontweight="bold"
    )
    axs[1, 0].set_ylabel("Total Energy (µJ, modeled)")
    axs[1, 0].grid(axis="y", linestyle="--", alpha=0.4)
    for bar in bars_c:
        h = bar.get_height()
        axs[1, 0].text(
            bar.get_x() + bar.get_width() / 2.0,
            h + max(en_vals) * 0.02,
            f"{h:.1f} µJ",
            ha="center",
            va="bottom",
            fontweight="bold",
        )
    axs[1, 0].text(
        0.5,
        max(en_vals) * 0.55,
        f"{local['energy_saving_pct']:.2f}% Modeled\nEnergy Saved",
        ha="center",
        color="white",
        fontweight="bold",
        bbox=dict(facecolor="#27ae60", alpha=0.9, boxstyle="round,pad=0.45"),
    )

    # ── Panel D: HF stream or fallback note ───────────────────────────
    if hf is not None:
        hf_labels = ["Static Baseline\n(Always Tier 3)", "Adaptive Stream\n(LogReg + Q-Learning)"]
        hf_vals = [hf["static_latency_ms"], hf["adaptive_latency_ms"]]
        bars_d = axs[1, 1].bar(hf_labels, hf_vals, color=["#c0392b", "#9b59b6"], width=0.45)
        n_hf = int(hf["n_packets"])
        axs[1, 1].set_title(
            f"D. HuggingFace PII Stream Latency ({n_hf} Packets)", fontweight="bold"
        )
        axs[1, 1].set_ylabel("Total Encryption Time (ms)")
        axs[1, 1].grid(axis="y", linestyle="--", alpha=0.4)
        for bar in bars_d:
            h = bar.get_height()
            axs[1, 1].text(
                bar.get_x() + bar.get_width() / 2.0,
                h + max(hf_vals) * 0.02,
                f"{h:.2f} ms",
                ha="center",
                va="bottom",
                fontweight="bold",
            )
        axs[1, 1].text(
            0.5,
            max(hf_vals) * 0.55,
            f"{hf['latency_saving_pct']:.2f}% Stream\nLatency Reduction",
            ha="center",
            color="white",
            fontweight="bold",
            bbox=dict(facecolor="black", alpha=0.65, boxstyle="round,pad=0.45"),
        )
    else:
        axs[1, 1].axis("off")
        axs[1, 1].text(
            0.5,
            0.5,
            "D. HuggingFace stream benchmark unavailable\n"
            "(run with network / datasets installed)",
            ha="center",
            va="center",
            fontsize=11,
            color="#7f8c8d",
        )

    fig.text(
        0.5,
        0.01,
        "Production sensitivity model: Logistic Regression | Energy is modeled (latency × tier multiplier) | "
        "Adaptive policy: pretrained Q-table + safety mask",
        ha="center",
        fontsize=9,
        color="#555555",
    )

    plt.tight_layout(rect=[0, 0.035, 1, 0.95])
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=300, bbox_inches="tight")
        print(f"Saved: {path}")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot LogReg ACF benchmark dashboard.")
    parser.add_argument(
        "--lofo",
        default=str(RESULTS_DIR / "classifier_lofo_summary.csv"),
    )
    parser.add_argument(
        "--benchmark-csv",
        default=str(RESULTS_DIR / "benchmark_logreg_summary.csv"),
    )
    parser.add_argument(
        "--benchmark-json",
        default=str(RESULTS_DIR / "benchmark_logreg_summary.json"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    lofo_path = Path(args.lofo)
    csv_path = Path(args.benchmark_csv)
    json_path = Path(args.benchmark_json)
    if not lofo_path.is_absolute():
        lofo_path = REPO_ROOT / lofo_path
    if not csv_path.is_absolute():
        csv_path = REPO_ROOT / csv_path
    if not json_path.is_absolute():
        json_path = REPO_ROOT / json_path

    lofo = load_lofo(lofo_path)
    rows = load_benchmarks(csv_path, json_path)
    local = pick_scenario(rows, "local_")
    hf = pick_scenario(rows, "hf_")
    if local is None:
        raise RuntimeError("No local_* scenario found in benchmark results.")

    outputs = [
        RESULTS_DIR / "benchmark_results_dashboard.png",
        DOCUMENTS / "images" / "benchmark_results_dashboard.png",
    ]
    generate_dashboard(lofo, local, hf, outputs)
    print("Done. Use Documents/images/benchmark_results_dashboard.png in the report.")


if __name__ == "__main__":
    main()
