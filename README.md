# Adaptive Cryptography Framework 🔐

An intelligent, multi-tier cryptographic routing engine that dynamically selects the right encryption cipher for every data packet based on two real-time signals — **data sensitivity** (classified by a KNN model) and **live network threat level** (monitored by a psutil background thread). A Q-Learning reinforcement agent makes the final cipher decision and continuously improves its policy through rewards.

---

## Key Results

| Scenario | Latency Reduction | Energy Savings |
|----------|:-----------------:|:--------------:|
| Local file (1,200 packets) | **61.99%** | **65.94%** |
| HuggingFace live stream (200 packets) | **68.50%** | — |

---

## How the Pipeline Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA INPUT                                   │
│          (Local File Upload  OR  HuggingFace Stream)                │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  STAGE 1 — FEATURE EXTRACTION                       │
│                       src/monitor.py                                │
│                                                                     │
│  For each line / record:                                            │
│    • File extension ID  (csv=1, json=2, other=0)                    │
│    • Size in KB                                                     │
│    • Shannon Entropy  (measures text randomness)                    │
│    • Keyword match  (ssn, password, cvv, bank, medical …)           │
│                                                                     │
│  Output:  [Ext_ID, Size_KB, Entropy, Keywords]  ← 4-D vector       │
└────────────────────────────┬────────────────────────────────────────┘
                             │
               ┌─────────────┴──────────────┐
               │                            │
               ▼                            ▼
┌──────────────────────────┐   ┌────────────────────────────────────┐
│  STAGE 2A — KNN MODEL    │   │  STAGE 2B — NETWORK MONITOR        │
│  src/knn_model.pkl       │   │  psutil background thread          │
│                          │   │                                    │
│  Input:  4-D vector      │   │  Samples bytes_recv every 1 s      │
│  Output: sens_state      │   │  > 500 KB/s  →  threat_state = 1   │
│    0 = PUBLIC            │   │  ≤ 500 KB/s  →  threat_state = 0   │
│    1 = SENSITIVE         │   │                                    │
└──────────────┬───────────┘   └──────────────┬─────────────────────┘
               │                              │
               └─────────────┬────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│               STAGE 3 — Q-LEARNING AGENT                            │
│                     src/classifiers.py                              │
│                                                                     │
│  State:  (sens_state, threat_state)  →  2 × 2 = 4 possible states  │
│  Actions: 0 = Tier 1 · 1 = Tier 2 · 2 = Tier 3                     │
│                                                                     │
│  Policy (default Q-table):                                          │
│  ┌──────────────┬────────────┬─────────────────────────┐           │
│  │ Sensitivity  │  Threat    │  Action Selected        │           │
│  ├──────────────┼────────────┼─────────────────────────┤           │
│  │ PUBLIC  (0)  │ SAFE  (0)  │ Tier 1 — ChaCha20       │           │
│  │ PUBLIC  (0)  │ HIGH  (1)  │ Tier 2 — AES-CTR        │           │
│  │ SENSITIVE(1) │ SAFE  (0)  │ Tier 3 — ECDH + AES     │           │
│  │ SENSITIVE(1) │ HIGH  (1)  │ Tier 3 — ECDH + AES     │           │
│  └──────────────┴────────────┴─────────────────────────┘           │
│                                                                     │
│  After each packet, Q-values are updated via the Bellman equation:  │
│    Q(s,a) ← Q(s,a) + α [ r + γ · max Q(s',a') − Q(s,a) ]          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│               STAGE 4 — ENCRYPTION ENGINE                           │
│                    src/crypto_engines.py                            │
│                                                                     │
│  Tier 1 · ChaCha20 Stream Cipher   — lightweight, lowest energy    │
│  Tier 2 · AES-128 CTR              — balanced speed / security      │
│  Tier 3 · Hybrid ECDH + AES        — strongest, highest cost        │
│                                                                     │
│  Returns:  (ciphertext, latency_ms, energy_µJ)                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RESULT + LOGGING                                  │
│                                                                     │
│  Logged per packet:  source, size_kb, sens_state, threat_state,     │
│                      cipher_tier, latency_ms, energy_µJ             │
│                                                                     │
│  Dashboard compares Adaptive total vs. Standard (always Tier 3)     │
│  and reports:  energy saved (µJ), latency saved (ms), % reduction   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
adaptive_crypto_framework/
│
├── src/
│   ├── monitor.py              # Feature extraction (entropy, keywords, size)
│   ├── classifiers.py          # KNN loader + Q-Learning agent + reward function
│   ├── crypto_engines.py       # ChaCha20, AES-CTR, ECDH+AES implementations
│   └── knn_model.pkl           # Pre-trained KNN classifier (serialized)
│
├── templates/
│   └── dashboard.html          # Flask HTML template
│
├── static/
│   ├── css/dashboard.css       # Dashboard styles
│   └── js/dashboard.js         # SSE client + all UI logic
│
├── tests/
│   ├── run_live_web_dashboard.py   # Main Flask app (backend + Scapy + SSE)
│   ├── test_production_streams.py  # Lightweight test runner
│   └── run_benchmarks.py           # Offline benchmark suite
│
├── notebooks/
│   ├── 01_data_preprocessing.ipynb     # Raw data cleaning + feature engineering
│   ├── 02_knn_model_training.ipynb     # KNN training + knn_model.pkl export
│   └── 03_q_learning_simulator.ipynb   # Q-Learning simulation + benchmarks
│
├── data/
│   ├── raw/sensitive/          # PHI / PCI sample CSVs (not committed)
│   ├── raw/normal/             # Public domain CSVs (not committed)
│   └── processed/              # Merged feature dataset (not committed)
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Running Locally with Docker

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### 1. Clone the repository

