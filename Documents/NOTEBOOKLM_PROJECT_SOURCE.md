# Adaptive Cryptography Framework (ACF)
## Complete Project Source Document for Academic Report Generation

> **Purpose of this document:** Upload this file to NotebookLM along with your college report format template and previous semester report. NotebookLM should treat this file as the authoritative technical source for the project’s current state.
>
> **Last updated:** July 2026  
> **Companion files:** `dataset_summary.md`, `COLLABORATOR_AI_CONTEXT.md`, `results/classifier_lofo_summary.csv`

---

## 1. Project Identity

| Field | Detail |
|-------|--------|
| **Project Title** | Adaptive Cryptography Framework (ACF) — A Context-Aware Multi-Tier Encryption Routing Engine |
| **Domain** | Cybersecurity · Machine Learning · Applied Cryptography · Reinforcement Learning |
| **Project Type** | Semester / major project with experimental evaluation and research-oriented validation |
| **Author** | Param Patel |
| **Repository** | `adaptive_crypto_framework` (GitHub: parampatel885/adaptive_crypto_framework) |
| **Production sensitivity model** | Logistic Regression (`StandardScaler` + `LogisticRegression`) |
| **Model artifact** | `Production/src/sensitivity_model.pkl` (compat copy also at `Production/src/knn_model.pkl`) |

---

## 2. Abstract (Draft for Report)

Traditional cryptographic systems apply a single heavyweight encryption scheme to all data regardless of content sensitivity or environmental threat level. This one-size-fits-all approach wastes computational resources on low-risk public data and cannot adapt when threat conditions change. The **Adaptive Cryptography Framework (ACF)** addresses this gap through a three-stage decision pipeline: (1) real-time feature extraction from incoming packets into a **14-dimensional** numeric vector, (2) **Logistic Regression** classification of data sensitivity, and (3) **Q-Learning** selection of the optimal cipher tier using both sensitivity and live network threat state.

The system implements three cryptographic tiers — ChaCha20 (Tier 1), AES-128 CTR (Tier 2), and hybrid ECDH + AES (Tier 3) — using the Python `cryptography` library. A Flask dashboard with Server-Sent Events (SSE) compares the adaptive framework against a static baseline that always applies the heaviest cipher.

On a multi-source dataset of **1,800 samples across 9 files**, leave-one-file-out (LOFO) evaluation shows Logistic Regression achieves **91.11% accuracy** and **90.75% macro-F1**, outperforming KNN and Random Forest. Earlier adaptive crypto benchmarks (on the prior local pipeline) reported approximately **61.99% latency reduction** and **65.94% energy savings** versus always using Tier 3, and about **68.50% latency reduction** on a HuggingFace PII stream of 200 packets. These crypto-system metrics should be re-verified after the classifier upgrade when presenting final numbers.

---

## 3. Problem Statement

### 3.1 The Core Problem

Modern data systems face a trade-off between **security strength** and **computational efficiency**:

- Always using maximum-strength encryption (ECDH + AES) is secure but expensive in latency and energy.
- Always using lightweight encryption reduces cost but under-protects PHI / PCI / PII when risk is high.
- Static policies cannot adapt to changing content and network conditions in real time.

### 3.2 Why Existing Approaches Fall Short

| Approach | Limitation |
|----------|------------|
| Single-cipher static encryption | No context awareness; over-encrypts public data |
| Rule-based keyword engines | Brittle; weak on free-text PII and unseen schemas |
| Homogeneous TLS cipher suites | Same strength for all payloads |
| Manual classification | Not scalable for streaming ingestion |
| Random train/test ML splits on same source files | Inflated accuracy due to file/domain leakage |

### 3.3 Proposed Solution

ACF routes each packet to one of three cipher tiers using two live signals:

1. **Data sensitivity** — Logistic Regression on engineered features from `Production/src/monitor.py`
2. **Network threat** — `psutil` inbound throughput vs 500 KB/s threshold

A Q-Learning agent selects the cipher tier and updates its policy with a reward function that penalizes under-protection of sensitive/high-threat traffic and over-protection of public/safe traffic.

---

## 4. Objectives

### 4.1 Primary Objectives

