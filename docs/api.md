# API Reference

This document describes the public Python API for the hardware-aware quantum compilation and QED pipeline.

---

## `src.compiler`

### `HardwareAwareMappingPass`

```python
from src.compiler.mapping_pass import HardwareAwareMappingPass

pass_obj = HardwareAwareMappingPass(
    backend,
    T0=1.0,
    alpha=0.995,
    n_iter=5000,
    ilp_window=10,
    lmax=None,
    beta=10.0,
)
```

**Parameters**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `backend` | `IBMBackend` | required | Target hardware backend supplying fidelity and topology data |
| `T0` | `float` | `1.0` | Initial simulated annealing temperature |
| `alpha` | `float` | `0.995` | SA cooling rate per step |
| `n_iter` | `int` | `5000` | Number of SA iterations |
| `ilp_window` | `int` | `10` | Maximum sub-circuit width for the ILP kernel |
| `lmax` | `float \| None` | `None` | Latency budget in milliseconds; `None` = unconstrained |
| `beta` | `float` | `10.0` | Penalty coefficient for latency overruns |

**Methods**

#### `run(dag: DAGCircuit) -> DAGCircuit`

Execute the mapping pass on a `DAGCircuit`.

Returns the mapped and SWAP-inserted `DAGCircuit` with KAK cancellation applied.

---

### `NoiseWeightedCost`

```python
from src.compiler.cost_computation import NoiseWeightedCost

cost_fn = NoiseWeightedCost(backend, use_critical_path_weights=True)
value = cost_fn.compute(mapping: dict, dag: DAGCircuit) -> float
```

Computes the noise-weighted mapping cost (Eq. 2):

```
Cost(m) = Σ_{g ∈ Gates} w_g · (1 − F̂_g(m))
```

where `w_g` is the critical-path importance weight and `F̂_g(m)` is the expected gate fidelity under mapping `m`.

---

## `src.scheduler`

### `QEDScheduler`

```python
from src.scheduler.scheduler import QEDScheduler

scheduler = QEDScheduler(
    model_path="data/training/model_checkpoint.pkl",
    lambda_=0.8,
    mu=5e-4,
    lmax=None,
)
```

**Parameters**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `model_path` | `str` | required | Path to saved XGBoost model checkpoint |
| `lambda_` | `float` | `0.8` | Success-retention trade-off weight in utility function |
| `mu` | `float` | `5e-4` | Latency overrun penalty weight |
| `lmax` | `float \| None` | `None` | Latency budget in milliseconds |

**Methods**

#### `schedule(circuit: QuantumCircuit, backend) -> tuple[float, int, QuantumCircuit]`

Returns `(f_star, p_star, qed_circuit)` — the optimal syndrome frequency, block-insertion position, and the augmented circuit with QED blocks inserted.

Inference completes within 6 ms on CPU.

---

### `FeatureExtractor`

```python
from src.scheduler.feature_extractor import FeatureExtractor

extractor = FeatureExtractor(backend)
features = extractor.extract(circuit: QuantumCircuit) -> np.ndarray  # shape (6,)
```

Returns a 6-dimensional feature vector:

| Index | Feature | Description |
|-------|---------|-------------|
| 0 | `n_2q_gates` | Total two-qubit gate count |
| 1 | `critical_path_depth` | Longest path through the circuit DAG |
| 2 | `connectivity_entropy` | H = −Σ pᵢ log pᵢ over qubit-pair interaction distribution |
| 3 | `mean_gate_fidelity` | Mean local gate fidelity under current mapping |
| 4 | `qubit_allocation_ratio` | Logical qubits / physical qubits |
| 5 | `idle_coherence_coeff` | t̄_idle / T₂ |

---

## `src.qed`

### `QEDPrimitiveBuilder`

```python
from src.qed.primitives import QEDPrimitiveBuilder

builder = QEDPrimitiveBuilder(n_data_qubits=6)
qed_circuit = builder.build_detection_block() -> QuantumCircuit
```

