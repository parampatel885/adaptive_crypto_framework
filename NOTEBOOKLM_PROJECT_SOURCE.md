# Adaptive Cryptography Framework (ACF)
## Complete Project Source Document for Academic Report Generation

> **Purpose of this document:** Upload this file to NotebookLM along with your college's report format template and your previous semester report. NotebookLM can then synthesize a formal report matching your institution's structure while preserving accurate technical details from this project.

---

## 1. Project Identity

| Field | Detail |
|-------|--------|
| **Project Title** | Adaptive Cryptography Framework (ACF) — A Context-Aware Multi-Tier Encryption Routing Engine |
| **Domain** | Cybersecurity · Machine Learning · Applied Cryptography |
| **Project Type** | Minor / Major Project (Semester-end implementation with experimental evaluation) |
| **Author** | Param Patel |
| **Repository** | `adaptive_crypto_framework` (GitHub: parampatel885/adaptive_crypto_framework) |

---

## 2. Abstract (Draft for Report)

Traditional cryptographic systems apply a single, heavyweight encryption scheme to all data regardless of content sensitivity or environmental threat level. This one-size-fits-all approach wastes computational resources on low-risk public data while still requiring manual policy decisions for sensitive payloads. The **Adaptive Cryptography Framework (ACF)** addresses this gap by introducing an intelligent, three-stage decision pipeline: (1) real-time feature extraction from incoming data packets, (2) K-Nearest Neighbors (KNN) classification of data sensitivity, and (3) Q-Learning reinforcement agent selection of the optimal cipher tier based on both sensitivity and live network threat state.

The system implements three cryptographic tiers — lightweight ChaCha20 (Tier 1), standard AES-128 CTR (Tier 2), and hybrid ECDH + AES (Tier 3) — using the Python `cryptography` library. A Flask-based web dashboard with Server-Sent Events (SSE) provides live comparison between the adaptive framework and a static baseline that always applies the heaviest cipher.

Experimental evaluation on a balanced dataset of 1,200 locally processed packets demonstrates **61.99% latency reduction** and **65.94% energy savings** compared to the static baseline. On a live HuggingFace PII stream of 200 packets (`ai4privacy/pii-masking-300k`), the framework achieves **68.50% latency reduction**. The KNN sensitivity classifier achieves **100% accuracy** on a held-out test set of 240 samples.

---

## 3. Problem Statement

### 3.1 The Core Problem

Modern data transmission systems face a fundamental trade-off between **security strength** and **computational efficiency**:

- Applying maximum-strength encryption (e.g., ECDH key exchange + AES) to every packet is secure but computationally expensive, increasing latency and energy consumption — critical concerns for IoT devices, mobile systems, and high-throughput streaming pipelines.
- Applying lightweight encryption to all data reduces overhead but leaves sensitive payloads (PHI, PCI, PII) under-protected when threat conditions escalate.
- Static security policies cannot adapt to changing network conditions (e.g., DDoS indicators, traffic spikes) in real time.

### 3.2 Why Existing Approaches Fall Short

| Approach | Limitation |
|----------|------------|
| Single-cipher static encryption | No context awareness; over-encrypts public data |
| Rule-based policy engines | Brittle keyword rules; no learning from outcomes |
| Homogeneous TLS configurations | Same cipher suite for all connections regardless of payload |
| Manual security classification | Not scalable for streaming / high-volume ingestion |

### 3.3 Proposed Solution

ACF dynamically routes each data packet to one of three cipher tiers based on two real-time signals:
1. **Data Sensitivity** — classified by a trained KNN model using file metadata features
2. **Network Threat Level** — monitored live via `psutil` network throughput sampling

A Q-Learning agent makes the final cipher allocation decision and improves its policy through a reward function that penalizes under-protection of sensitive data and over-protection of public data.

---

## 4. Objectives

### 4.1 Primary Objectives

1. Design and implement a multi-tier cryptographic routing engine with three distinct cipher implementations
2. Build a machine learning pipeline to automatically classify data sensitivity from lightweight features (no deep inspection required)
3. Integrate a Q-Learning reinforcement agent for adaptive cipher selection under varying threat conditions
4. Develop a web-based dashboard for real-time pipeline execution, side-by-side baseline comparison, and live threat monitoring
5. Quantitatively evaluate the adaptive framework against a static cryptographic baseline on latency and energy metrics

