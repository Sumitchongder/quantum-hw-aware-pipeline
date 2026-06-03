# System Architecture

## Overview

This repository implements a co-design pipeline that unifies hardware-aware quantum compilation with data-driven lightweight error detection. The design targets the early fault-tolerance regime where full quantum error correction is too expensive, yet controlled error detection measurably improves algorithmic success rates.

---

## Top-Level Components

```
┌─────────────────────────────────────────────────────────────────┐
│                  Logical Circuit Core Interface                  │
│              (OpenQASM 3.0 / Qiskit Standard Input)              │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┴──────────────────┐
         ▼                                  ▼
┌─────────────────┐               ┌──────────────────────┐
│  Hardware-Aware │               │   Data-Driven QED    │
│    Compiler     │◄──────────────│     Scheduler        │
│  (SA + ILP)     │  Calibration  │   (XGBoost Models)   │
└────────┬────────┘  Feedback     └──────────┬───────────┘
         │                                   │
         └────────────────┬──────────────────┘
                          ▼
         ┌────────────────────────────────────┐
         │         HPC Evaluation Engine      │
         │   cuQuantum (cuStateVec / cuTN)    │
         │   SLURM / Docker orchestration     │
         └────────────────┬───────────────────┘
                          │
              ┌───────────┴────────────┐
              ▼                        ▼
   ┌──────────────────┐     ┌────────────────────┐
   │  HPC Simulation  │     │  Physical Device   │
   │     Backend      │     │     Backend        │
   │  (Density Matrix)│     │  (IBM Eagle, etc.) │
   └──────────┬───────┘     └────────┬───────────┘
              └────────────┬─────────┘
                           ▼
              ┌────────────────────────┐
              │   Metrics Aggregator   │
              │  Bootstrap CIs, Stats  │
              └────────────────────────┘
```

---

## Component Details

### 1. Hardware-Aware Compilation Pass (`src/compiler/`)

**Purpose:** Map logical qubits to physical locations and insert SWAP gates while minimising expected error under latency constraints.

**Pipeline stages:**

| Stage | Module | Description |
|-------|--------|-------------|
| Front-end ingestion | `mapping_pass.py` | Parse OpenQASM 3.0 / Qiskit AST → DAG; build weighted interaction graph |
| Heuristic initial allocation | `mapping_pass.py` | Subgraph isomorphism to warm-start annealing |
| SA + ILP refinement | `mapping_pass.py` | Outer SA loop with embedded ILP kernel for sub-circuits ≤ w qubits |
| SWAP insertion | `swap_inserter.py` | A*/SABRE heuristic routing |
| Gate reduction | `swap_inserter.py` | KAK decomposition cancellation pass |
| Cost evaluation | `cost_computation.py` | Noise-weighted mapping cost (Eq. 2 in paper) |

**Key parameters:**

- `T0`, `alpha`, `Niter` — simulated annealing schedule
- `w` — ILP window size (default: 10 qubits, saturates at w=10)
- `beta` — latency overrun penalty coefficient
- `Lmax` — maximum allowed end-to-end latency

---

### 2. Data-Driven QED Scheduler (`src/scheduler/`)

**Purpose:** Predict the marginal benefit of syndrome insertions at candidate positions and return the Pareto-optimal schedule within milliseconds.

**Feature set (6 scalars per circuit):**

1. Total two-qubit gate count
2. Critical-path depth
3. Connectivity entropy H = −Σ pᵢ log pᵢ
4. Mean local gate fidelity under mapping m
5. Qubit allocation ratio
6. Idle coherence coefficient t̄ᵢdₗₑ / T₂

**ML models:**

- `M_ΔS` — XGBoost regressor predicting success uplift
- `M_R` — XGBoost regressor predicting post-selection retention
- Training corpus: 50,000 circuit-noise pairs (GPU-simulated)
- Cross-validation: 5-fold, mean R² = 0.903

**Inference:** Evaluates utility U(f, p) over discrete candidate set Q = {0, 0.25, 0.5, 0.75, 1.0} × {0, 1, 2, 3} and returns the feasible maximiser in under 6 ms.

---

### 3. QED Primitives (`src/qed/`)

**Purpose:** Implement [[n, n−2, 2]] detection-code blocks with one ancilla qubit per block.

- `primitives.py` — Gate-level construction of stabiliser checks
- `circuit_builder.py` — Insert QED blocks at scheduler-specified positions with classical post-selection logic

---

### 4. HPC Evaluation Framework (`src/simulation/`)

**Purpose:** GPU-accelerated density-matrix simulation with reproducible benchmarking harness.

| Simulator backend | Use case |
|-------------------|----------|
| `cuStateVec` | Exact density-matrix propagation, 6–20 qubits |
| `cuTensorNet` | Approximate simulation, > 20 qubits |
| `Qiskit Aer` | CPU fallback for development/testing |

**Orchestration:**

- SLURM job scripts for HPC cluster (see `scripts/run_slurm.sh`)
- Docker container for local reproducibility (see `docker/`)
- REST microservice wrapper for cloud integration

---

### 5. Metrics Layer (`src/metrics/`)

| Module | Function |
|--------|----------|
| `aggregator.py` | Collect S, R, latency, ancilla overhead across trials |
| `statistical_tests.py` | Bootstrap CIs (B=10,000), Wilcoxon signed-rank tests |
| `plots.py` | All paper figures: success vs. syndrome freq, Pareto scatter, ablation bars, scaling plots |

---

## Data Flow Summary

```
Input circuit (QASM)
        │
        ▼
Compiler Pass ──► Noise-weighted cost optimisation
        │
        ├──► Feature Extraction ──► QED Scheduler (XGBoost)
        │                                    │
        │         ┌──────────────────────────┘
        ▼          ▼
QED Block Insertion ──► Augmented circuit C'
        │
        ▼
GPU Simulation / Physical Backend
        │
        ▼
Metrics (S, R, Latency, Overhead)
        │
        ▼
Bootstrap CIs + Wilcoxon Tests ──► Figures + Tables
```

---

## Reproducibility

All experiments are fully reproducible via:

1. `scripts/reproduce_key_results.sh` — end-to-end from QASM to figures
2. Docker container — `docker/Dockerfile`
3. SLURM scripts — `scripts/run_slurm.sh`

See `docs/reproducible_checklist.md` for the complete checklist.
