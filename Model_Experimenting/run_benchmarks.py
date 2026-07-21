import pickle
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from repo_paths import DATA_PROCESSED, MODEL_CANDIDATES, setup_production_imports  # noqa: E402

setup_production_imports()

from src.classifiers import AdaptiveQLearner, calculate_reinforcement_reward  # noqa: E402
from src.crypto_engines import (  # noqa: E402
    execute_hybrid_ecc_aes,
    execute_lightweight_trivium,
    execute_standard_aes,
)
from src.monitor import FEATURE_COLUMNS  # noqa: E402


def run_system_benchmarks():
    print("🎬 Initializing Real Cryptography Benchmark Evaluation Harness...")
    dataset = pd.read_csv(DATA_PROCESSED / "sensitivity_dataset.csv")
    model_path = next(path for path in MODEL_CANDIDATES if path.exists())
    with model_path.open("rb") as f:
        sensitivity_model = pickle.load(f)
    print(f"Loaded sensitivity model: {model_path.relative_to(REPO_ROOT)}")

    rl_agent = AdaptiveQLearner()
    metrics = {
        "static_heavy_time": 0.0,
        "static_heavy_energy": 0.0,
        "adaptive_time": 0.0,
        "adaptive_energy": 0.0,
        "lightweight_triggers": 0,
        "standard_aes_triggers": 0,
        "hybrid_ecc_triggers": 0,
    }

    for index, row in dataset.iterrows():
        features_df = pd.DataFrame([row[FEATURE_COLUMNS].to_dict()], columns=FEATURE_COLUMNS)

        sens_state = sensitivity_model.predict(features_df)[0]
        threat_state = 1 if (index % 4 == 0) else 0
        raw_payload_string = str(row.to_dict())

        # Approach A (Static control)
        _, s_time, s_energy = execute_hybrid_ecc_aes(raw_payload_string)
        metrics["static_heavy_time"] += s_time
        metrics["static_heavy_energy"] += s_energy

        # Approach B (Adaptive framework)
        selected_action = rl_agent.select_action(sens_state, threat_state, epsilon=0.05)
        if selected_action == 0:
            _, a_time, a_energy = execute_lightweight_trivium(raw_payload_string)
            metrics["lightweight_triggers"] += 1
        elif selected_action == 1:
            _, a_time, a_energy = execute_standard_aes(raw_payload_string)
            metrics["standard_aes_triggers"] += 1
        else:
            _, a_time, a_energy = execute_hybrid_ecc_aes(raw_payload_string)
            metrics["hybrid_ecc_triggers"] += 1

        metrics["adaptive_time"] += a_time
        metrics["adaptive_energy"] += a_energy
        rl_agent.update_q_values(
            sens_state,
            threat_state,
            selected_action,
            calculate_reinforcement_reward(sens_state, threat_state, selected_action),
            sens_state,
            threat_state,
        )

    print("\n" + "=" * 65 + "\n             FINAL REAL CRYPTOGRAPHY BENCHMARK REPORT           \n" + "=" * 65)
    print(f" [Approach A] Total Static Latency:   {metrics['static_heavy_time']:.2f} ms")
    print(f" [Approach B] Total Adaptive Latency: {metrics['adaptive_time']:.2f} ms")
    print(
        f" 📈 LATENCY REDUCTION EFFICIENCY:     {((metrics['static_heavy_time'] - metrics['adaptive_time']) / metrics['static_heavy_time']) * 100:.2f}%"
    )
    print("-" * 65)
    print(f" [Approach A] Total Static Energy:    {metrics['static_heavy_energy']:.2f} uJ")
    print(f" [Approach B] Total Adaptive Energy:  {metrics['adaptive_energy']:.2f} uJ")
    print(
        f" 🔋 TOTAL SYSTEM BATTERY SAVED:       {((metrics['static_heavy_energy'] - metrics['adaptive_energy']) / metrics['static_heavy_energy']) * 100:.2f}%"
    )
    print(
        "-" * 65
        + "\n 🕹️  Q-LEARNING INTELLIGENCE TIER ROUTING DISTRIBUTION:"
        + f"\n    -> Tier 1 (Real ChaCha20 Stream): {metrics['lightweight_triggers']} times"
        + f"\n    -> Tier 2 (Real AES-128 CTR):     {metrics['standard_aes_triggers']} times"
        + f"\n    -> Tier 3 (Real Hybrid ECC-AES):  {metrics['hybrid_ecc_triggers']} times\n"
        + "=" * 65
    )


if __name__ == "__main__":
    run_system_benchmarks()
