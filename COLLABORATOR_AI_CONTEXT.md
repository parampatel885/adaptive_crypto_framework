# Adaptive Cryptography Framework — Collaborator / AI Agent Context Brief

> **Audience:** Human collaborator + their AI coding agent  
> **Owner:** Param Patel (+ new contributor)  
> **Repo:** `adaptive_crypto_framework`  
> **Purpose of this file:** Give full project context so a new contributor (or their AI) can continue work without re-deriving decisions from chat history.

---

## 1. One-sentence summary

An intelligent encryption router that classifies each data packet as **sensitive or public**, reads **live network threat**, then uses **Q-Learning** to pick one of three real ciphers (ChaCha20 / AES-CTR / ECDH+AES) to reduce latency and energy vs always using maximum encryption.

---

## 2. Problem & purpose

### Problem
Static crypto (always ECDH+AES) over-protects public data and wastes compute/energy. Manual or brittle keyword rules do not adapt to content + threat together.

### Goal
Build a **context-aware adaptive cryptography framework** that:
1. Extracts features from incoming text/packets
2. Classifies sensitivity with ML
3. Monitors network threat (`psutil` throughput)
4. Selects cipher tier with Q-Learning
5. Compares against a static Tier-3 baseline in a live Flask dashboard
6. Supports academic reporting (LOFO validation, ablation-ready design)

### Academic framing
College / semester project with research upgrades:
- Honest evaluation via **leave-one-file-out (LOFO)** (not only random split)
- Classifier comparison (KNN vs Logistic Regression vs Random Forest)
- Feature engineering for cross-domain generalization
- Planned ablation + security discussion for the report

---

## 3. High-level architecture

```
Incoming packet / file line / HF stream record
        │
        ▼
┌──────────────────────────┐
│ Feature extraction       │  src/monitor.py  (14-D vector)
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│ Sensitivity classifier   │  src/sensitivity_model.pkl
│ (Logistic Regression)    │  0 = Public, 1 = Sensitive
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐     ┌─────────────────────┐
│ Threat state             │◄────│ psutil bytes/sec    │
│ 0=SAFE / 1=HIGH          │     │ threshold 500 KB/s  │
└────────────┬─────────────┘     └─────────────────────┘
             ▼
┌──────────────────────────┐
│ Q-Learning agent         │  src/classifiers.py
│ state=(sens, threat)     │
│ action = tier 0/1/2      │
└────────────┬─────────────┘
             │
     ┌───────┼────────┐
     ▼       ▼        ▼
  Tier 1   Tier 2   Tier 3
  ChaCha20 AES-CTR  ECDH+AES
```

### Important split of responsibilities
| Component | Role | File |
|-----------|------|------|
| Feature extractor | Text → numeric vector | `src/monitor.py` |
| Sensitivity model | Public vs Sensitive | `src/sensitivity_model.pkl` |
| Q-Learning | Cipher selector (not sensitivity classifier) | `src/classifiers.py` |
| Crypto engines | Real encryption + latency/energy | `src/crypto_engines.py` |
| Live dashboard | Production demo UI | `tests/run_live_web_dashboard.py` |

**Do not confuse:** `classifiers.py` is Q-Learning only. Sensitivity ML lives in the pickle + `monitor.py` features.

---

## 4. Current production stack (as of latest work)

| Item | Current value |
|------|----------------|
| Production sensitivity model | **Logistic Regression** (`StandardScaler` + `LogisticRegression`) |
| Model artifact | `src/sensitivity_model.pkl` (+ compat copy `src/knn_model.pkl`) |
| Feature dimension | **14 features** (was originally 4) |
| Dataset size | ~1800 rows (200 rows × 9 source files) |
| Sensitive sources | 5 files |
| Normal sources | 4 files |
| Best LOFO result | Logistic Regression ≈ **91.1% acc / 90.8% macro-F1** |
| Live app entrypoint | `python tests/run_live_web_dashboard.py` → `http://127.0.0.1:5000` |
| Docker | `docker compose up --build` (uses same dashboard) |

### Cipher tiers
| Tier | Cipher | Typical use |
|------|--------|-------------|
| 0 / Tier 1 | ChaCha20 | Public + safe |
| 1 / Tier 2 | AES-128 CTR | Medium |
| 2 / Tier 3 | ECDH (SECP256R1) + HKDF + AES-CTR | Sensitive or high threat |

Energy in code is **modeled** as `latency_ms × multiplier` (not hardware wattmeter). Document this as a limitation.

---

## 5. Feature vector (critical for any ML change)

Defined in `src/monitor.py` as `FEATURE_COLUMNS`:

1. `Ext_ID`
2. `Size_KB`
3. `Entropy`
4. `Keywords`
5. `PII_Patterns`
6. `PII_Label_Cues`
7. `Labeled_PII_Fields`
8. `Email_Count`
9. `Keyword_Density`
10. `Digit_Ratio`
11. `Special_Ratio`
12. `Whitespace_Ratio`
13. `Column_Name_Signals`
14. `Public_Signals`

