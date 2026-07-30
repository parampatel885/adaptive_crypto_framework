"""
Offline crypto benchmark: Always Tier 3 vs Adaptive (LogReg + Q-Learning).

Uses the production Logistic Regression sensitivity model and, by default,
the pretrained Q-table with safety mask (matches live dashboard policy).

Usage:
    python Model_Experimenting/run_benchmarks.py
    python Model_Experimenting/run_benchmarks.py --max-rows 1200
    python Model_Experimenting/run_benchmarks.py --hf-limit 200
"""

from __future__ import annotations

import argparse
import csv
import json
import pickle
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from repo_paths import (  # noqa: E402
    DATA_PROCESSED,
    MODEL_CANDIDATES,
    Q_TABLE_CANDIDATES,
    Q_TABLE_PRETRAINED,
    RESULTS_DIR,
    setup_production_imports,
)

setup_production_imports()

from src.classifiers import AdaptiveQLearner, calculate_reinforcement_reward  # noqa: E402
from src.crypto_engines import (  # noqa: E402
    execute_hybrid_ecc_aes,
    execute_lightweight_trivium,
    execute_standard_aes,
)
from src.monitor import FEATURE_COLUMNS, extract_file_features  # noqa: E402

ENGINES = (
    execute_lightweight_trivium,
    execute_standard_aes,
    execute_hybrid_ecc_aes,
)


def build_agent(use_pretrained: bool, epsilon: float) -> AdaptiveQLearner:
    agent = AdaptiveQLearner(
        persist_path=None,
        load_existing=False,
        safety_mask=True,
        epsilon=epsilon,
        epsilon_min=0.01,
        epsilon_decay=0.9995,
        decay_epsilon=False,  # fixed epsilon for reproducible benchmark
    )
    if use_pretrained:
        q_path = next((p for p in Q_TABLE_CANDIDATES if p.exists()), None)
        if q_path is not None:
            agent.load(q_path)
            print(f"Loaded Q-table: {q_path.relative_to(REPO_ROOT)}")
        else:
            print("No pretrained Q-table found; using default policy + safety mask.")
    return agent


def run_packet_loop(
    payloads: list[str],
    sens_states: list[int],
    threats: list[int],
    agent: AdaptiveQLearner,
    epsilon: float,
) -> dict:
    metrics = {
        "static_heavy_time": 0.0,
        "static_heavy_energy": 0.0,
        "adaptive_time": 0.0,
        "adaptive_energy": 0.0,
        "lightweight_triggers": 0,
        "standard_aes_triggers": 0,
        "hybrid_ecc_triggers": 0,
        "n_packets": len(payloads),
    }

    for i, payload in enumerate(payloads):
        sens = int(sens_states[i])
        threat = int(threats[i])

        _, s_time, s_energy = execute_hybrid_ecc_aes(payload)
        metrics["static_heavy_time"] += s_time
        metrics["static_heavy_energy"] += s_energy

        action = int(agent.select_action(sens, threat, epsilon=epsilon))
        _, a_time, a_energy = ENGINES[action](payload)
        metrics["adaptive_time"] += a_time
        metrics["adaptive_energy"] += a_energy

        if action == 0:
            metrics["lightweight_triggers"] += 1
        elif action == 1:
            metrics["standard_aes_triggers"] += 1
        else:
            metrics["hybrid_ecc_triggers"] += 1

        reward = calculate_reinforcement_reward(sens, threat, action)
        next_sens = int(sens_states[(i + 1) % len(sens_states)])
        next_threat = int(threats[(i + 1) % len(threats)])
        agent.update_q_values(sens, threat, action, reward, next_sens, next_threat)

    return metrics


def summarize(metrics: dict, scenario: str) -> dict:
    static_t = metrics["static_heavy_time"]
    adapt_t = metrics["adaptive_time"]
    static_e = metrics["static_heavy_energy"]
    adapt_e = metrics["adaptive_energy"]
    lat_save = ((static_t - adapt_t) / static_t * 100.0) if static_t else 0.0
    en_save = ((static_e - adapt_e) / static_e * 100.0) if static_e else 0.0
    return {
        "scenario": scenario,
        "n_packets": metrics["n_packets"],
        "static_latency_ms": round(static_t, 2),
        "adaptive_latency_ms": round(adapt_t, 2),
        "latency_saving_pct": round(lat_save, 2),
        "static_energy_uj": round(static_e, 2),
        "adaptive_energy_uj": round(adapt_e, 2),
        "energy_saving_pct": round(en_save, 2),
        "tier1": metrics["lightweight_triggers"],
        "tier2": metrics["standard_aes_triggers"],
        "tier3": metrics["hybrid_ecc_triggers"],
    }


