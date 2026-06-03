#!/bin/bash
set -e

echo "=========================================================================="
echo "Master Reproducibility Automation Suite: Hardware-Aware Quantum Compilation"
echo "=========================================================================="

# Step 1: Verification of Environment Dependencies and Toolchain Sanity
echo "[1/4] Running automated structural regression suite..."
pytest tests/ -v --tb=short

# Step 2: Scale-Up Data Gathering Profile Phase
echo "[2/4] Executing numerical simulation profiles (6 to 40 qubit horizons)..."
python3 -m src.pipeline.run_benchmarks \
    --scale_min 6 \
    --scale_max 40 \
    --samples 50000 \
    --out_file results/raw_data/simulation_results.csv

# Step 3: Analytics Processing and Metric Evaluation
echo "[3/4] Parsing raw validation sets and generating SHAP explainability matrices..."
python3 -m src.analytics.process_results \
    --data_path results/raw_data/simulation_results.csv \
    --output_plots results/plots/

# Step 4: Verification Against Physical Hardware Baseline Constraints
echo "[4/4] Executing cross-platform reality-gap metrics evaluation..."
python3 -m src.hardware.verify_qpu \
    --mock_qpu_data tests/fixtures/ibm_kyoto_cal.json \
    --output_pdf results/plots/hardware_reality_gap_analysis.pdf

echo "=========================================================================="
echo "Artifact verification pipeline completed successfully. Plots generated."
echo "=========================================================================="