### Design rules already learned the hard way
- Prefer **word-boundary** matching (`\bterm\b`) to avoid substring false positives (e.g. `pressure` inside `bloodpressure`)
- Phone regex must **not** match unix timestamps (HomeC bug)
- Free-text PII needs dedicated cues (`Email:`, `Passport:`, etc.), not only tabular column names
- Random row split can show ~100% while LOFO is much lower → **always report LOFO for research claims**

---

## 6. Data layout

```
data/
  raw/
    sensitive/
      diabetes.csv
      employee_records.csv
      FraudShield_Banking_Data.csv
      pii_masking_sample.csv          # HF ai4privacy sample (rows 1–200)
      pii_masking_sample_b.csv        # second independent HF sample (skip 200)
    normal/
      Airlines.csv
      HomeC.csv
      weatherHistory.csv
      world_population.csv
  processed/
    sensitivity_dataset.csv           # engineered features + labels
    final_balanced_dataset.csv        # same rebuild output
```

### Labeling policy
- Entire file labeled by folder: `sensitive/` → 1, `normal/` → 0
- This is convenient but causes domain/file leakage under random splits
- Mitigation: **leave-one-file-out** validation

### Adding a new dataset
1. Put CSV in `data/raw/sensitive/` or `data/raw/normal/`
2. Rebuild:
   ```bash
   python tests/rebuild_sensitivity_dataset.py --rows-per-file 200
   ```
3. Compare classifiers:
   ```bash
   python tests/compare_classifiers_lofo.py --rows-per-file 200
   ```

Helpers already exist:
- `tests/fetch_pii_masking_sample.py` (HuggingFace streaming; supports `--skip`)
- `tests/fetch_weather_dataset.py`

---

## 7. Key scripts (what to run / edit)

| Script | Purpose |
|--------|---------|
| `tests/run_live_web_dashboard.py` | **Main production dashboard** (adaptive + baseline + SSE + HF) |
| `tests/run_benchmarks.py` | Offline latency/energy benchmark on processed dataset |
| `tests/test_production_streams.py` | Older/lighter harness (Scapy-oriented; secondary) |
| `tests/rebuild_sensitivity_dataset.py` | Rebuild features + train production model |
| `tests/leave_one_file_out_validation.py` | LOFO for one model style |
| `tests/compare_classifiers_lofo.py` | LOFO compare KNN / LogReg / RF / constrained RF |
| `tests/fetch_pii_masking_sample.py` | Stream small PII sample from HF |
| `tests/fetch_weather_dataset.py` | Prepare weather as normal source |
| `src/monitor.py` | Feature extraction (shared truth) |
| `src/classifiers.py` | Q-Learning + reward |
| `src/crypto_engines.py` | Real crypto primitives |

### Retrain production model
```bash
python tests/rebuild_sensitivity_dataset.py --rows-per-file 200 --model-type logistic_regression
```
Options: `logistic_regression` (default), `random_forest`, `knn`

### Dashboard load order
Looks for `src/sensitivity_model.pkl` first, then falls back to `src/knn_model.pkl`.

---

## 8. Research journey & decisions (do not undo casually)

### Evolution
1. Started with **4 features** + **KNN** → random split looked perfect (~100%)
2. LOFO exposed reality (~50% initially) → model memorized file domains
3. Expanded features → LOFO improved (~83%), then collapsed again after adding diverse PII/weather (~62% LogReg)
4. Diagnosed weak folds (PII free-text, Airlines, HomeC timestamp false PII)
5. Fixed features + added second PII file → LogReg LOFO **~91%**
6. Switched production from KNN → **Logistic Regression**

### Latest LOFO summary (`results/classifier_lofo_summary.csv`)
| Model | Accuracy | Macro F1 | Sens Recall | Norm Recall |
|-------|----------|----------|-------------|-------------|
| **logistic_regression** | **0.911** | **0.908** | **0.997** | **0.804** |
| random_forest | 0.778 | 0.750 | 1.000 | 0.500 |
| random_forest_constrained | 0.778 | 0.750 | 1.000 | 0.500 |
| knn | 0.706 | 0.688 | 0.849 | 0.526 |

### Remaining known weak spots
- `Airlines.csv` still hard for some models under LOFO
- Random Forest over-predicts sensitive on some normal domains
- Perfect random-split accuracy is **not** trustworthy as main evidence
- Energy is modeled, not hardware-measured
- Live entropy is now real; keep it that way (do not hardcode `4.5`)

### Earlier crypto benchmark numbers (pre-latest classifier switch; re-verify after model change)
- Local 1200 packets: ~**61.99%** latency reduction, ~**65.94%** energy savings vs static Tier 3
- HF stream demo: ~**68.50%** latency reduction (archived dashboard metrics)

**Action for collaborator:** after major classifier/feature changes, rerun:
```bash
python tests/run_benchmarks.py
```
and update report numbers.

---

## 9. Q-Learning notes

- State space: `(sensitivity ∈ {0,1}, threat ∈ {0,1})` → 4 states
- Actions: 3 cipher tiers
- Defaults: α=0.2, γ=0.9, ε≈0.05 in benchmarks
- Reward penalizes under-protecting sensitive/high-threat and over-protecting public/safe
- Q-table is small and **in-memory**; not currently persisted across restarts
- Future improvement: save/load Q-table + learning curves