def print_report(row: dict) -> None:
    print("\n" + "=" * 65)
    print(f"  BENCHMARK: {row['scenario']}  ({row['n_packets']} packets)")
    print("=" * 65)
    print(f" [Static Tier 3] Latency:  {row['static_latency_ms']:.2f} ms")
    print(f" [Adaptive]      Latency:  {row['adaptive_latency_ms']:.2f} ms")
    print(f" Latency reduction:        {row['latency_saving_pct']:.2f}%")
    print("-" * 65)
    print(f" [Static Tier 3] Energy:   {row['static_energy_uj']:.2f} uJ  (modeled)")
    print(f" [Adaptive]      Energy:   {row['adaptive_energy_uj']:.2f} uJ  (modeled)")
    print(f" Energy savings:           {row['energy_saving_pct']:.2f}%")
    print("-" * 65)
    print(
        f" Tier mix -> T1:{row['tier1']}  T2:{row['tier2']}  T3:{row['tier3']}"
    )
    print("=" * 65)


def run_local_benchmark(
    model,
    max_rows: int | None,
    agent: AdaptiveQLearner,
    epsilon: float,
) -> dict:
    dataset = pd.read_csv(DATA_PROCESSED / "sensitivity_dataset.csv")
    if max_rows is not None:
        dataset = dataset.head(max_rows)

    features = dataset[FEATURE_COLUMNS]
    sens_states = [int(x) for x in model.predict(features)]
    threats = [1 if (i % 4 == 0) else 0 for i in range(len(dataset))]
    payloads = [str(row.to_dict()) for _, row in dataset.iterrows()]

    print(f"Local dataset packets: {len(payloads)}")
    metrics = run_packet_loop(payloads, sens_states, threats, agent, epsilon)
    return summarize(metrics, f"local_{len(payloads)}_packets")


def run_hf_benchmark(
    model,
    limit: int,
    agent: AdaptiveQLearner,
    epsilon: float,
) -> dict | None:
    try:
        from datasets import load_dataset
    except ImportError:
        print("datasets package missing; skipping HuggingFace stream benchmark.")
        return None

    print(f"Streaming HuggingFace ai4privacy/pii-masking-300k (limit={limit})...")
    try:
        stream = load_dataset(
            "ai4privacy/pii-masking-300k",
            split="train",
            streaming=True,
        )
    except Exception as exc:
        print(f"HuggingFace stream failed ({exc}); skipping HF benchmark.")
        return None

    keys = ["source_text", "text", "unmasked_text", "content", "utterance", "inputs", "prompt"]
    payloads: list[str] = []
    for i, record in enumerate(stream):
        if i >= limit:
            break
        text = next((str(record[k]) for k in keys if k in record and record[k]), str(record))
        payloads.append(text)

    if not payloads:
        print("No HF records streamed; skipping.")
        return None

    sens_states = []
    for i, text in enumerate(payloads):
        feats = extract_file_features(f"hf_packet_{i}.txt", text)
        df = pd.DataFrame([feats], columns=FEATURE_COLUMNS)
        sens_states.append(int(model.predict(df)[0]))
    threats = [1 if (i % 4 == 0) else 0 for i in range(len(payloads))]

    print(f"HF packets: {len(payloads)}")
    metrics = run_packet_loop(payloads, sens_states, threats, agent, epsilon)
    return summarize(metrics, f"hf_stream_{len(payloads)}_packets")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ACF crypto benchmarks with LogReg.")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Cap local dataset rows (default: all ~1800).",
    )
    parser.add_argument(
        "--hf-limit",
        type=int,
        default=200,
        help="HuggingFace stream packet count (0 to skip).",
    )
    parser.add_argument("--epsilon", type=float, default=0.01)
    parser.add_argument(
        "--no-pretrained-q",
        action="store_true",
        help="Start from default Q policy instead of pretrained table.",
    )
    parser.add_argument(
        "--output",
        default=str(RESULTS_DIR / "benchmark_logreg_summary.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model_path = next(path for path in MODEL_CANDIDATES if path.exists())
    with model_path.open("rb") as handle:
        model = pickle.load(handle)
    print(f"Loaded sensitivity model: {model_path.relative_to(REPO_ROOT)}")
    print(f"Model type: {type(model)}")

    rows: list[dict] = []

    local_agent = build_agent(use_pretrained=not args.no_pretrained_q, epsilon=args.epsilon)
    local_row = run_local_benchmark(model, args.max_rows, local_agent, args.epsilon)
    print_report(local_row)
    rows.append(local_row)

    if args.hf_limit > 0:
        hf_agent = build_agent(use_pretrained=not args.no_pretrained_q, epsilon=args.epsilon)
        hf_row = run_hf_benchmark(model, args.hf_limit, hf_agent, args.epsilon)
        if hf_row is not None:
            print_report(hf_row)
            rows.append(hf_row)

    out = Path(args.output)
    if not out.is_absolute():
        out = REPO_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # Also dump JSON for the plotter
    json_path = out.with_suffix(".json")
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nWrote: {out.relative_to(REPO_ROOT)}")
    print(f"Wrote: {json_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
