"""
Stream a small sample from HuggingFace ai4privacy/pii-masking-300k
and save it as a local sensitive CSV for training / LOFO validation.

Does NOT download the full 300k dataset — uses streaming only.

Usage:
    python tests/fetch_pii_masking_sample.py
    python tests/fetch_pii_masking_sample.py --limit 200
    python tests/fetch_pii_masking_sample.py --limit 500 --language English
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "raw" / "sensitive" / "pii_masking_sample.csv"
DEFAULT_DATASET = "ai4privacy/pii-masking-300k"

# Prefer unmasked text fields that contain real PII
TEXT_KEYS = ("source_text", "unmasked_text", "text", "content")


def extract_text(record: dict) -> str | None:
    """Pull the best available unmasked text field from a HF record."""
    for key in TEXT_KEYS:
        value = record.get(key)
        if value and isinstance(value, str) and value.strip():
            return value.strip()
    return None


def fetch_sample(
    dataset_name: str,
    limit: int,
    language: str | None,
    skip: int = 0,
) -> list[dict]:
    """Stream up to `limit` records and return rows ready for CSV export."""
    from datasets import load_dataset  # type: ignore

    print(f"Streaming from HuggingFace: {dataset_name}")
    print(
        f"Target rows: {limit}"
        + (f" | skip first {skip}" if skip else "")
        + (f" | language filter: {language}" if language else "")
    )

    stream = load_dataset(dataset_name, split="train", streaming=True)
    rows: list[dict] = []
    skipped = 0

    for record in stream:
        if language:
            record_lang = str(record.get("language", "")).strip()
            if record_lang.lower() != language.lower():
                continue

        text = extract_text(record)
        if not text:
            continue

        if skipped < skip:
            skipped += 1
            continue

        rows.append(
            {
                "source_text": text,
                "language": record.get("language", ""),
                "record_id": record.get("id", ""),
                "split_set": record.get("set", "train"),
            }
        )

        if len(rows) % 50 == 0:
            print(f"  collected {len(rows)}/{limit} ...")

        if len(rows) >= limit:
            break

    return rows


def write_csv(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["source_text", "language", "record_id", "split_set"]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stream a small PII sample from HuggingFace into data/raw/sensitive/."
    )
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET,
        help="HuggingFace dataset name (default: ai4privacy/pii-masking-300k).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Number of rows to save (default: 200).",
    )
    parser.add_argument(
        "--language",
        default="English",
        help="Optional language filter (default: English). Pass empty string to disable.",
    )
    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        help="Skip this many matching records before collecting (for a second independent sample).",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output CSV path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be >= 1")
    if args.skip < 0:
        raise SystemExit("--skip must be >= 0")

    language = args.language.strip() or None
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    rows = fetch_sample(args.dataset, args.limit, language, skip=args.skip)
    if not rows:
        raise SystemExit("No rows collected. Check dataset name / language filter.")

    write_csv(rows, output_path)

    print("\nPII sample saved")
    print("=" * 40)
    print(f"Rows:     {len(rows)}")
    print(f"Columns:  source_text, language, record_id, split_set")
    print(f"Output:   {output_path.relative_to(ROOT)}")
    print("\nNext steps:")
    print("  python tests/rebuild_sensitivity_dataset.py --rows-per-file 200")
    print("  python tests/compare_classifiers_lofo.py --rows-per-file 200 --k 1")


if __name__ == "__main__":
    main()
