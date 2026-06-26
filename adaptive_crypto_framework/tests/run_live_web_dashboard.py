import os
import sys
import threading
import time
import json
import pickle
import pandas as pd
import numpy as np
from flask import Flask, jsonify, render_template_string

# 1. Environment and Dependency Safeguard Checks
try:
    from scapy.all import sniff, IP, TCP, Raw
except ImportError:
    print("❌ ERROR: Missing real-time packet capture packet drivers!")
    print("👉 Please run your local console: pip install scapy flask pandas cryptography")
    sys.exit(1)

# Configure tracking directory anchors
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.classifiers import AdaptiveQLearner, calculate_reinforcement_reward
from src.crypto_engines import execute_lightweight_trivium, execute_standard_aes, execute_hybrid_ecc_aes
from src.monitor import extract_file_features

app = Flask(__name__)

# Global runtime state accumulators tracking live traffic parameters
live_dashboard_state = {
    "total_packets_sniffed": 0,
    "current_network_threat_state": 0,
    "battery_energy_saved_uj": 0.0,
    "latency_optimization_pct": 0.0,
    "tier_distribution": {"tier_1": 0, "tier_2": 0, "tier_3": 0},
    "recent_transactions_log": []
}

# Load serialized analytical framework assets compiled during laboratory notebooks
try:
    with open(os.path.join('src', 'knn_model.pkl'), 'rb') as f:
        knn_model = pickle.load(f)
except FileNotFoundError:
    print("⚠️ WARNING: Local knn_model.pkl binary missing. Using a fallback mock classifier layer for UI layout.")
    class MockKNN:
        def predict(self, df): return [np.random.choice([0, 1])]
    knn_model = MockKNN()

rl_agent = AdaptiveQLearner()

# -----------------------------------------------------------------
# 🔍 1. ASYNCHRONOUS PACKET CAPTURE SNIFFER DAEMON BACKGROUND THREAD
# -----------------------------------------------------------------
def live_traffic_sniffer_loop():
    print("📡 Packet Sniffer Hook Active. Sniffing live bidirectional socket frames...")
    
    # Internal rolling tracking registers measuring latency thresholds
    rolling_packet_timestamps = []

    def process_sniffed_packet(packet):
        if packet.haslayer(Raw) and packet.haslayer(IP):
            live_dashboard_state["total_packets_sniffed"] += 1
            
            # Extract raw string text block from the payload layer
            try:
                raw_payload_text = packet[Raw].load.decode('utf-8', errors='ignore')
            except Exception:
                return
            
            # Basic data sanity filter to ignore blank tracking frames
            if len(raw_payload_text.strip()) < 5:
                return

            simulated_name = f"live_socket_packet_{live_dashboard_state['total_packets_sniffed']}.json"
            
            # Step A: Compute Shannon Entropy and keywords metrics on the fly
            features = extract_file_features(simulated_name, raw_payload_text)
            features_df = pd.DataFrame([features], columns=['Ext_ID', 'Size_KB', 'Entropy', 'Keywords'])
            
            # Step B: Classify sensitivity profile context boundaries using machine learning
            sens_state = knn_model.predict(features_df)[0]
            
            # Step C: Dynamic Threat Context Evaluation (Track round-trip packet spacing intervals)
            current_time = time.time()
            rolling_packet_timestamps.append(current_time)
            if len(rolling_packet_timestamps) > 10:
                rolling_packet_timestamps.pop(0)
            
            # Real-World Anomaly calculation: if traffic density spikes under 0.1s gaps, trigger anomaly state
            if len(rolling_packet_timestamps) >= 2 and (rolling_packet_timestamps[-1] - rolling_packet_timestamps[0]) < 0.1:
                threat_state = 1  # Active Flooding / Traffic Malicious Intrusion State detected
            else:
                threat_state = 0  # Normal network operating baseline
                
            live_dashboard_state["current_network_threat_state"] = threat_state

            # --- EXPERIMENTAL COMPARATIVE EVALUATION ROUTINE ---
            # Profile Traditional Control Profile (Asymmetric Static Baseline)
            _, s_time, s_energy = execute_hybrid_ecc_aes(raw_payload_text)
            
            # Profile Upgraded Intelligence Core Decision routing
            selected_action = rl_agent.select_action(sens_state, threat_state, epsilon=0.01)
            if selected_action == 0:
                _, a_time, a_energy = execute_lightweight_trivium(raw_payload_text)
                live_dashboard_state["tier_distribution"]["tier_1"] += 1
                tier_lbl = "Tier 1 (ChaCha20)"
            elif selected_action == 1:
                _, a_time, a_energy = execute_standard_aes(raw_payload_text)
                live_dashboard_state["tier_distribution"]["tier_2"] += 1
                tier_lbl = "Tier 2 (AES-CTR)"
            else:
                _, a_time, a_energy = execute_hybrid_ecc_aes(raw_payload_text)
                live_dashboard_state["tier_distribution"]["tier_3"] += 1
                tier_lbl = "Tier 3 (ECC Hybrid)"

            # Self-correcting Q-value reinforcement tracking register calculation
            reward = calculate_reinforcement_reward(sens_state, threat_state, selected_action)
            rl_agent.update_q_values(sens_state, threat_state, selected_action, reward, sens_state, threat_state)

            # Update master dashboard accumulation registers
            live_dashboard_state["battery_energy_saved_uj"] += (s_energy - a_energy)
            
            # Push clean data map to log buffer view arrays
            log_entry = {
                "id": live_dashboard_state["total_packets_sniffed"],
                "size": f"{features[1]:.2f} KB",
                "entropy": f"{features[2]:.3f}",
                "context": "🚨 CRITICAL PRIVATE" if sens_state == 1 else "🟢 PUBLIC LOG",
                "threat": "⚠️ ANOMALY ALERT" if threat_state == 1 else "✅ SECURE",
                "cipher": tier_lbl,
                "latency_saved": f"{(s_time - a_time):.2f} ms"
            }
            live_dashboard_state["recent_transactions_log"].insert(0, log_entry)
            if len(live_dashboard_state["recent_transactions_log"]) > 10:
                live_dashboard_state["recent_transactions_log"].pop()

    # Launch native link-layer loop sniffer using standard filter flags capturing TCP payloads
    sniff(filter="tcp", prn=process_sniffed_packet, store=0)

