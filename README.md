# Context-Aware Adaptive Cryptography Framework 🔐

An intelligent, multi-tier cryptographic routing engine that dynamically balances enterprise security standards with processing efficiency in resource-constrained environments. By leveraging a dual-intelligence layer (Machine Learning + Reinforcement Learning), the system profiles incoming payloads and network states to swap real cryptographic ciphers on the fly.

## 📊 Core Performance Breakthroughs Verified
* **Local Ingestion Inferences (1,200 Packets):** **61.99% Latency Reduction** and **65.94% Energy Footprint Savings** achieved over traditional static configurations.
* **Production Live Stream Inferences (200 Hugging Face Packets):** **68.50% Net Delay Optimization** attained under organic, unstructured textual drift conditions.

---

## 📁 Repository Architecture Mapping
```text
adaptive-crypto-framework/
│
├── data/                             # Dataset Storage Directory
│   ├── raw/                          # Source files segmented by risk profiles
│   │   ├── sensitive/                # High-Sensitivity PHI/PCI CSV data sources
│   │   └── normal/                   # Public domain telemetry CSV data sources
│   └── processed/                    # Cleaned, unified data matrices
│       ├── sensitivity_dataset.csv   # Aggregated feature map used for KNN training
│       
│
├── src/                              # Framework Core Source Library
│   ├── __init__.py
│   ├── monitor.py                    # Feature Extraction Unit (Shannon Entropy, Keywords)
│   ├── classifiers.py                # Intelligence Sorter (KNN + Reinforcement Q-Table)
│   └── crypto_engines.py             # Cryptographic Suites (ChaCha20, AES-CTR, ECDH Hybrid)
│
├── notebooks/                        # Modular Google Colab Workspace 
│   ├── 01_data_preprocessing.ipynb   # Raw data ingestion & metadata feature synthesis
│   ├── 02_knn_model_training.ipynb   # Machine learning optimization & KNN serialization
│   └── 03_q_learning_simulator.ipynb # Real crypto execution & Q-Learning stress testing
│
├── tests/                            # Experimental Benchmarking Layout 🧪
│   ├── run_benchmarks.py             # 👈LOCAL RUNS: Local dataset evaluations (Static vs. Adaptive)
│   └── test_production_streams.py    # 👈PRODUCTION RUNS: Out-of-sample Hugging Face live streams
│
├── benchmark_results_dashboard.py         # Independent graphical report hub for your mentor
├── README.md                         # Product documentation and user execution guide
└── requirements.txt                  # Consolidated library environmental dependencies
