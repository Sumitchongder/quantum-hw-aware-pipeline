"""
[[n, n-2, 2]] quantum error detection code primitives (§4.2 of the paper).

Each QEDBlock encodes n logical qubits into n physical data qubits plus one
ancilla qubit per block.  It appends stabiliser check gates (CNOT ladder)
followed by a measurement of the ancilla, implementing a distance-2 parity
check that detects (but does not correct) single-qubit errors.

Reference: Chao & Reichardt, PRL 121, 050502 (2018); Ginsberg & Patel,
arXiv:2503.10790 (2025) — see §2 of the paper.
"""

from __future__ import annotations

from typing import List, Optional

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister


class QEDBlock:
    """A single [[n, n-2, 2]] detection-code block for *n* data qubits.

    The block implements two Z-type parity checks using one ancilla qubit,
    providing distance-2 error detection with post-selection on the classical
    syndrome.

    Parameters
    ----------
    n_data : int
        Number of data qubits in the block (>= 3).
    ancilla_label : str
        Label for the ancilla qubit register.
    syndrome_label : str
        Label for the classical syndrome register.
    """

    def __init__(
        self,
        n_data: int,
        ancilla_label: str = "anc",
        syndrome_label: str = "syn",
    ) -> None:
        if n_data < 3:
            raise ValueError(
                f"QEDBlock requires at least 3 data qubits, got {n_data}."
            )
        self.n_data = n_data
        self.ancilla_label = ancilla_label
        self.syndrome_label = syndrome_label

    def build_circuit(self) -> QuantumCircuit:
        """Construct the [[n, n-2, 2]] detection-code circuit.

        Returns a ``QuantumCircuit`` with ``n_data`` data qubits, one ancilla
        qubit, and one classical bit for the syndrome measurement.  The
        circuit structure follows Fig. 3 of the paper:

          Ingestion → Inference Layer 1 → Inference Layer 2 → Syndrome Meas.

        In code this translates to:
          1. Reset ancilla to |0>.
          2. Hadamard on ancilla (prepare |+>).
          3. CNOT from ancilla to each data qubit in the first parity group.
          4. Hadamard on ancilla.
          5. Measure ancilla into classical register.
        """
        data_reg = QuantumRegister(self.n_data, name="d")
        anc_reg = QuantumRegister(1, name=self.ancilla_label)
        syn_reg = ClassicalRegister(1, name=self.syndrome_label)

        qc = QuantumCircuit(data_reg, anc_reg, syn_reg)

        # Ingestion stage: reset ancilla
        qc.reset(anc_reg[0])

        # Inference Layer 1 — first Z-parity check
        qc.h(anc_reg[0])
        parity_group_1 = list(range(0, self.n_data // 2))
        for idx in parity_group_1:
            qc.cx(anc_reg[0], data_reg[idx])
        qc.h(anc_reg[0])

        # Inference Layer 2 — second Z-parity check
        qc.reset(anc_reg[0])
        qc.h(anc_reg[0])
        parity_group_2 = list(range(self.n_data // 2, self.n_data))
        for idx in parity_group_2:
            qc.cx(anc_reg[0], data_reg[idx])
        qc.h(anc_reg[0])

        # Syndrome measurement stage
        qc.measure(anc_reg[0], syn_reg[0])

        return qc

    def post_select(self, counts: dict) -> dict:
        """Filter shot counts to retain only syndrome-0 outcomes.

        Parameters
        ----------
        counts : dict
            Qiskit-style shot counts ``{'bitstring': count, ...}``.

        Returns
        -------
        dict
            Counts with all syndrome-violating shots discarded.
        """
        accepted = {}
        for bitstring, count in counts.items():
            # The syndrome bit is the rightmost classical bit in the string
            syndrome_bit = bitstring.strip()[-1]
            if syndrome_bit == "0":
                accepted[bitstring] = count
        return accepted

    def retention(self, counts: dict) -> float:
        """Return the post-selection retention fraction R.

        R = (accepted shots) / (total shots).
        """
        total = sum(counts.values())
        if total == 0:
            return 0.0
        accepted = sum(v for k, v in counts.items() if k.strip()[-1] == "0")
        return accepted / total