# -----------------------------------------------------------------
# 💻 2. FLASK INTERACTIVE REAL-TIME USER INTERFACE DASHBOARD RENDERS
# -----------------------------------------------------------------
HTML_UI_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ACF Framework Live Control Hub</title>
    <meta http-equiv="refresh" content="1"> <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1e272e; color: #f5f6fa; margin: 30px; }
        .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }
        .card { background: #2f3640; border-radius: 8px; padding: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); border-left: 5px solid #3498db; }
        .card.alert { border-left-color: #e74c3c; background: #3c2f2f; }
        .card h3 { margin: 0 0 10px 0; font-size: 14px; color: #a4b0be; text-transform: uppercase; }
        .card h1 { margin: 0; font-size: 28px; }
        table { width: 100%; border-collapse: collapse; background: #2f3640; border-radius: 8px; overflow: hidden; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #414b57; }
        th { background: #718093; color: white; text-transform: uppercase; font-size: 12px; }
        tr:hover { background: #353b48; }
        .badge { padding: 5px 10px; border-radius: 4px; font-weight: bold; font-size: 11px; }
        .badge.safe { background: #2ecc71; color: white; }
        .badge.danger { background: #e74c3c; color: white; }
    </style>
</head>
<body>
    <h2 style="margin-bottom:5px;">🤖 Context-Aware Adaptive Cryptography Framework (ACF)</h2>
    <p style="color:#a4b0be; margin-top:0; margin-bottom:30px;">Production Real-Time Network Packet Ingestion & Cipher Allocation Gateway Dashboard</p>
    
    <div class="grid">
        <div class="card">
            <h3>Total Packets Evaluated</h3>
            <h1>{{ state.total_packets_sniffed }}</h1>
        </div>
        <div class="card {% if state.current_network_threat_state == 1 %}alert{% endif %}">
            <h3>Network Perimeter Vector</h3>
            <h1>{% if state.current_network_threat_state == 1 %}⚠️ HIGH ATTACK RISK{% else %}🟢 VERIFIED CLEAN{% endif %}</h1>
        </div>
        <div class="card" style="border-left-color: #2ecc71;">
            <h3>Net Hardware Battery Power Saved</h3>
            <h1>{{ "%.2f"|format(state.battery_energy_saved_uj) }} &mu;J</h1>
        </div>
        <div class="card" style="border-left-color: #9b59b6;">
            <h3>Cipher Allocation Split</h3>
            <p style="margin:5px 0; font-size:13px;">🟩 Tier 1 (ChaCha20): <b>{{ state.tier_distribution.tier_1 }}</b></p>
            <p style="margin:5px 0; font-size:13px;">🟨 Tier 2 (AES-CTR): <b>{{ state.tier_distribution.tier_2 }}</b></p>
            <p style="margin:5px 0; font-size:13px;">🟥 Tier 3 (ECC Hybrid): <b>{{ state.tier_distribution.tier_3 }}</b></p>
        </div>
    </div>

    <h3>📜 Live Pipeline Execution Stream Log Registry (Recent 10 Frames)</h3>
    <table>
        <thead>
            <tr>
                <th>Packet ID</th>
                <th>Payload Size</th>
                <th>Shannon Entropy</th>
                <th>KNN Data Context</th>
                <th>Threat Scope</th>
                <th>Deployed Router Action</th>
                <th>Latency Optim. Delay</th>
            </tr>
        </thead>
        <tbody>
            {% for item in state.recent_transactions_log %}
            <tr>
                <td>#{{ item.id }}</td>
                <td>{{ item.size }}</td>
                <td>{{ item.entropy }}</td>
                <td><span class="badge {% if 'CRITICAL' in item.context %}danger{% else %}safe{% endif %}">{{ item.context }}</span></td>
                <td><span class="badge {% if 'ALERT' in item.threat %}danger{% else %}safe{% endif %}">{{ item.threat }}</span></td>
                <td><b>{{ item.cipher }}</b></td>
                <td style="color:#2ecc71; font-weight:bold;">+ {{ item.latency_saved }}</td>
            </tr>
            {% endfor %}
            {% if not state.recent_transactions_log %}
            <tr>
                <td colspan="7" style="text-align:center; color:#a4b0be;">📡 Waiting for active network TCP socket payload streams to pass... (Browse the web to fire network packets)</td>
            </tr>
            {% endif %}
        </tbody>
    </table>
</body>
</html>
"""

@app.route('/')
def index_portal_view():
    return render_template_string(HTML_UI_TEMPLATE, state=live_dashboard_state)

if __name__ == "__main__":
    # Initialize packet sniffer processing as a detached network background service daemon thread
    sniffer_daemon = threading.Thread(target=live_traffic_sniffer_loop, daemon=True)
    sniffer_daemon.start()
    
    # Launch local application dashboard server gateway
    print("🌐 Launching application interactive portal dashboard at local socket loop...")
    print("👉 View the dashboard by navigating to browser URL: http://127.0.0.1:5000")
    app.run(port=5000, debug=False, use_reloader=False)