"""
run_live_web_dashboard.py  —  Flask backend only.

psutil background thread monitors live network throughput and writes
to `live_threat_state` (no root/admin privileges required).
SSE endpoint (/stream) pushes threat changes and pipeline
progress to the browser over a single persistent connection.

Data sources supported:
  - Local file upload  (routes: /run_adaptive, /run_standard)
  - HuggingFace stream (routes: /run_adaptive_hf, /run_standard_hf)
"""

import os
import sys
import json
import pickle
import queue
import threading
import time

import pandas as pd

# Make project root importable from tests/
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(_ROOT)

from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from src.classifiers import AdaptiveQLearner, calculate_reinforcement_reward
from src.crypto_engines import (
    execute_lightweight_trivium,
    execute_standard_aes,
    execute_hybrid_ecc_aes,
)

# ── Flask app (templates + static at project root) ──────────────────
app = Flask(
    __name__,
    template_folder=os.path.join(_ROOT, "templates"),
    static_folder=os.path.join(_ROOT, "static"),
)

# ── Global state ──────────────────────────────────────────────────────
live_threat_state: int = 0
sse_queue: queue.Queue = queue.Queue()
session_results: dict = {"adaptive": None, "standard": None}
rl_agent = AdaptiveQLearner()

# ── Load KNN model ────────────────────────────────────────────────────
_MODEL_PATH = os.path.join(_ROOT, "src", "knn_model.pkl")
try:
    with open(_MODEL_PATH, "rb") as _f:
        knn_model = pickle.load(_f)
    print("✅ KNN model loaded.")
except FileNotFoundError:
    knn_model = None
    print("⚠️  knn_model.pkl not found — using keyword fallback.")

# ── psutil network-throughput threat monitor ──────────────────────────
# Threshold: if inbound traffic exceeds 500 KB/s → anomaly (threat = 1).
# Adjust _THREAT_THRESHOLD_BYTES to suit your network environment.
_THREAT_THRESHOLD_BYTES: int = 500_000   # 500 KB/s

def _psutil_monitor() -> None:
    """
    Samples net_io_counters every second and computes inbound bytes/s.
    Requires no elevated privileges and works inside Docker out of the box.

    threat_state = 1  when  bytes_recv/s  >  _THREAT_THRESHOLD_BYTES
    threat_state = 0  otherwise
    """
    global live_threat_state
    try:
        import psutil  # type: ignore

        prev = psutil.net_io_counters()
        print("📡 psutil network monitor active "
              f"(threshold: {_THREAT_THRESHOLD_BYTES // 1000} KB/s)…")

        while True:
            time.sleep(1)
            curr = psutil.net_io_counters()
            bytes_per_sec = curr.bytes_recv - prev.bytes_recv
            prev = curr

            new_state = 1 if bytes_per_sec > _THREAT_THRESHOLD_BYTES else 0
            if new_state != live_threat_state:
                live_threat_state = new_state
                sse_queue.put({"type": "threat", "state": live_threat_state})

    except Exception as exc:
        print(f"⚠️  psutil unavailable: {exc}. Threat state will stay 0.")


threading.Thread(target=_psutil_monitor, daemon=True).start()

# ── Constants / helpers ───────────────────────────────────────────────
_MAX_LINES = 1000

_SENSITIVE_KW = [
    "ssn", "patient_id", "cvv", "password", "amount",
    "medical", "bank", "routing", "balance", "glucose",
]

_HF_TEXT_KEYS = ["text", "unmasked_text", "content", "utterance", "inputs", "prompt"]


def _classify(ext_id: int, size_kb: float, keywords: int) -> int:
    if knn_model:
        df = pd.DataFrame(
            [[ext_id, size_kb, 4.5, keywords]],
            columns=["Ext_ID", "Size_KB", "Entropy", "Keywords"],
        )
        return int(knn_model.predict(df)[0])
    return 1 if keywords else 0


def _ext_id(filename: str) -> int:
    ext = os.path.splitext(filename)[1].lower()
    return 2 if ext == ".json" else (1 if ext == ".csv" else 0)


