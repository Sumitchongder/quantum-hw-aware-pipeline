# Changelog

All notable changes to the **Quantum Hardware-Aware Co-Design Pipeline** project will be documented in this file. This project strictly adheres to [Semantic Versioning](https://semver.org/) and follows the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) standard.

---

## [1.0.0] - 2026-06-03
### Added
- **Physical Hardware Verification Baseline**: Integrated live execution telemetry from an 8192-shot deployment configuration on the `ibm_kyoto` Eagle-family processor.
- **Explainable AI (XAI) Architecture**: Integrated game-theoretic SHAP (SHapley Additive exPlanations) beeswarm visualization matrices to evaluate top-tier features (graph connectivity entropy, multi-qubit gate density) steering the XGBoost scheduler.
- **Advanced Rigorous Statistical Evaluation Matrix**: Added automated execution of the non-parametric Wilcoxon signed-rank test and Cohen's $d$ effect size computations to statistically reject performance null-hypotheses.
- **Comprehensive Continuous Integration Environment**: Added automated multi-version GitHub Actions workflow configuration executing syntax validation, parallel regression sweeps, and production multi-stage Docker compilation tests.

### Changed
- **Validation Scale-Up Horizon**: Expanded classical simulation scaling horizons from standard mid-scale blocks up to **40 qubits** via high-performance Tensor Network and Matrix Product State configuration models within the GPU-accelerated NVIDIA cuQuantum SDK.
- **Compilation Comparative Baselines**: Upgraded benchmarking suites to compare performance trajectories simultaneously against **SABRE**, **Qiskit `NoiseAdaptiveLayout`**, and **`t|ket>`'s routing engine**.
- **Formatted Plot Layout Configurations**: Upgraded matplotlib/seaborn configurations to meet Q1 publication specifications, utilizing high-DPI vector outputs with integrated 95% Confidence Intervals (CI).

### Fixed
- **Physical Reality Gap Mitigation**: Resolved an uncalibrated 4%–8% performance gap between classical density-matrix simulation engines and physical hardware nodes by introducing spectator cross-talk error weights to the global Simulated Annealing cost matrix.
- **Local Optimization Bounding**: Fixed an NP-hard timeout issue within the Integer Linear Programming (ILP) router pass by constraining optimization kernels to a sliding window of localized sub-circuits restricted to $W \le 10$ qubits, reducing worst-case local complexity to a linear function of circuit depth.

### Removed
- Removed old static syndrome scheduling profiles to clear technical overhead in favor of dynamic, data-driven machine learning scheduling predictions.

---

## [0.2.0] - 2026-02-15
### Added
- **Hybrid Lookahead Routing Engine**: Designed a dual-stage compiler pass coupling global Simulated Annealing qubit placement with exact localized ILP routing refinement loops.
- **HPC Cluster Slurm Automation Support**: Built execution scripts (`run_slurm.sh`) enabling automated resource allocation and multi-threaded processing patterns across dedicated clusters utilizing NVIDIA A100 GPUs.
- **Lightweight Predictive Model**: Designed an optimized, real-time XGBoost regressor predicting error syndrome insertion frequencies with execution latencies constrained strictly under **6 ms**.

### Changed
- Migrated legacy compilation dependencies to conform with the modern decoupled **Qiskit 1.x core ecosystem framework layout**.

### Fixed
- Fixed an error cascading issue during syndrome extraction by introducing systematic, real-time ancilla recycling loops using immediate physical `reset` primitives.

---

## [0.1.0] - 2025-11-10
### Added
- Initial functional prototype of the hardware-aware qubit placement mechanism.
- Basic framework supporting static Quantum Error Detection (QED) syndrome insertion checks.
- Baseline evaluation capabilities against default SABRE routing heuristics.

```

---

