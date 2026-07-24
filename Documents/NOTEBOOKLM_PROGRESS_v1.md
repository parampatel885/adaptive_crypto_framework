# ACF Progress Update for NotebookLM (July 2026)

> **Purpose:** Upload this file to NotebookLM **together with** `NOTEBOOKLM_PROJECT_SOURCE.md`.  
> This document describes **recent changes, why they were made, new experiments, and how to write the report honestly**.  
> Where this file conflicts with older notes, **prefer this file**.

**Author:** Param Patel  
**Project:** Adaptive Cryptography Framework (ACF)  
**Date of this update:** July 2026  

**Companion sources:**
- `Documents/NOTEBOOKLM_PROJECT_SOURCE.md` — baseline full project narrative
- `Documents/COLLABORATOR_AI_CONTEXT.md` — engineering handoff
- `PROJECT_PHASES.md` — phase roadmap at repo root
- `Model_Experimenting/results/ablation_summary.csv` — ablation numbers
- `Model_Experimenting/results/ablation_dashboard.png` — ablation figures

---

## 0. Instructions for NotebookLM (read first)

When generating the college report:

1. Treat **Logistic Regression** as the production sensitivity classifier (not KNN).
2. Treat **Q-Learning + safety mask + decaying ε** as the production cipher selector.
3. Use **leave-one-file-out (LOFO)** as primary classifier evidence (not random-split 100%).
4. Use the **ablation study** as primary evidence for adaptive routing value.
5. Label energy as **modeled** (`latency × tier multiplier`), not hardware-measured joules.
6. Do **not** claim Q-Learning hugely beats a simple rule on latency; claim it is competitive and safer with a mask.
7. Recommend **Full RL + safety mask** as the production policy story (~50% latency save, 0% underprotect).

---

## 1. What changed recently (summary)

| Area | Before | After | Why |
|------|--------|-------|-----|
| Repo layout | Flat `src/`, `tests/`, docs scattered | `Documents/`, `Model_Experimenting/`, `Production/` | Clear separation of docs vs experiments vs live system |
| Sensitivity model | KNN historically; later LogReg | **Logistic Regression** in production | Best LOFO macro-F1 |
| UI labels | Some strings still said “KNN” | Updated to Logistic Regression | Match runtime truth |
| System evaluation | Mostly Adaptive vs Always Tier 3 | Full **ablation study** (8 policies) | Prove what each component contributes |
| Security metric | Mostly implied | Explicit **underprotect / overprotect** rates | Measure safety cost of speed |
| Q-Learning | In-memory, fixed ε, could underprotect | **Persisted Q-table**, **decaying ε**, **safety mask**, pretrained showcase table | Fix research gaps in RL |
| Report phases doc | Informal chat memory | `PROJECT_PHASES.md` at repo root | Durable project timeline |

---

## 2. Repository restructure

The project was reorganized into three top-level categories:

```text
adaptive_crypto_framework/
├── Documents/                 # Report sources, collaborator notes, figures
├── Model_Experimenting/       # Data, notebooks, LOFO, ablation, training, results
├── Production/                # Live dashboard, src/, templates, static, models
├── repo_paths.py              # Shared path constants
├── PROJECT_PHASES.md          # Phase roadmap
├── README.md
├── Dockerfile
└── docker-compose.yml
```

### Important paths (current)

| Role | Path |
|------|------|
| Feature extractor | `Production/src/monitor.py` (14-D) |
| Q-Learning agent | `Production/src/classifiers.py` |
| Crypto engines | `Production/src/crypto_engines.py` |
| Sensitivity model | `Production/src/sensitivity_model.pkl` |
| Live Q-table | `Production/src/q_table.npy` (updates at runtime) |
| Showcase Q-table | `Production/src/q_table_pretrained.npy` (fixed bootstrap) |
| Live dashboard | `Production/run_live_web_dashboard.py` |
| Ablation script | `Model_Experimenting/run_ablation_study.py` |
| Ablation plots | `Model_Experimenting/plot_ablation_results.py` |
| Q pretrain script | `Model_Experimenting/train_q_table.py` |
| Dataset | `Model_Experimenting/data/processed/sensitivity_dataset.csv` (~1800 rows) |

