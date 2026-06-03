"""I/O helpers for loading circuits, noise models, and saving results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from qiskit import QuantumCircuit
from qiskit.qasm2 import load as qasm2_load
from qiskit.qasm3 import load as qasm3_load


def load_circuit(path: str) -> QuantumCircuit:
    """Load a quantum circuit from a QASM 2.0 or QASM 3.0 file.

    Parameters
    ----------
    path : str
        Path to ``.qasm`` file.

    Returns
    -------
    QuantumCircuit
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Circuit file not found: {path}")

    text = p.read_text()
    # Detect QASM version from header
    if "OPENQASM 3" in text[:50]:
        return qasm3_load(str(p))
    else:
        return qasm2_load(str(p))


def load_noise_model_json(path: str) -> Dict[str, Any]:
    """Load a device calibration JSON file.

    Returns the raw calibration dictionary; pass to
    ``NoiseModelFactory.from_json()`` to construct an Aer NoiseModel.
    """
    with open(path) as fh:
        return json.load(fh)


def save_results(results: Dict[str, Any], path: str) -> None:
    """Save a results dictionary as a pretty-printed JSON file."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(results, fh, indent=2, default=str)
