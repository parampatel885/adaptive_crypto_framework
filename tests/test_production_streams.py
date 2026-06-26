import os
import csv
import threading
import pickle
import pandas as pd
from flask import Flask, request, jsonify, render_template_string
from datasets import load_dataset
from scapy.all import sniff

# Import your core custom library modules
from src.monitor import extract_file_features
from src.classifiers import AdaptiveQLearner
from src.crypto_engines import execute_standard_aes, execute_hybrid_ecc_aes, execute_lightweight_trivium

app = Flask(__name__)

# Core Framework Shared Memory Pools
packet_log_history = []
rl_agent = AdaptiveQLearner()

# Safeguard verification for model assets
MODEL_PATH = 'src/knn_model.pkl'
if os.path.exists(MODEL_PATH):
    with open(MODEL_PATH, 'rb') as f:
        knn_model = pickle.load(f)
else:
    knn_model = None
    print("⚠️ Warning: knn_model.pkl not found! Falling back to heuristic keyword flags.")

# --- Background Network Sentinel (Scapy Thread) ---
def background_network_sniffer():
    """Captures hardware socket traffic asynchronously to prevent Flask blocking."""
    print("📡 Background Thread: Scapy network packet monitoring active...")
    try:
        sniff(prn=process_live_network_packet, store=0)
    except Exception as e:
        print(f"❌ Sniffer Driver Error: {e}. Check Admin/Npcap clearance.")

def process_live_network_packet(packet):
    """Processes bidirectional hardware packets captured on the fly."""
    if packet.haslayer('Raw'):
        payload_text = str(packet['Raw'].load)
        # Mocking an environment threat state for live network validation
        simulated_threat = 1 if len(packet_log_history) % 4 == 0 else 0
        evaluate_and_encrypt_stream("Live_Network_Packet.bin", payload_text, simulated_threat)

# --- Core Pipeline Execution Core ---
def evaluate_and_encrypt_stream(filename, raw_text, threat_state):
    """Funnels text streams through the feature monitor, KNN classifier, and Q-table."""
    global knn_model, rl_agent
    
    # 1. Feature Extraction (src/monitor.py)
    ext = os.path.splitext(filename)[1] or ".txt"
    ext_id = 2 if ext == ".json" else (1 if ext == ".csv" else 0)
    size_kb = len(raw_text.encode('utf-8')) / 1024.0
    
    # Custom statistical extraction block
    keywords_matched = 1 if any(k in raw_text.lower() for k in ["ssn", "patient_id", "cvv", "password", "amount"]) else 0
    
    # 2. KNN Sensitivity Classification
    if knn_model:
        # Wrap into a small DataFrame to eliminate Scikit-Learn feature name warnings
        input_df = pd.DataFrame([[ext_id, size_kb, 4.5, keywords_matched]], 
                                columns=['Ext_ID', 'Size_KB', 'Entropy', 'Keywords'])
        sens_state = int(knn_model.predict(input_df)[0])
    else:
        sens_state = 1 if keywords_matched == 1 else 0

    # 3. Reinforcement Learning Action Selection
    action = rl_agent.select_action((sens_state, threat_state))
    
    # 4. Real Cryptographic Block Transformations
    if action == 0:
        tier_label = "Tier 1 (ChaCha20 Stream)"
        _ = execute_lightweight_trivium(raw_text)
    elif action == 1:
        tier_label = "Tier 2 (AES-128 CTR)"
        _ = execute_standard_aes(raw_text)
    else:
        tier_label = "Tier 3 (Hybrid ECDH Loop)"
        _ = execute_hybrid_ecc_aes(raw_text)
        
    # Log telemetry metrics back to the shared dashboard registry
    log_entry = {
        "source": filename,
        "size_kb": round(size_kb, 3),
        "knn_state": "SENSITIVE" if sens_state == 1 else "PUBLIC",
        "threat_state": "HIGH RISK" if threat_state == 1 else "SAFE",
        "allocated_tier": tier_label
    }
    packet_log_history.append(log_entry)
    return log_entry

# --- Flask Routing Web Controllers ---