### 4.2 Secondary Objectives

1. Support multiple data ingestion routes: local file upload and HuggingFace dataset streaming
2. Containerize the application with Docker for reproducible deployment
3. Provide Jupyter notebook workflows for data preprocessing, model training, and benchmark simulation
4. Generate publication-quality performance dashboards and academic result charts

---

## 5. System Architecture

### 5.1 High-Level Pipeline

```
Incoming Data Packet
        │
        ▼
┌───────────────────────┐
│  Feature Extraction   │  ← monitor.py
│  (Ext_ID, Size_KB,    │
│   Entropy, Keywords)  │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  KNN Classifier       │  ← knn_model.pkl (K=1)
│  Sensitivity State:   │
│  0 = Public           │
│  1 = Sensitive        │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐     ┌──────────────────────┐
│  Threat Monitor       │◄────│  psutil bytes/sec    │
│  Threat State:        │     │  threshold: 500 KB/s   │
│  0 = Safe             │     └──────────────────────┘
│  1 = High Risk        │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  Q-Learning Agent     │  ← classifiers.py
│  State: (sens, threat)│
│  Action: Tier 0/1/2   │
└───────────┬───────────┘
            │
     ┌──────┼──────┐
     ▼      ▼      ▼
  Tier 1  Tier 2  Tier 3
  ChaCha20 AES-CTR ECDH+AES
```

### 5.2 Module Breakdown

| Module | File | Responsibility |
|--------|------|----------------|
| Feature Monitor | `src/monitor.py` | Shannon entropy, file extension encoding, keyword matching, payload size |
| Classifiers | `src/classifiers.py` | KNN model loader, `AdaptiveQLearner` class, reward function |
| Crypto Engines | `src/crypto_engines.py` | Three real cipher implementations with latency/energy measurement |
| Trained Model | `src/knn_model.pkl` | Serialized scikit-learn KNN classifier (K=1) |
| Web Dashboard | `tests/run_live_web_dashboard.py` | Flask backend, SSE streaming, dual pipeline execution |
| Benchmark Harness | `tests/run_benchmarks.py` | Offline evaluation over full dataset |
| Stream Tester | `tests/test_production_streams.py` | HuggingFace live stream ingestion test |

### 5.3 Three-Tier Cryptographic Design

| Tier | Cipher | Use Case | Relative Cost |
|------|--------|----------|---------------|
| **Tier 1** | ChaCha20 stream cipher | Public data, safe network | Lowest (3.1× latency multiplier for energy estimate) |
| **Tier 2** | AES-128 CTR | Moderate sensitivity or elevated threat on public data | Medium (12.5× multiplier) |
| **Tier 3** | ECDH (SECP256R1) + HKDF + AES-128 CTR | Sensitive data or high-threat environment | Highest (38.2× multiplier) |

All three tiers use the Python `cryptography` library (`cryptography.hazmat.primitives`) and return a tuple of `(ciphertext, latency_ms, energy_uj)` for benchmarking.

---

## 6. Methodology

### 6.1 Phase 1 — Data Collection and Preprocessing

**Source:** Notebook `01_data_preprocessing.ipynb`

**Raw data structure:**
- `data/raw/sensitive/` — 3 CSV files containing PHI/PCI-style records (medical, financial)
- `data/raw/normal/` — 3 CSV files containing public-domain records

**Sampling strategy:**
- 200 rows extracted per file using `df.head(200)`
- 6 files × 200 rows = **1,200 total instances**
- Perfectly balanced: 600 sensitive (label=1) + 600 normal (label=0)

**Feature engineering pipeline (`extract_file_features`):**

| Feature | Computation |
|---------|-------------|
| `Ext_ID` | File extension mapped to integer (`.csv`→1, `.json`→2, `.db`→3, `.txt`→4) |
| `Size_KB` | `len(content.encode('utf-8')) / 1024` |
| `Entropy` | Shannon entropy: `-Σ p(c) · log₂(p(c))` over character distribution |
| `Keywords` | Count of compliance terms found in lowercase content |

**Compliance keywords:** `medical`, `patient`, `ssn`, `balance`, `password`, `bank`, `cc_num`, `glucose`, `routing`