1. Implement a multi-tier cryptographic routing engine with three real cipher implementations
2. Build an ML sensitivity classifier that generalizes across source files (validated with LOFO)
3. Integrate Q-Learning for adaptive cipher selection under threat variation
4. Deliver a web dashboard for adaptive vs baseline comparison and live threat monitoring
5. Quantify latency and energy gains versus a static maximum-security baseline

### 4.2 Secondary / Research Objectives

1. Move beyond random-split accuracy to **leave-one-file-out** evaluation
2. Compare multiple classifiers (KNN, Logistic Regression, Random Forest, constrained RF)
3. Expand features from 4-D metadata to 14-D content/PII/public-domain signals
4. Support HuggingFace streaming and Docker deployment
5. Document honest limitations (energy modeling, remaining weak folds, security trade-offs)

---

## 5. System Architecture

### 5.1 High-Level Pipeline

```
Incoming Data Packet / File Line / HF Record
        │
        ▼
┌──────────────────────────────┐
│ Feature Extraction (14-D)    │  ← Production/src/monitor.py
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ Logistic Regression          │  ← Production/src/sensitivity_model.pkl
│ Sensitivity: 0=Public / 1=Sensitive
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐     ┌─────────────────────┐
│ Threat Monitor               │◄────│ psutil bytes/sec    │
│ Threat: 0=SAFE / 1=HIGH      │     │ threshold 500 KB/s  │
└──────────────┬───────────────┘     └─────────────────────┘
               ▼
┌──────────────────────────────┐
│ Q-Learning Agent             │  ← Production/src/classifiers.py
│ State=(sens, threat)         │
│ Action = Tier 0 / 1 / 2      │
└──────────────┬───────────────┘
               │
        ┌──────┼──────┐
        ▼      ▼      ▼
     Tier 1  Tier 2  Tier 3
     ChaCha20 AES-CTR ECDH+AES
```

### 5.2 Important Design Clarification

| Component | What it does | What it does NOT do |
|-----------|--------------|---------------------|
| `Production/src/monitor.py` | Builds the feature vector | Does not choose cipher |
| `Production/src/sensitivity_model.pkl` | Predicts Public vs Sensitive | Does not choose cipher |
| `Production/src/classifiers.py` (`AdaptiveQLearner`) | Chooses cipher tier | Is not the sensitivity classifier |
| `Production/src/crypto_engines.py` | Encrypts and returns latency/energy | Does not classify content |

### 5.3 Module Breakdown

| Module | File | Responsibility |
|--------|------|----------------|
| Feature monitor | `Production/src/monitor.py` | 14-D feature extraction (entropy, PII cues, public signals, etc.) |
| Q-Learning | `Production/src/classifiers.py` | `AdaptiveQLearner`, reward function |
| Crypto engines | `Production/src/crypto_engines.py` | ChaCha20, AES-CTR, ECDH+AES |
| Production model | `Production/src/sensitivity_model.pkl` | Logistic Regression pipeline |
| Live dashboard | `Production/run_live_web_dashboard.py` | Flask + SSE + adaptive/baseline routes |
| Rebuild/train | `Model_Experimenting/rebuild_sensitivity_dataset.py` | Rebuild processed CSV + retrain model |
| LOFO compare | `Model_Experimenting/compare_classifiers_lofo.py` | Classifier comparison under LOFO |
| Benchmarks | `Model_Experimenting/run_benchmarks.py` | Offline latency/energy harness |

### 5.4 Three-Tier Cryptographic Design

| Tier | Cipher | Typical use | Relative energy model |
|------|--------|-------------|------------------------|
| Tier 1 | ChaCha20 | Public + safe | Lowest (×3.1) |
| Tier 2 | AES-128 CTR | Medium risk | Medium (×12.5) |
| Tier 3 | ECDH SECP256R1 + HKDF + AES-CTR | Sensitive or high threat | Highest (×38.2) |

Each engine returns `(ciphertext, latency_ms, energy_uj)` where energy is **estimated** as `latency × multiplier` (not hardware wattmeter).

---

## 6. Methodology

### 6.1 Phase 1 — Data Collection

Current raw inventory (9 source files, 200 rows each → **1,800 samples**):

**Sensitive (`Model_Experimenting/data/raw/sensitive/`):**
- `diabetes.csv` — medical tabular
- `employee_records.csv` — HR / salary
- `FraudShield_Banking_Data.csv` — banking / transactions
- `pii_masking_sample.csv` — free-text PII from HuggingFace `ai4privacy/pii-masking-300k` (first 200 English)
- `pii_masking_sample_b.csv` — second independent HF PII sample (skip 200)

