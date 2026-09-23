# Data Dictionary — Adaptive Cryptography Framework (ACF)

> **Source of truth:** `Production/src/monitor.py` (`FEATURE_COLUMNS`) and  
> `Model_Experimenting/data/processed/sensitivity_dataset.csv`  
> **Last updated:** July 2026

This chapter documents all data fields used by the sensitivity classifier and related pipeline labels.

---

## 1. Sensitivity Feature Vector (14 features)

These features are extracted from each packet / file line / text payload and fed to the Logistic Regression model.

| # | Feature Name | Data Type | Description |
|---|--------------|-----------|-------------|
| 1 | `Ext_ID` | Integer | Encoded file extension of the payload source. Mapping: unknown/other = `0`, `.csv` = `1`, `.json` = `2`, `.db` = `3`, `.txt` = `4`. |
| 2 | `Size_KB` | Float | Payload size in kilobytes (`UTF-8` byte length ÷ 1024). |
| 3 | `Entropy` | Float | Shannon entropy of the payload text (higher values indicate more randomness / mixed character distribution). |
| 4 | `Keywords` | Integer | Count of compliance / sensitive keyword hits (e.g., `patient`, `ssn`, `salary`, `transaction`, `password`). |
| 5 | `PII_Patterns` | Integer | Count of regex-detected PII-like patterns (e.g., email, phone-like, SSN-like, card-like, IPv4). |
| 6 | `PII_Label_Cues` | Integer | Count of free-text PII cue phrases (e.g., `passport`, `social security`, `date of birth`, `applicant`). |
| 7 | `Labeled_PII_Fields` | Integer | Count of labeled field patterns such as `Email:`, `Passport:`, `Social Security:`. |
| 8 | `Email_Count` | Integer | Number of email-address matches found in the payload. |
| 9 | `Keyword_Density` | Float | Sensitive keyword count normalized by payload size (`Keywords / Size_KB`). |
| 10 | `Digit_Ratio` | Float | Fraction of characters that are digits (`0.0`–`1.0`). |
| 11 | `Special_Ratio` | Float | Fraction of characters that are special (non-alphanumeric, non-whitespace). |
| 12 | `Whitespace_Ratio` | Float | Fraction of whitespace characters; helps distinguish prose-like free text from compact tabular rows. |
| 13 | `Column_Name_Signals` | Integer | Count of sensitive schema/column-name cues (e.g., `employee_id`, `salary`, `customer_id`, `cvv`). |
| 14 | `Public_Signals` | Integer | Count of public-domain cues (e.g., airline / weather / sensor-style terms) that support a non-sensitive label. |

**Feature vector shape:** 14 numeric values per sample  
**Used by:** Logistic Regression sensitivity classifier (`Production/src/sensitivity_model.pkl`)

---

## 2. Dataset Label and Metadata Fields

These columns appear in the processed training/evaluation CSV but are **not** model input features (except as supervision / provenance).

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| `Is_Sensitive` | Integer (binary) | Ground-truth class label. `0` = Normal / Public, `1` = Sensitive. Assigned from source folder (`raw/normal` vs `raw/sensitive`). |
| `Source_File` | String (text) | Relative path of the original raw CSV file from which the row was sampled (used for leave-one-file-out validation). |

---

## 3. Runtime Decision Variables (pipeline state)

These are not training CSV columns; they are produced during live / benchmark routing.

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| `sensitivity_state` | Integer (binary) | Classifier output. `0` = Public, `1` = Sensitive. |
| `threat_state` | Integer (binary) | Network threat flag. Live dashboard: `1` if inbound throughput > 500 KB/s, else `0`. Offline ablation/benchmarks: synthetic pattern (e.g., every 4th packet). |
| `action` / cipher tier | Integer | Q-Learning action. `0` = Tier 1 (ChaCha20), `1` = Tier 2 (AES-CTR), `2` = Tier 3 (ECDH+AES). |
| `latency_ms` | Float | Measured encryption latency for the chosen cipher (milliseconds). |
| `energy_uj` | Float | **Modeled** energy estimate (`latency_ms × tier multiplier`), in microjoules — not hardware-measured. |

---

## 4. Class Label Encoding

| Code | Class Name | Meaning |
|------|------------|---------|
| `0` | Normal / Public | Non-sensitive content (transport, weather, demographics, IoT sensor-style public data). |
| `1` | Sensitive | PHI / PCI / PII-like content (medical, employee, banking, free-text PII). |

---

## 5. Notes for the Report

1. All 14 features are numeric; the classifier does not take raw text as direct input.  
2. Feature extraction is centralized in `Production/src/monitor.py` so training, LOFO, and production stay aligned.  
3. `Is_Sensitive` is folder-based labeling (file-level supervision), which is why leave-one-file-out validation is used.  
4. Ratios (`Digit_Ratio`, `Special_Ratio`, `Whitespace_Ratio`) are continuous floats in `[0, 1]`.  
5. Count features (`Keywords`, `PII_Patterns`, etc.) are non-negative integers.

---

## 6. Compact table (for narrow report layouts)

| Feature | Type | Short description |
|---------|------|-------------------|
| Ext_ID | int | File-extension code |
| Size_KB | float | Payload size (KB) |
| Entropy | float | Shannon entropy |
| Keywords | int | Sensitive keyword count |
| PII_Patterns | int | Regex PII hit count |
| PII_Label_Cues | int | Free-text PII cue count |
| Labeled_PII_Fields | int | `Label:` style PII field count |
| Email_Count | int | Email address count |
| Keyword_Density | float | Keywords per KB |
| Digit_Ratio | float | Digit character ratio |
| Special_Ratio | float | Special character ratio |
| Whitespace_Ratio | float | Whitespace ratio |
| Column_Name_Signals | int | Sensitive column-name cues |
| Public_Signals | int | Public-domain cues |
| Is_Sensitive | int | Class label (0/1) |
| Source_File | string | Origin raw file path |