---

## 10. Future plans / research roadmap

Prioritized for collaborator work:

### A. Evaluation honesty (high value)
1. Rerun crypto benchmarks with current LogReg model; refresh tables
2. Ablation study:
   - Always Tier 3
   - Always ChaCha20
   - Rule-based (no RL)
   - Classifier only (threat fixed)
   - Full adaptive system
3. Multi-seed stats (mean ± std)
4. Measure decision overhead (feature+ML time vs encrypt time)

### B. Classifier / data improvements
1. Further improve `Airlines.csv` LOFO fold
2. More diverse sources (news/public text + more PII schemas)
3. Prefer row-level labels where possible (mixed sensitive/normal in one file)
4. Optional: keep LogReg as production; use RF only if LOFO improves without normal-recall collapse

### C. Security chapter (good for marks)
1. Threat model write-up
2. Leakage via tier choice / timing
3. Action masking: never allow Tier 1 when sensitive=1
4. Quantify under-protection under ε-greedy exploration

### D. Engineering polish
1. Config file (`config.yaml`) for thresholds, seeds, multipliers
2. Persist Q-table
3. Clean nested duplicate path `adaptive_crypto_framework/adaptive_crypto_framework/` if still present
4. Keep notebooks as narrative; keep scripts as source of truth

### E. Report / NotebookLM
Existing docs to update when results change:
- `NOTEBOOKLM_PROJECT_SOURCE.md`
- `dataset_summary.md`
- `results/*.csv`

---

## 11. Collaboration guidelines for the new contributor

### Safe contribution zones
- Ablation / benchmark scripts
- Report docs and result tables
- Additional datasets under `data/raw/...`
- Dashboard UX polish
- Security analysis experiments
- Tests for feature extractor edge cases

### Handle with care (ask before large changes)
- `src/monitor.py` feature schema (breaks pickle + all scripts)
- Production model type / `rebuild_sensitivity_dataset.py` defaults
- Reward function / Q-table shape in `src/classifiers.py`
- Crypto engine APIs (dashboard + benchmarks depend on return tuple shape)

### Workflow expectations
1. Prefer scripts over one-off notebook cells for anything that affects results
2. After feature or model changes:
   ```bash
   python tests/rebuild_sensitivity_dataset.py --rows-per-file 200
   python tests/compare_classifiers_lofo.py --rows-per-file 200
   python tests/run_benchmarks.py
   ```
3. Commit result CSVs when metrics change intentionally
4. Do not claim 100% accuracy from random split alone
5. Keep Docker/dashboard runnable (`tests/run_live_web_dashboard.py`)

### Suggested first tasks for the new contributor
1. Read this file + `README.md` + `src/monitor.py` + `tests/run_live_web_dashboard.py`
2. Run dashboard locally and process a small CSV
3. Run LOFO comparison and confirm numbers match `results/classifier_lofo_summary.csv`
4. Pick one roadmap item (ablation script is highest leverage)

---

## 12. Prompt starter for the collaborator's AI agent

Paste this with the repo open:

```text
You are helping on the Adaptive Cryptography Framework repo.
Read COLLABORATOR_AI_CONTEXT.md first and treat it as project truth.
Do not revert production classifier to KNN unless LOFO evidence supports it.
Do not hardcode entropy to 4.5.
Prefer leave-one-file-out metrics over random-split accuracy for claims.
Shared feature extraction must stay in src/monitor.py (FEATURE_COLUMNS).
Production model is Logistic Regression in src/sensitivity_model.pkl.
Q-Learning in src/classifiers.py selects cipher tiers; it is not the sensitivity classifier.
After feature/model changes, rebuild dataset, rerun LOFO compare, and rerun benchmarks.
```

---

## 13. Quick command cheat sheet

```bash
# Install
pip install -r requirements.txt

# Rebuild data + retrain production LogReg
python tests/rebuild_sensitivity_dataset.py --rows-per-file 200

# Classifier LOFO comparison
python tests/compare_classifiers_lofo.py --rows-per-file 200

# Offline crypto benchmark
python tests/run_benchmarks.py

# Live dashboard
python tests/run_live_web_dashboard.py

# Fetch more PII (second sample example)
python tests/fetch_pii_masking_sample.py --limit 200 --skip 400 --output data/raw/sensitive/pii_masking_sample_c.csv

# Docker
docker compose up --build
```

---

## 14. Glossary

| Term | Meaning |
|------|---------|
| LOFO | Leave-one-file-out validation |
| Static baseline | Always Tier 3 ECDH+AES |
| Adaptive path | Classifier + threat + Q-Learning tiering |
| Weak fold | Source file where LOFO accuracy collapses |
| Serialized model | Pickled sklearn pipeline (`.pkl`) |
| Word-boundary match | Regex `\bterm\b` whole-word matching |

---

*Generated as a collaborator handoff brief for Param Patel’s Adaptive Cryptography Framework. Update this file whenever production model, feature schema, dataset inventory, or headline metrics change.*