**Normal (`Model_Experimenting/data/raw/normal/`):**
- `Airlines.csv` — transport
- `HomeC.csv` — smart-home sensors
- `weatherHistory.csv` — meteorology (Kaggle weather dataset)
- `world_population.csv` — geography / demographics

**Labeling:** folder-based (`sensitive`→1, `normal`→0). Convenient, but creates file/domain leakage under random splits; therefore LOFO is the primary research metric.

Processed output: `Model_Experimenting/data/processed/sensitivity_dataset.csv`

### 6.2 Phase 2 — Feature Engineering (14-D)

Originally the project used only 4 features (`Ext_ID`, `Size_KB`, `Entropy`, `Keywords`). After LOFO exposed weak generalization, features were expanded.

| # | Feature | Purpose |
|---|---------|---------|
| 1 | `Ext_ID` | File extension encoding |
| 2 | `Size_KB` | Payload size |
| 3 | `Entropy` | Shannon entropy (computed live; not hardcoded) |
| 4 | `Keywords` | Sensitive keyword hits |
| 5 | `PII_Patterns` | Regex hits (email, SSN-like, phone, IPv4, card-like) |
| 6 | `PII_Label_Cues` | Free-text cues (`email`, `passport`, `applicant`, …) |
| 7 | `Labeled_PII_Fields` | `Email:`, `Passport:`, `Social Security:` style fields |
| 8 | `Email_Count` | Count of email addresses |
| 9 | `Keyword_Density` | Keywords per KB |
| 10 | `Digit_Ratio` | Digit fraction |
| 11 | `Special_Ratio` | Special-character fraction |
| 12 | `Whitespace_Ratio` | Prose vs compact tabular signal |
| 13 | `Column_Name_Signals` | Sensitive column/field names |
| 14 | `Public_Signals` | Public-domain cues (`airline`, `humidity`, `furnace`, …) |

**Important implementation details:**
- Whole-word / word-boundary matching reduces false positives (e.g., `pressure` inside `bloodpressure`)
- Phone regex tightened so unix timestamps in `HomeC.csv` are not treated as phone numbers
- Feature extraction is centralized in `Production/src/monitor.py` so training, LOFO, and production stay aligned

### 6.3 Phase 3 — Sensitivity Classification

#### Historical baseline (initial notebooks)
- Algorithm: KNN (K=1)
- Random 80/20 split on early 1,200-row / 4-feature dataset → ~100% accuracy
- This result was **optimistic** because train/test rows came from the same source files

#### Current production model
- Algorithm: **Logistic Regression**
- Pipeline: `StandardScaler` → `LogisticRegression(max_iter=2000, random_state=42)`
- Artifact: `Production/src/sensitivity_model.pkl`
- Retrain command:
  ```bash
  python Model_Experimenting/rebuild_sensitivity_dataset.py --rows-per-file 200 --model-type logistic_regression
  ```

#### Classifier comparison under Leave-One-File-Out (authoritative)

Protocol: for each source file, train on all other files, test on the held-out file; aggregate predictions.

| Model | Accuracy | Macro F1 | Sensitive Recall | Normal Recall |
|-------|----------|----------|------------------|---------------|
| **Logistic Regression** | **0.9111** | **0.9075** | **0.9970** | **0.8037** |
| Random Forest (unconstrained) | 0.7778 | 0.7500 | 1.0000 | 0.5000 |
| Random Forest (constrained: max_depth=5, min_samples_leaf=5) | 0.7778 | 0.7500 | 1.0000 | 0.5000 |
| KNN (K=1 + scaler) | 0.7056 | 0.6879 | 0.8490 | 0.5262 |

**Why Logistic Regression was selected for production:** best LOFO macro-F1 and strong sensitive recall with better normal recall than Random Forest on the current multi-source set.

**Research narrative for the report:**
1. Random split with 4 features / KNN looked perfect
2. LOFO revealed poor cross-file generalization
3. Feature expansion + second free-text PII source fixed the hard PII fold
4. Production switched from KNN to Logistic Regression based on LOFO evidence

### 6.4 Phase 4 — Q-Learning Cipher Selection

