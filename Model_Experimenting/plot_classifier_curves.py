"""
Research figures for the sensitivity classifier (Logistic Regression).

Why not a single pooled LOFO ROC?
  Each raw CSV is class-pure (all Sensitive or all Normal). Holding out one
  file therefore yields a single-class test set, so per-fold ROC AUC is
  undefined. Pooling those scores can produce an almost-perfect aggregate
  ROC that looks research-unrealistic and hides hard files (e.g. Airlines).

What this script reports instead:
  1) Leave-one-file-out (LOFO) confusion matrix + per-file accuracy
  2) Leave-one-pair-out ROC: each fold holds out one Sensitive file and one
     Normal file so both classes appear in the test set (AUC is well-defined)

Usage:
    python Model_Experimenting/plot_classifier_curves.py
    python Model_Experimenting/plot_classifier_curves.py --rows-per-file 200
"""

from __future__ import annotations

import argparse
import csv
import sys
from itertools import product
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    auc,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_curve,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from repo_paths import DOCUMENTS, RESULTS_DIR, setup_production_imports  # noqa: E402

setup_production_imports()

from leave_one_file_out_validation import (  # noqa: E402
    discover_source_files,
    load_feature_cache,
)


def _make_model():
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2000, random_state=42),
    )


def run_lofo(
    source_files: list[tuple[Path, int]],
    feature_cache: dict,
) -> tuple[list[int], list[int], list[float], list[dict]]:
    """Leave-one-file-out predictions + per-file metrics + scores."""
    y_true: list[int] = []
    y_pred: list[int] = []
    y_score: list[float] = []
    fold_rows: list[dict] = []

    for heldout_path, heldout_label in source_files:
        x_train: list[list[float]] = []
        y_train: list[int] = []
        for train_path, _ in source_files:
            if train_path == heldout_path:
                continue
            feats, labels = feature_cache[train_path]
            x_train.extend(feats)
            y_train.extend(labels)

        x_test, y_test = feature_cache[heldout_path]
        model = _make_model()
        model.fit(x_train, y_train)
        preds = model.predict(x_test)
        scores = model.predict_proba(x_test)[:, 1]

        y_true.extend(y_test)
        y_pred.extend(preds.tolist())
        y_score.extend(scores.tolist())
        fold_rows.append(
            {
                "heldout_file": heldout_path.name,
                "heldout_label": heldout_label,
                "n_test": len(y_test),
                "accuracy": float(accuracy_score(y_test, preds)),
                "n_errors": int(np.sum(np.asarray(y_test) != preds)),
                "mean_score": float(np.mean(scores)),
            }
        )

    return y_true, y_pred, y_score, fold_rows


def run_leave_one_pair_out(
    source_files: list[tuple[Path, int]],
    feature_cache: dict,
) -> tuple[list[dict], list[float]]:
    """
    Hold out one Sensitive + one Normal file per fold.

    Returns fold dicts (with fpr/tpr/auc) and a list of fold AUCs.
    """
    sensitive = [(p, lab) for p, lab in source_files if lab == 1]
    normal = [(p, lab) for p, lab in source_files if lab == 0]
    if len(sensitive) < 2 or len(normal) < 2:
        raise RuntimeError(
            "Need at least 2 Sensitive and 2 Normal files for leave-one-pair-out."
        )

    folds: list[dict] = []
    aucs: list[float] = []

    for (s_path, _), (n_path, _) in product(sensitive, normal):
        held = {s_path, n_path}
        x_train: list[list[float]] = []
        y_train: list[int] = []
        for train_path, _ in source_files:
            if train_path in held:
                continue
            feats, labels = feature_cache[train_path]
            x_train.extend(feats)
            y_train.extend(labels)

        x_test: list[list[float]] = []
        y_test: list[int] = []
        for path in (s_path, n_path):
            feats, labels = feature_cache[path]
            x_test.extend(feats)
            y_test.extend(labels)

        model = _make_model()
        model.fit(x_train, y_train)
        scores = model.predict_proba(x_test)[:, 1]
        preds = model.predict(x_test)
        fpr, tpr, _ = roc_curve(y_test, scores)
        fold_auc = float(auc(fpr, tpr))
        # Operating point at default threshold 0.5
        cm = confusion_matrix(y_test, preds, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()
        fpr_op = fp / (fp + tn) if (fp + tn) else 0.0
        tpr_op = tp / (tp + fn) if (tp + fn) else 0.0

        folds.append(
            {
                "heldout_sensitive": s_path.name,
                "heldout_normal": n_path.name,
                "auc": fold_auc,
                "fpr": fpr,
                "tpr": tpr,
                "fpr_at_0.5": fpr_op,
                "tpr_at_0.5": tpr_op,
                "accuracy": float(accuracy_score(y_test, preds)),
            }
        )
        aucs.append(fold_auc)

    return folds, aucs


def _apply_academic_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "figure.dpi": 120,
            "savefig.dpi": 300,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linestyle": ":",
        }
    )


