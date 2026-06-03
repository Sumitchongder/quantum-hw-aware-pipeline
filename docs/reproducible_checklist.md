# Reproducibility Checklist

This checklist certifies that all experimental claims in the associated publication can be independently reproduced from this repository.

---

## Environment Reproducibility

- [x] Python version pinned (`3.10`) in `docker/requirements.txt`
- [x] All package versions pinned with exact version specifiers
- [x] CUDA toolkit version documented (`12.x`, A100-compatible)
- [x] `Dockerfile` builds a self-contained runtime image
- [x] `docker/docker_entrypoint.sh` runs the full pipeline in a single command
- [x] Random seeds fixed globally (`seed=42`) in all experiment scripts
- [x] SLURM job scripts specify node type and GPU count

---

## Data Reproducibility

- [x] All four benchmark circuits provided as OpenQASM 3.0 files under `data/circuits/`
- [x] All three noise model JSON files provided under `data/noise_models/`
- [x] Training corpus generation is deterministic and scripted in `notebooks/00_setup_and_data_generation.ipynb`
- [x] Pre-generated `features.csv` and `labels.csv` included under `data/training/`
- [x] Pre-trained model checkpoint `model_checkpoint.pkl` included
- [x] All random splits use a fixed seed; cross-validation folds are reproducible

---

## Experimental Reproducibility

| Claim | Table / Figure | Reproducing notebook | Script |
|-------|---------------|----------------------|--------|
| SABRE baseline success probabilities | Table 4 | `04_full_pipeline_evaluation.ipynb` | `reproduce_key_results.sh` |
| Joint co-design success probabilities + 95% CI | Table 4 | `04_full_pipeline_evaluation.ipynb` | `reproduce_key_results.sh` |
| Ablation study (mapper-only, QED-only, joint) | Table 5 | `04_full_pipeline_evaluation.ipynb` | `reproduce_key_results.sh` |
| Success vs. syndrome frequency curves | Figure 5 | `05_plotting_and_results.ipynb` | — |
| Latency vs. improvement curves | Figure 6 | `05_plotting_and_results.ipynb` | — |
| Retention-success Pareto scatter | Figure 7 | `05_plotting_and_results.ipynb` | — |
| Per-benchmark ablation bar charts | Figure 8 | `05_plotting_and_results.ipynb` | — |
| Scaling (qubit count + gate depth) | Figure 9 | `05_plotting_and_results.ipynb` | — |
| Retention vs. ancilla + runtime decomposition | Figure 10 | `05_plotting_and_results.ipynb` | — |
| ML scheduler diagnostics (feature importance, CV R²) | Figure 11 | `02_scheduler_training.ipynb` | — |
| Simulation vs. hardware validation | Figure 12 | `06_hardware_validation.ipynb` | — |
| ILP kernel sensitivity (w = 5, 10, 15) | Table 6 | `04_full_pipeline_evaluation.ipynb` | — |

---

## Statistical Reproducibility

- [x] All confidence intervals use B = 10,000 bootstrap resamples
- [x] All paired comparisons use the Wilcoxon signed-rank test (non-parametric, two-sided)
- [x] Significance threshold is α = 0.01 throughout
- [x] Minimum trial count per condition is n = 100
- [x] `results/benchmark_summary.csv` contains raw per-trial data for independent re-analysis
- [x] `results/ablation_results.csv` contains per-benchmark ablation scores
- [x] `results/runtime_breakdown.csv` contains per-component latency measurements

---

## Model Reproducibility

- [x] XGBoost hyperparameters documented in `config/scheduler_config.yaml`
- [x] Training / validation / test split sizes documented (50k / 10k / 10k)
- [x] 5-fold CV procedure is deterministic under fixed seed
- [x] `model_checkpoint.pkl` is the exact model used to produce all paper results
- [x] Feature extraction code is unit-tested in `tests/test_scheduler.py`

---

## Hardware Validation Reproducibility

- [x] IBM Eagle-family processor specification documented in Table 3 of the paper
- [x] 8,192 shots per configuration
- [x] Calibration snapshot retrieved at job-submission time (noted in `notebooks/06_hardware_validation.ipynb`)
- [x] Raw hardware counts available in `results/` after running the hardware notebook
- [ ] Full multi-benchmark hardware ablation pending (IBM Quantum queue constraints — see paper §6.10)

---

## How to Reproduce

### Option A: Docker (recommended)

```bash
docker build -t qhwp docker/
docker run --gpus all qhwp
```

### Option B: SLURM

```bash
bash scripts/run_slurm.sh
```

### Option C: Manual notebook execution

```bash
pip install -r docker/requirements.txt
jupyter nbconvert --to notebook --execute notebooks/00_setup_and_data_generation.ipynb
jupyter nbconvert --to notebook --execute notebooks/01_compiler_baselines.ipynb
jupyter nbconvert --to notebook --execute notebooks/02_scheduler_training.ipynb
jupyter nbconvert --to notebook --execute notebooks/04_full_pipeline_evaluation.ipynb
jupyter nbconvert --to notebook --execute notebooks/05_plotting_and_results.ipynb
```

### One-command key results

```bash
bash scripts/reproduce_key_results.sh
```

This script regenerates Table 4, Table 5, and Figures 5–10 and writes outputs to `results/figures/` and `results/tables/`.

---

## Known Limitations

1. GPU simulation requires CUDA 12.x and an NVIDIA GPU with at least 16 GB VRAM for the 20-qubit experiments. CPU fallback (Qiskit Aer) is available for smaller circuits.
2. IBM Quantum hardware access requires a valid IBM Quantum Network account. Notebook 06 is the only component that needs hardware credentials.
3. Absolute success probability values from GPU simulation may differ by ±0.01 from those in the paper due to floating-point non-determinism across GPU driver versions.