**Output:** `data/processed/sensitivity_dataset.csv` — 1,200 rows × 5 columns (4 features + `Is_Sensitive` label)

### 6.2 Phase 2 — KNN Sensitivity Classification

**Source:** Notebook `02_knn_model_training.ipynb`

**Algorithm:** K-Nearest Neighbors (scikit-learn `KNeighborsClassifier`)

**Train/Test Split:**
```
train_test_split(X, y, test_size=0.2, random_state=42)
→ Training: 960 samples (80%)
→ Testing:  240 samples (20%)
```

**Hyperparameter search:** K ∈ {1, 3, 5, 7} — all achieved 100% test accuracy; K=1 selected

**Test set results (K=1):**

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|----|---------|
| Normal (0) | 1.00 | 1.00 | 1.00 | 118 |
| Sensitive (1) | 1.00 | 1.00 | 1.00 | 122 |
| **Overall Accuracy** | | | **1.00** | **240** |

**Model artifact:** `src/knn_model.pkl` (pickle-serialized, deployed in production dashboard)

### 6.3 Phase 3 — Q-Learning Adaptive Cipher Selection

**Source:** Notebook `03_q_learning_simulator.ipynb`, `src/classifiers.py`

**State space:** `(sensitivity_state, threat_state)` → 2 × 2 = 4 discrete states

| State | Sensitivity | Threat |
|-------|-------------|--------|
| S₀ | Public (0) | Safe (0) |
| S₁ | Public (0) | High (1) |
| S₂ | Sensitive (1) | Safe (0) |
| S₃ | Sensitive (1) | High (1) |

**Action space:** 3 actions → Tier 0 (ChaCha20), Tier 1 (AES-CTR), Tier 2 (ECDH+AES)

**Q-Learning parameters:**

| Parameter | Symbol | Value |
|-----------|--------|-------|
| Learning rate | α | 0.2 |
| Discount factor | γ | 0.9 |
| Exploration rate | ε | 0.05 (benchmark) / 0.1 (default) |
| Q-table shape | — | `(2, 2, 3)` numpy array |

**Reward function (`calculate_reinforcement_reward`):**

| Condition | Action (Tier) | Reward |
|-----------|---------------|--------|
| Sensitive OR High Threat | Tier 3 (ECDH+AES) | +15 |
| Sensitive OR High Threat | Tier 2 (AES-CTR) | +2 |
| Sensitive OR High Threat | Tier 1 (ChaCha20) | −30 |
| Public AND Safe | Tier 1 (ChaCha20) | +10 |
| Public AND Safe | Tier 2 (AES-CTR) | +4 |
| Public AND Safe | Tier 3 (ECDH+AES) | −15 |

**Default policy initialization:** Q-table pre-seeded with high values for contextually appropriate tiers (e.g., Tier 3 favored when sensitive + high threat).

### 6.4 Phase 4 — Threat Detection

**Production implementation:** `psutil.net_io_counters()` sampled every 1 second

- Computes inbound bytes per second
- If `bytes_recv/s > 500,000` (500 KB/s) → `threat_state = 1` (HIGH)
- Otherwise → `threat_state = 0` (SAFE)
- State changes pushed to browser via Server-Sent Events (SSE) at `/stream`

**Benchmark simulation:** `threat_state = 1` when `packet_index % 4 == 0` (deterministic 25% high-threat rate for reproducible evaluation)

### 6.5 Phase 5 — Evaluation and Benchmarking

**Two evaluation scenarios:**

| Scenario | Dataset | Packets | Threat Model |
|----------|---------|---------|--------------|
| Local benchmark | `sensitivity_dataset.csv` | 1,200 | Simulated (index % 4) |
| Live stream | HuggingFace `ai4privacy/pii-masking-300k` | 200 | Simulated (index % 3) in test harness |

**Baseline (Approach A):** Every packet encrypted with Tier 3 (Hybrid ECDH + AES) — represents traditional static maximum-security approach.

**Adaptive (Approach B):** KNN classification → Q-Learning action selection → appropriate tier encryption.

**Metrics collected:**
- Total cumulative latency (milliseconds)
- Total cumulative energy (microjoules, estimated from latency × tier-specific multiplier)
- Per-tier allocation counts
- Percentage improvement over baseline

---

## 7. Implementation Details

