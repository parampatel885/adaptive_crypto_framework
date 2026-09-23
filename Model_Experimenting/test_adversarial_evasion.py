"""
Adversarial Evasion & Obfuscation Robustness Evaluation for ACF Sensitivity Classifier.

Tests the classifier against realistic evasion techniques:
  1. Clean baseline (unmodified sensitive and normal records)
  2. Token splitting & delimiter noise (e.g. S.S.N: 1 2 3 - 4 5 - 6 7 8 9)
  3. Padding & Camouflage (sensitive record buried in benign filler text)
  4. Base64 encoding evasion (encoded payload string)
  5. Special character / zero-width whitespace injection

Outputs:
  - Model_Experimenting/results/adversarial_evasion_summary.csv
  - Model_Experimenting/results/adversarial_evasion_summary.png
  - Documents/images/adversarial_evasion_summary.png
"""

from __future__ import annotations

import argparse
import base64
import csv
import pickle
import random
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, recall_score

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from repo_paths import (  # noqa: E402
    DATA_PROCESSED,
    DOCUMENTS,
    MODEL_CANDIDATES,
    RESULTS_DIR,
    setup_production_imports,
)

setup_production_imports()

from src.monitor import FEATURE_COLUMNS, extract_file_features  # noqa: E402


def obfuscate_token_split(text: str) -> str:
    """Inject spaces/dots into keywords and digits to defeat simple regexes."""
    out = []
    for ch in text:
        if ch.isdigit() and random.random() < 0.4:
            out.append(f" {ch} ")
        elif ch in ":=-_" and random.random() < 0.5:
            out.append(f" {ch} ")
        else:
            out.append(ch)
    return "".join(out)


def obfuscate_padding_camouflage(text: str) -> str:
    """Pad sensitive data with benign dictionary and sensor noise."""
    benign_noise = (
        " [SENSOR_LOG temperature=22.4 humidity=55.1 wind=12.1 airport=JFK flight=AA102] "
    )
    return benign_noise * 3 + text + benign_noise * 3


def obfuscate_base64_wrap(text: str) -> str:
    """Base64-encode the payload string."""
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return f"ENC_PAYLOAD_B64: {encoded}"


def obfuscate_char_noise(text: str) -> str:
    """Insert special characters and noise symbols."""
    symbols = ["~", "^", "*", "#", "$", "/"]
    words = text.split(" ")
    noisy_words = [w + random.choice(symbols) if random.random() < 0.3 else w for w in words]
    return " ".join(noisy_words)


PERTURBATIONS = {
    "1. Clean Baseline": lambda txt: txt,
    "2. Token Splitting": obfuscate_token_split,
    "3. Camouflage Padding": obfuscate_padding_camouflage,
    "4. Special Char Noise": obfuscate_char_noise,
    "5. Base64 Encoding": obfuscate_base64_wrap,
}


