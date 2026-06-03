"""
Hardware-Aware Mapping Pass — Algorithm 1 of the paper.

Implements:
  1. Subgraph-isomorphism warm-start allocation.
  2. Simulated annealing (SA) outer loop with ILP kernel for sub-circuits
     of width <= w (default w = 10).
  3. Latency-aware penalty for budget overruns.

The pass is a Qiskit TranspilerPass subclass and integrates directly into
the Qiskit transpiler pipeline via ``PassManager``.
"""

from __future__ import annotations

import copy
import math
import random
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
from qiskit.dagcircuit import DAGCircuit
from qiskit.transpiler import TranspilerError
from qiskit.transpiler.basepasses import TransformationPass
from qiskit.transpiler.layout import Layout

try:
    from scipy.optimize import linprog
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

from .cost_computation import NoiseWeightedCost


class HardwareAwareMappingPass(TransformationPass):
    """Noise-weighted SA + ILP qubit mapping pass.

    Parameters
    ----------
    coupling_map : list of (int, int)
        Physical device edges (undirected).
    gate_fidelities : dict
        Map from physical edge ``(p, q)`` to two-qubit gate fidelity.
    single_qubit_fidelities : dict
        Map from physical qubit index to single-qubit gate fidelity.
    t1_times : dict
        T1 relaxation times (µs) per physical qubit.
    t2_times : dict
        T2 dephasing times (µs) per physical qubit.
    latency_budget : float
        Maximum end-to-end latency (ms).
    latency_penalty : float
        Penalty coefficient *beta* for latency overruns.
    T0 : float
        Initial SA temperature.
    alpha : float
        SA cooling rate (geometric schedule).
    n_iter : int
        Number of SA iterations.
    ilp_window : int
        Maximum sub-circuit width for the ILP kernel (w in the paper, ≤ 10).
    seed : int
        Random seed for reproducibility.
    """

    def __init__(
        self,
        coupling_map: List[Tuple[int, int]],
        gate_fidelities: Dict[Tuple[int, int], float],
        single_qubit_fidelities: Dict[int, float],
        t1_times: Optional[Dict[int, float]] = None,
        t2_times: Optional[Dict[int, float]] = None,
        latency_budget: float = 1000.0,
        latency_penalty: float = 1e3,
        T0: float = 1.0,
        alpha: float = 0.995,
        n_iter: int = 5000,
        ilp_window: int = 10,
        seed: int = 42,
    ) -> None:
        super().__init__()
        self.coupling_map = coupling_map
        self.gate_fidelities = gate_fidelities
        self.single_qubit_fidelities = single_qubit_fidelities
        self.t1_times = t1_times or {}
        self.t2_times = t2_times or {}
        self.latency_budget = latency_budget
        self.latency_penalty = latency_penalty
        self.T0 = T0
        self.alpha = alpha
        self.n_iter = n_iter
        self.ilp_window = ilp_window
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)

        # Build adjacency structures
        self._physical_qubits: List[int] = sorted(
            {q for edge in coupling_map for q in edge}
        )
        self._neighbours: Dict[int, List[int]] = {q: [] for q in self._physical_qubits}
        for u, v in coupling_map:
            self._neighbours[u].append(v)
            self._neighbours[v].append(u)

    # ------------------------------------------------------------------
    # Subgraph-isomorphism warm start (heuristic version)
    # ------------------------------------------------------------------

    def _warm_start_mapping(self, dag: DAGCircuit) -> Dict[int, int]:
        """Place frequently-interacting logical qubit pairs on high-fidelity
        device edges (greedy subgraph matching).

        Returns
        -------
        dict
            Initial logical-to-physical mapping.
        """
        logical_qubits = list(range(dag.num_qubits()))
        if len(logical_qubits) > len(self._physical_qubits):
            raise TranspilerError(
                f"Circuit has {len(logical_qubits)} qubits but device has "
                f"only {len(self._physical_qubits)} physical qubits."
            )

        # Count two-qubit interaction frequency between logical qubits
        interaction: Dict[Tuple[int, int], int] = {}
        for layer in dag.layers():
            for node in layer["graph"].op_nodes():
                if len(node.qargs) == 2:
                    q0, q1 = node.qargs[0]._index, node.qargs[1]._index
                    key = (min(q0, q1), max(q0, q1))
                    interaction[key] = interaction.get(key, 0) + 1

        # Sort logical pairs by frequency (descending)
        sorted_pairs = sorted(interaction, key=interaction.get, reverse=True)

        # Sort physical edges by two-qubit fidelity (descending)
        sorted_phys_edges = sorted(
            self.gate_fidelities,
            key=self.gate_fidelities.get,
            reverse=True,
        )

        mapping: Dict[int, int] = {}
        used_phys: set = set()

        for lq_pair, phys_edge in zip(sorted_pairs, sorted_phys_edges):
            lq0, lq1 = lq_pair
            pq0, pq1 = phys_edge
            if lq0 not in mapping and pq0 not in used_phys:
                mapping[lq0] = pq0
                used_phys.add(pq0)
            if lq1 not in mapping and pq1 not in used_phys:
                mapping[lq1] = pq1
                used_phys.add(pq1)

        # Assign remaining logical qubits to unused physical qubits
        available_phys = [p for p in self._physical_qubits if p not in used_phys]
        self.rng.shuffle(available_phys)
        for lq in logical_qubits:
            if lq not in mapping:
                if not available_phys:
                    raise TranspilerError("Ran out of physical qubits during warm start.")
                mapping[lq] = available_phys.pop(0)

        return mapping

    # ------------------------------------------------------------------
    # ILP kernel for small sub-circuits
    # ------------------------------------------------------------------

    def _ilp_local_opt(
        self,
        sub_logical_qubits: List[int],
        current_mapping: Dict[int, int],
        cost_fn: NoiseWeightedCost,
    ) -> Dict[int, int]:
        """Exhaustively search over all permutations of the physical qubits
        currently assigned to *sub_logical_qubits* to find the locally
        optimal sub-mapping.

        The window is bounded to ``ilp_window <= 10`` qubits, keeping the
        search space at most 10! = 3,628,800 — but in practice we sample a
        Monte Carlo subset when |sub| > 8.

        Returns
        -------
        dict
            Updated mapping (full mapping with the sub-circuit fragment
            replaced by the locally optimal assignment).
        """
        import itertools

        w = len(sub_logical_qubits)
        if w == 0:
            return current_mapping

        # Physical qubits currently used by this sub-circuit
        current_phys = [current_mapping[lq] for lq in sub_logical_qubits]

        best_mapping = copy.copy(current_mapping)
        best_cost = cost_fn(current_mapping)

        # For w <= 8 try all permutations; for w in (8, 10] random sample
        perms: list
        if w <= 8:
            perms = list(itertools.permutations(current_phys))
        else:
            seen: set = set()
            perms = []
            for _ in range(512):
                p = tuple(self.np_rng.permutation(current_phys).tolist())
                if p not in seen:
                    seen.add(p)
                    perms.append(p)

        for perm in perms:
            candidate = copy.copy(current_mapping)
            for lq, pq in zip(sub_logical_qubits, perm):
                candidate[lq] = pq
            c = cost_fn(candidate)
            if c < best_cost:
                best_cost = c
                best_mapping = candidate

        return best_mapping

    # ------------------------------------------------------------------
    # Latency estimator
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_latency(dag: DAGCircuit, n_swaps: int) -> float:
        """Rough latency estimate (ms): proportional to circuit depth plus
        SWAP overhead (each SWAP ≈ 3 CNOT gates at ~0.5 µs each).
        """
        depth = dag.depth()
        gate_time_us = 0.5  # typical CNOT gate time in µs
        swap_overhead_us = n_swaps * 3 * gate_time_us
        return (depth * gate_time_us + swap_overhead_us) / 1000.0  # convert to ms

    # ------------------------------------------------------------------
    # Simulated Annealing main loop
    # ------------------------------------------------------------------

    def _simulated_annealing(
        self,
        dag: DAGCircuit,
        initial_mapping: Dict[int, int],
        cost_fn: NoiseWeightedCost,
    ) -> Dict[int, int]:
        """Run the SA outer loop (Algorithm 1, lines 2-13).

        Parameters
        ----------
        dag :
            Logical circuit DAG.
        initial_mapping :
            Starting mapping from warm-start.
        cost_fn :
            Callable noise-weighted cost function.

        Returns
        -------
        dict
            Optimised logical-to-physical mapping.
        """
        logical_qubits = list(range(dag.num_qubits()))
        mapping = copy.copy(initial_mapping)
        current_cost = cost_fn(mapping)
        best_mapping = copy.copy(mapping)
        best_cost = current_cost

        T = self.T0
        n_swaps_est = 0  # running estimate of SWAP count

        for i in range(self.n_iter):
            # Propose neighbour: swap two random logical qubits
            if len(logical_qubits) < 2:
                break
            lq_a, lq_b = self.rng.sample(logical_qubits, 2)
            new_mapping = copy.copy(mapping)
            new_mapping[lq_a], new_mapping[lq_b] = mapping[lq_b], mapping[lq_a]

            # ILP refinement for small sub-circuits
            sub = [lq_a, lq_b]
            if len(sub) <= self.ilp_window and _HAS_SCIPY:
                new_mapping = self._ilp_local_opt(sub, new_mapping, cost_fn)

            delta = cost_fn(new_mapping) - current_cost

            # Metropolis acceptance criterion
            if delta <= 0 or self.rng.random() < math.exp(-delta / max(T, 1e-12)):
                mapping = new_mapping
                current_cost = cost_fn(mapping)

                # Latency penalty check (line 10 of Algorithm 1)
                lat_est = self._estimate_latency(dag, n_swaps_est)
                if lat_est > self.latency_budget:
                    current_cost += self.latency_penalty * (
                        lat_est - self.latency_budget
                    )

                if current_cost < best_cost:
                    best_cost = current_cost
                    best_mapping = copy.copy(mapping)

            # Geometric cooling
            T *= self.alpha

        return best_mapping

    # ------------------------------------------------------------------
    # TranspilerPass entry point
    # ------------------------------------------------------------------

    def run(self, dag: DAGCircuit) -> DAGCircuit:
        """Execute the mapping pass on *dag*.

        Sets ``self.property_set['layout']`` so downstream Qiskit passes
        can use the computed mapping.

        Returns
        -------
        DAGCircuit
            The input DAG (mapping is stored in property_set, not yet
            physically applied; SWAP insertion is handled by SwapInserter).
        """
        if dag.num_qubits() == 0:
            return dag

        cost_fn = NoiseWeightedCost(
            dag=dag,
            gate_fidelities=self.gate_fidelities,
            single_qubit_fidelities=self.single_qubit_fidelities,
            latency_budget=self.latency_budget,
            latency_penalty=self.latency_penalty,
        )

        t_start = time.perf_counter()

        # Step 1: Warm-start
        initial_mapping = self._warm_start_mapping(dag)

        # Step 2: SA + ILP
        optimised_mapping = self._simulated_annealing(dag, initial_mapping, cost_fn)

        t_elapsed_ms = (time.perf_counter() - t_start) * 1e3

        # Store layout in property_set for Qiskit compatibility
        layout = Layout()
        for logical_idx, physical_idx in optimised_mapping.items():
            qubit = dag.qubits[logical_idx]
            layout[qubit] = physical_idx
        self.property_set["layout"] = layout
        self.property_set["hw_mapping"] = optimised_mapping
        self.property_set["mapping_latency_ms"] = t_elapsed_ms
        self.property_set["mapping_cost"] = cost_fn(optimised_mapping)

        return dag
