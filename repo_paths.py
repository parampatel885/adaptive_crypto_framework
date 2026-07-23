"""Shared repository layout paths for Documents / Model_Experimenting / Production."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DOCUMENTS = REPO_ROOT / "Documents"
MODEL_EXPERIMENTING = REPO_ROOT / "Model_Experimenting"
PRODUCTION = REPO_ROOT / "Production"

DATA_DIR = MODEL_EXPERIMENTING / "data"
DATA_RAW_SENSITIVE = DATA_DIR / "raw" / "sensitive"
DATA_RAW_NORMAL = DATA_DIR / "raw" / "normal"
DATA_PROCESSED = DATA_DIR / "processed"
RESULTS_DIR = MODEL_EXPERIMENTING / "results"

SRC_DIR = PRODUCTION / "src"
TEMPLATES_DIR = PRODUCTION / "templates"
STATIC_DIR = PRODUCTION / "static"

SENSITIVITY_MODEL = SRC_DIR / "sensitivity_model.pkl"
COMPAT_MODEL = SRC_DIR / "knn_model.pkl"
Q_TABLE_PATH = SRC_DIR / "q_table.npy"

MODEL_CANDIDATES = (SENSITIVITY_MODEL, COMPAT_MODEL)


def setup_production_imports() -> None:
    """Make ``Production/`` importable so ``from src...`` resolves."""
    prod = str(PRODUCTION)
    if prod not in sys.path:
        sys.path.insert(0, prod)


def setup_repo_imports() -> None:
    """Make the repository root importable (for ``repo_paths``)."""
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
