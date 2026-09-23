"""
Centralized repository path definitions and environment import setup for
Adaptive Cryptographic Framework.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRODUCTION_DIR = ROOT / "Production"
SRC_DIR = PRODUCTION_DIR / "src"
MODEL_EXPERIMENTING_DIR = ROOT / "Model_Experimenting"
DATA_DIR = MODEL_EXPERIMENTING_DIR / "data"
DATA_RAW_NORMAL = DATA_DIR / "raw" / "normal"
DATA_RAW_SENSITIVE = DATA_DIR / "raw" / "sensitive"
DATA_PROCESSED = DATA_DIR / "processed"
RESULTS_DIR = MODEL_EXPERIMENTING_DIR / "results"
DOCUMENTS = ROOT / "Documents"

TEMPLATES_DIR = PRODUCTION_DIR / "templates"
STATIC_DIR = PRODUCTION_DIR / "static"

SENSITIVITY_MODEL = SRC_DIR / "sensitivity_model.pkl"
COMPAT_MODEL = SRC_DIR / "knn_model.pkl"
MODEL_CANDIDATES = [
    SRC_DIR / "sensitivity_model.pkl",
    SRC_DIR / "knn_model.pkl",
]

Q_TABLE_PATH = SRC_DIR / "q_table.npy"
Q_TABLE_PRETRAINED = SRC_DIR / "q_table_pretrained.npy"
Q_TABLE_CANDIDATES = [
    SRC_DIR / "q_table.npy",
    SRC_DIR / "q_table_pretrained.npy",
]


def setup_production_imports() -> None:
    """Ensure root, Production, and Model_Experimenting are in sys.path."""
    for p in (ROOT, PRODUCTION_DIR, SRC_DIR, MODEL_EXPERIMENTING_DIR):
        p_str = str(p)
        if p_str not in sys.path:
            sys.path.insert(0, p_str)