Constructs a [[n, n−2, 2]] detection-code block with one ancilla qubit. The block appends stabiliser measurements and classical post-selection logic.

---

### `QEDCircuitBuilder`

```python
from src.qed.circuit_builder import QEDCircuitBuilder

qed_builder = QEDCircuitBuilder(backend)
augmented = qed_builder.insert_blocks(
    circuit: QuantumCircuit,
    syndrome_freq: float,
    insertion_point: int,
) -> QuantumCircuit
```

Inserts QED blocks into the compiled circuit at the positions returned by `QEDScheduler`.

---

## `src.simulation`

### `DensityMatrixSimulator`

```python
from src.simulation.simulator import DensityMatrixSimulator

sim = DensityMatrixSimulator(
    backend="custatevec",   # "custatevec" | "cutensornet" | "aer"
    noise_model=noise_model,
    n_shots=8192,
)

result = sim.run(circuit: QuantumCircuit) -> SimulationResult
```

`SimulationResult` fields:

| Field | Type | Description |
|-------|------|-------------|
| `success_probability` | `float` | Fraction of runs returning the target bitstring |
| `retention` | `float` | Fraction of shots not discarded by post-selection |
| `latency_ms` | `float` | Wall-clock time for simulation |
| `counts` | `dict` | Raw bitstring counts |

---

### `NoiseModelFactory`

```python
from src.simulation.noise_models import NoiseModelFactory

nm = NoiseModelFactory.from_json("data/noise_models/ibm_lagos.json")
nm = NoiseModelFactory.superconducting()
nm = NoiseModelFactory.trapped_ion()
nm = NoiseModelFactory.adversarial()
```

---

## `src.metrics`

### `MetricsAggregator`

```python
from src.metrics.aggregator import MetricsAggregator

agg = MetricsAggregator(n_bootstrap=10000, random_state=42)
agg.add_trial(success=0.64, retention=0.64, latency_ms=370.0)
summary = agg.summarise()
# {"mean_S": ..., "ci_S": (lo, hi), "mean_R": ..., "ci_R": (lo, hi), ...}
```

### `StatisticalTests`

```python
from src.metrics.statistical_tests import StatisticalTests

p_val = StatisticalTests.wilcoxon_paired(baseline_scores, joint_scores)
ci_lo, ci_hi = StatisticalTests.bootstrap_ci(scores, n_bootstrap=10000)
```

### `ResultsPlotter`

```python
from src.metrics.plots import ResultsPlotter

plotter = ResultsPlotter(output_dir="results/figures/")
plotter.plot_success_vs_syndrome_freq(results_dict, noise_profiles)
plotter.plot_latency_vs_improvement(results_dict)
plotter.plot_pareto_scatter(results_dict)
plotter.plot_ablation_bars(ablation_dict)
plotter.plot_scaling(qubit_counts, success_dict)
```

---

## `src.main`

### Command-line interface

```bash
python src/main.py \
    --circuit data/circuits/vqe_h2.qasm \
    --noise-model data/noise_models/ibm_lagos.json \
    --config config/default.yaml \
    --output results/
```

**Arguments**

| Flag | Description |
|------|-------------|
| `--circuit` | Path to input QASM file |
| `--noise-model` | Path to JSON noise model |
| `--config` | Path to YAML configuration file |
| `--output` | Output directory for results and figures |
| `--backend` | Simulation backend: `custatevec`, `cutensornet`, `aer` (default: `custatevec`) |
| `--shots` | Number of simulation shots (default: `8192`) |
| `--no-qed` | Disable QED scheduler (run compiler-only baseline) |
| `--hardware` | Submit to real IBM Quantum backend instead of simulation |

---

## Configuration Files

See `config/default.yaml`, `config/scheduler_config.yaml`, and `config/simulator_config.yaml` for all tuneable hyperparameters with inline documentation.
