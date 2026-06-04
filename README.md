# Hardware-Aware Quantum Compilation with Data-Driven Error Detection

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![Qiskit](https://img.shields.io/badge/Qiskit-%E2%89%A52.0-blueviolet)](https://qiskit.org/)

Reproducibility repository for the paper:

> **Hardware-aware Low-latency Quantum Compilation with Data-driven Lightweight Error Detection for Early Fault-Tolerant Systems**  
> Sumit Chongder, Indian Institute of Technology Jodhpur

## Overview

This repository provides the complete, self-contained implementation of a co-design pipeline that simultaneously optimises qubit mapping and lightweight quantum error-detection (QED) syndrome scheduling for noisy quantum processors. It targets the early fault-tolerance regime, where full quantum error correction is too expensive but lightweight detection codes can meaningfully raise algorithmic success probabilities.

The three principal components are:

1. **Hardware-Aware Compilation Pass** - a simulated-annealing outer loop augmented with an ILP kernel that minimises a noise-weighted mapping cost (Eq. 2 of the paper) while enforcing latency budgets.
2. **Data-Driven QED Scheduler** is an XGBoost-based multi-objective scheduler that predicts marginal success uplift minus post-selection penalty and selects a Pareto-optimal syndrome-placement configuration in under 6 ms.
3. **HPC-Accelerated Evaluation Framework** - GPU-accelerated density-matrix simulation via NVIDIA cuQuantum (cuStateVec / cuTensorNet), SLURM orchestration, bootstrap statistical testing, and a Docker REST microservice.

---

## Repository Layout

```
quantum-hw-aware-pipeline/
├── src/
│   ├── compiler/          # Hardware-aware mapping pass (SA + ILP)
│   ├── scheduler/         # XGBoost QED scheduler
│   ├── qed/               # [[n,n-2,2]] detection-code primitives
│   ├── simulation/        # cuQuantum / Aer density-matrix engine
│   ├── metrics/           # Bootstrap CI, Wilcoxon tests, plots
│   └── utils/             # I/O helpers, SLURM runner
├── notebooks/             # Jupyter experiment and plotting notebooks
├── data/
│   ├── circuits/          # Benchmark QASM circuits
│   ├── noise_models/      # Calibrated device noise profiles
│   ├── training/          # XGBoost training corpus and checkpoints
│   └── results/           # Pre-computed benchmark result tables
├── scripts/               # SLURM, Docker, and reproduction scripts
├── docker/                # Dockerfile and REST microservice
├── tests/                 # Pytest unit-test suite
├── config/                # YAML configuration files
└── docs/                  # Architecture, API reference, checklist
```

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/quantum-hw-aware-pipeline/quantum-hw-aware-pipeline.git
cd quantum-hw-aware-pipeline
```

### 2. Install dependencies

```bash
pip install -r docker/requirements.txt
```

GPU-accelerated simulation requires CUDA 12 and the cuQuantum Python package:

```bash
pip install cuquantum-python-cu12
```

### 3. Run the full pipeline on VQE-H₂

```bash
python src/main.py \
    --circuit data/circuits/vqe_h2.qasm \
    --noise_model data/noise_models/ibm_lagos.json \
    --mode joint \
    --output results/vqe_h2_joint.json
```

### 4. Reproduce all paper figures

```bash
bash scripts/reproduce_key_results.sh
```

---

## Reproducing Paper Results

All numerical results, confidence intervals, and figures reported in the paper can be reproduced from the pre-computed result tables under `data/results/` and the plotting notebook:

```bash
jupyter nbconvert --to notebook --execute notebooks/05_plotting_and_results.ipynb
```

For full end-to-end reproduction on an HPC cluster with A100 GPUs:

```bash
bash scripts/run_slurm.sh
```

See `docs/reproducible_checklist.md` for the complete reproducibility checklist.

---

## Benchmarks and Results

Summary of success probability under the Superconducting noise profile (mean ± 95% bootstrap CI, n = 100 trials, Wilcoxon p < 0.01 for all joint gains):

| Circuit    | Baseline (SABRE) | Mapper-only | QED-only | Joint Co-design |
|------------|-----------------|-------------|----------|-----------------|
| VQE-H₂    | 0.38            | 0.44        | 0.49     | **0.64**        |
| VQE-LiH   | 0.29            | 0.35        | 0.41     | **0.55**        |
| QPE-12     | 0.22            | 0.28        | 0.31     | **0.48**        |
| Grover-10  | 0.34            | 0.41        | 0.39     | **0.58**        |

---

## License

MIT — see [LICENSE](LICENSE).

## Contact

Sumit Chongder · `sumitchongder960@gmail.com`  
Inter-Disciplinary Research Platform, Quantum Information and Computation  
Indian Institute of Technology Jodhpur, Rajasthan 342037, India