**State space:** `(sensitivity, threat)` → 4 states  
**Actions:** Tier 0 / 1 / 2  
**Parameters:** α=0.2, γ=0.9, ε≈0.05 (benchmark) / 0.1 (default)  
**Q-table shape:** `(2, 2, 3)`

**Reward summary:**
- Sensitive or high threat → strongly reward Tier 3; heavily punish Tier 1
- Public and safe → reward Tier 1; punish unnecessary Tier 3

Q-Learning is the **cipher selector**, not the sensitivity classifier. The Q-table is currently in-memory (not persisted across restarts).

### 6.5 Phase 5 — Threat Detection

Production: `psutil.net_io_counters()` every second  
- inbound > 500 KB/s → threat = HIGH  
- else SAFE  
- changes streamed to UI via SSE `/stream`

Benchmark simulation: often `index % 4 == 0` → HIGH (reproducible)

### 6.6 Phase 6 — System Evaluation

| Scenario | Description |
|----------|-------------|
| Local offline benchmark | Process processed dataset; compare static Tier 3 vs adaptive routing |
| HuggingFace live stream | Stream records from `ai4privacy/pii-masking-300k` through dashboard/test harness |
| Classifier LOFO | Cross-file generalization of sensitivity models |

**Baseline:** always Tier 3  
**Adaptive:** classifier + threat + Q-Learning

---

## 7. Implementation Details

### 7.1 Technology Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| Web | Flask + SSE |
| ML | scikit-learn (LogReg / KNN / RF) |
| Crypto | `cryptography` hazmat |
| Data | pandas, numpy |
| Streaming | HuggingFace `datasets` |
| Monitoring | psutil |
| Charts | matplotlib |
| Deploy | Docker / docker-compose |

### 7.2 Dashboard Routes

Main app: `Production/run_live_web_dashboard.py` → `http://127.0.0.1:5000`

- `/run_adaptive`, `/run_standard`
- `/run_adaptive_hf`, `/run_standard_hf`
- `/compare_data`
- `/stream` (SSE)

### 7.3 Key Commands

```bash
pip install -r requirements.txt

# Rebuild features + retrain production LogReg
python Model_Experimenting/rebuild_sensitivity_dataset.py --rows-per-file 200

# Classifier LOFO comparison
python Model_Experimenting/compare_classifiers_lofo.py --rows-per-file 200

# Offline crypto benchmark
python Model_Experimenting/run_benchmarks.py

# Live dashboard
python Production/run_live_web_dashboard.py

# Docker
docker compose up --build
```

### 7.4 Project Structure (current)

```
adaptive_crypto_framework/
├── Documents/
│   ├── dataset_summary.md
│   ├── NOTEBOOKLM_PROJECT_SOURCE.md
│   ├── COLLABORATOR_AI_CONTEXT.md
│   └── images/
├── Model_Experimenting/
│   ├── notebooks/                 # Historical Colab narrative
│   ├── data/raw/{sensitive,normal}/
│   ├── data/processed/
│   ├── results/                   # LOFO CSVs
│   ├── rebuild_sensitivity_dataset.py
│   ├── compare_classifiers_lofo.py
│   ├── leave_one_file_out_validation.py
│   ├── run_benchmarks.py
│   └── dashboards/
├── Production/
│   ├── src/
│   │   ├── monitor.py             # 14-D feature extraction
│   │   ├── classifiers.py         # Q-Learning + rewards
│   │   ├── crypto_engines.py      # Tier 1/2/3 ciphers
│   │   ├── sensitivity_model.pkl  # Production LogReg
│   │   └── knn_model.pkl          # Compat copy
│   ├── templates/ + static/
│   ├── run_live_web_dashboard.py
│   └── test_production_streams.py
├── repo_paths.py
└── README.md
```

---

## 8. Experimental Results

### 8.1 Classifier LOFO Results (primary research evidence)

Source: `results/classifier_lofo_summary.csv` (1,800 samples, 9 files)

| Model | Acc | Macro F1 | Sens Recall | Norm Recall |
|-------|-----|----------|-------------|-------------|
| Logistic Regression | **0.911** | **0.908** | **0.997** | **0.804** |
| Random Forest | 0.778 | 0.750 | 1.000 | 0.500 |
| Constrained RF | 0.778 | 0.750 | 1.000 | 0.500 |
| KNN | 0.706 | 0.688 | 0.849 | 0.526 |

