# Adaptive Cryptography Framework — Dataset Profile & Evaluation Summary

## 1. Dataset Shape

| Property | Value |
|----------|-------|
| **Total instances** | 1,200 |
| **Feature count** | 4 |
| **Target classes** | 2 (`Is_Sensitive`) |
| **Class balance** | 600 Normal (0) · 600 Sensitive (1) — perfectly balanced |

### Feature Names

| Feature | Description |
|---------|-------------|
| `Ext_ID` | Encoded file extension (`.csv`→1, `.json`→2, `.db`→3, `.txt`→4, other→0) |
| `Size_KB` | Payload size in kilobytes (`len(content) / 1024`) |
| `Entropy` | Shannon entropy of character distribution (bits) |
| `Keywords` | Count of compliance keywords matched in payload text |

**Compliance keywords scanned:** `medical`, `patient`, `ssn`, `balance`, `password`, `bank`, `cc_num`, `glucose`, `routing`

### Target Labels

| Label | Value | Meaning |
|-------|-------|---------|
| Normal / Public | `0` | Non-sensitive data (sourced from `data/raw/normal/`) |
| Sensitive | `1` | PHI / PCI / PII data (sourced from `data/raw/sensitive/`) |

### Raw Data Provenance

- **6 source CSV files** — 3 sensitive + 3 normal domain files
- **200 rows sampled** per file (`df.head(200)`) → 6 × 200 = **1,200 total rows**
- Processed output: `data/processed/sensitivity_dataset.csv`

---

## 2. Pre-calculated Outcomes (Train / Test Splits)

### KNN Sensitivity Classifier Split

| Split | Formula | Count | Percentage |
|-------|---------|-------|------------|
| **Training set** | `train_test_split(test_size=0.2, random_state=42)` | **960** | 80% |
| **Testing set** | same split | **240** | 20% |

**Test-set class distribution:**

| Class | Support |
|-------|---------|
| Normal (0) | 118 |
| Sensitive (1) | 122 |

### KNN Hyperparameter Search Space

| K value | Test accuracy |
|---------|---------------|
| K = 1 | 100.00% |
| K = 3 | 100.00% |
| K = 5 | 100.00% |
| K = 7 | 100.00% |

**Selected model:** K = 1 (saved to `src/knn_model.pkl`)

**Classification report (test set, K = 1):**

| Class | Precision | Recall | F1-Score | Support |
|-------|-----------|--------|----------|---------|
| Normal (0) | 1.00 | 1.00 | 1.00 | 118 |
| Sensitive (1) | 1.00 | 1.00 | 1.00 | 122 |
| **Accuracy** | | | **1.00** | **240** |

### Benchmark Evaluation Streams

| Stream | Packets evaluated | Source |
|--------|-------------------|--------|
| Local cross-domain benchmark | 1,200 | Full `sensitivity_dataset.csv` |
| HuggingFace live PII stream | 200 | `ai4privacy/pii-masking-300k` (streaming) |

---

## 3. Evaluation Metrics — Baseline vs. Adaptive System

### Approach Definitions

| Approach | Description |
|----------|-------------|
| **Static Baseline** | Always applies Tier 3 — Hybrid ECDH + AES-128 CTR on every packet |
| **Adaptive Framework** | KNN sensitivity state + simulated threat state → Q-Learning agent selects Tier 1 (ChaCha20), Tier 2 (AES-128 CTR), or Tier 3 (Hybrid ECDH + AES) |

### Local Dataset Benchmark (1,200 packets)

| Metric | Static Baseline (ECDH + AES) | Adaptive Framework | Improvement |
|--------|------------------------------|--------------------|-------------|
| Total latency | 363.47 ms | 138.16 ms | **61.99% reduction** |
| Total energy | 13,884.70 µJ | 4,729.37 µJ | **65.94% savings** |

**Adaptive cipher tier routing distribution:**

| Tier | Cipher | Allocations | Share |
|------|--------|-------------|-------|
| Tier 1 | ChaCha20 stream cipher | 442 | 36.8% |
| Tier 2 | AES-128 CTR | 165 | 13.8% |
| Tier 3 | Hybrid ECDH + AES | 593 | 49.4% |

### HuggingFace Live Stream Benchmark (200 packets)

| Metric | Static Baseline (ECDH + AES) | Adaptive Framework | Improvement |
|--------|------------------------------|--------------------|-------------|
| Total latency | 114.27 ms | 35.99 ms | **68.50% reduction** |
| Total energy | — | — | Not measured |

**Adaptive cipher tier routing distribution (production stream test):**

| Tier | Cipher | Allocations | Share |
|------|--------|-------------|-------|
| Tier 1 | ChaCha20 stream cipher | 138 | 69.0% |
| Tier 2 | AES-128 CTR | 40 | 20.0% |
| Tier 3 | Hybrid ECDH + AES | 22 | 11.0% |

### Combined Summary Table

| Scenario | Algorithm | Latency (ms) | Energy (µJ) | Latency Δ | Energy Δ |
|----------|-----------|-------------|-------------|-----------|----------|
| Local (1,200 pkts) | Static Baseline | 363.47 | 13,884.70 | — | — |
| Local (1,200 pkts) | Adaptive Framework | 138.16 | 4,729.37 | −61.99% | −65.94% |
| HuggingFace (200 pkts) | Static Baseline | 114.27 | — | — | — |
| HuggingFace (200 pkts) | Adaptive Framework | 35.99 | — | −68.50% | — |

---

## 4. Q-Learning Agent Configuration

| Parameter | Value |
|-----------|-------|
| State space | `(sensitivity_state, threat_state)` — 2 × 2 = 4 states |
| Action space | 3 cipher tiers (0, 1, 2) |
| Learning rate (α) | 0.2 |
| Discount factor (γ) | 0.9 |
| Exploration (ε) | 0.05 (benchmark) / 0.1 (default) |
| Threat simulation | `threat_state = 1` when `index % 4 == 0` (local benchmark) |

---

*Generated from notebook outputs (`01_data_preprocessing`, `02_knn_model_training`, `03_q_learning_simulator`), `tests/run_benchmarks.py`, and archived dashboard metrics.*
