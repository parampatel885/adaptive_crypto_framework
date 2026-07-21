"""
Leave-one-file-out comparison of sensitivity classifiers.

Compares:
  - KNN (current production-style model)
  - Logistic Regression (simple baseline)
  - Random Forest unconstrained (upper-bound performance)
  - Random Forest constrained (robustness / genuineness check)

Usage:
    python Model_Experimenting/compare_classifiers_lofo.py
    python Model_Experimenting/compare_classifiers_lofo.py --rows-per-file 200 --k 1
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from repo_paths import RESULTS_DIR, setup_production_imports  # noqa: E402

setup_production_imports()

from leave_one_file_out_validation import (  # noqa: E402
    discover_source_files,
    load_feature_cache,
)


def build_models(k: int) -> dict:
    return {
        "knn": make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=k)),
        "logistic_regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=2000, random_state=42),
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            random_state=42,
            n_jobs=-1,
        ),
        # Constrained RF: shallower trees + larger leaves reduce memorization risk
        "random_forest_constrained": RandomForestClassifier(
            n_estimators=200,
            max_depth=5,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
        ),
    }


def run_comparison(rows_per_file: int, k: int) -> tuple[list[dict], list[dict]]:
    source_files = discover_source_files()
    if len(source_files) < 3:
        raise RuntimeError(
            "Need at least three raw CSV files under data/raw/sensitive and "
            "data/raw/normal to run leave-one-file-out comparison."
        )

    labels_present = {label for _, label in source_files}
    if labels_present != {0, 1}:
        raise RuntimeError("Need at least one normal CSV and one sensitive CSV.")

    feature_cache = load_feature_cache(source_files, rows_per_file)
    fold_rows: list[dict] = []
    aggregate_rows: list[dict] = []
    model_names = list(build_models(k).keys())
    preds_by_model: dict[str, list[int]] = {name: [] for name in model_names}
    truths: list[int] = []

    for heldout_path, heldout_label in source_files:
        x_train: list[list[float]] = []
        y_train: list[int] = []
        for train_path, _ in source_files:
            if train_path == heldout_path:
                continue
            features, labels = feature_cache[train_path]
            x_train.extend(features)
            y_train.extend(labels)

        x_test, y_test = feature_cache[heldout_path]
        if not x_test:
            raise RuntimeError(f"Held-out file has no readable rows: {heldout_path}")

        truths.extend(y_test)

        for model_name, model in build_models(k).items():
            fitted = model.fit(x_train, y_train)
            predictions = fitted.predict(x_test)
            preds_by_model[model_name].extend(predictions.tolist())

            fold_rows.append(
                {
                    "model": model_name,
                    "heldout_file": str(heldout_path.relative_to(ROOT)),
                    "heldout_label": heldout_label,
                    "train_rows": len(y_train),
                    "test_rows": len(y_test),
                    "accuracy": round(accuracy_score(y_test, predictions), 4),
                    "macro_f1": round(
                        f1_score(y_test, predictions, average="macro", zero_division=0), 4
                    ),
                    "precision_sensitive": round(
                        precision_score(y_test, predictions, pos_label=1, zero_division=0), 4
                    ),
                    "recall_sensitive": round(
                        recall_score(y_test, predictions, pos_label=1, zero_division=0), 4
                    ),
                }
            )

    for model_name, preds in preds_by_model.items():
        aggregate_rows.append(
            {
                "model": model_name,
                "accuracy": round(accuracy_score(truths, preds), 4),
                "macro_f1": round(f1_score(truths, preds, average="macro", zero_division=0), 4),
                "precision_normal": round(
                    precision_score(truths, preds, pos_label=0, zero_division=0), 4
                ),
                "recall_normal": round(
                    recall_score(truths, preds, pos_label=0, zero_division=0), 4
                ),
                "precision_sensitive": round(
                    precision_score(truths, preds, pos_label=1, zero_division=0), 4
                ),
                "recall_sensitive": round(
                    recall_score(truths, preds, pos_label=1, zero_division=0), 4
                ),
                "n_samples": len(truths),
            }
        )

    return fold_rows, aggregate_rows


def write_csv(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare KNN, Logistic Regression, and Random Forest under LOFO."
    )
    parser.add_argument("--rows-per-file", type=int, default=200)
    parser.add_argument("--k", type=int, default=1, help="K for KNeighborsClassifier.")
    parser.add_argument(
        "--fold-output",
        default=str(RESULTS_DIR / "classifier_lofo_folds.csv"),
    )
    parser.add_argument(
        "--summary-output",
        default=str(RESULTS_DIR / "classifier_lofo_summary.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    fold_rows, aggregate_rows = run_comparison(args.rows_per_file, args.k)

    fold_output = Path(args.fold_output)
    summary_output = Path(args.summary_output)
    if not fold_output.is_absolute():
        fold_output = ROOT / fold_output
    if not summary_output.is_absolute():
        summary_output = ROOT / summary_output

    write_csv(fold_rows, fold_output)
    write_csv(aggregate_rows, summary_output)

    print("\nLeave-One-File-Out Classifier Comparison")
    print("=" * 50)
    print(f"{'Model':<22} {'Acc':>8} {'MacroF1':>8} {'SensRec':>8} {'NormRec':>8}")
    print("-" * 50)
    for row in sorted(aggregate_rows, key=lambda r: r["accuracy"], reverse=True):
        print(
            f"{row['model']:<22} "
            f"{row['accuracy']:>8.4f} "
            f"{row['macro_f1']:>8.4f} "
            f"{row['recall_sensitive']:>8.4f} "
            f"{row['recall_normal']:>8.4f}"
        )

    best = max(aggregate_rows, key=lambda r: (r["macro_f1"], r["accuracy"]))
    print("-" * 50)
    print(f"Best by macro-F1: {best['model']} ({best['macro_f1']:.4f})")
    print(f"Fold metrics:    {os.path.relpath(fold_output, ROOT)}")
    print(f"Summary metrics: {os.path.relpath(summary_output, ROOT)}")


if __name__ == "__main__":
    main()