```bash
git clone https://github.com/parampatel885/adaptive_crypto_framework.git
cd adaptive_crypto_framework
```

### 2. Build and start the container

```bash
docker compose up --build
```

Expected output:
```
✅ KNN model loaded.
📡 psutil network monitor active (threshold: 500 KB/s)…
🚀 Dashboard running at http://127.0.0.1:5000
```

### 3. Open the dashboard

Navigate to **http://localhost:5000** in your browser.

### 4. Run a test

**Option A — Local File:**
1. Click the **📁 Local File** tab
2. Upload any `.txt`, `.csv`, or `.json` file (up to 1,000 lines)
3. Click **🤖 Run Adaptive Encryption**
4. Click **🔒 Run Standard Encryption**
5. Click **📊 Compare Results**

**Option B — HuggingFace Dataset:**
1. Click the **🤗 HuggingFace Dataset** tab
2. Enter a dataset name (default: `ai4privacy/pii-masking-300k`)
3. Set how many records to stream (1–1,000)
4. Run both pipelines and compare

### 5. Stop the container

```bash
docker compose down
```

### Rebuild after code changes

```bash
docker compose up --build --force-recreate
```

---

## Running Locally without Docker

```bash
pip install -r requirements.txt
python tests/run_live_web_dashboard.py
```

Then open **http://127.0.0.1:5000**.

---

## Network Threat Detection

The dashboard runs a background thread using `psutil` that samples inbound network bytes every second. If traffic exceeds **500 KB/s**, the threat state flips to `HIGH` and the Q-Learning agent automatically escalates cipher selection to Tier 2 or Tier 3. The live threat status is pushed to the browser instantly via **Server-Sent Events (SSE)** — no polling required.

To adjust the sensitivity threshold, change this constant in `tests/run_live_web_dashboard.py`:

```python
_THREAT_THRESHOLD_BYTES: int = 500_000   # bytes per second
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `flask` | Web server and SSE streaming |
| `scikit-learn` | KNN classifier |
| `pandas` / `numpy` | Feature vector construction |
| `cryptography` | ChaCha20, AES-CTR, ECDH+AES implementations |
| `datasets` | HuggingFace dataset streaming |
| `psutil` | Live network throughput monitoring |
| `matplotlib` | Benchmark chart generation |