**Interpretation for report:**
- Sensitive recall is security-critical; LogReg keeps it near-perfect while retaining usable normal recall
- Random Forest’s perfect early scores on fewer files were over-optimistic; on broader data it over-predicts sensitive on some normal domains
- Constrained RF (`max_depth=5`, `min_samples_leaf=5`) was used as a genuineness check; it did not beat LogReg overall

### 8.2 Weak-fold research findings (useful Discussion section)

| Issue | Finding | Fix |
|-------|---------|-----|
| Random split 100% | Train/test leakage across same source files | Adopt LOFO as main metric |
| HomeC false PII | Phone regex matched unix timestamps | Tighten phone pattern |
| Free-text PII miss | Cues absent when only one PII file existed | Add labeled-field/email features + second PII file |
| Airlines hardness | Sparse public signals / domain shift | Public_Signals features; still a residual weak fold for some models |

### 8.3 Adaptive Crypto Benchmark Results (archived system metrics)

These numbers come from earlier end-to-end adaptive vs static runs and remain useful as system-level evidence. After the classifier upgrade, they should be re-run for final submission if the examiner expects exact current figures.

#### Local benchmark (historical, ~1,200 packets)

| Metric | Static Baseline | Adaptive | Improvement |
|--------|-----------------|----------|-------------|
| Latency | 363.47 ms | 138.16 ms | **61.99%** |
| Energy | 13,884.70 µJ | 4,729.37 µJ | **65.94%** |

Tier mix (historical): Tier1 442 · Tier2 165 · Tier3 593

#### HuggingFace stream (historical, 200 packets)

| Metric | Static Baseline | Adaptive | Improvement |
|--------|-----------------|----------|-------------|
| Latency | 114.27 ms | 35.99 ms | **68.50%** |

Tier mix (historical): Tier1 138 · Tier2 40 · Tier3 22

### 8.4 Combined summary table for report

| Evidence type | Result |
|---------------|--------|
| LOFO sensitivity classification (LogReg) | **91.11% accuracy**, **90.75% macro-F1** |
| Adaptive latency vs static (local, historical) | **~61.99% reduction** |
| Adaptive energy vs static (local, historical) | **~65.94% savings** |
| Adaptive latency vs static (HF stream, historical) | **~68.50% reduction** |

---

## 9. Key Innovations and Contributions

1. **Dual-signal adaptive routing** — content sensitivity + live threat
2. **Research-honest classifier evaluation** — LOFO instead of only random split
3. **Expanded transferable feature design** — 14-D vector for tabular + free-text PII + public domains
4. **Evidence-based production model choice** — Logistic Regression selected via LOFO, not notebook convenience
5. **Real cryptography** — ChaCha20 / AES-CTR / ECDH+AES via `cryptography`
6. **Interactive evaluation dashboard** — adaptive vs baseline with SSE threat updates
7. **Reproducible scripts** — rebuild, LOFO compare, fetch helpers (not notebook-only)

---

## 10. Limitations (must include for academic credibility)

1. Energy is **modeled** from latency multipliers, not measured with RAPL/power meter
2. Threat detection is a simple throughput threshold, not IDS-grade anomaly detection
3. Folder-level labels can still encourage domain cues; row-level mixed labels would be stronger
4. Some normal domains (notably Airlines) remain difficult under LOFO for certain models
5. Q-table is small and not persisted across process restarts
6. Benchmark threat patterns are simulated (`index % 4`) in offline harnesses
7. Crypto engines use fixed demo keys/nonces for measurement fairness; not a secure key-management deployment
8. Historical crypto latency/energy tables predate the final LogReg production switch and should be re-verified for final figures

---

## 11. Future Scope

1. Re-run full adaptive crypto benchmarks with current LogReg model and publish refreshed tables
2. Ablation study: static Tier3 vs rule-based vs classifier-only vs full adaptive
3. Improve remaining weak normal folds (Airlines) and add more diverse public/sensitive sources
4. Hardware energy measurement
5. Persist Q-learning policy and plot learning curves
6. Security analysis: tier-choice leakage, under-protection under ε-greedy, action masking for sensitive data
7. Deeper NLP / NER for free-text PII
8. Optional TLS middleware integration and post-quantum tiers

---

## 12. Conclusion

