"""
Build a shuffled mixed demo file (sensitive + public) for the production dashboard.

Rows are interleaved randomly — not "first half sensitive, second half public".

Usage:
    python Model_Experimenting/make_mixed_demo_file.py
    python Model_Experimenting/make_mixed_demo_file.py --total 100 --seed 42
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from repo_paths import DATA_RAW_NORMAL, DATA_RAW_SENSITIVE, DATA_DIR  # noqa: E402

DEMO_DIR = DATA_DIR / "demo"
DEFAULT_OUTPUT = DEMO_DIR / "mixed_production_demo.csv"


def sample_rows_from_dir(directory: Path, label: str, n: int, rng: random.Random) -> list[dict]:
    files = sorted(directory.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {directory}")

    # Draw from all files so the mix is diverse
    per_file = max(1, n // len(files))
    extras = n - per_file * len(files)
    picked: list[dict] = []

    for i, path in enumerate(files):
        take = per_file + (1 if i < extras else 0)
        df = pd.read_csv(path, encoding="latin1", low_memory=False)
        if df.empty:
            continue
        take = min(take, len(df))
        idxs = rng.sample(range(len(df)), k=take)
        for idx in idxs:
            row = df.iloc[idx]
            payload = str(row.to_dict())
            # Keep payload compact enough for demo uploads
            if len(payload) > 2000:
                payload = payload[:2000]
            picked.append(
                {
                    "payload": payload,
                    "expected_class": label,
                    "source_file": path.name,
                }
            )

    # If some files were short, top up from any file
    while len(picked) < n:
        path = rng.choice(files)
        df = pd.read_csv(path, encoding="latin1", low_memory=False)
        if df.empty:
            break
        row = df.iloc[rng.randrange(len(df))]
        payload = str(row.to_dict())
        if len(payload) > 2000:
            payload = payload[:2000]
        picked.append(
            {
                "payload": payload,
                "expected_class": label,
                "source_file": path.name,
            }
        )

    return picked[:n]


def build_mixed_dataset(total: int, sensitive_ratio: float, seed: int) -> list[dict]:
    rng = random.Random(seed)
    n_sens = int(round(total * sensitive_ratio))
    n_pub = total - n_sens

    sensitive = sample_rows_from_dir(DATA_RAW_SENSITIVE, "Sensitive", n_sens, rng)
    public = sample_rows_from_dir(DATA_RAW_NORMAL, "Public", n_pub, rng)

    mixed = sensitive + public
    rng.shuffle(mixed)  # critical: not blocked by class
    return mixed


def write_csv(rows: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["row_id", "payload", "expected_class", "source_file"],
        )
        writer.writeheader()
        for i, row in enumerate(rows, start=1):
            writer.writerow(
                {
                    "row_id": i,
                    "payload": row["payload"],
                    "expected_class": row["expected_class"],
                    "source_file": row["source_file"],
                }
            )


def write_txt_lines(rows: list[dict], output: Path) -> None:
    """One payload per line — convenient for the dashboard line-as-packet model."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            # Single-line record
            line = row["payload"].replace("\n", " ").replace("\r", " ")
            handle.write(line + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create shuffled mixed demo dataset.")
    parser.add_argument("--total", type=int, default=100, help="Total rows in the demo file.")
    parser.add_argument(
        "--sensitive-ratio",
        type=float,
        default=0.5,
        help="Fraction of sensitive rows (default 0.5).",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output CSV path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = Path(args.output)
    if not output.is_absolute():
        output = REPO_ROOT / output

    rows = build_mixed_dataset(args.total, args.sensitive_ratio, args.seed)
    write_csv(rows, output)

    txt_output = output.with_suffix(".txt")
    write_txt_lines(rows, txt_output)

    n_sens = sum(1 for r in rows if r["expected_class"] == "Sensitive")
    n_pub = len(rows) - n_sens

    # Show interleaving pattern (first 20 labels)
    preview = "".join("S" if r["expected_class"] == "Sensitive" else "P" for r in rows[:40])

    print("Mixed demo dataset created")
    print(f"  Total rows:     {len(rows)}")
    print(f"  Sensitive:      {n_sens}")
    print(f"  Public:         {n_pub}")
    print(f"  Seed:           {args.seed}")
    print(f"  Label preview:  {preview}...  (S=Sensitive, P=Public)")
    print(f"  CSV (with labels): {output.relative_to(REPO_ROOT)}")
    print(f"  TXT (for upload):  {txt_output.relative_to(REPO_ROOT)}")
    print()
    print("Dashboard tip: upload the .txt file (Local File tab) so each line is one packet.")
    print("The CSV keeps expected_class for your own checking; the live model does not read that label.")


if __name__ == "__main__":
    main()