**Why:** Makes the report structure match the codebase (methodology vs production deployment).

---

## 3. Production pipeline (current truth)

```text
Packet / file line / HF record
        │
        ▼
Feature extraction (14-D)          ← Production/src/monitor.py
        │
        ▼
Logistic Regression                ← sensitivity_model.pkl
Sensitivity ∈ {0=Public, 1=Sensitive}
        │
        ▼
Threat monitor (psutil)            ← inbound > 500 KB/s → HIGH
Threat ∈ {0=SAFE, 1=HIGH}
        │
        ▼
Q-Learning + safety mask           ← classifiers.py + q_table*.npy
Action ∈ {Tier1, Tier2, Tier3}
        │
        ▼
ChaCha20 / AES-CTR / ECDH+AES      ← crypto_engines.py
```

### Critical clarifications for the report

| Component | Does | Does NOT |
|-----------|------|----------|
| Logistic Regression | Classifies sensitivity | Choose cipher |
| Q-Learning | Chooses cipher tier | Classify sensitivity |
| Threat (psutil) | Binary network risk signal | Count requests/sec (it is **bytes/sec / KB/s**) |
| Energy numbers | Modeled proxy | Hardware joulemeter readings |

Threat threshold in the live dashboard: **500 KB/s inbound** (`500_000` bytes/sec), **not** 500 requests/sec.

---

## 4. Ablation study (major new contribution)

### 4.1 Motivation (research gap fixed)

Earlier comparisons were mostly:

- Adaptive system vs Always Tier 3

That cannot prove whether gains come from:
- the classifier,
- the threat signal,
- or Q-Learning itself.

**Ablation** runs the **same 1800 packets** through multiple stripped-down policies.

### 4.2 Policies compared

| Policy ID | Name | Meaning |
|-----------|------|---------|
| A0 | `always_tier3` | Always max security (baseline) |
| A1 | `always_tier1` | Always cheapest (unsafe reference) |
| A2 | `always_tier2` | Always medium |
| A3 | `rule_based` | if sensitive OR high threat → Tier 3 else Tier 1 (**no RL**) |
| A4 | `classifier_only` | Uses ML sensitivity; threat forced SAFE |
| A5 | `threat_only` | Uses threat; sensitivity forced PUBLIC |
| A6 | `full_adaptive_rl` | LogReg + threat + Q-Learning (ε-greedy) |
| A7 | `full_adaptive_safe` | Same as A6 + **hard ban on Tier 1 if sensitive** |

### 4.3 Metrics

- **Latency saving %** vs Always Tier 3  
- **Energy saving %** vs Always Tier 3 (**modeled**)  
- **Underprotection rate** = sensitive packets that got Tier 1 (security failure)  
- **Overprotection rate** = public+safe packets that got Tier 3 (efficiency waste)  

Seeds: `--seeds 3` means **3 full independent passes** of the whole dataset (different random exploration / threat offsets), then mean ± std.  
One seed ≈ all ~1800 rows once — seeds do **not** split the dataset.

### 4.4 Key results (1800 packets, 3 seeds)

| Policy | Latency save (mean) | Energy save (mean, modeled) | Underprotect | Overprotect |
|--------|---------------------|-----------------------------|--------------|-------------|
| Always Tier 3 | 0% | 0% | 0% | **100%** |
| Always Tier 1 | ~92% | ~99% | **100%** | 0% |
| Threat only | ~76% | ~80% | **~75%** | 0% |
| Rule-based | ~43% | ~45% | **0%** | 0% |
| Classifier only | ~54% | ~56% | **0%** | 0% |
| Full adaptive RL | ~52% | ~55% | ~1.1% | ~1.6% |
| Full RL + safe | ~50% | ~53% | **0%** | ~1.4% |

Figures:
- `Model_Experimenting/results/ablation_dashboard.png` (4-panel bar charts)
- `Model_Experimenting/results/ablation_tradeoff.png` (efficiency–safety scatter)
- `Model_Experimenting/results/ablation_tier_mix.png`

### 4.5 Ablation conclusions (use these in Results/Discussion)