### 7.1 Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.11 |
| Web Framework | Flask | ≥ 3.0 |
| ML | scikit-learn | ≥ 1.3 |
| Data | pandas, numpy | ≥ 2.0 / ≥ 1.24 |
| Cryptography | cryptography (hazmat) | ≥ 41.0 |
| Streaming Data | HuggingFace `datasets` | ≥ 2.14 |
| System Monitoring | psutil | ≥ 5.9 |
| Visualization | matplotlib | ≥ 3.7 |
| Containerization | Docker + docker-compose | — |
| Development | Google Colab (notebooks) | — |

### 7.2 Web Dashboard Features

**URL:** `http://127.0.0.1:5000`

**Data ingestion routes:**
- **Local file upload** — `.txt`, `.csv`, `.json` (up to 1,000 lines)
- **HuggingFace streaming** — configurable dataset name and record limit

**Pipeline routes:**
- `/run_adaptive` — adaptive Q-Learning pipeline on uploaded file
- `/run_standard` — static baseline pipeline on uploaded file
- `/run_adaptive_hf` — adaptive pipeline on HuggingFace stream
- `/run_standard_hf` — static baseline on HuggingFace stream
- `/compare_data` — side-by-side metrics comparison (energy saved, latency saved, percentages)
- `/stream` — SSE endpoint for live threat state and progress updates

**Dashboard UI:** `templates/dashboard.html` + `static/css/dashboard.css` + `static/js/dashboard.js`

### 7.3 Docker Deployment

```bash
docker compose up --build
# Dashboard available at http://localhost:5000
```

- Base image: `python:3.11-slim`
- No root privileges required (psutil-based monitoring, not packet capture)
- Portable via `docker save` / `docker load` for distribution

### 7.4 Project Directory Structure

```
adaptive_crypto_framework/
├── src/
│   ├── monitor.py              # Feature extraction
│   ├── classifiers.py          # Q-Learning agent + reward function
│   ├── crypto_engines.py       # Three cipher implementations
│   └── knn_model.pkl           # Pre-trained KNN model
├── notebooks/
│   ├── 01_data_preprocessing.ipynb
│   ├── 02_knn_model_training.ipynb
│   └── 03_q_learning_simulator.ipynb
├── tests/
│   ├── run_live_web_dashboard.py
│   ├── run_benchmarks.py
│   └── test_production_streams.py
├── data/
│   ├── raw/sensitive/          # 3 PHI/PCI CSVs
│   ├── raw/normal/             # 3 public CSVs
│   └── processed/              # sensitivity_dataset.csv
├── templates/ + static/          # Dashboard frontend
├── Dockerfile + docker-compose.yml
└── requirements.txt
```

---

## 8. Experimental Results

### 8.1 Local Dataset Benchmark (1,200 Packets)

| Metric | Static Baseline | Adaptive Framework | Improvement |
|--------|----------------|-------------------|-------------|
| Total Latency | 363.47 ms | 138.16 ms | **61.99% reduction** |
| Total Energy | 13,884.70 µJ | 4,729.37 µJ | **65.94% savings** |

**Adaptive tier routing distribution:**

| Tier | Cipher | Count | Percentage |
|------|--------|-------|------------|
| Tier 1 | ChaCha20 | 442 | 36.8% |
| Tier 2 | AES-128 CTR | 165 | 13.8% |
| Tier 3 | ECDH + AES | 593 | 49.4% |

**Interpretation:** Even though ~49% of packets still route to Tier 3 (due to sensitive content or simulated threats), the adaptive system saves significant resources by routing ~51% of packets to lighter tiers — demonstrating that context-aware selection outperforms blanket maximum encryption.

### 8.2 HuggingFace Live Stream Benchmark (200 Packets)

| Metric | Static Baseline | Adaptive Framework | Improvement |
|--------|----------------|-------------------|-------------|
| Total Latency | 114.27 ms | 35.99 ms | **68.50% reduction** |

**Adaptive tier routing distribution:**

| Tier | Cipher | Count | Percentage |
|------|--------|-------|------------|
| Tier 1 | ChaCha20 | 138 | 69.0% |
| Tier 2 | AES-128 CTR | 40 | 20.0% |
| Tier 3 | ECDH + AES | 22 | 11.0% |