def run_adversarial_evaluation(seed: int = 42) -> dict:
    random.seed(seed)
    np.random.seed(seed)

    # 1. Load trained classifier
    model_path = next(p for p in MODEL_CANDIDATES if p.exists())
    with model_path.open("rb") as handle:
        model = pickle.load(handle)

    # 2. Load dataset
    df = pd.read_csv(DATA_PROCESSED / "sensitivity_dataset.csv")
    raw_texts = [str(dict(row)) for _, row in df.iterrows()]
    y_true = df["Is_Sensitive"].values

    results_table = []
    print("\n" + "=" * 75)
    print("  ADVERSARIAL EVASION & OBFUSCATION ROBUSTNESS EVALUATION")
    print("=" * 75)

    for p_name, perturb_fn in PERTURBATIONS.items():
        # Apply perturbation to all payloads
        perturbed_features = []
        for txt in raw_texts:
            mod_text = perturb_fn(txt)
            feats = extract_file_features("data.txt", mod_text)
            perturbed_features.append(feats)

        feats_df = pd.DataFrame(perturbed_features, columns=FEATURE_COLUMNS)
        y_pred = model.predict(feats_df).astype(int)

        acc = accuracy_score(y_true, y_pred)
        f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
        sens_recall = recall_score(y_true, y_pred, pos_label=1, zero_division=0)
        norm_recall = recall_score(y_true, y_pred, pos_label=0, zero_division=0)

        # Count how many sensitive items were caught vs leaked
        sens_total = int(np.sum(y_true == 1))
        sens_caught = int(np.sum((y_true == 1) & (y_pred == 1)))
        sens_leaked = int(np.sum((y_true == 1) & (y_pred == 0)))

        res = {
            "attack_type": p_name,
            "accuracy": round(acc * 100, 2),
            "macro_f1": round(f1, 4),
            "sensitive_recall_pct": round(sens_recall * 100, 2),
            "normal_recall_pct": round(norm_recall * 100, 2),
            "sensitive_caught": sens_caught,
            "sensitive_leaked": sens_leaked,
        }
        results_table.append(res)

        print(
            f"{p_name:<26} | Acc: {acc*100:5.2f}% | F1: {f1:.4f} | "
            f"Sens Recall: {sens_recall*100:5.2f}% | Caught: {sens_caught}/{sens_total} "
            f"(Leaked: {sens_leaked})"
        )

    print("=" * 75)

    # 3. Save to CSV
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    csv_out = RESULTS_DIR / "adversarial_evasion_summary.csv"
    with csv_out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results_table[0].keys()))
        writer.writeheader()
        writer.writerows(results_table)
    print(f"\n[Saved CSV]: {csv_out}")

    # 4. Generate Publication Figure
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    names = [r["attack_type"] for r in results_table]
    sens_recalls = [r["sensitive_recall_pct"] for r in results_table]
    macro_f1s = [r["macro_f1"] * 100 for r in results_table]

    x = np.arange(len(names))
    width = 0.35

    # (a) Sensitive Recall vs Macro F1
    ax0 = axes[0]
    ax0.bar(x - width / 2, sens_recalls, width, label="Sensitive Recall (%)", color="#198754")
    ax0.bar(x + width / 2, macro_f1s, width, label="Macro F1 (%)", color="#0d6efd")
    ax0.set_xticks(x)
    ax0.set_xticklabels(names, rotation=20, ha="right", fontsize=9)
    ax0.set_ylabel("Performance (%)")
    ax0.set_ylim(0, 110)
    ax0.set_title("(a) Evasion Defense Robustness", fontweight="bold", fontsize=11)
    ax0.grid(True, linestyle=":", alpha=0.5)
    ax0.legend(loc="lower left", fontsize=9)

    # (b) Caught vs Leaked Sensitive Payloads
    ax1 = axes[1]
    caught = [r["sensitive_caught"] for r in results_table]
    leaked = [r["sensitive_leaked"] for r in results_table]

    ax1.bar(names, caught, label="Protected (Escalated to Tier 3)", color="#20c997")
    ax1.bar(names, leaked, bottom=caught, label="Evasion Leak (Underprotected)", color="#dc3545")
    ax1.set_xticks(x)
    ax1.set_xticklabels(names, rotation=20, ha="right", fontsize=9)
    ax1.set_ylabel("Sensitive Payload Count")
    ax1.set_title("(b) Sensitive Payload Protection under Evasion", fontweight="bold", fontsize=11)
    ax1.grid(True, linestyle=":", alpha=0.5)
    ax1.legend(loc="lower left", fontsize=9)

    fig.tight_layout()
    img_out = RESULTS_DIR / "adversarial_evasion_summary.png"
    fig.savefig(img_out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"[Saved Plot]: {img_out}")

    # Copy to Documents/images for presentation
    doc_img_dir = DOCUMENTS / "images"
    doc_img_dir.mkdir(parents=True, exist_ok=True)
    doc_img_out = doc_img_dir / "adversarial_evasion_summary.png"
    import shutil
    shutil.copy2(img_out, doc_img_out)
    print(f"[Saved Presentation Image]: {doc_img_out}")

    return {
        "results": results_table,
        "csv_path": str(csv_out),
        "img_path": str(img_out),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    run_adversarial_evaluation(seed=args.seed)