def plot_confusion_matrix(y_true, y_pred, output: Path) -> np.ndarray:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True).clip(min=1)

    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    im = ax.imshow(cm_norm, interpolation="nearest", cmap="Greys", vmin=0, vmax=1)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Row-normalized rate")

    classes = ["Normal", "Sensitive"]
    ax.set_xticks([0, 1], classes)
    ax.set_yticks([0, 1], classes)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title("LOFO confusion matrix (Logistic Regression)")

    for i in range(2):
        for j in range(2):
            ax.text(
                j,
                i,
                f"{cm[i, j]}\n({cm_norm[i, j] * 100:.1f}%)",
                ha="center",
                va="center",
                color="white" if cm_norm[i, j] > 0.55 else "black",
                fontsize=9,
            )

    # Corner annotations for security interpretation
    ax.text(
        0.5,
        -0.22,
        f"Underprotect (FN): {cm[1, 0]}   |   Overprotect (FP): {cm[0, 1]}   |   n={len(y_true)}",
        transform=ax.transAxes,
        ha="center",
        fontsize=8,
        color="#333333",
    )

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output}")
    return cm


def plot_per_file_accuracy(fold_rows: list[dict], output: Path) -> None:
    names = [r["heldout_file"] for r in fold_rows]
    accs = [r["accuracy"] * 100 for r in fold_rows]
    labels = [r["heldout_label"] for r in fold_rows]
    colors = ["#4a4a4a" if lab == 1 else "#9a9a9a" for lab in labels]

    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    y_pos = np.arange(len(names))
    ax.barh(y_pos, accs, color=colors, edgecolor="black", linewidth=0.4, height=0.7)
    ax.set_yticks(y_pos, names)
    ax.set_xlabel("LOFO accuracy (%)")
    ax.set_xlim(0, 105)
    ax.set_title("Per-file leave-one-file-out accuracy")
    ax.axvline(100, color="#bbbbbb", linewidth=0.6, linestyle="--")

    for i, (acc, row) in enumerate(zip(accs, fold_rows)):
        ax.text(min(acc + 1.5, 92), i, f"{acc:.1f}%  (err={row['n_errors']})", va="center", fontsize=7.5)

    from matplotlib.patches import Patch

    ax.legend(
        handles=[
            Patch(facecolor="#4a4a4a", edgecolor="black", label="Sensitive file"),
            Patch(facecolor="#9a9a9a", edgecolor="black", label="Normal file"),
        ],
        loc="lower right",
        frameon=True,
    )
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output}")


def plot_pair_out_roc(folds: list[dict], aucs: list[float], output: Path) -> None:
    """Mean ROC over leave-one-pair-out folds, with individual folds faded."""
    # Interpolate each fold onto a common FPR grid
    mean_fpr = np.linspace(0, 1, 101)
    tprs = []
    for fold in folds:
        tpr_i = np.interp(mean_fpr, fold["fpr"], fold["tpr"])
        tpr_i[0] = 0.0
        tprs.append(tpr_i)
    tprs_arr = np.asarray(tprs)
    mean_tpr = tprs_arr.mean(axis=0)
    std_tpr = tprs_arr.std(axis=0)
    mean_tpr[-1] = 1.0
    mean_auc = float(np.mean(aucs))
    std_auc = float(np.std(aucs))

    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    for fold in folds:
        ax.plot(fold["fpr"], fold["tpr"], color="#aaaaaa", linewidth=0.7, alpha=0.45)

    ax.plot(
        mean_fpr,
        mean_tpr,
        color="black",
        linewidth=1.8,
        label=f"Mean ROC (AUC = {mean_auc:.3f} +/- {std_auc:.3f})",
    )
    ax.fill_between(
        mean_fpr,
        np.clip(mean_tpr - std_tpr, 0, 1),
        np.clip(mean_tpr + std_tpr, 0, 1),
        color="black",
        alpha=0.12,
        label="+/- 1 SD",
    )
    ax.plot([0, 1], [0, 1], linestyle="--", color="#666666", linewidth=1.0, label="Chance")

    # Default decision threshold operating points across folds
    op_fpr = [f["fpr_at_0.5"] for f in folds]
    op_tpr = [f["tpr_at_0.5"] for f in folds]
    ax.scatter(
        op_fpr,
        op_tpr,
        s=18,
        c="black",
        marker="x",
        linewidths=0.9,
        label=f"Threshold 0.5 (mean FPR={np.mean(op_fpr):.2f})",
        zorder=5,
    )

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title(
        f"Leave-one-pair-out ROC ({len(folds)} folds)\n"
        "one Sensitive + one Normal file held out"
    )
    ax.legend(loc="lower right", frameon=True)
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output}  (mean AUC = {mean_auc:.4f} +/- {std_auc:.4f})")