**Interpretation:** On real-world PII streaming data, the majority of packets are public/low-sensitivity, allowing the framework to heavily favor Tier 1 — yielding even greater latency savings than the local benchmark.

### 8.3 KNN Classification Performance

- **100% accuracy** across all tested K values (1, 3, 5, 7)
- Selected model: K=1
- Perfect precision, recall, and F1 on both classes
- Indicates that the engineered features (extension, size, entropy, keywords) provide strong separability between sensitive and normal data in this dataset

### 8.4 Summary Results Table (for Report)

| Scenario | Algorithm | Latency (ms) | Energy (µJ) | Latency Δ | Energy Δ |
|----------|-----------|-------------|-------------|-----------|----------|
| Local (1,200 pkts) | Static Baseline | 363.47 | 13,884.70 | — | — |
| Local (1,200 pkts) | Adaptive Framework | 138.16 | 4,729.37 | −61.99% | −65.94% |
| HuggingFace (200 pkts) | Static Baseline | 114.27 | — | — | — |
| HuggingFace (200 pkts) | Adaptive Framework | 35.99 | — | −68.50% | — |

---

## 9. Key Innovations and Contributions

1. **Dual-signal decision making** — Combines content-based ML classification with environment-based threat monitoring, not just one or the other
2. **Reinforcement learning for cipher routing** — Q-Learning agent learns optimal tier selection through a domain-specific reward function rather than fixed if-else rules
3. **Real cryptographic primitives** — All three tiers use actual `cryptography` library implementations (ChaCha20, AES-CTR, ECDH+HKDF), not simulated/mock encryption
4. **Live evaluation dashboard** — Interactive web interface with SSE for real-time threat visualization and side-by-side baseline comparison
5. **Multi-source data ingestion** — Supports both local files and remote HuggingFace dataset streaming for diverse evaluation scenarios
6. **Containerized deployment** — Docker packaging enables reproducible experiments and easy demonstration

---

## 10. Limitations

1. **Energy estimation is modeled, not measured** — Energy values are computed as `latency × tier_multiplier` (3.1, 12.5, 38.2), not from actual hardware power sensors
2. **Threat detection is throughput-based** — The psutil monitor uses bytes/sec threshold, not deep packet inspection or IDS signatures; high legitimate traffic could trigger false positives
3. **KNN accuracy may reflect dataset separability** — 100% accuracy on engineered features from the same source domain may not generalize to unseen data formats
4. **Q-table is small (4 states × 3 actions)** — Sufficient for proof-of-concept but limited for complex multi-dimensional threat landscapes
5. **Entropy is approximated in live dashboard** — Production pipeline uses a fixed entropy placeholder (4.5) when KNN classifies streamed data, rather than computing Shannon entropy on every packet in real time
6. **Simulated threat in benchmarks** — Offline evaluation uses deterministic threat patterns (`index % 4`) rather than real network anomalies
7. **Single-machine evaluation** — No distributed or cloud-scale throughput testing performed

---

## 11. Future Scope

1. **Hardware energy profiling** — Integrate RAPL or external power meters for real energy measurements
2. **Deep learning classifiers** — Replace KNN with neural network or transformer-based sensitivity detection for unstructured text
3. **Expanded threat intelligence** — Integrate Snort/Suricata IDS feeds or ML-based anomaly detection for threat state
4. **Federated Q-Learning** — Distributed agents learning cipher policies across multiple nodes
5. **Post-quantum cipher tiers** — Add Kyber/Dilithium-based tiers for quantum-resistant routing
6. **TLS integration** — Embed the adaptive router into an actual TLS handshake negotiation layer
7. **Larger and more diverse datasets** — Evaluate on NIST SP 800-122 compliant datasets, ENRON corpus, and healthcare HL7/FHIR streams
8. **A/B testing in production** — Deploy as a middleware proxy and measure real-world SLA impact

---

## 12. Conclusion

The Adaptive Cryptography Framework successfully demonstrates that **context-aware, ML-driven cipher selection** can significantly reduce computational overhead without sacrificing protection of sensitive data. By combining KNN-based sensitivity classification with Q-Learning adaptive routing across three real cryptographic tiers, the system achieves:

