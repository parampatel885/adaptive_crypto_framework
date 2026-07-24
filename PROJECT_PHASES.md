# Adaptive Cryptography Framework — Project Phases

> **Purpose:** Quick reference for how this project evolved and how work is organized.  
> **Last updated:** July 2026  
> **Related docs:** `Documents/NOTEBOOKLM_PROJECT_SOURCE.md`, `Documents/COLLABORATOR_AI_CONTEXT.md`, `README.md`

---

## How to read this file

This note covers **three different “phase” views** discussed in project chats:

1. **Pipeline phases** — the technical methodology (data → features → classifier → RL → threat → evaluation)
2. **Research evolution** — what we built, discovered, and fixed over time
3. **Future roadmap** — recommended next steps for the report and system

Use pipeline phases when writing the **Methodology** chapter. Use research evolution when explaining **why** decisions were made (especially the KNN → Logistic Regression switch).

---

## A. Pipeline phases (methodology)

These are the end-to-end system phases as implemented today.

| Phase | Name | What happens | Key files / outputs |
|-------|------|--------------|---------------------|
| **1** | Data collection | Gather sensitive + normal CSV sources; label by folder (`sensitive`→1, `normal`→0); sample 200 rows/file → ~1,800 rows | `Model_Experimenting/data/raw/sensitive/`, `Model_Experimenting/data/raw/normal/`, `Model_Experimenting/data/processed/sensitivity_dataset.csv` |
| **2** | Feature engineering | Convert each row into a **14-D** numeric vector (entropy, PII cues, public signals, etc.) | `Production/src/monitor.py` (`FEATURE_COLUMNS`) |
| **3** | Sensitivity classification | Predict **Public (0)** vs **Sensitive (1)** | `Production/src/sensitivity_model.pkl` — **Logistic Regression** (`StandardScaler` + `LogisticRegression`) |
| **4** | Q-Learning cipher selection | Agent picks Tier 1 / 2 / 3 from state `(sensitivity, threat)` | `Production/src/classifiers.py` (`AdaptiveQLearner`) |
| **5** | Threat detection | Live network throughput via `psutil`; >500 KB/s → HIGH threat; SSE to UI | `Production/run_live_web_dashboard.py` |
| **6** | System evaluation | Compare adaptive routing vs always-on Tier 3 (latency, energy, tier mix) | `Model_Experimenting/run_benchmarks.py`, live dashboard compare view |

### Current pipeline (one line)

```
Packet/line → monitor.py (14 features) → Logistic Regression → threat (psutil) → Q-Learning → Tier 1/2/3 crypto
```

### Important design split

| Component | Role |
|-----------|------|
| `sensitivity_model.pkl` | **Classifies** sensitivity (Logistic Regression) |
| `classifiers.py` | **Selects cipher tier** (Q-Learning — not the sensitivity classifier) |
| `crypto_engines.py` | **Encrypts** and returns latency/energy estimates |

---

## B. Research evolution (chronological journey)

This is the honest story of how the project matured — useful for Results / Discussion.

### Phase B1 — Initial prototype (notebooks + early dashboard)

- Jupyter notebooks: preprocessing, KNN training, Q-Learning simulation
- **4 features:** `Ext_ID`, `Size_KB`, `Entropy`, `Keywords`
- **KNN (K=1)** on ~1,200 rows
- Random 80/20 split reported ~**100% accuracy**
- Flask dashboard with adaptive vs static comparison
- Docker deployment for the live demo

**Problem discovered:** Random split accuracy was misleading — rows from the same source file leaked into both train and test.

---

### Phase B2 — Evaluation honesty (LOFO introduced)

- Added **leave-one-file-out (LOFO)** validation: train on all files except one, test on the held-out file
- First LOFO result with 4 features + KNN: ~**50% accuracy** (reality check)
- Conclusion: model was learning **file identity**, not **sensitive content**

**Scripts:** `Model_Experimenting/leave_one_file_out_validation.py`, `Model_Experimenting/compare_classifiers_lofo.py`

---

### Phase B3 — Feature expansion (steps 1–3 implemented)

Expanded `monitor.py` from 4 → **9**, then **14** features:

- PII regex patterns, keyword density, digit/special ratios
- Column-name signals, public-domain cues
- Free-text PII: `PII_Label_Cues`, `Labeled_PII_Fields`, `Email_Count`, `Whitespace_Ratio`
- Fixes: live Shannon entropy (no hardcoded 4.5), word-boundary matching, tighter phone regex (HomeC timestamp false positives)

**Result:** LOFO improved significantly (roughly 50% → ~83%, then varied as dataset grew).

**Script:** `Model_Experimenting/rebuild_sensitivity_dataset.py`

---

### Phase B4 — Dataset diversification

- Added more sensitive sources (banking, employee records, HuggingFace PII samples)
- Added normal sources (Airlines, HomeC, weather, world population)
- Added **second independent PII file** (`pii_masking_sample_b.csv`) so LOFO on one PII file still has free-text PII in training
- Final inventory: **9 files × 200 rows = 1,800 samples**

**Known remaining weak fold:** `Airlines.csv` under LOFO for some models.

---

### Phase B5 — Classifier comparison & production switch

Compared under LOFO (`Model_Experimenting/results/classifier_lofo_summary.csv`):

| Model | Accuracy | Macro F1 |
|-------|----------|----------|
| **Logistic Regression** | **~0.91** | **~0.91** |
| Random Forest | ~0.78 | ~0.75 |
| KNN | ~0.71 | ~0.69 |

**Decision:** Switch production from KNN → **Logistic Regression** based on LOFO macro-F1 and better normal recall than RF.

**Artifacts:** `Production/src/sensitivity_model.pkl` (+ legacy compat copy `Production/src/knn_model.pkl`)

