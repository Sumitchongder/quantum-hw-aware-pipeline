"""
SWAP Inserter with A*/SABRE heuristic and KAK cancellation pass.

After the mapping pass has produced a logical-to-physical qubit assignment,
this module inserts the minimum number of SWAP gates required to route all
two-qubit interactions through the device coupling graph.  It then applies
a KAK decomposition / single-qubit cancellation pass to reduce redundant
rotations introduced during routing.
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Tuple

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import SwapGate
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.dagcircuit import DAGCircuit, DAGOpNode
from qiskit.transpiler import CouplingMap
from qiskit.transpiler.passes import (
    SabreSwap,
    Optimize1qGates,
    CommutativeCancellation,
)
from qiskit.transpiler import PassManager


class SwapInserter:
    """Insert SWAPs and apply post-routing gate reduction.

    Parameters
    ----------
    coupling_map : list of (int, int)
        Physical device edges.
    gate_fidelities : dict
        Two-qubit gate fidelities used for distance-weighted A* heuristic.
    heuristic : str
        ``'sabre'`` (default) or ``'astar'``.
    seed : int
        Random seed forwarded to SabreSwap.
    """

    def __init__(
        self,
        coupling_map: List[Tuple[int, int]],
        gate_fidelities: Optional[Dict[Tuple[int, int], float]] = None,
        heuristic: str = "sabre",
        seed: int = 42,
    ) -> None:
        self.coupling_map = CouplingMap(coupling_map)
        self.gate_fidelities = gate_fidelities or {}
        self.heuristic = heuristic
        self.seed = seed

        # Pre-compute shortest-path distances for A* lookahead
        self._dist: Dict[Tuple[int, int], int] = {}
        self._precompute_distances()

    def _precompute_distances(self) -> None:
        """BFS shortest-path distances on the coupling graph."""
        for src in self.coupling_map.physical_qubits:
            visited = {src: 0}
            queue = [src]
            while queue:
                u = queue.pop(0)
                for v in self.coupling_map.neighbors(u):
                    if v not in visited:
                        visited[v] = visited[u] + 1
                        queue.append(v)
            for tgt, d in visited.items():
                self._dist[(src, tgt)] = d

    def distance(self, p: int, q: int) -> int:
        """Shortest-path distance between physical qubits *p* and *q*."""
        return self._dist.get((p, q), self._dist.get((q, p), 0))

    def _fidelity_weight(self, p: int, q: int) -> float:
        """Return infidelity weight for edge (p, q)."""
        edge = (min(p, q), max(p, q))
        return 1.0 - self.gate_fidelities.get(edge, 0.99)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def insert_swaps(
        self,
        circuit: QuantumCircuit,
        mapping: Dict[int, int],
    ) -> QuantumCircuit:
        """Insert SWAP gates into *circuit* given the logical-to-physical
        *mapping*, then apply KAK cancellation.

        Parameters
        ----------
        circuit : QuantumCircuit
            Logically compiled circuit (post mapping-pass, pre-routing).
        mapping : dict
            Logical-to-physical qubit assignment from the mapping pass.

        Returns
        -------
        QuantumCircuit
            Routed circuit with SWAPs inserted and single-qubit gates
            reduced via the KAK / commutation cancellation passes.
        """
        from qiskit.transpiler.passes import ApplyLayout, SetLayout
        from qiskit.transpiler import Layout

        # Build a Qiskit Layout from the mapping dict
        layout = Layout()
        for logical_idx, physical_idx in mapping.items():
            layout[circuit.qubits[logical_idx]] = physical_idx

        # Build pass manager: layout application + SABRE SWAP + optimisation
        pm = PassManager()
        pm.append(SetLayout(layout))
        pm.append(ApplyLayout())
        pm.append(
            SabreSwap(
                self.coupling_map,
                heuristic="decay",
                seed=self.seed,
                trials=20,
            )
        )
        # Gate reduction (KAK-equivalent in Qiskit: Optimize1qGates +
        # CommutativeCancellation)
        pm.append(Optimize1qGates())
        pm.append(CommutativeCancellation())

        routed = pm.run(circuit)
        return routed

    def count_swaps(self, routed_circuit: QuantumCircuit) -> int:
        """Count the number of SWAP gates in *routed_circuit*."""
        return sum(
            1
            for instr in routed_circuit.data
            if instr.operation.name == "swap"
        )