1. **Always-max crypto is wasteful** — 100% overprotection on public+safe traffic.  
2. **Threat alone is unsafe** — high savings but ~75% underprotection.  
3. **Sensitivity (classifier) is necessary for safe savings** — classifier-only / rule-based keep underprotect at 0%.  
4. **Q-Learning does not clearly beat a simple rule on raw savings** — Full RL ≈ classifier-only range; do not overclaim RL superiority.  
5. **ε-greedy has a security cost** — Full RL shows ~1% underprotect from exploration.  
6. **Best production recommendation:** Full RL + safety mask ≈ **50% latency reduction** with **0% underprotect**.

### 4.6 One-sentence thesis for the report

> Adaptive routing saves about half the latency of always-on Tier 3 **only when sensitivity classification is used**; threat-only routing is fast but unsafe; Q-Learning with a safety mask is the recommended adaptive policy because it preserves efficiency while eliminating underprotection from exploration.

---

## 5. Q-Learning improvements (production)

### 5.1 Problems identified

| Gap | Issue |
|-----|-------|
| Non-persistent Q-table | Learning reset every dashboard restart |
| Fixed ε exploration | Could choose Tier 1 on sensitive data |
| No hard safety constraint | Security depended only on reward penalties |
| Weak “future” usage in live loop | Sometimes next state = current state (closer to bandit behavior) |

### 5.2 Fixes implemented

#### A) Persistent Q-tables
- `Production/src/q_table_pretrained.npy` — trained offline for demos; **does not update** during normal dashboard use  
- `Production/src/q_table.npy` — live table; **updates** as the dashboard runs  
- Load order: live file if present, else pretrained bootstrap  

#### B) Safety mask
Hard rule:

> If sensitivity = 1, Tier 1 is **forbidden** (explore/exploit only over Tier 2/3; any Tier 1 is escalated to Tier 3).

This is why underprotect can be forced to 0% even with ε-greedy.

#### C) Decaying ε
- Start with higher exploration during training (e.g. 0.25)  
- Decay toward a minimum (e.g. 0.01)  
- Live dashboard starts at low ε (e.g. 0.05) after pretraining  

#### D) Offline pretraining
Script: `Model_Experimenting/train_q_table.py`  
Example run: **10 epochs × 1800 packets**, safety mask ON.

Observed greedy policy after training:

| State `(sens, threat)` | Preferred tier |
|------------------------|----------------|
| public + safe | Tier 1 (ChaCha20) |
| public + high | Tier 3 (ECDH+AES) |
| sensitive + safe | Tier 3 |
| sensitive + high | Tier 3 |

Training underprotect events: **0** (mask enforced).  
Note: `public + high → Tier 3` matches the hand-crafted reward (high threat strongly rewards Tier 3).

### 5.3 How reward is calculated (unchanged formula, important for report)

Reward is **hand-designed**, not measured from latency:

**If sensitive OR high threat:**
- Tier 3 → +15  
- Tier 2 → +2  
- Tier 1 → −30  

**If public AND safe:**
- Tier 1 → +10  
- Tier 2 → +4  
- Tier 3 → −15  

Q-update target:

```text
target = r + γ · maxQ_allowed(s')
Q(s,a) ← Q(s,a) + α · (target − Q(s,a))
```

With α=0.2, γ=0.9.  
Meaning: immediate reward plus discounted best **allowed** future value.

### 5.4 Honest RL claim (do not oversell)

Supported claim:
- Q-Learning provides an online adaptive cipher policy competitive with rule/classifier baselines.
- With persistence + decaying ε + safety mask, it is suitable for a live demo without underprotecting sensitive data via exploration.

Unsupported / weak claim:
- “Q-Learning is necessary and far better than rules for latency.”

Optional future baseline mentioned in design discussions: **contextual bandit** (learns from immediate reward only, no multi-step planning). Not required to claim as implemented unless separately coded.

---

## 6. Security narrative for the report

In this project, “security” in ablation means **routing safety**, mainly:

- **Underprotection** = sensitive content encrypted too weakly (Tier 1)  
- Not a penetration test of ChaCha20/AES/ECDH primitives  