def plot_score_distributions(
    y_true,
    y_score,
    fold_rows: list[dict],
    output: Path,
) -> None:
    """
    Predicted P(Sensitive) by true class, plus per-file mean scores.

    This is usually more informative than a near-ceiling ROC when keyword/PII
    features make ranking easy across heterogeneous corpora.
    """
    y_true_arr = np.asarray(y_true)
    y_score_arr = np.asarray(y_score)
    scores_n = y_score_arr[y_true_arr == 0]
    scores_s = y_score_arr[y_true_arr == 1]

    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.5))

    ax = axes[0]
    bins = np.linspace(0, 1, 21)
    ax.hist(scores_n, bins=bins, alpha=0.65, color="#9a9a9a", edgecolor="black",
            linewidth=0.4, label=f"True Normal (n={len(scores_n)})")
    ax.hist(scores_s, bins=bins, alpha=0.65, color="#3a3a3a", edgecolor="black",
            linewidth=0.4, label=f"True Sensitive (n={len(scores_s)})")
    ax.axvline(0.5, color="black", linestyle="--", linewidth=1.0, label="Decision threshold 0.5")
    ax.set_xlabel("Predicted P(Sensitive)")
    ax.set_ylabel("Count (LOFO)")
    ax.set_title("(a) Score distribution by true class")
    ax.legend(loc="upper center", fontsize=7)

    ax = axes[1]
    names = [r["heldout_file"].replace(".csv", "") for r in fold_rows]
    means = [r["mean_score"] for r in fold_rows]
    colors = ["#4a4a4a" if r["heldout_label"] == 1 else "#b0b0b0" for r in fold_rows]
    y_pos = np.arange(len(names))
    ax.barh(y_pos, means, color=colors, edgecolor="black", linewidth=0.35, height=0.72)
    ax.axvline(0.5, color="black", linestyle="--", linewidth=1.0)
    ax.set_yticks(y_pos, names, fontsize=7)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Mean predicted P(Sensitive)")
    ax.set_title("(b) Per-file mean score (LOFO)")
    ax.text(0.52, len(names) - 0.3, "thr=0.5", fontsize=7, va="center")

    fig.suptitle(
        "LOFO predicted scores — ranking can look strong while threshold errors remain",
        fontsize=9,
        y=1.02,
    )
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output}")


