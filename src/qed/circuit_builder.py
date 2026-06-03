"""
QEDCircuitBuilder: insert QED blocks into a compiled circuit at the
optimal (f*, p*) positions returned by the scheduler.
"""

from __future__ import annotations

import math
from typing import Optional

from qiskit import QuantumCircuit, ClassicalRegister
from qiskit.circuit import Barrier

from .primitives import QEDBlock


class QEDCircuitBuilder:
    """Augment a compiled circuit with [[n, n-2, 2]] QED blocks.

    Parameters
    ----------
    ancilla_prefix : str
        Prefix for ancilla qubit register names.
    """

    def __init__(self, ancilla_prefix: str = "qed_anc") -> None:
        self.ancilla_prefix = ancilla_prefix

    def build(
        self,
        circuit: QuantumCircuit,
        syndrome_frequency: float,
        block_position: int,
    ) -> QuantumCircuit:
        """Insert QED blocks into *circuit* at the scheduled positions.

        Parameters
        ----------
        circuit :
            Compiled, routed quantum circuit.
        syndrome_frequency : float
            Fraction of circuit depth at which to insert QED blocks (0–1).
            0.0 means no blocks; 1.0 means blocks at every layer boundary.
        block_position : int
            Number of QED blocks to insert (0-3, indexed from p*).

        Returns
        -------
        QuantumCircuit
            Augmented circuit with QED blocks and classical post-selection
            registers attached.
        """
        if syndrome_frequency == 0.0 or block_position == 0:
            return circuit  # No QED — return unchanged

        n_blocks = block_position  # p* in the paper
        depth = circuit.depth()

        if depth == 0 or n_blocks == 0:
            return circuit

        # Determine insertion points (evenly spaced by syndrome_frequency)
        insertion_depths = [
            int(round(syndrome_frequency * depth * (i + 1) / n_blocks))
            for i in range(n_blocks)
        ]
        insertion_depths = sorted(set(max(1, min(d, depth - 1)) for d in insertion_depths))

        n_data = circuit.num_qubits
        qed_circuit = QuantumCircuit()

        # Copy all registers from the original circuit
        for reg in circuit.qregs:
            qed_circuit.add_register(reg)
        for reg in circuit.cregs:
            qed_circuit.add_register(reg)

        # Add ancilla and syndrome registers for each block
        ancilla_regs = []
        syndrome_regs = []
        for blk_idx in range(len(insertion_depths)):
            from qiskit import QuantumRegister
            anc = QuantumRegister(1, name=f"{self.ancilla_prefix}_{blk_idx}")
            syn = ClassicalRegister(1, name=f"syn_{blk_idx}")
            qed_circuit.add_register(anc)
            qed_circuit.add_register(syn)
            ancilla_regs.append(anc)
            syndrome_regs.append(syn)

        # Rebuild circuit instruction by instruction, inserting QED blocks
        # at the scheduled depth checkpoints
        current_depth = 0
        block_idx = 0
        inserted_at = set()

        for instr in circuit.data:
            qed_circuit.append(instr.operation, instr.qubits, instr.clbits)
            current_depth += 1

            if (
                block_idx < len(insertion_depths)
                and current_depth >= insertion_depths[block_idx]
                and current_depth not in inserted_at
            ):
                inserted_at.add(current_depth)
                # Insert one QED parity check sweep
                anc = ancilla_regs[block_idx]
                syn = syndrome_regs[block_idx]

                qed_circuit.barrier()
                qed_circuit.reset(anc[0])
                qed_circuit.h(anc[0])
                # CNOT from ancilla to each data qubit (first half)
                data_qubits = list(circuit.qubits)
                for dq in data_qubits[: n_data // 2]:
                    qed_circuit.cx(anc[0], dq)
                qed_circuit.h(anc[0])
                qed_circuit.measure(anc[0], syn[0])
                qed_circuit.barrier()

                block_idx += 1

        return qed_circuit