- **61.99% latency reduction** on local cross-domain data (1,200 packets)
- **65.94% energy savings** on the same dataset
- **68.50% latency reduction** on live HuggingFace PII streams (200 packets)
- **100% sensitivity classification accuracy** on held-out test data

The project delivers a complete end-to-end pipeline — from raw data preprocessing through model training, reinforcement learning simulation, real cryptography execution, web dashboard deployment, and Docker containerization — making it a viable foundation for further research in adaptive security systems.

---

## 13. Suggested Report Section Mapping

Use this mapping when instructing NotebookLM to format the report according to your college template:

| Typical Report Section | Source Sections in This Document |
|--------------------------|----------------------------------|
| Title Page / Certificate | Section 1 |
| Abstract | Section 2 |
| Introduction | Sections 3, 4 |
| Literature Survey | Section 3.2 (limitations of existing approaches) + general crypto/ML concepts |
| System Analysis / Design | Section 5 |
| Methodology | Section 6 |
| Implementation | Section 7 |
| Testing / Results | Section 8 |
| Screenshots / Diagrams | Pipeline diagram (Section 5.1), Dashboard at localhost:5000, `data/processed/academic_results_dashboard.png` |
| Conclusion | Section 12 |
| Future Work | Section 11 |
| References | Section 14 |
| Appendices | `dataset_summary.md`, notebook outputs, source code listings |

---

## 14. References and Tools Used

1. Python Software Foundation — Python 3.11 (https://python.org)
2. scikit-learn — KNeighborsClassifier, train_test_split (https://scikit-learn.org)
3. pandas — DataFrame operations and CSV I/O (https://pandas.pydata.org)
4. cryptography — hazmat primitives for ChaCha20, AES, ECDH (https://cryptography.io)
5. Flask — Web application framework (https://flask.palletsprojects.com)
6. HuggingFace Datasets — `ai4privacy/pii-masking-300k` streaming (https://huggingface.co/datasets)
7. psutil — Cross-platform system monitoring (https://github.com/giampaolo/psutil)
8. matplotlib — Performance visualization (https://matplotlib.org)
9. Docker — Containerization platform (https://docker.com)
10. Google Colab — Notebook-based development environment (https://colab.research.google.com)

---

## 15. Glossary of Terms

| Term | Definition |
|------|------------|
| **ACF** | Adaptive Cryptography Framework — this project |
| **AES-CTR** | Advanced Encryption Standard in Counter Mode |
| **ChaCha20** | Stream cipher designed for high performance on software platforms |
| **ECDH** | Elliptic Curve Diffie-Hellman key exchange |
| **HKDF** | HMAC-based Key Derivation Function |
| **KNN** | K-Nearest Neighbors — instance-based ML classifier |
| **PHI** | Protected Health Information |
| **PII** | Personally Identifiable Information |
| **PCI** | Payment Card Industry data |
| **Q-Learning** | Model-free reinforcement learning algorithm using a Q-table |
| **SSE** | Server-Sent Events — one-way server-to-browser streaming |
| **Shannon Entropy** | Measure of randomness/uncertainty in data content |
| **Static Baseline** | Control approach applying maximum cipher (Tier 3) to all packets |

---

## 16. Prompt Suggestions for NotebookLM

When generating your report, paste one of these prompts into NotebookLM after uploading this document, your format template, and your previous semester report:

**Prompt 1 — Full report generation:**
> Using the uploaded project source document, my college report format template, and my previous semester report as style reference, generate a complete semester project report. Match the section headings, formatting style, and academic tone of my previous report. Include all experimental results, architecture diagrams described in text, and proper tables for metrics.

**Prompt 2 — Section-by-section:**
> Generate the Introduction and Problem Statement sections for my Adaptive Cryptography Framework project report, following my college's format from the uploaded template.

**Prompt 3 — Results chapter:**
> Write the Results and Discussion chapter using the benchmark data from the project source document. Include comparison tables for static baseline vs adaptive framework, tier distribution analysis, and interpretation of the 61.99% latency and 65.94% energy improvements.

**Prompt 4 — Abstract and conclusion:**
> Write a formal abstract (150–250 words) and conclusion for my project report based on the uploaded source document. Use academic language suitable for a computer science / IT engineering submission.

---

*End of NotebookLM Project Source Document*
*Companion file: `dataset_summary.md` (detailed dataset profile and metric tables)*
