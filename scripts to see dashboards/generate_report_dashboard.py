import os
import matplotlib.pyplot as plt
import numpy as np

def generate_academic_dashboard():
    print("📊 Generating Adaptive Framework Academic Report Dashboard...")
    
    # -----------------------------------------------------------------
    # FIXED LOGGED PERFORMANCE METRICS (COMPUTED VIA NATIVE PRIMITIVES)
    # -----------------------------------------------------------------
    # Dataset 1: Kaggle Local Cross-Domain Stream (1,200 Packets)
    local_static_latency = 363.47
    local_adaptive_latency = 138.16
    local_static_energy = 13884.70
    local_adaptive_energy = 4729.37
    
    # Dataset 2: Hugging Face Live PII Stream (200 Packets)
    hf_static_latency = 114.27
    hf_adaptive_latency = 35.99
    
    # KNN Classification Model Accuracy Checkpoints
    k_values = ['K=1', 'K=3', 'K=5', 'K=7']
    accuracies = [100.0, 100.0, 100.0, 100.0]

    # Initialize a clean multi-panel publication plotting canvas
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Adaptive Cryptographic Framework (ACF) - Comprehensive Performance Dashboard', 
                 fontsize=16, fontweight='bold', y=0.96)
    
    # -----------------------------------------------------------------
    # PANEL A: K-NEAREST NEIGHBORS MODEL ACCURACY
    # -----------------------------------------------------------------
    axs[0, 0].plot(k_values, accuracies, marker='o', linestyle='-', color='#3498db', linewidth=2.5, markersize=8)
    axs[0, 0].set_title('A. KNN Hyperparameter Evaluation Curve', fontsize=12, fontweight='bold', pad=10)
    axs[0, 0].set_ylabel('Model Classification Accuracy (%)')
    axs[0, 0].set_ylim(90, 105)
    axs[0, 0].grid(axis='y', linestyle='--', alpha=0.5)
    for idx, txt in enumerate(accuracies):
        axs[0, 0].annotate(f"{txt:.2f}%", (k_values[idx], accuracies[idx]), 
                            textcoords="offset points", xytext=(0,10), ha='center', fontweight='bold', color='#2c3e50')

    # -----------------------------------------------------------------
    # PANEL B: LOCAL KAGGLE BENCHMARK LATENCY COMPARISON
    # -----------------------------------------------------------------
    categories = ['Traditional Static\n(ECDH + AES)', 'Our Adaptive\nFramework']
    latency_values = [local_static_latency, local_adaptive_latency]
    bars_b = axs[0, 1].bar(categories, latency_values, color=['#e74c3c', '#2ecc71'], width=0.4)
    axs[0, 1].set_title('B. Local Ingestion Latency (1,200 Packets)', fontsize=12, fontweight='bold', pad=10)
    axs[0, 1].set_ylabel('Cumulative Execution Time (ms)')
    axs[0, 1].grid(axis='y', linestyle='--', alpha=0.5)
    for bar in bars_b:
        yval = bar.get_height()
        axs[0, 1].text(bar.get_x() + bar.get_width()/2.0, yval + 10, f"{yval:.2f} ms", 
                       ha='center', va='bottom', fontweight='bold')
    # Label net latency drop efficiency percentage
    axs[0, 1].text(0.5, local_static_latency * 0.7, "61.99% Delay\nReduction!", 
                   ha='center', color='white', fontweight='bold', bbox=dict(facecolor='black', alpha=0.6, boxstyle='round,pad=0.5'))

    # -----------------------------------------------------------------
    # PANEL C: LOCAL KAGGLE BENCHMARK ENERGY DISSIPATION Preservation
    # -----------------------------------------------------------------
    energy_values = [local_static_energy, local_adaptive_energy]
    bars_c = axs[1, 0].bar(categories, energy_values, color=['#e74c3c', '#34495e'], width=0.4)
    axs[1, 0].set_title('C. Local System Power Dissipation (uJ)', fontsize=12, fontweight='bold', pad=10)
    axs[1, 0].set_ylabel('Total Energy Expended (microjoules)')
    axs[1, 0].grid(axis='y', linestyle='--', alpha=0.5)
    for bar in bars_c:
        yval = bar.get_height()
        axs[1, 0].text(bar.get_x() + bar.get_width()/2.0, yval + 350, f"{yval:.1f} uJ", 
                       ha='center', va='bottom', fontweight='bold')
    axs[1, 0].text(0.5, local_static_energy * 0.7, "65.94% Total\nBattery Saved!", 
                   ha='center', color='white', fontweight='bold', bbox=dict(facecolor='#27ae60', alpha=0.9, boxstyle='round,pad=0.5'))

    # -----------------------------------------------------------------
    # PANEL D: HUGGING FACE LIVE STREAM PERFORMANCE RESULTS
    # -----------------------------------------------------------------
    hf_labels = ['Static Traditional\nBaseline', 'Adaptive Streaming\nSwitcher']
    hf_values = [hf_static_latency, hf_adaptive_latency]
    bars_d = axs[1, 1].bar(hf_labels, hf_values, color=['#c0392b', '#9b59b6'], width=0.4)
    axs[1, 1].set_title('D. Hugging Face Live PII Stream Latency (200 Packets)', fontsize=12, fontweight='bold', pad=10)
    axs[1, 1].set_ylabel('Inference Routing Delay (ms)')
    axs[1, 1].grid(axis='y', linestyle='--', alpha=0.5)
    for bar in bars_d:
        yval = bar.get_height()
        axs[1, 1].text(bar.get_x() + bar.get_width()/2.0, yval + 3, f"{yval:.2f} ms", 
                       ha='center', va='bottom', fontweight='bold')
    axs[1, 1].text(0.5, hf_static_latency * 0.6, "68.50% Net\nOptimization!", 
                   ha='center', color='white', fontweight='bold', bbox=dict(facecolor='black', alpha=0.6, boxstyle='round,pad=0.5'))

    # Finalize padding adjustments and save a high-res master copy to Google Drive storage
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    output_img_path = 'data/processed/academic_results_dashboard.png'
    plt.savefig(output_img_path, dpi=300)
    plt.show()
    print(f"✔ Analytical Master Graph compiled and saved to disk path: {output_img_path}")

if __name__ == "__main__":
    generate_academic_dashboard()
