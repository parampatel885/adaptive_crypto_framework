import math
import re
from collections import Counter


FEATURE_COLUMNS = [
    "Ext_ID",
    "Size_KB",
    "Entropy",
    "Keywords",
    "PII_Patterns",
    "PII_Label_Cues",
    "Labeled_PII_Fields",
    "Email_Count",
    "Keyword_Density",
    "Digit_Ratio",
    "Special_Ratio",
    "Whitespace_Ratio",
    "Column_Name_Signals",
    "Public_Signals",
]

COMPLIANCE_KEYWORDS = [
    "medical",
    "patient",
    "patient_id",
    "ssn",
    "balance",
    "password",
    "bank",
    "account",
    "account_balance",
    "card",
    "credit",
    "cvv",
    "cc_num",
    "glucose",
    "insulin",
    "bloodpressure",
    "diabetes",
    "employee",
    "salary",
    "customer",
    "transaction",
    "fraud",
    "routing",
]

# Free-text PII labels common in emails / admissions / forms
PII_LABEL_CUES = [
    "email",
    "e-mail",
    "password",
    "passport",
    "driver's license",
    "drivers license",
    "social security",
    "social number",
    "telephone",
    "phone",
    "postcode",
    "zip code",
    "id card",
    "date of birth",
    "applicant",
    "username",
    "street",
    "address",
    "admission",
    "admissions",
    "dear",
    "regards",
]

SENSITIVE_COLUMN_TERMS = [
    "employee_id",
    "employee_name",
    "salary",
    "customer_id",
    "transaction_id",
    "account_balance",
    "ip_address",
    "card_type",
    "fraud_label",
    "glucose",
    "bloodpressure",
    "insulin",
    "bmi",
    "outcome",
]

# Explicit "Label: value" style fields in free-text PII documents
LABELED_PII_FIELD_PATTERNS = [
    re.compile(r"\bemail\s*:", re.IGNORECASE),
    re.compile(r"\bpassword\s*:", re.IGNORECASE),
    re.compile(r"\bpassport\s*:", re.IGNORECASE),
    re.compile(r"\btelephone\s*:", re.IGNORECASE),
    re.compile(r"\bphone\s*:", re.IGNORECASE),
    re.compile(r"\bsocial security(?: number)?\s*:", re.IGNORECASE),
    re.compile(r"\bsocial number\s*:", re.IGNORECASE),
    re.compile(r"\bid card\s*:", re.IGNORECASE),
    re.compile(r"\bdriver'?s license\s*:", re.IGNORECASE),
    re.compile(r"\bpostcode\s*:", re.IGNORECASE),
    re.compile(r"\baddress\s*:", re.IGNORECASE),
    re.compile(r"\busername\s*:", re.IGNORECASE),
]

# Helps separate public domains (airlines, sensors, weather, geography)
PUBLIC_SIGNALS = [
    "airline",
    "airport",
    "flight",
    "delay",
    "humidity",
    "temperature",
    "weather",
    "precip",
    "pressure",
    "wind",
    "furnace",
    "dishwasher",
    "fridge",
    "microwave",
    "solar",
    "population",
    "continent",
    "visibility",
]

EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")

# Tightened patterns: avoid matching unix timestamps / float digit runs
PII_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN-like with dashes
    re.compile(r"\b\d{3}\.\d{3}\.\d{4}\b"),  # SSN-like with dots
    re.compile(r"\b(?:\d{4}[ -]){3}\d{4}\b"),  # card with separators
    EMAIL_PATTERN,
    # phone: require separators or leading + (blocks bare timestamps like 1451624400)
    re.compile(
        r"(?:\+\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s])\d{3,4}[-.\s]\d{3,4}\b"
    ),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),  # IPv4
]


def calculate_shannon_entropy(data_str):
    """Evaluates character probability distributions to measure randomness density."""
    if not data_str:
        return 0
    total_len = len(data_str)
    counts = Counter(data_str)
    entropy = 0
    for count in counts.values():
        p = count / total_len
        entropy -= p * math.log2(p)
    return round(entropy, 3)


def _ratio(matches: int, total: int) -> float:
    return round(matches / total, 4) if total else 0.0


def _count_terms(text: str, terms: list[str]) -> int:
    """Count whole-word / phrase hits to avoid substring false positives."""
    return sum(
        1
        for term in terms
        if re.search(rf"\b{re.escape(term)}\b", text)
    )


def extract_file_features(filename, content):
    """Transforms a raw textual payload into transferable numeric sensitivity features."""
    ext_map = {".csv": 1, ".json": 2, ".db": 3, ".txt": 4}
    ext = "." + filename.split(".")[-1] if "." in filename else ".txt"
    ext_id = ext_map.get(ext, 0)

    size_kb = len(content.encode("utf-8")) / 1024
    entropy = calculate_shannon_entropy(content)

    lower_content = content.lower()
    keyword_matches = _count_terms(lower_content, COMPLIANCE_KEYWORDS)
    pii_label_cues = _count_terms(lower_content, PII_LABEL_CUES)
    labeled_pii_fields = sum(
        len(pattern.findall(content)) for pattern in LABELED_PII_FIELD_PATTERNS
    )
    email_count = len(EMAIL_PATTERN.findall(content))
    pii_patterns = sum(len(pattern.findall(content)) for pattern in PII_PATTERNS)
    column_name_signals = _count_terms(lower_content, SENSITIVE_COLUMN_TERMS)
    public_signals = _count_terms(lower_content, PUBLIC_SIGNALS)

    total_chars = len(content)
    digit_ratio = _ratio(sum(ch.isdigit() for ch in content), total_chars)
    special_ratio = _ratio(
        sum(not ch.isalnum() and not ch.isspace() for ch in content), total_chars
    )
    whitespace_ratio = _ratio(sum(ch.isspace() for ch in content), total_chars)
    keyword_density = round(keyword_matches / max(size_kb, 0.001), 4)

    return [
        ext_id,
        round(size_kb, 6),
        entropy,
        keyword_matches,
        pii_patterns,
        pii_label_cues,
        labeled_pii_fields,
        email_count,
        keyword_density,
        digit_ratio,
        special_ratio,
        whitespace_ratio,
        column_name_signals,
        public_signals,
    ]