@app.route('/')
def home_dashboard():
    """Renders a simple dark-mode workspace console view."""
    return render_template_string("""
    <html>
    <head><title>Adaptive Crypto Dashboard</title></head>
    <body style="background-color:#121212; color:#ffffff; font-family:sans-serif; padding:20px;">
        <h2>🔐 Context-Aware Adaptive Cryptography Management Hub</h2>
        <hr style="border-color:#333;">
        
        <h3>📤 Route 1: Upload Local Dataset File</h3>
        <form action="/upload_local" method="post" enctype="multipart/form-data">
            <input type="file" name="file" required>
            <button type="submit">Process File Pipeline</button>
        </form>
        
        <h3>🌐 Route 2: Stream Live Dataset via Hugging Face Hub</h3>
        <form action="/stream_huggingface" method="post">
            <input type="text" name="dataset_name" value="ai4privacy/pii-masking-300k" style="width:300px;" required>
            <input type="number" name="limit" value="10" style="width:60px;" required>
            <button type="submit">Initialize Remote Stream</button>
        </form>
        
        <h3>📊 Current Pipeline Transmission History Logs</h3>
        <table border="1" cellpadding="5" style="border-collapse:collapse; width:100%; border-color:#333; text-align:left;">
            <tr style="background-color:#1e1e1e;">
                <th>Data Source Field</th><th>Footprint Size (KB)</th><th>KNN Sorter State</th><th>Threat Perimeter Context</th><th>Assigned Cryptographic Tier</th>
            </tr>
            {% for log in logs %}
            <tr>
                <td>{{ log.source }}</td><td>{{ log.size_kb }}</td><td>{{ log.knn_state }}</td><td>{{ log.threat_state }}</td><td>{{ log.allocated_tier }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """, logs=packet_log_history[::-1][:15])

@app.route('/upload_local', methods=['POST'])
def handle_local_upload():
    """Ingests text data files dynamically from the client's local storage."""
    if 'file' not in request.files:
        return jsonify({"error": "No file stream selected"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty file boundary"}), 400
        
    try:
        content = file.read().decode('utf-8', errors='ignore')
        lines = content.split('\n')[:50]  # Processing top 50 rows to protect buffer pools
        for index, line in enumerate(lines):
            if line.strip():
                evaluate_and_encrypt_stream(f"Uploaded_{file.filename}_Row_{index}", line, threat_state=0)
        return jsonify({"status": "Success", "rows_processed": len(lines), "redirect": "/"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to parse upload matrix: {str(e)}"}), 500

@app.route('/stream_huggingface', methods=['POST'])
def handle_huggingface_stream():
    """Connects to the Hugging Face Hub API to parse live un-labeled streams on demand."""
    dataset_name = request.form.get('dataset_name', 'ai4privacy/pii-masking-300k')
    limit = int(request.form.get('limit', 10))
    
    try:
        print(f"📦 Streaming fresh records from Hugging Face: {dataset_name}")
        hf_stream = load_dataset(dataset_name, split='train', streaming=True)
        
        for i, record in enumerate(hf_stream.take(limit)):
            # Defensive field mapping to safely pull textual values
            possible_keys = ['text', 'unmasked_text', 'content', 'utterance', 'inputs', 'prompt']
            raw_payload_text = next((record[k] for k in possible_keys if k in record), str(record))
            
            # Simulate shifting network threats during the automated remote streaming test
            threat_context = 1 if i % 3 == 0 else 0
            evaluate_and_encrypt_stream(f"HF_Stream_Packet_{i}", raw_payload_text, threat_context)
            
        return jsonify({"status": "Hugging Face stream compiled successfully", "packets_scanned": limit}), 200
    except Exception as e:
        return jsonify({"error": f"Hugging Face transaction failure: {str(e)}"}), 500

if __name__ == '__main__':
    # Step 1: Spin up Scapy sniffer inside a dedicated background daemon thread
    sniffer_thread = threading.Thread(target=background_network_sniffer, daemon=True)
    sniffer_thread.start()
    
    # Step 2: Launch Flask web micro-gateway on the primary thread
    print("🚀 Main Thread: Booting Framework Web Application Hub at http://127.0.0.1:5000")
    app.run(debug=False, port=5000)  # Keep debug=False to avoid spawning the sniffer thread twice
