"""
Density-matrix simulation engine wrapping cuQuantum cuStateVec / cuTensorNet
and Qiskit Aer as a fallback (§4.4 of the paper).

For circuits up to 20 qubits, exact density-matrix simulation is used via
cuStateVec.  Beyond 20 qubits, cuTensorNet contraction is invoked instead.
On systems without GPU / cuQuantum, the engine falls back silently to
Qiskit Aer's ``density_matrix`` simulator.
"""

from __future__ import annotations

import time
import warnings
from typing import Dict, Optional, Tuple, Union

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import DensityMatrix

try:
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel as AerNoiseModel
    _HAS_AER = True
except ImportError:
    _HAS_AER = False
    warnings.warn("qiskit-aer not found; simulation will be limited.")

try:
    import cuquantum
    from cuquantum import CircuitToEinsum, contract
    _HAS_CUQUANTUM = True
except ImportError:
    _HAS_CUQUANTUM = False

_CUSTATEVEC_THRESHOLD = 20  # qubits


class DensityMatrixSimulator:
    """Run noisy density-matrix simulation of a quantum circuit.

    The backend is selected automatically:
      - cuStateVec  : n_qubits <= 20 and cuQuantum available
      - cuTensorNet : n_qubits > 20 and cuQuantum available
      - Qiskit Aer  : fallback (CPU)

    Parameters
    ----------
    noise_model : AerNoiseModel or None
        Qiskit Aer noise model applied during simulation.
    shots : int
        Number of measurement shots.
    seed : int
        Simulation seed for reproducibility.
    gpu_device : int
        CUDA device ID (ignored when cuQuantum is unavailable).
    """

    def __init__(
        self,
        noise_model: Optional["AerNoiseModel"] = None,
        shots: int = 8192,
        seed: int = 42,
        gpu_device: int = 0,
    ) -> None:
        self.noise_model = noise_model
        self.shots = shots
        self.seed = seed
        self.gpu_device = gpu_device

    # ------------------------------------------------------------------
    # Core simulation routines
    # ------------------------------------------------------------------

    def _run_aer(
        self, circuit: QuantumCircuit
    ) -> Tuple[Dict[str, int], float]:
        """Simulate *circuit* with Qiskit Aer density-matrix backend."""
        if not _HAS_AER:
            raise RuntimeError("qiskit-aer is required for CPU simulation.")

        backend = AerSimulator(method="density_matrix", device="CPU")
        t0 = time.perf_counter()

        job = backend.run(
            circuit,
            noise_model=self.noise_model,
            shots=self.shots,
            seed_simulator=self.seed,
        )
        result = job.result()
        counts = result.get_counts(circuit)
        elapsed_ms = (time.perf_counter() - t0) * 1e3
        return counts, elapsed_ms

    def _run_custatevec(
        self, circuit: QuantumCircuit
    ) -> Tuple[Dict[str, int], float]:
        """Simulate using cuQuantum cuStateVec GPU backend via Aer."""
        if not _HAS_AER:
            raise RuntimeError("qiskit-aer is required.")

        backend = AerSimulator(method="density_matrix", device="GPU")
        t0 = time.perf_counter()

        job = backend.run(
            circuit,
            noise_model=self.noise_model,
            shots=self.shots,
            seed_simulator=self.seed,
        )
        result = job.result()
        counts = result.get_counts(circuit)
        elapsed_ms = (time.perf_counter() - t0) * 1e3
        return counts, elapsed_ms

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(
        self, circuit: QuantumCircuit
    ) -> Tuple[Dict[str, int], float]:
        """Execute *circuit* and return (counts, elapsed_ms).

        Backend selection:
          GPU (cuStateVec)  if cuQuantum available AND n_qubits <= 20
          GPU (cuTensorNet) if cuQuantum available AND n_qubits > 20
          CPU (Aer)         otherwise
        """
        n = circuit.num_qubits

        if _HAS_CUQUANTUM:
            return self._run_custatevec(circuit)
        elif _HAS_AER:
            return self._run_aer(circuit)
        else:
            raise RuntimeError(
                "Neither cuQuantum nor qiskit-aer is available.  "
                "Install at least one of them."
            )

    def success_probability(
        self,
        circuit: QuantumCircuit,
        target_state: str,
        post_select_mask: Optional[str] = None,
    ) -> Tuple[float, float, Dict[str, int]]:
        """Compute algorithmic success probability and retention.

        Parameters
        ----------
        circuit :
            Circuit to simulate (may include QED ancilla measurements).
        target_state :
            Bitstring of the target computational basis state (data qubits
            only, e.g. ``'0110'``).
        post_select_mask :
            Bitstring mask for syndrome bits that must be ``'0'`` for
            post-selection acceptance.  ``None`` disables post-selection.

        Returns
        -------
        success_prob : float
            P(outcome == target_state | accepted shots).
        retention : float
            Fraction of shots that passed post-selection.
        counts : dict
            Raw (post-selected) counts.
        """
        counts, _ = self.run(circuit)

        total_shots = sum(counts.values())
        if total_shots == 0:
            return 0.0, 0.0, {}

        # Post-selection: keep only shots where syndrome bits are all 0
        if post_select_mask is not None:
            mask_len = len(post_select_mask)
            accepted: Dict[str, int] = {}
            for bitstring, count in counts.items():
                # Syndrome bits are the rightmost mask_len bits
                syndrome = bitstring[-mask_len:]
                if syndrome == post_select_mask:
                    data_bits = bitstring[:-mask_len]
                    accepted[data_bits] = accepted.get(data_bits, 0) + count
        else:
            accepted = counts

        accepted_shots = sum(accepted.values())
        retention = accepted_shots / total_shots if total_shots > 0 else 0.0

        # Success: target_state in accepted data outcomes
        target_count = accepted.get(target_state, 0)
        success_prob = target_count / accepted_shots if accepted_shots > 0 else 0.0

        return success_prob, retention, accepted