def _push(event: dict) -> None:
    sse_queue.put(event)


def _parse_file_lines(file_storage) -> tuple:
    """Returns (filename, list_of_lines) from a Flask file upload."""
    filename = file_storage.filename
    content = file_storage.read().decode("utf-8", errors="ignore")
    lines = [ln for ln in content.split("\n") if ln.strip()][:_MAX_LINES]
    return filename, lines


def _fetch_hf_lines(dataset_name: str, limit: int) -> list[str]:
    """Streams `limit` records from a HuggingFace dataset and returns text lines."""
    from datasets import load_dataset  # type: ignore  (optional dep)

    hf_stream = load_dataset(dataset_name, split="train", streaming=True)
    lines = []
    for record in hf_stream.take(limit):
        text = next((record[k] for k in _HF_TEXT_KEYS if k in record), str(record))
        lines.append(str(text))
    return lines


# ── Shared pipeline cores (reused by file + HF routes) ───────────────

def _adaptive_pipeline(lines: list[str], source_name: str) -> dict:
    eid = _ext_id(source_name)
    n = len(lines)

    tier_counts = {
        "Tier 1 (ChaCha20)": 0,
        "Tier 2 (AES-CTR)": 0,
        "Tier 3 (ECDH+AES)": 0,
    }
    total_energy = total_latency = 0.0
    packet_log = []

    for i, line in enumerate(lines):
        size_kb = len(line.encode()) / 1024.0
        kw = 1 if any(k in line.lower() for k in _SENSITIVE_KW) else 0
        sens = _classify(eid, size_kb, kw)
        threat = live_threat_state

        action = rl_agent.select_action(sens, threat, epsilon=0.05)

        if action == 0:
            _, lat, eng = execute_lightweight_trivium(line)
            tier = "Tier 1 (ChaCha20)"
        elif action == 1:
            _, lat, eng = execute_standard_aes(line)
            tier = "Tier 2 (AES-CTR)"
        else:
            _, lat, eng = execute_hybrid_ecc_aes(line)
            tier = "Tier 3 (ECDH+AES)"

        reward = calculate_reinforcement_reward(sens, threat, action)
        rl_agent.update_q_values(sens, threat, action, reward, sens, threat)

        tier_counts[tier] += 1
        total_energy += eng
        total_latency += lat

        packet_log.append({
            "id": i + 1,
            "size_kb": round(size_kb, 4),
            "sensitive": "YES" if sens else "NO",
            "cipher": tier,
            "threat": "HIGH" if threat else "SAFE",
            "latency_ms": round(lat, 4),
            "energy_uj": round(eng, 4),
        })

        _push({"type": "progress", "mode": "adaptive", "current": i + 1, "total": n})

    result = {
        "total_packets": n,
        "tier_counts": tier_counts,
        "total_energy_uj": round(total_energy, 3),
        "total_latency_ms": round(total_latency, 3),
        "avg_energy_uj": round(total_energy / n, 3) if n else 0,
        "avg_latency_ms": round(total_latency / n, 3) if n else 0,
        "packet_log": packet_log,
    }
    session_results["adaptive"] = result
    _push({"type": "done", "mode": "adaptive", "total": n})
    return result


def _standard_pipeline(lines: list[str]) -> dict:
    n = len(lines)
    total_energy = total_latency = 0.0
    packet_log = []

    for i, line in enumerate(lines):
        size_kb = len(line.encode()) / 1024.0
        _, lat, eng = execute_hybrid_ecc_aes(line)
        total_energy += eng
        total_latency += lat
        packet_log.append({
            "id": i + 1,
            "size_kb": round(size_kb, 4),
            "cipher": "Tier 3 (ECDH+AES)",
            "latency_ms": round(lat, 4),
            "energy_uj": round(eng, 4),
        })
        _push({"type": "progress", "mode": "standard", "current": i + 1, "total": n})

    result = {
        "total_packets": n,
        "total_energy_uj": round(total_energy, 3),
        "total_latency_ms": round(total_latency, 3),
        "avg_energy_uj": round(total_energy / n, 3) if n else 0,
        "avg_latency_ms": round(total_latency / n, 3) if n else 0,
        "packet_log": packet_log,
    }
    session_results["standard"] = result
    _push({"type": "done", "mode": "standard", "total": n})
    return result


