"""
main.py — End-to-end pipeline entry point.

Usage
-----
python src/main.py \\
    --circuit data/circuits/vqe_h2.qasm \\
    --noise_model data/noise_models/ibm_lagos.json \\
    --mode joint \\
    --output results/vqe_h2_joint.json

Modes
-----
baseline     : SABRE routing, no QED
mapper_only  : SA+ILP mapping, no QED
qed_only     : SABRE routing + QED scheduler
joint        : SA+ILP mapping + QED scheduler  (full co-design)
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Dict

from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import SabreLayout, SabreSwap

from compiler import HardwareAwareMappingPass
from compiler.swap_inserter import SwapInserter
from scheduler import QEDScheduler
from simulation import DensityMatrixSimulator, NoiseModelFactory
from metrics import MetricsAggregator, bootstrap_ci
from metrics.aggregator import TrialResult
from utils.io import load_circuit, load_noise_model_json, save_results


# ---------------------------------------------------------------------------
# Default device topology (IBM Eagle 27-qubit heavy-hex subset)
# ---------------------------------------------------------------------------
_EAGLE_COUPLING = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (4, 6),
    (5, 7), (6, 8),
    (7, 9), (8, 10),
    (9, 11), (10, 12),
    (11, 13), (12, 14),
    (13, 15), (14, 16),
    (15, 17), (16, 18),
    (17, 19), (18, 20),
    (19, 21), (20, 22),
    (21, 23), (22, 24),
    (23, 25), (24, 26),
]

_DEFAULT_2Q_FIDELITY = 0.986
_DEFAULT_1Q_FIDELITY = 0.9991
_N_PHYSICAL = 27


def _build_gate_fidelities(coupling: list, fidelity: float = _DEFAULT_2Q_FIDELITY):
    return {(min(u, v), max(u, v)): fidelity for u, v in coupling}


def _build_1q_fidelities(n: int, fidelity: float = _DEFAULT_1Q_FIDELITY):
    return {q: fidelity for q in range(n)}


# ---------------------------------------------------------------------------
# Pipeline configurations
# ---------------------------------------------------------------------------

def run_baseline(circuit, noise_model, simulator, n_trials=100):
    """SABRE routing, no QED."""
    from qiskit.transpiler.passes import SabreLayout, SabreSwap, Optimize1qGates
    pm = PassManager([
        SabreLayout(coupling_map=_EAGLE_COUPLING, seed=42),
        SabreSwap(coupling_map=_EAGLE_COUPLING, heuristic="decay", seed=42),
        Optimize1qGates(),
    ])
    compiled = pm.run(circuit)
    results = []
    for _ in range(n_trials):
        s, r, _ = simulator.success_probability(compiled, "0" * circuit.num_qubits)
        results.append((s, r))
    return compiled, results


def run_mapper_only(circuit, noise_model, simulator, gate_fidelities, n_trials=100):
    """SA+ILP mapping, no QED."""
    mapping_pass = HardwareAwareMappingPass(
        coupling_map=_EAGLE_COUPLING,
        gate_fidelities=gate_fidelities,
        single_qubit_fidelities=_build_1q_fidelities(_N_PHYSICAL),
        T0=1.0, alpha=0.995, n_iter=5000, ilp_window=10, seed=42,
    )
    pm = PassManager([mapping_pass])
    dag = pm.run(circuit)
    hw_mapping = mapping_pass.property_set.get("hw_mapping", {})

    inserter = SwapInserter(_EAGLE_COUPLING, gate_fidelities, seed=42)
    compiled = inserter.insert_swaps(circuit, hw_mapping)

    results = []
    for _ in range(n_trials):
        s, r, _ = simulator.success_probability(compiled, "0" * circuit.num_qubits)
        results.append((s, r))
    return compiled, results, hw_mapping


def run_joint(
    circuit, noise_model, simulator,
    gate_fidelities, checkpoint_path, n_trials=100,
):
    """Full co-design: SA+ILP mapping + QED scheduler."""
    t_start = time.perf_counter()

    # Mapping
    mapping_pass = HardwareAwareMappingPass(
        coupling_map=_EAGLE_COUPLING,
        gate_fidelities=gate_fidelities,
        single_qubit_fidelities=_build_1q_fidelities(_N_PHYSICAL),
        T0=1.0, alpha=0.995, n_iter=5000, ilp_window=10, seed=42,
    )
    pm = PassManager([mapping_pass])
    pm.run(circuit)
    hw_mapping = mapping_pass.property_set.get("hw_mapping", {})
    mapping_lat_ms = mapping_pass.property_set.get("mapping_latency_ms", 0.0)

    inserter = SwapInserter(_EAGLE_COUPLING, gate_fidelities, seed=42)
    routed = inserter.insert_swaps(circuit, hw_mapping)

    # QED scheduling
    scheduler = QEDScheduler(
        checkpoint_path=checkpoint_path,
        gate_fidelities=gate_fidelities,
        n_physical_qubits=_N_PHYSICAL,
        lambda_ret=0.8, mu_lat=5e-4, latency_budget=1000.0,
    )
    qed_circuit, f_star, p_star, utility = scheduler.schedule(
        routed, mapping=hw_mapping, base_latency=mapping_lat_ms,
    )

    compilation_lat_ms = (time.perf_counter() - t_start) * 1e3

    results = []
    syndrome_mask = "0" * p_star if p_star > 0 else None
    for _ in range(n_trials):
        s, r, _ = simulator.success_probability(
            qed_circuit,
            "0" * circuit.num_qubits,
            post_select_mask=syndrome_mask,
        )
        results.append((s, r))

    return qed_circuit, results, f_star, p_star, compilation_lat_ms


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="Hardware-Aware Quantum Compilation + QED Pipeline"
    )
    p.add_argument("--circuit", required=True, help="Path to .qasm circuit file")
    p.add_argument("--noise_model", required=True, help="Path to noise model JSON")
    p.add_argument(
        "--mode",
        choices=["baseline", "mapper_only", "qed_only", "joint"],
        default="joint",
    )
    p.add_argument(
        "--checkpoint",
        default="data/training/model_checkpoint.pkl",
        help="Path to XGBoost scheduler checkpoint",
    )
    p.add_argument("--n_trials", type=int, default=100)
    p.add_argument("--shots", type=int, default=8192)
    p.add_argument("--output", default="results/output.json")
    return p.parse_args()


def main():
    args = parse_args()

    circuit = load_circuit(args.circuit)
    cal = load_noise_model_json(args.noise_model)

    factory = NoiseModelFactory(coupling_map=_EAGLE_COUPLING, n_qubits=_N_PHYSICAL)
    noise_model = factory.from_json(args.noise_model)
    simulator = DensityMatrixSimulator(noise_model=noise_model, shots=args.shots, seed=42)

    gate_fidelities = _build_gate_fidelities(
        _EAGLE_COUPLING, cal.get("fid_2q", _DEFAULT_2Q_FIDELITY)
    )

    aggregator = MetricsAggregator(n_bootstrap=10_000)
    circuit_name = Path(args.circuit).stem
    noise_name = Path(args.noise_model).stem

    if args.mode == "baseline":
        _, trials = run_baseline(circuit, noise_model, simulator, args.n_trials)
    elif args.mode == "mapper_only":
        _, trials, _ = run_mapper_only(circuit, noise_model, simulator, gate_fidelities, args.n_trials)
    elif args.mode == "joint":
        _, trials, f_star, p_star, lat = run_joint(
            circuit, noise_model, simulator, gate_fidelities,
            args.checkpoint, args.n_trials,
        )

    for s, r in trials:
        aggregator.add(TrialResult(
            circuit=circuit_name,
            noise_profile=noise_name,
            configuration=args.mode,
            success_probability=s,
            retention=r,
            latency_ms=lat if args.mode == "joint" else 0.0,
        ))

    summary = aggregator.summary()
    print(summary.to_string(index=False))
    save_results(summary.to_dict(orient="records"), args.output)


if __name__ == "__main__":
    main()