The Adaptive Cryptography Framework demonstrates that **context-aware encryption routing** can reduce computational cost relative to always-max cryptography while prioritizing protection of sensitive data. The project’s research contribution is not only the adaptive pipeline, but also the move from inflated random-split KNN accuracy to a **cross-file LOFO evaluation** that selected **Logistic Regression** as the production sensitivity model (**~91% LOFO accuracy**). Combined with Q-Learning cipher selection and a live dashboard, ACF provides a complete prototype for adaptive security systems and a credible base for further academic work.

---

## 13. Suggested Report Section Mapping

| Typical college report section | Use from this document |
|--------------------------------|------------------------|
| Title / Certificate | Section 1 |
| Abstract | Section 2 |
| Introduction / Problem | Sections 3–4 |
| Literature / Related work | Section 3.2 + crypto/ML background |
| System design | Section 5 |
| Methodology | Section 6 |
| Implementation | Section 7 |
| Results & Discussion | Section 8 (emphasize LOFO + weak-fold story) |
| Limitations | Section 10 |
| Conclusion | Section 12 |
| Future work | Section 11 |
| References | Section 14 |
| Appendices | `results/*.csv`, feature list, screenshots |

---

## 14. References and Tools

1. Python — https://python.org  
2. scikit-learn — LogisticRegression, KNeighborsClassifier, RandomForestClassifier, StandardScaler  
3. pandas / numpy  
4. cryptography (hazmat) — ChaCha20, AES, ECDH, HKDF  
5. Flask — web dashboard / SSE  
6. HuggingFace Datasets — `ai4privacy/pii-masking-300k`  
7. Kaggle weather dataset — `muthuj7/weather-dataset` (`weatherHistory.csv`)  
8. psutil — network throughput monitoring  
9. matplotlib — result dashboards  
10. Docker — reproducible deployment  

---

## 15. Glossary

| Term | Definition |
|------|------------|
| ACF | Adaptive Cryptography Framework |
| LOFO | Leave-One-File-Out validation |
| Logistic Regression | Current production sensitivity classifier |
| KNN | Earlier sensitivity classifier (baseline comparison) |
| Q-Learning | Cipher-tier selector using a Q-table |
| Static baseline | Always encrypt with Tier 3 (ECDH+AES) |
| Weak fold | Source file where LOFO accuracy collapses |
| PII / PHI / PCI | Personal / health / payment sensitive data |
| SSE | Server-Sent Events |
| Word-boundary match | Whole-word regex matching (`\bterm\b`) |

---

## 16. Prompt Suggestions for NotebookLM

**Prompt 1 — Full report:**
> Using this project source document, my college format template, and my previous semester report as style reference, generate a complete project report. Emphasize the current system: 14-D features, Logistic Regression sensitivity classification, Q-Learning cipher selection, LOFO classifier comparison, and adaptive vs static crypto results. Do not claim KNN is the production model. Treat LOFO metrics as primary classifier evidence and clearly note that early random-split 100% accuracy was optimistic due to file leakage.

**Prompt 2 — Results & Discussion:**
> Write the Results and Discussion chapter. Include: (1) LOFO table comparing KNN, Logistic Regression, and Random Forest; (2) why Logistic Regression was chosen; (3) weak-fold analysis (HomeC timestamp false PII, free-text PII, Airlines); (4) adaptive vs static latency/energy tables; (5) honest limitations.

**Prompt 3 — Methodology:**
> Write the Methodology chapter covering data sources (9 files), feature engineering from 4-D to 14-D, LOFO protocol, Logistic Regression training, Q-Learning design, threat monitoring, and evaluation setup.

**Prompt 4 — Abstract + Conclusion:**
> Write a formal abstract (150–250 words) and conclusion based on the current document. Mention dual-signal adaptive crypto, LOFO-validated Logistic Regression (~91% accuracy), and reported latency/energy reductions versus static Tier-3 encryption.

**Prompt 5 — Correct outdated claims:**
> If any older notes say the production model is KNN with 4 features and 100% accuracy, correct them using this document. Production model is Logistic Regression with 14 features; primary classifier metric is leave-one-file-out performance.

---

*End of NotebookLM Project Source Document*  
*Also useful: `COLLABORATOR_AI_CONTEXT.md` (engineering handoff), `results/classifier_lofo_summary.csv` (raw LOFO metrics)*
