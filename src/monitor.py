import math
from collections import Counter
import os

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

def extract_file_features(filename, content):
    """Transforms a raw textual string payload into a 4-dimensional numeric vector coordinate."""
    ext_map = {'.csv': 1, '.json': 2, '.db': 3, '.txt': 4}
    ext = '.' + filename.split('.')[-1] if '.' in filename else '.txt'
    ext_id = ext_map.get(ext, 0)
    
    size_kb = len(content.encode('utf-8')) / 1024
    entropy = calculate_shannon_entropy(content)
    
    compliance_keywords = ["medical", "patient", "ssn", "balance", "password", "bank", "cc_num", "glucose", "routing"]
    keyword_matches = sum(1 for word in compliance_keywords if word in content.lower())
    
    return [ext_id, size_kb, entropy, keyword_matches]