def plot_combined_figure(
    y_true,
    y_pred,
    y_score,
    fold_rows: list[dict],
    folds: list[dict],
    aucs: list[float],
    output: Path,
) -> None:
    """2x2 research panel: CM, per-file accuracy, scores, pair-out ROC."""
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True).clip(min=1)

    mean_fpr = np.linspace(0, 1, 101)
    tprs = [np.interp(mean_fpr, f["fpr"], f["tpr"]) for f in folds]
    for t in tprs:
        t[0] = 0.0
    tprs_arr = np.asarray(tprs)
    mean_tpr = tprs_arr.mean(axis=0)
    std_tpr = tprs_arr.std(axis=0)
    mean_tpr[-1] = 1.0
    mean_auc = float(np.mean(aucs))
    std_auc = float(np.std(aucs))

    y_true_arr = np.asarray(y_true)
    y_score_arr = np.asarray(y_score)
    scores_n = y_score_arr[y_true_arr == 0]
    scores_s = y_score_arr[y_true_arr == 1]

    fig, axes = plt.subplots(2, 2, figsize=(9.5, 7.2))

    # --- A: confusion matrix ---
    ax = axes[0, 0]
    im = ax.imshow(cm_norm, cmap="Greys", vmin=0, vmax=1)
    ax.set_xticks([0, 1], ["Normal", "Sensitive"])
    ax.set_yticks([0, 1], ["Normal", "Sensitive"])
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title("(a) LOFO confusion matrix")
    for i in range(2):
        for j in range(2):
            ax.text(
                j,
                i,
                f"{cm[i, j]}\n{cm_norm[i, j] * 100:.1f}%",
                ha="center",
                va="center",
                color="white" if cm_norm[i, j] > 0.55 else "black",
                fontsize=8,
            )
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    # --- B: per-file accuracy ---
    ax = axes[0, 1]
    names = [r["heldout_file"].replace(".csv", "") for r in fold_rows]
    accs = [r["accuracy"] * 100 for r in fold_rows]
    colors = ["#4a4a4a" if r["heldout_label"] == 1 else "#b0b0b0" for r in fold_rows]
    y_pos = np.arange(len(names))
    ax.barh(y_pos, accs, color=colors, edgecolor="black", linewidth=0.35, height=0.72)
    ax.set_yticks(y_pos, names, fontsize=7)
    ax.set_xlabel("Accuracy (%)")
    ax.set_xlim(0, 105)
    ax.set_title("(b) Per-file LOFO accuracy")
    ax.axvline(np.mean(accs), color="black", linestyle="--", linewidth=0.8, label="Mean")
    ax.legend(loc="lower right", fontsize=7)

    # --- C: score histograms ---
    ax = axes[1, 0]
    bins = np.linspace(0, 1, 21)
    ax.hist(
        scores_n,
        bins=bins,
        alpha=0.65,
        color="#9a9a9a",
        edgecolor="black",
        linewidth=0.35,
        label="True Normal",
    )
    ax.hist(
        scores_s,
        bins=bins,
        alpha=0.65,
        color="#3a3a3a",
        edgecolor="black",
        linewidth=0.35,
        label="True Sensitive",
    )
    ax.axvline(0.5, color="black", linestyle="--", linewidth=1.0)
    ax.set_xlabel("Predicted P(Sensitive)")
    ax.set_ylabel("Count")
    ax.set_title("(c) LOFO score distribution")
    ax.legend(loc="upper center", fontsize=7)

    # --- D: pair-out ROC (secondary; ranking can look near-ceiling) ---
    ax = axes[1, 1]
    for fold in folds:
        ax.plot(fold["fpr"], fold["tpr"], color="#bbbbbb", linewidth=0.55, alpha=0.35)
    ax.plot(
        mean_fpr,
        mean_tpr,
        color="black",
        linewidth=1.5,
        label=f"Mean AUC={mean_auc:.3f}+/-{std_auc:.3f}",
    )
    ax.fill_between(
        mean_fpr,
        np.clip(mean_tpr - std_tpr, 0, 1),
        np.clip(mean_tpr + std_tpr, 0, 1),
        color="black",
        alpha=0.10,
    )
    ax.plot([0, 1], [0, 1], "--", color="#666666", linewidth=0.9)
    op_fpr = [f["fpr_at_0.5"] for f in folds]
    op_tpr = [f["tpr_at_0.5"] for f in folds]
    ax.scatter(
        op_fpr,
        op_tpr,
        s=14,
        c="black",
        marker="x",
        linewidths=0.8,
        zorder=5,
        label=f"thr=0.5 (mean FPR={np.mean(op_fpr):.2f})",
    )
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("(d) Leave-one-pair-out ROC")
    ax.legend(loc="lower right", fontsize=6.5)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)

    fig.suptitle(
        "Sensitivity classifier (LogReg, 14 features) — LOFO decision quality + pair-out ranking",
        fontsize=10,
        y=1.01,
    )
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output}")


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot research-grade classifier evaluation figures."
    )
    parser.add_argument("--rows-per-file", type=int, default=200)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _apply_academic_style()

    source_files = discover_source_files()
    print(f"Loading features from {len(source_files)} source files...")
    feature_cache = load_feature_cache(source_files, args.rows_per_file)

    print("Running leave-one-file-out...")
    y_true, y_pred, y_score, fold_rows = run_lofo(source_files, feature_cache)

    print("Running leave-one-pair-out ROC folds...")
    pair_folds, aucs = run_leave_one_pair_out(source_files, feature_cache)

    acc = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    p, r, f, s = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1], zero_division=0
    )

    print("\n=== LOFO aggregate ===")
    print(f"Accuracy: {acc:.4f}   Macro-F1: {macro_f1:.4f}   n={len(y_true)}")
    print(
        classification_report(
            y_true,
            y_pred,
            target_names=["Normal", "Sensitive"],
            zero_division=0,
        )
    )
    print("Per-file LOFO accuracy:")
    for row in fold_rows:
        tag = "SENS" if row["heldout_label"] == 1 else "NORM"
        print(
            f"  [{tag}] {row['heldout_file']:40s}  "
            f"acc={row['accuracy']:.3f}  errors={row['n_errors']}/{row['n_test']}  "
            f"mean_P={row['mean_score']:.3f}"
        )

    print("\n=== Leave-one-pair-out ROC ===")
    print(f"Folds: {len(pair_folds)}")
    print(f"Mean AUC: {np.mean(aucs):.4f} +/- {np.std(aucs):.4f}")
    print(f"AUC range: [{min(aucs):.4f}, {max(aucs):.4f}]")
    mean_fpr05 = float(np.mean([f["fpr_at_0.5"] for f in pair_folds]))
    mean_tpr05 = float(np.mean([f["tpr_at_0.5"] for f in pair_folds]))
    print(f"At threshold 0.5: mean TPR={mean_tpr05:.3f}, mean FPR={mean_fpr05:.3f}")

    # Persist tables for the report
    write_csv(
        [
            {
                "heldout_file": r["heldout_file"],
                "heldout_label": r["heldout_label"],
                "n_test": r["n_test"],
                "accuracy": round(r["accuracy"], 4),
                "n_errors": r["n_errors"],
                "mean_score": round(r["mean_score"], 4),
            }
            for r in fold_rows
        ],
        RESULTS_DIR / "classifier_lofo_per_file.csv",
    )
    pair_table = [
        {
            "heldout_sensitive": f["heldout_sensitive"],
            "heldout_normal": f["heldout_normal"],
            "auc": round(f["auc"], 4),
            "accuracy": round(f["accuracy"], 4),
            "tpr_at_0.5": round(f["tpr_at_0.5"], 4),
            "fpr_at_0.5": round(f["fpr_at_0.5"], 4),
        }
        for f in pair_folds
    ]
    write_csv(pair_table, RESULTS_DIR / "classifier_pairout_roc.csv")

    # Figures
    cm_path = RESULTS_DIR / "confusion_matrix_lofo.png"
    roc_path = RESULTS_DIR / "roc_curve_lofo.png"
    per_file_path = RESULTS_DIR / "lofo_per_file_accuracy.png"
    scores_path = RESULTS_DIR / "lofo_score_distributions.png"
    combined_path = RESULTS_DIR / "classifier_eval_panel.png"

    plot_confusion_matrix(y_true, y_pred, cm_path)
    plot_per_file_accuracy(fold_rows, per_file_path)
    plot_score_distributions(y_true, y_score, fold_rows, scores_path)
    plot_pair_out_roc(pair_folds, aucs, roc_path)
    plot_combined_figure(
        y_true, y_pred, y_score, fold_rows, pair_folds, aucs, combined_path
    )

    # Copies for Documents/images
    doc_img = DOCUMENTS / "images"
    plot_confusion_matrix(y_true, y_pred, doc_img / "confusion_matrix_lofo.png")
    plot_pair_out_roc(pair_folds, aucs, doc_img / "roc_curve_lofo.png")
    plot_per_file_accuracy(fold_rows, doc_img / "lofo_per_file_accuracy.png")
    plot_score_distributions(
        y_true, y_score, fold_rows, doc_img / "lofo_score_distributions.png"
    )
    plot_combined_figure(
        y_true,
        y_pred,
        y_score,
        fold_rows,
        pair_folds,
        aucs,
        doc_img / "classifier_eval_panel.png",
    )

    print("\nNote for the report:")
    print(
        "  Do not cite a pooled single-file LOFO ROC AUC~1.0 - each held-out file"
        " is class-pure, so that curve is misleading. Prefer panels (a)-(c):"
        " confusion matrix, per-file accuracy (Airlines fails), and score"
        " distributions. Pair-out AUC remains high because keyword/PII features"
        f" separate domains easily ({np.mean(aucs):.3f} +/- {np.std(aucs):.3f}),"
        " while threshold FPR stays non-trivial."
    )


if __name__ == "__main__":
    main()
