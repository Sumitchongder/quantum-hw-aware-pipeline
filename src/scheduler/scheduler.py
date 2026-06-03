"""
High-level QED scheduler that combines feature extraction and inference.

Implements Algorithm 2 of the paper (full pseudocode).
"""

from __future__ import annotations

import time
from typing import Dict, Optional, Tuple

import numpy as np
from qiskit import QuantumCircuit

from .feature_extractor import FeatureExtractor
from .model_inference import QEDSchedulerInference
from ..qed.circuit_builder import QEDCircuitBuilder


class QEDScheduler:
    """End-to-end QED scheduler.

    Wraps FeatureExtractor + QEDSchedulerInference + QEDCircuitBuilder into
    a single ``schedule()`` call that mirrors Algorithm 2.

    Parameters
    ----------
    checkpoint_path : str
        Path to trained XGBoost checkpoint.
    gate_fidelities : dict
        Physical edge -> two-qubit gate fidelity.
    t2_times : dict
        Physical qubit -> T2 time in µs.
    n_physical_qubits : int
        Number of physical qubits on the target device.
    lambda_ret : float
        Retention penalty weight.
    mu_lat : float
        Latency overrun penalty.
    latency_budget : float
        Max end-to-end latency (ms).
    """

    def __init__(
        self,
        checkpoint_path: str,
        gate_fidelities: Optional[Dict] = None,
        t2_times: Optional[Dict] = None,
        n_physical_qubits: int = 27,
        lambda_ret: float = 0.8,
        mu_lat: float = 5e-4,
        latency_budget: float = 1000.0,
    ) -> None:
        self.extractor = FeatureExtractor(
            gate_fidelities=gate_fidelities or {},
            t2_times=t2_times or {},
        )
        self.inference = QEDSchedulerInference(
            checkpoint_path=checkpoint_path,
            lambda_ret=lambda_ret,
            mu_lat=mu_lat,
            latency_budget=latency_budget,
        )
        self.builder = QEDCircuitBuilder()
        self.n_physical_qubits = n_physical_qubits

    def schedule(
        self,
        compiled_circuit: QuantumCircuit,
        mapping: Optional[Dict[int, int]] = None,
        base_latency: float = 0.0,
    ) -> Tuple[QuantumCircuit, float, int, float]:
        """Run the full scheduler pipeline on a compiled circuit.

        Parameters
        ----------
        compiled_circuit :
            Routed, gate-reduced quantum circuit.
        mapping :
            Logical-to-physical qubit assignment.
        base_latency :
            Current compilation latency (ms) from the mapping pass.

        Returns
        -------
        qed_circuit : QuantumCircuit
            Circuit with QED blocks inserted at the optimal schedule.
        f_star : float
            Optimal syndrome frequency.
        p_star : int
            Optimal block position index.
        utility : float
            Utility value of the selected configuration.
        """
        t0 = time.perf_counter()

        # Algorithm 2, line 1: extract features
        features = self.extractor.extract(
            circuit=compiled_circuit,
            mapping=mapping,
            n_physical_qubits=self.n_physical_qubits,
        )

        # Lines 2-9: evaluate candidates and select q*
        f_star, p_star, utility = self.inference.predict(
            base_features=features,
            base_latency=base_latency,
        )

        # Lines 11-12: insert QED blocks and return
        qed_circuit = self.builder.build(
            circuit=compiled_circuit,
            syndrome_frequency=f_star,
            block_position=p_star,
        )

        scheduler_ms = (time.perf_counter() - t0) * 1e3
        return qed_circuit, f_star, p_star, utility
