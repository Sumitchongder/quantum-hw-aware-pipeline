"""
Feature extraction for the QED scheduler (§4.2 of the paper).

Six scalar features are computed per compiled circuit:
  1. Total two-qubit gate count.
  2. Critical-path depth.
  3. Connectivity entropy  H = -sum_i p_i log p_i.
  4. Mean local gate fidelity under mapping m.
  5. Qubit allocation ratio.
  6. Idle coherence coefficient  t_idle_bar / T2.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np
from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag


class FeatureExtractor:
    """Compute the six-dimensional feature vector for a compiled circuit.

    Parameters
    ----------
    gate_fidelities : dict
        Physical edge -> two-qubit gate fidelity (used for feature 4).
    t2_times : dict
        Physical qubit -> T2 dephasing time in µs (used for feature 6).
    gate_time_us : float
        Typical two-qubit gate time in µs (default 0.5).
    """

    FEATURE_NAMES: List[str] = [
        "two_qubit_gate_count",
        "critical_path_depth",
        "connectivity_entropy",
        "mean_local_gate_fidelity",
        "qubit_allocation_ratio",
        "idle_coherence_coeff",
    ]

    def __init__(
        self,
        gate_fidelities: Optional[Dict[Tuple[int, int], float]] = None,
        t2_times: Optional[Dict[int, float]] = None,
        gate_time_us: float = 0.5,
    ) -> None:
        self.gate_fidelities = gate_fidelities or {}
        self.t2_times = t2_times or {}
        self.gate_time_us = gate_time_us

    # ------------------------------------------------------------------
    # Individual feature computations
    # ------------------------------------------------------------------

    @staticmethod
    def two_qubit_gate_count(circuit: QuantumCircuit) -> int:
        """Feature 1: total number of two-qubit gates."""
        return sum(
            1
            for instr in circuit.data
            if len(instr.qubits) == 2 and instr.operation.name != "barrier"
        )

    @staticmethod
    def critical_path_depth(circuit: QuantumCircuit) -> int:
        """Feature 2: depth of the circuit DAG (critical-path length)."""
        return circuit.depth()

    @staticmethod
    def connectivity_entropy(circuit: QuantumCircuit) -> float:
        """Feature 3: Shannon entropy of the qubit-interaction frequency
        distribution.  H = -sum_i p_i * log(p_i).
        """
        counts: Dict[int, int] = {}
        for instr in circuit.data:
            if len(instr.qubits) == 2:
                for q in instr.qubits:
                    idx = circuit.find_bit(q).index
                    counts[idx] = counts.get(idx, 0) + 1
        if not counts:
            return 0.0
        total = sum(counts.values())
        probs = [v / total for v in counts.values()]
        return -sum(p * math.log(p + 1e-12) for p in probs)

    def mean_local_gate_fidelity(
        self,
        circuit: QuantumCircuit,
        mapping: Optional[Dict[int, int]] = None,
    ) -> float:
        """Feature 4: mean expected fidelity of two-qubit gates under
        the supplied *mapping* (or identity mapping if None).
        """
        fidelities = []
        for instr in circuit.data:
            if len(instr.qubits) == 2 and instr.operation.name != "barrier":
                q0_logical = circuit.find_bit(instr.qubits[0]).index
                q1_logical = circuit.find_bit(instr.qubits[1]).index
                if mapping:
                    pq0 = mapping.get(q0_logical, q0_logical)
                    pq1 = mapping.get(q1_logical, q1_logical)
                else:
                    pq0, pq1 = q0_logical, q1_logical
                edge = (min(pq0, pq1), max(pq0, pq1))
                fidelities.append(self.gate_fidelities.get(edge, 0.99))
        return float(np.mean(fidelities)) if fidelities else 0.99

    @staticmethod
    def qubit_allocation_ratio(
        circuit: QuantumCircuit,
        n_physical_qubits: int,
    ) -> float:
        """Feature 5: fraction of physical qubits used by this circuit."""
        return circuit.num_qubits / max(n_physical_qubits, 1)

    def idle_coherence_coeff(
        self,
        circuit: QuantumCircuit,
        mapping: Optional[Dict[int, int]] = None,
    ) -> float:
        """Feature 6: mean idle time normalised by T2 per qubit.

        t_idle_bar = mean idle time per qubit (estimated from depth and
        gate count).  Normalised by mean T2 across allocated qubits.
        """
        if not self.t2_times:
            return 0.0

        n_q = circuit.num_qubits
        depth = circuit.depth()
        gate_counts = np.zeros(n_q)

        for instr in circuit.data:
            if instr.operation.name in ("barrier", "measure"):
                continue
            for q in instr.qubits:
                idx = circuit.find_bit(q).index
                gate_counts[idx] += 1

        # Idle time estimate per qubit: (depth - gate_count[q]) * gate_time_us
        idle_times_us = np.maximum(depth - gate_counts, 0) * self.gate_time_us

        # Map logical qubits to physical to look up T2
        t2_vals = []
        for lq in range(n_q):
            pq = mapping.get(lq, lq) if mapping else lq
            t2_vals.append(self.t2_times.get(pq, 100.0))

        t2_arr = np.array(t2_vals)
        mean_t2 = float(np.mean(t2_arr)) if len(t2_arr) > 0 else 100.0
        mean_idle = float(np.mean(idle_times_us))
        return mean_idle / max(mean_t2, 1e-6)

    # ------------------------------------------------------------------
    # Unified feature vector
    # ------------------------------------------------------------------

    def extract(
        self,
        circuit: QuantumCircuit,
        mapping: Optional[Dict[int, int]] = None,
        n_physical_qubits: int = 27,
    ) -> np.ndarray:
        """Return the six-dimensional feature vector as a 1-D NumPy array.

        Parameters
        ----------
        circuit :
            Compiled (routed) quantum circuit.
        mapping :
            Logical-to-physical qubit assignment.
        n_physical_qubits :
            Total number of physical qubits on the target device.

        Returns
        -------
        np.ndarray, shape (6,)
        """
        features = np.array([
            float(self.two_qubit_gate_count(circuit)),
            float(self.critical_path_depth(circuit)),
            self.connectivity_entropy(circuit),
            self.mean_local_gate_fidelity(circuit, mapping),
            self.qubit_allocation_ratio(circuit, n_physical_qubits),
            self.idle_coherence_coeff(circuit, mapping),
        ], dtype=np.float64)
        return features
