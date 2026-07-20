"""
Leave-one-file-out validation for the KNN sensitivity classifier.

This script evaluates whether the feature set generalizes across source files:
for each raw CSV, it trains on every other CSV and tests on the held-out file.
That is more research-credible than a random row split when rows from the same
source file may be very similar.

Expected raw dataset layout:
    data/raw/sensitive/*.csv  -> label 1
    data/raw/normal/*.csv     -> label 0

Usage:
    python tests/leave_one_file_out_validation.py
    python tests/leave_one_file_out_validation.py --rows-per-file 200 --k 1
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.monitor import extract_file_features  # noqa: E402


RAW_DIRS = (
    (ROOT / "data" / "raw" / "sensitive", 1),
    (ROOT / "data" / "raw" / "normal", 0),
)


def discover_source_files() -> list[tuple[Path, int]]:
    """Return all labeled raw CSV files available for validation."""
    source_files: list[tuple[Path, int]] = []
    for directory, label in RAW_DIRS:
        for path in sorted(directory.glob("*.csv")):
            source_files.append((path, label))
    return source_files


def build_features(path: Path, label: int, rows_per_file: int) -> tuple[list[list[float]], list[int]]:
    """Convert up to rows_per_file rows from a CSV into KNN feature vectors."""
    try:
        # nrows avoids loading multi-hundred-MB CSVs into memory
        df = pd.read_csv(path, encoding="latin1", low_memory=False, nrows=rows_per_file)
    except Exception as exc:
        raise RuntimeError(f"Could not read {path}: {exc}") from exc

    features: list[list[float]] = []
    labels: list[int] = []
    for _, row in df.iterrows():
        features.append(extract_file_features(path.name, str(row.to_dict())))
        labels.append(label)
    return features, labels


def load_feature_cache(
    source_files: list[tuple[Path, int]], rows_per_file: int
) -> dict[Path, tuple[list[list[float]], list[int]]]:
    """Precompute features once so each fold only retrains the classifier."""
    cache: dict[Path, tuple[list[list[float]], list[int]]] = {}
    for path, label in source_files:
        cache[path] = build_features(path, label, rows_per_file)
    return cache


def run_leave_one_file_out(rows_per_file: int, k: int) -> tuple[list[dict], list[int], list[int]]:
    """Run one fold per source file and return fold rows plus aggregate labels."""
    source_files = discover_source_files()
    if len(source_files) < 3:
        raise RuntimeError(
            "Need at least three raw CSV files under data/raw/sensitive and "
            "data/raw/normal to run leave-one-file-out validation."
        )

    labels_present = {label for _, label in source_files}
    if labels_present != {0, 1}:
        raise RuntimeError("Need at least one normal CSV and one sensitive CSV.")

    feature_cache = load_feature_cache(source_files, rows_per_file)
    fold_rows: list[dict] = []
    all_true: list[int] = []
    all_pred: list[int] = []

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

        model = make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=k))
        model.fit(x_train, y_train)
        predictions = model.predict(x_test)

        accuracy = accuracy_score(y_test, predictions)
        macro_f1 = f1_score(y_test, predictions, average="macro", zero_division=0)

        fold_rows.append(
            {
                "heldout_file": str(heldout_path.relative_to(ROOT)),
                "heldout_label": heldout_label,
                "train_rows": len(y_train),
                "test_rows": len(y_test),
                "k": k,
                "accuracy": round(accuracy, 4),
                "macro_f1": round(macro_f1, 4),
            }
        )
        all_true.extend(y_test)
        all_pred.extend(predictions.tolist())

    return fold_rows, all_true, all_pred


def write_results_csv(rows: list[dict], output_path: Path) -> None:
    """Persist fold-level metrics for report tables and plotting."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run leave-one-file-out validation for the KNN sensitivity classifier."
    )
    parser.add_argument(
        "--rows-per-file",
        type=int,
        default=200,
        help="Maximum rows to sample from each raw CSV file.",
    )
    parser.add_argument("--k", type=int, default=1, help="K value for KNeighborsClassifier.")
    parser.add_argument(
        "--output",
        default=str(ROOT / "results" / "leave_one_file_out_validation.csv"),
        help="CSV path for fold-level validation metrics.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows, y_true, y_pred = run_leave_one_file_out(args.rows_per_file, args.k)
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    write_results_csv(rows, output_path)

    print("\nLeave-One-File-Out KNN Validation")
    print("=" * 40)
    for row in rows:
        print(
            f"{row['heldout_file']}: "
            f"accuracy={row['accuracy']:.4f}, macro_f1={row['macro_f1']:.4f}, "
            f"test_rows={row['test_rows']}"
        )

    print("\nAggregate Classification Report")
    print("=" * 40)
    print(
        classification_report(
            y_true,
            y_pred,
            target_names=["Normal (0)", "Sensitive (1)"],
            zero_division=0,
        )
    )
    print(f"Fold metrics written to: {os.path.relpath(output_path, ROOT)}")


if __name__ == "__main__":
    main()
