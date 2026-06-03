"""
QED scheduler inference module (§4.2 — Algorithm 2 lines 2-9).

Loads a trained checkpoint and returns the Pareto-optimal syndrome
schedule (f*, p*) within the latency and ancilla budget.
"""

from __future__ import annotations

import pickle
import time
from typing import Dict, List, Optional, Tuple

import numpy as np


class QEDSchedulerInference:
    """Lightweight inference wrapper around the trained XGBoost models.

    Parameters
    ----------
    checkpoint_path : str
        Path to the ``.pkl`` model checkpoint saved by ``QEDSchedulerTrainer``.
    lambda_ret : float
        Retention penalty weight *lambda* (paper: 0.8).
    mu_lat : float
        Latency overrun penalty weight *mu* (paper: 5e-4).
    latency_budget : float
        Maximum allowed total latency (ms).
    """

    # Candidate syndrome schedules Q = {f} x {p} (§4.2)
    FREQ_CANDIDATES: List[float] = [0.0, 0.25, 0.50, 0.75, 1.0]
    POS_CANDIDATES: List[int] = [0, 1, 2, 3]

    def __init__(
        self,
        checkpoint_path: str,
        lambda_ret: float = 0.8,
        mu_lat: float = 5e-4,
        latency_budget: float = 1000.0,
    ) -> None:
        with open(checkpoint_path, "rb") as fh:
            payload = pickle.load(fh)
        self.model_delta_s = payload["model_delta_s"]
        self.model_R = payload["model_R"]
        self.lambda_ret = lambda_ret
        self.mu_lat = mu_lat
        self.latency_budget = latency_budget

    # ------------------------------------------------------------------

    @staticmethod
    def _encode_candidate(f: float, p: int) -> np.ndarray:
        """Encode a (f, p) candidate as a 2-D feature extension."""
        return np.array([f, float(p)], dtype=np.float64)

    def _utility(
        self,
        delta_s_hat: float,
        R_hat: float,
        base_latency: float,
        delta_latency: float,
    ) -> float:
        """Compute U(f, p) = Delta_S - lambda*(1-R) - mu*max(0, L_delta-L_max).

        Equation (3) of the paper.
        """
        latency_overrun = max(0.0, base_latency + delta_latency - self.latency_budget)
        return (
            delta_s_hat
            - self.lambda_ret * (1.0 - R_hat)
            - self.mu_lat * latency_overrun
        )

    def predict(
        self,
        base_features: np.ndarray,
        base_latency: float = 0.0,
        delta_latency_per_block: float = 5.0,
    ) -> Tuple[float, int, float]:
        """Find the feasible (f*, p*) maximising U(f, p).

        Parameters
        ----------
        base_features : np.ndarray, shape (6,)
            Circuit feature vector from ``FeatureExtractor.extract()``.
        base_latency : float
            Current compilation + execution latency estimate (ms).
        delta_latency_per_block : float
            Additional latency (ms) per QED block inserted.

        Returns
        -------
        f_star : float
            Optimal syndrome measurement frequency.
        p_star : int
            Optimal block insertion position index.
        utility_star : float
            Utility of the selected configuration.
        """
        t0 = time.perf_counter()

        best_f, best_p, best_u = 0.0, 0, -np.inf
        for f in self.FREQ_CANDIDATES:
            for p in self.POS_CANDIDATES:
                extra = self._encode_candidate(f, p)
                X_q = np.concatenate([base_features, extra]).reshape(1, -1)

                delta_s_hat = float(self.model_delta_s.predict(X_q)[0])
                R_hat = float(self.model_R.predict(X_q)[0])
                # Clamp predictions to valid ranges
                delta_s_hat = max(delta_s_hat, 0.0)
                R_hat = min(max(R_hat, 0.0), 1.0)

                # Check latency feasibility (Algorithm 2, line 5)
                delta_lat = delta_latency_per_block * (p + 1)
                if base_latency + delta_lat > self.latency_budget:
                    continue  # infeasible

                u = self._utility(delta_s_hat, R_hat, base_latency, delta_lat)
                if u > best_u:
                    best_u = u
                    best_f = f
                    best_p = p

        inference_ms = (time.perf_counter() - t0) * 1e3
        # Paper reports inference latency <= 6 ms
        assert inference_ms < 60.0, f"Inference took {inference_ms:.1f} ms (expected < 60 ms)"

        return best_f, best_p, best_u

    def feature_importance(self) -> Dict[str, float]:
        """Return feature importances for M_delta_S (Fig. 11a of the paper)."""
        names = [
            "two_qubit_gate_count",
            "critical_path_depth",
            "connectivity_entropy",
            "mean_local_gate_fidelity",
            "qubit_allocation_ratio",
            "idle_coherence_coeff",
            "syndrome_frequency_f",
            "block_position_p",
        ]
        importances = self.model_delta_s.feature_importances_
        return dict(zip(names, importances.tolist()))