Security findings:
1. Sensitivity classification is the key safety signal.  
2. Threat throughput alone is not a confidentiality control.  
3. Exploration without a mask creates residual underprotect risk.  
4. Safety mask is a practical control for production adaptive crypto.  
5. Remaining risk: if the classifier mislabels sensitive as public, any policy trusting that label can underprotect (classifier error risk).

---

## 7. Energy measurement honesty

Current energy figures remain:

```text
energy ≈ latency_ms × tier_multiplier
```

This is a **proxy model**, useful for relative comparison, not absolute battery joules.

Future optional improvement (discussed, not required as completed):
- Measure wall power on a dedicated Raspberry Pi + USB energy meter (e.g. TC66C), subtract idle baseline.

Report wording:
- Prefer “estimated / modeled energy”  
- Prefer leading with **latency** + **underprotection** as primary evidence  

---

## 8. Classifier status (unchanged but must stay accurate)

- Production model: **Logistic Regression** (`StandardScaler` + `LogisticRegression`)  
- Features: **14-D** from `monitor.py`  
- Dataset: **9 source files × 200 rows ≈ 1800 samples**  
- Primary metric: **LOFO** (LogReg ~91% accuracy / ~91% macro-F1 class of results)  
- Do not present early KNN random-split ~100% as main evidence  

---

## 9. Suggested report chapter mapping

| Report section | Use this update for |
|----------------|---------------------|
| Introduction / Abstract | Current pipeline: 14-D → LogReg → threat → Q-Learning(+mask) |
| Literature / Motivation | Static crypto inefficiency; need adaptive routing |
| Methodology | Repo split; ablation design; reward; LOFO; seeds meaning |
| Implementation | Safety mask, decaying ε, Q persistence, dashboard |
| Results | Ablation table + figures; LOFO classifier table |
| Discussion | Sensitivity necessary; RL ≈ rules on savings; mask needed for safety |
| Limitations | Modeled energy; file-level labels; synthetic threat in offline tests; tiny RL state space |
| Conclusion | Recommend Full RL + safety mask; ~50% latency save with 0% underprotect |
| Future work | Hardware energy; richer state / bandit baseline; row-level labels; action masking already started |

---

## 10. Commands NotebookLM can cite

```bash
# Live demo
python Production/run_live_web_dashboard.py

# Ablation (full)
python Model_Experimenting/run_ablation_study.py --seeds 3

# Plot ablation
python Model_Experimenting/plot_ablation_results.py

# Pretrain showcase Q-table
python Model_Experimenting/train_q_table.py --epochs 10 --seed 42

# Retrain sensitivity model
python Model_Experimenting/rebuild_sensitivity_dataset.py --rows-per-file 200 --model-type logistic_regression

# LOFO classifier compare
python Model_Experimenting/compare_classifiers_lofo.py --rows-per-file 200
```

---

## 11. Phrases to avoid / prefer

| Avoid | Prefer |
|-------|--------|
| “Production uses KNN” | “Production uses Logistic Regression” |
| “Energy was measured on the laptop OS” | “Energy was modeled from latency × tier factors” |
| “Q-Learning dramatically outperforms rules” | “Q-Learning is competitive with rules; safety mask removes exploration underprotect” |
| “Threat = 500 requests/sec” | “Threat = inbound throughput > 500 KB/s” |
| “100% accuracy proves the classifier” | “LOFO ~91% is the primary classifier evidence” |
| “Seeds split the dataset” | “Each seed is a full pass with different randomness; we average seeds” |

---

## 12. Bottom-line status snapshot (July 2026)

The Adaptive Cryptography Framework is now:

1. **Organized** into Documents / Model Experimenting / Production  
2. **Classifier-honest** via LOFO and LogReg production model  
3. **System-evaluated** via multi-policy ablation with safety metrics  
4. **RL-hardened** with persistent Q-tables, decaying ε, and a hard safety mask  
5. **Demo-ready** with a pretrained Q-table for consistent showcases  

Primary academic story:
- **Feature + classifier research honesty (LOFO)**  
- **Ablation-driven adaptive crypto evaluation**  
- **Safety-aware reinforcement learning for cipher selection**

Primary engineering story:
- Live Flask dashboard comparing adaptive vs static encryption under a live threat signal.

---

*End of NotebookLM progress update. Prefer this document over older chat excerpts if details conflict.*
