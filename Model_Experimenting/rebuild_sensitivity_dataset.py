"""
Rebuild the processed sensitivity dataset and retrain the production classifier.

Default production model: Logistic Regression (best LOFO macro-F1 on the
current multi-source dataset). Also writes a compatibility copy to
src/knn_model.pkl so older scripts keep working.

Usage:
    python Model_Experimenting/rebuild_sensitivity_dataset.py
    python Model_Experimenting/rebuild_sensitivity_dataset.py --rows-per-file 200
    python Model_Experimenting/rebuild_sensitivity_dataset.py --model-type logistic_regression
"""

from __future__ import annotations

import argparse
import pickle
import shutil
import sys
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from repo_paths import (  # noqa: E402
    COMPAT_MODEL,
    DATA_PROCESSED,
    DATA_RAW_NORMAL,
    DATA_RAW_SENSITIVE,
    SENSITIVITY_MODEL,
    setup_production_imports,
)

setup_production_imports()

from src.monitor import FEATURE_COLUMNS, extract_file_features  # noqa: E402


RAW_DIRS = (
    (DATA_RAW_SENSITIVE, 1),
    (DATA_RAW_NORMAL, 0),
)

DEFAULT_MODEL_PATH = SENSITIVITY_MODEL
COMPAT_MODEL_PATH = COMPAT_MODEL


def build_dataset(rows_per_file: int) -> pd.DataFrame:
    rows: list[dict] = []
    for directory, label in RAW_DIRS:
        for path in sorted(directory.glob("*.csv")):
            df = pd.read_csv(path, encoding="latin1", low_memory=False, nrows=rows_per_file)
            for _, source_row in df.iterrows():
                features = extract_file_features(path.name, str(source_row.to_dict()))
                row = dict(zip(FEATURE_COLUMNS, features))
                row["Is_Sensitive"] = label
                row["Source_File"] = str(path.relative_to(ROOT))
                rows.append(row)

    if not rows:
        raise RuntimeError("No raw CSV rows found under data/raw/sensitive or data/raw/normal.")
    return pd.DataFrame(rows)


def build_model(model_type: str, k: int):
    model_type = model_type.lower().strip()
    if model_type == "logistic_regression":
        return make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=2000, random_state=42),
        )
    if model_type == "random_forest":
        return RandomForestClassifier(
            n_estimators=200,
            max_depth=5,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
        )
    if model_type == "knn":
        return make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=k))
    raise ValueError(
        f"Unsupported model type: {model_type}. "
        "Choose logistic_regression, random_forest, or knn."
    )


def train_model(dataset: pd.DataFrame, model_type: str, k: int, model_path: Path) -> None:
    x = dataset[FEATURE_COLUMNS]
    y = dataset["Is_Sensitive"]
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    model = build_model(model_type, k)
    model.fit(x_train, y_train)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    with model_path.open("wb") as handle:
        pickle.dump(model, handle)

    # Keep legacy filename working for older scripts / Docker layers
    if model_path.resolve() != COMPAT_MODEL_PATH.resolve():
        shutil.copy2(model_path, COMPAT_MODEL_PATH)

    print("\nRandom Split Validation Report")
    print("=" * 40)
    print(f"Production model type: {model_type}")
    print(
        classification_report(
            y_test,
            model.predict(x_test),
            target_names=["Normal (0)", "Sensitive (1)"],
            zero_division=0,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild sensitivity_dataset.csv and retrain the production classifier."
    )
    parser.add_argument(
        "--rows-per-file",
        type=int,
        default=200,
        help="Maximum rows to sample from each raw CSV file.",
    )
    parser.add_argument(
        "--model-type",
        default="logistic_regression",
        choices=["logistic_regression", "random_forest", "knn"],
        help="Classifier to serialize for production (default: logistic_regression).",
    )
    parser.add_argument("--k", type=int, default=1, help="K value when --model-type knn.")
    parser.add_argument(
        "--processed-path",
        default=str(DATA_PROCESSED / "sensitivity_dataset.csv"),
        help="Output path for processed feature dataset.",
    )
    parser.add_argument(
        "--model-path",
        default=str(DEFAULT_MODEL_PATH),
        help="Output path for serialized production model.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    processed_path = Path(args.processed_path)
    model_path = Path(args.model_path)
    if not processed_path.is_absolute():
        processed_path = ROOT / processed_path
    if not model_path.is_absolute():
        model_path = ROOT / model_path

    dataset = build_dataset(args.rows_per_file)
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(processed_path, index=False)

    final_balanced_path = processed_path.parent / "final_balanced_dataset.csv"
    dataset.to_csv(final_balanced_path, index=False)

    train_model(dataset, args.model_type, args.k, model_path)

    print("Dataset rebuilt")
    print("=" * 40)
    print(f"Rows: {len(dataset)}")
    print(f"Features: {', '.join(FEATURE_COLUMNS)}")
    print(dataset["Is_Sensitive"].value_counts().sort_index().to_string())
    print(f"Processed CSV: {processed_path.relative_to(ROOT)}")
    print(f"Balanced CSV:  {final_balanced_path.relative_to(ROOT)}")
    print(f"Production model: {model_path.relative_to(ROOT)}")
    print(f"Compat copy:      {COMPAT_MODEL_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