---

### Phase B6 — Documentation & collaboration

- Created report source docs for NotebookLM
- Created collaborator handoff doc (`Documents/COLLABORATOR_AI_CONTEXT.md`)
- Documented architecture, LOFO protocol, and “do not undo casually” decisions

---

### Phase B7 — Repository restructure (this chat)

Reorganized repo into three top-level categories:

| Folder | Purpose |
|--------|---------|
| `Documents/` | Reports, NotebookLM source, collaborator context, figures |
| `Model_Experimenting/` | Notebooks, data, results, LOFO, retrain, benchmarks |
| `Production/` | Live dashboard, `src/`, templates, static |

Shared paths: `repo_paths.py` at repo root.

---

### Phase B8 — Production UI alignment

- Updated dashboard UI strings from **KNN** → **Logistic Regression** where users see classifier labels
- Production runtime already used LogReg; labels were stale

---

## C. Recommended future roadmap

From project planning chats — not all done yet. Ordered by value for the semester report.

### Phase 0 — Reproducibility foundation *(partially done)*

| Task | Status | Notes |
|------|--------|-------|
| Fixed random seeds in training scripts | ✅ Partial | `random_state=42` in sklearn paths |
| Central config file (`config.yaml`) | ⬜ Todo | α, γ, ε, threat threshold, tier multipliers, paths |
| One command → all result CSVs | ⬜ Todo | e.g. `run_all_experiments.py` |
| Plot script from CSVs | ⬜ Partial | `Model_Experimenting/dashboards/` exists |

---

### Phase C1 — Refresh crypto benchmarks *(high priority)*

Re-run adaptive vs static benchmarks with the **current LogReg model** and update report tables.

```bash
python Model_Experimenting/run_benchmarks.py
```

**Why:** Archived numbers (~61.99% latency, ~65.94% energy on local run; ~68.50% on HF stream) predate the final classifier switch.

---

### Phase C2 — Ablation study *(implemented)*

Script: `Model_Experimenting/run_ablation_study.py`

Compares:

1. Always Tier 3 / Tier 1 / Tier 2
2. Rule-based (no RL)
3. Classifier only (threat fixed SAFE)
4. Threat only (sensitivity fixed PUBLIC)
5. Full adaptive RL
6. Full adaptive RL + safety mask (no Tier 1 on sensitive)

```bash
python Model_Experimenting/run_ablation_study.py
python Model_Experimenting/run_ablation_study.py --max-rows 500 --seeds 3
```

Outputs: `Model_Experimenting/results/ablation_summary.csv`, `ablation_per_seed.csv`

---

### Phase C3 — Classifier & data improvements

- Improve `Airlines.csv` LOFO fold
- Add more diverse public + PII sources
- Prefer row-level labels where possible
- Keep LogReg as production unless LOFO evidence supports another model **without** normal-recall collapse

---

### Phase C4 — Security chapter *(good for marks)*

- Formal threat model
- Leakage via tier choice / timing side channels
- Action masking (never Tier 1 when sensitive=1)
- Quantify under-protection during ε-greedy exploration

---

### Phase C5 — Engineering polish

- Persist Q-table across restarts ✅ (`Production/src/q_table.npy`)
- Safety mask + decaying ε in production ✅
- Pretrain showcase Q-table ✅ (`Production/src/q_table_pretrained.npy`, via `train_q_table.py`)
- Multi-seed benchmark stats (mean ± std)
- Measure decision overhead (feature + ML time vs encrypt time)
- Sync `Documents/dataset_summary.md` to current 14-feature / 1,800-row / LOFO numbers

---

## D. Current status snapshot

| Area | State |
|------|-------|
| Production sensitivity model | **Logistic Regression** in `Production/src/sensitivity_model.pkl` |
| Features | **14-D** in `Production/src/monitor.py` |
| Dataset | **9 files, ~1,800 rows** |
| Primary classifier metric | **Leave-one-file-out** (not random split) |
| Live demo | `python Production/run_live_web_dashboard.py` → http://127.0.0.1:5000 |
| Docker | `docker compose up --build` |
| Retrain | `python Model_Experimenting/rebuild_sensitivity_dataset.py --rows-per-file 200` |
| LOFO compare | `python Model_Experimenting/compare_classifiers_lofo.py --rows-per-file 200` |

---

## E. Quick command reference by phase

```bash
# Phase 1–3: Rebuild dataset + retrain production classifier
python Model_Experimenting/rebuild_sensitivity_dataset.py --rows-per-file 200 --model-type logistic_regression

# Phase 3: LOFO classifier comparison
python Model_Experimenting/compare_classifiers_lofo.py --rows-per-file 200

# Phase 6: Offline crypto benchmarks
python Model_Experimenting/run_benchmarks.py

# Production demo
python Production/run_live_web_dashboard.py
```

---

## F. Metrics to cite (and caveats)

### Classifier (LOFO — primary evidence)

- Logistic Regression: **~91.1% accuracy**, **~90.8% macro-F1**
- Source: `Model_Experimenting/results/classifier_lofo_summary.csv`

### Crypto system (re-verify after model changes)

- Local file run: ~**61.99%** latency reduction, ~**65.94%** energy savings vs static Tier 3
- HuggingFace stream (200 packets): ~**68.50%** latency reduction
- Energy is **modeled** (`latency × tier multiplier`), not hardware-measured

### Do not claim in the report

- KNN is the production sensitivity classifier (it is not)
- ~100% random-split accuracy as main evidence (file leakage)
- Random Forest is production model (LogReg was chosen for LOFO balance)

---

*This file is a living summary. Update it when major phases complete (new datasets, model changes, benchmark reruns, or repo layout changes).*
