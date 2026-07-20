"""
Prepare the Kaggle weather dataset as a normal/public training source.

Dataset:
    https://www.kaggle.com/datasets/muthuj7/weather-dataset
    File: weatherHistory.csv (~96k public meteorological rows)

This script can:
  1) Copy a locally downloaded weatherHistory.csv / zip into data/raw/normal/
  2) Optionally download via Kaggle API if `kaggle` is installed and
     ~/.kaggle/kaggle.json exists
  3) Fall back to a public GitHub mirror of the same CSV

Usage:
    python tests/fetch_weather_dataset.py
    python tests/fetch_weather_dataset.py --source "C:/Downloads/weatherHistory.csv"
    python tests/fetch_weather_dataset.py --source "C:/Downloads/archive.zip"
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "raw" / "normal" / "weatherHistory.csv"
KAGGLE_SLUG = "muthuj7/weather-dataset"
GITHUB_MIRROR = (
    "https://raw.githubusercontent.com/Abhishek20182/"
    "Performing-Analysis-of-Meteorological-Data/main/weatherHistory.csv"
)


def find_csv_in_dir(directory: Path) -> Path | None:
    candidates = sorted(directory.rglob("*.csv"))
    for path in candidates:
        if path.name.lower() == "weatherhistory.csv":
            return path
    return candidates[0] if candidates else None


def copy_from_local(source: Path, output_path: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Source not found: {source}")

    if source.suffix.lower() == ".csv":
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, output_path)
        return

    if source.suffix.lower() == ".zip":
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(source, "r") as zf:
                zf.extractall(tmp)
            csv_path = find_csv_in_dir(Path(tmp))
            if csv_path is None:
                raise RuntimeError(f"No CSV found inside zip: {source}")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(csv_path, output_path)
        return

    raise ValueError("Source must be a .csv or .zip file.")


def download_via_kaggle(output_path: Path) -> bool:
    """Return True if download succeeded via Kaggle CLI."""
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json.exists():
        print("Kaggle credentials not found at ~/.kaggle/kaggle.json")
        return False

    try:
        with tempfile.TemporaryDirectory() as tmp:
            cmd = [
                sys.executable,
                "-m",
                "kaggle",
                "datasets",
                "download",
                "-d",
                KAGGLE_SLUG,
                "-p",
                tmp,
                "--unzip",
            ]
            print("Downloading via Kaggle API...")
            subprocess.run(cmd, check=True)
            csv_path = find_csv_in_dir(Path(tmp))
            if csv_path is None:
                print("Kaggle download succeeded but no CSV was found.")
                return False
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(csv_path, output_path)
        return True
    except Exception as exc:
        print(f"Kaggle download failed: {exc}")
        return False


def download_via_mirror(output_path: Path) -> None:
    print(f"Downloading public mirror:\n  {GITHUB_MIRROR}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    urlretrieve(GITHUB_MIRROR, output_path)


def summarize(output_path: Path) -> None:
    import pandas as pd

    df = pd.read_csv(output_path, nrows=5)
    # Count rows cheaply
    with output_path.open("r", encoding="utf-8", errors="ignore") as handle:
        row_count = sum(1 for _ in handle) - 1

    print("\nWeather dataset ready")
    print("=" * 40)
    print(f"Rows:     ~{row_count}")
    print(f"Columns:  {list(df.columns)}")
    print(f"Output:   {output_path.relative_to(ROOT)}")
    print("Label:    Normal / Public (0)")
    print("\nNext steps:")
    print("  python tests/rebuild_sensitivity_dataset.py --rows-per-file 200")
    print("  python tests/compare_classifiers_lofo.py --rows-per-file 200 --k 1")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch/prepare Kaggle weather dataset as a normal CSV source."
    )
    parser.add_argument(
        "--source",
        default="",
        help="Optional local path to weatherHistory.csv or the Kaggle zip.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Destination CSV path under data/raw/normal/.",
    )
    parser.add_argument(
        "--prefer-kaggle",
        action="store_true",
        help="Try Kaggle API before the public mirror.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    if args.source.strip():
        copy_from_local(Path(args.source.strip()), output_path)
    elif args.prefer_kaggle and download_via_kaggle(output_path):
        pass
    else:
        # Default path: mirror first (no Kaggle login required)
        if args.prefer_kaggle:
            print("Falling back to public mirror...")
        download_via_mirror(output_path)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise SystemExit("Failed to prepare weatherHistory.csv")

    summarize(output_path)


if __name__ == "__main__":
    main()
