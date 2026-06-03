"""
Noise-weighted mapping cost function (Eq. 2 of the paper).

Cost(m) = sum_{g in Gates} w_g * (1 - F_hat_g(m))

where F_hat_g(m) is the expected fidelity of gate g under mapping m and w_g
is the critical-path importance weight.  Under independent Depolarising noise
with per-gate error rate epsilon_g = 1 - F_hat_g(m), minimising Cost(m)
minimises a first-order upper bound on circuit infidelity (Proposition 1).
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np
from qiskit.circuit import QuantumCircuit
from qiskit.dagcircuit import DAGCircuit
from qiskit.converters import circuit_to_dag


class NoiseWeightedCost:
    """Compute the noise-weighted mapping cost for a given qubit mapping.

    Parameters
    ----------
    dag : DAGCircuit
        Logical circuit in DAG form.
    gate_fidelities : dict
        Mapping from physical edge ``(p, q)`` to two-qubit gate fidelity.
    single_qubit_fidelities : dict
        Mapping from physical qubit index to single-qubit gate fidelity.
    latency_budget : float
        Maximum allowed end-to-end latency (milliseconds).  Proposals that
        exceed this budget receive a penalty proportional to the overrun.
    latency_penalty : float
        Penalty coefficient *beta* for latency overruns.
    """

    def __init__(
        self,
        dag: DAGCircuit,
        gate_fidelities: Dict[Tuple[int, int], float],
        single_qubit_fidelities: Dict[int, float],
        latency_budget: float = 1000.0,
        latency_penalty: float = 1e3,
    ) -> None:
        self.dag = dag
        self.gate_fidelities = gate_fidelities
        self.single_qubit_fidelities = single_qubit_fidelities
        self.latency_budget = latency_budget
        self.latency_penalty = latency_penalty

        # Compute critical-path weights once; they are independent of mapping.
        self._critical_path_weights: Dict[str, float] = {}
        self._compute_critical_path_weights()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_critical_path_weights(self) -> None:
        """Assign importance weights based on critical-path position.

        Gates on the critical path receive weight 1.0; gates one layer off
        the critical path receive a geometrically decayed weight.  This
        tightens the first-order infidelity bound for deep circuits (§3).
        """
        # Topological layers (front-to-back)
        layers = list(self.dag.layers())
        n_layers = len(layers)
        if n_layers == 0:
            return

        # Critical path length (number of layers)
        cp_len = n_layers

        for layer_idx, layer in enumerate(layers):
            # Weight decays as we move away from the critical path midpoint.
            # Nodes closest to the centre of the critical path get weight 1.
            distance_from_cp = abs(layer_idx - cp_len // 2)
            weight = math.exp(-0.1 * distance_from_cp)
            for node in layer["graph"].op_nodes():
                self._critical_path_weights[node.name + str(id(node))] = weight

    def _expected_fidelity(
        self, node, mapping: Dict[int, int]
    ) -> float:
        """Return the expected fidelity of *node* under *mapping*.

        Parameters
        ----------
        node :
            A DAG operation node.
        mapping : dict
            Logical-to-physical qubit mapping ``{logical: physical}``.
        """
        qargs = node.qargs
        if len(qargs) == 2:
            logical_q0 = qargs[0]._index
            logical_q1 = qargs[1]._index
            phys_q0 = mapping.get(logical_q0, logical_q0)
            phys_q1 = mapping.get(logical_q1, logical_q1)
            edge = (min(phys_q0, phys_q1), max(phys_q0, phys_q1))
            return self.gate_fidelities.get(edge, 0.99)
        elif len(qargs) == 1:
            logical_q = qargs[0]._index
            phys_q = mapping.get(logical_q, logical_q)
            return self.single_qubit_fidelities.get(phys_q, 0.999)
        else:
            # Measurement or barrier — fidelity 1 (not contributing to cost)
            return 1.0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def __call__(
        self,
        mapping: Dict[int, int],
        estimated_latency: float = 0.0,
    ) -> float:
        """Compute Cost(m) for the given logical-to-physical *mapping*.

        Parameters
        ----------
        mapping : dict
            Logical-to-physical qubit assignment.
        estimated_latency : float
            Estimated end-to-end latency (ms) for the current routing state.

        Returns
        -------
        float
            Scalar cost value (lower is better).
        """
        total_cost = 0.0
        for layer in self.dag.layers():
            for node in layer["graph"].op_nodes():
                if node.name in ("barrier", "measure", "reset"):
                    continue
                key = node.name + str(id(node))
                w_g = self._critical_path_weights.get(key, 1.0)
                f_hat = self._expected_fidelity(node, mapping)
                total_cost += w_g * (1.0 - f_hat)

        # Latency penalty (Eq. in §4.1)
        if estimated_latency > self.latency_budget:
            total_cost += self.latency_penalty * (
                estimated_latency - self.latency_budget
            )

        return total_cost

    def incremental_cost(
        self,
        node,
        mapping: Dict[int, int],
    ) -> float:
        """Cost contribution from a single gate node under *mapping*.

        Useful for computing delta-cost during the SA inner loop without
        re-evaluating the entire circuit.
        """
        if node.name in ("barrier", "measure", "reset"):
            return 0.0
        key = node.name + str(id(node))
        w_g = self._critical_path_weights.get(key, 1.0)
        f_hat = self._expected_fidelity(node, mapping)
        return w_g * (1.0 - f_hat)

    def first_order_infidelity_bound(self, mapping: Dict[int, int]) -> float:
        """Return the first-order Depolarising infidelity bound (Proposition 1).

        1 - prod_g F_hat_g(m)  ~=  sum_g epsilon_g  =  Cost(m)|_{w_g=1}
        """
        product = 1.0
        for layer in self.dag.layers():
            for node in layer["graph"].op_nodes():
                if node.name in ("barrier", "measure", "reset"):
                    continue
                f_hat = self._expected_fidelity(node, mapping)
                product *= f_hat
        return 1.0 - product