# ── Routes ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/stream")
def stream():
    """SSE endpoint — one persistent connection per browser tab."""
    def _generator():
        yield f"data: {json.dumps({'type': 'threat', 'state': live_threat_state})}\n\n"
        while True:
            try:
                event = sse_queue.get(timeout=20)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

    return Response(
        stream_with_context(_generator()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── File upload routes ────────────────────────────────────────────────

@app.route("/run_adaptive", methods=["POST"])
def run_adaptive():
    if "file" not in request.files or not request.files["file"].filename:
        return jsonify({"error": "No file provided"}), 400
    try:
        filename, lines = _parse_file_lines(request.files["file"])
        return jsonify(_adaptive_pipeline(lines, filename))
    except Exception as exc:
        _push({"type": "error", "mode": "adaptive", "message": str(exc)})
        return jsonify({"error": str(exc)}), 500


@app.route("/run_standard", methods=["POST"])
def run_standard():
    if "file" not in request.files or not request.files["file"].filename:
        return jsonify({"error": "No file provided"}), 400
    try:
        _, lines = _parse_file_lines(request.files["file"])
        return jsonify(_standard_pipeline(lines))
    except Exception as exc:
        _push({"type": "error", "mode": "standard", "message": str(exc)})
        return jsonify({"error": str(exc)}), 500


# ── HuggingFace stream routes ─────────────────────────────────────────

@app.route("/run_adaptive_hf", methods=["POST"])
def run_adaptive_hf():
    dataset_name = request.form.get("dataset_name", "ai4privacy/pii-masking-300k").strip()
    limit = min(max(int(request.form.get("limit", 100)), 1), _MAX_LINES)
    try:
        print(f"📦 Streaming {limit} records from HuggingFace: {dataset_name}")
        lines = _fetch_hf_lines(dataset_name, limit)
        return jsonify(_adaptive_pipeline(lines, f"hf_{dataset_name}.json"))
    except Exception as exc:
        _push({"type": "error", "mode": "adaptive", "message": str(exc)})
        return jsonify({"error": str(exc)}), 500


@app.route("/run_standard_hf", methods=["POST"])
def run_standard_hf():
    dataset_name = request.form.get("dataset_name", "ai4privacy/pii-masking-300k").strip()
    limit = min(max(int(request.form.get("limit", 100)), 1), _MAX_LINES)
    try:
        print(f"📦 Streaming {limit} records from HuggingFace: {dataset_name}")
        lines = _fetch_hf_lines(dataset_name, limit)
        return jsonify(_standard_pipeline(lines))
    except Exception as exc:
        _push({"type": "error", "mode": "standard", "message": str(exc)})
        return jsonify({"error": str(exc)}), 500


# ── Comparison + Reset ────────────────────────────────────────────────

@app.route("/compare_data")
def compare_data():
    a = session_results["adaptive"]
    s = session_results["standard"]
    if not a or not s:
        return jsonify({"error": "Both pipelines must be run before comparing."}), 400

    e_saved = s["total_energy_uj"] - a["total_energy_uj"]
    l_saved = s["total_latency_ms"] - a["total_latency_ms"]
    e_pct = (e_saved / s["total_energy_uj"] * 100) if s["total_energy_uj"] else 0
    l_pct = (l_saved / s["total_latency_ms"] * 100) if s["total_latency_ms"] else 0

    return jsonify({
        "adaptive": a,
        "standard": s,
        "energy_saved_uj": round(e_saved, 3),
        "latency_saved_ms": round(l_saved, 3),
        "energy_saving_pct": round(e_pct, 1),
        "latency_saving_pct": round(l_pct, 1),
    })


@app.route("/reset", methods=["POST"])
def reset():
    session_results["adaptive"] = None
    session_results["standard"] = None
    return jsonify({"status": "reset"})


# ── Entry point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Dashboard running at http://127.0.0.1:5000")
    app.run(debug=False, port=5000, threaded=True)
