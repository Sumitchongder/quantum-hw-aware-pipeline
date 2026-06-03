"""
Device noise model factory (Table 2 of the paper).

Provides three calibrated noise profiles:
  - Superconducting (IBM Eagle-like)
  - Trapped-ion
  - Adversarial (stress-test: 2x two-qubit error, correlated Z noise)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

try:
    from qiskit_aer.noise import (
        NoiseModel,
        depolarizing_error,
        thermal_relaxation_error,
        ReadoutError,
        pauli_error,
    )
    _HAS_AER = True
except ImportError:
    _HAS_AER = False


class NoiseModelFactory:
    """Build Qiskit Aer NoiseModel objects from device calibration data.

    Parameters
    ----------
    coupling_map : list of (int, int)
        Physical device edges.
    n_qubits : int
        Number of physical qubits.
    """

    def __init__(
        self,
        coupling_map: List[tuple],
        n_qubits: int = 27,
    ) -> None:
        self.coupling_map = coupling_map
        self.n_qubits = n_qubits

    # ------------------------------------------------------------------

    def _build_model(
        self,
        fid_1q: float,
        fid_2q: float,
        readout_fid: float,
        t1_us: float,
        t2_us: float,
        gate_time_1q_us: float = 0.05,
        gate_time_2q_us: float = 0.5,
        correlated_z_lambda: float = 0.0,
    ) -> "NoiseModel":
        if not _HAS_AER:
            raise ImportError("qiskit-aer is required to build noise models.")

        model = NoiseModel()

        err_1q = 1.0 - fid_1q
        err_2q = 1.0 - fid_2q
        readout_err = 1.0 - readout_fid

        # Single-qubit depolarising
        dep_1q = depolarizing_error(err_1q, 1)
        # Two-qubit depolarising
        dep_2q = depolarizing_error(err_2q, 2)

        # Thermal relaxation (T1, T2) for each qubit
        for q in range(self.n_qubits):
            t_relax_1q = thermal_relaxation_error(
                t1_us, t2_us, gate_time_1q_us
            )
            t_relax_2q = thermal_relaxation_error(
                t1_us, t2_us, gate_time_2q_us
            )
            # Compose depolarising + relaxation for 1Q gates
            combined_1q = dep_1q.compose(t_relax_1q)
            model.add_quantum_error(combined_1q, ["u1", "u2", "u3", "h", "x", "y", "z"], [q])
            # Readout error
            ro_error = ReadoutError([
                [1 - readout_err, readout_err],
                [readout_err, 1 - readout_err],
            ])
            model.add_readout_error(ro_error, [q])

        # Two-qubit gate errors on coupling edges
        for q0, q1 in self.coupling_map:
            t_relax_2q_q0 = thermal_relaxation_error(t1_us, t2_us, gate_time_2q_us)
            t_relax_2q_q1 = thermal_relaxation_error(t1_us, t2_us, gate_time_2q_us)
            t_relax_2q_both = t_relax_2q_q0.expand(t_relax_2q_q1)
            combined_2q = dep_2q.compose(t_relax_2q_both)
            model.add_quantum_error(combined_2q, ["cx", "ecr", "cz"], [q0, q1])

        # Adversarial correlated Z noise
        if correlated_z_lambda > 0.0:
            z_err = pauli_error([("Z", correlated_z_lambda), ("I", 1 - correlated_z_lambda)])
            for q in range(self.n_qubits):
                model.add_quantum_error(z_err, ["cx"], [q])

        return model

    # ------------------------------------------------------------------
    # Named profiles (Table 2 of the paper)
    # ------------------------------------------------------------------

    def superconducting(self) -> "NoiseModel":
        """IBM Eagle-like superconducting profile."""
        return self._build_model(
            fid_1q=0.9991,
            fid_2q=0.986,
            readout_fid=0.980,
            t1_us=70.0,
            t2_us=90.0,
        )

    def trapped_ion(self) -> "NoiseModel":
        """Trapped-ion profile with higher fidelities and longer coherence."""
        return self._build_model(
            fid_1q=0.9996,
            fid_2q=0.995,
            readout_fid=0.995,
            t1_us=500.0,
            t2_us=400.0,
        )

    def adversarial(self) -> "NoiseModel":
        """Adversarial stress-test: doubled 2Q error + correlated Z noise."""
        return self._build_model(
            fid_1q=0.9950,
            fid_2q=0.950,
            readout_fid=0.950,
            t1_us=50.0,
            t2_us=60.0,
            correlated_z_lambda=0.05,
        )

    def from_json(self, path: str) -> "NoiseModel":
        """Load device calibration from a JSON file and construct a model."""
        with open(path) as fh:
            cal = json.load(fh)
        return self._build_model(
            fid_1q=cal.get("fid_1q", 0.999),
            fid_2q=cal.get("fid_2q", 0.99),
            readout_fid=cal.get("readout_fid", 0.98),
            t1_us=cal.get("t1_us", 70.0),
            t2_us=cal.get("t2_us", 90.0),
        )
