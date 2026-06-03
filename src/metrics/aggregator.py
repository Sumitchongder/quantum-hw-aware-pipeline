"""
Metrics aggregator: collects per-trial results and computes summary statistics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .statistical_tests import bootstrap_ci, wilcoxon_test


@dataclass
class TrialResult:
    """Single trial outcome for one circuit-noise-configuration combination."""

    circuit: str
    noise_profile: str
    configuration: str  # 'baseline', 'mapper_only', 'qed_only', 'joint'
    success_probability: float
    retention: float
    latency_ms: float
    n_ancilla: int = 0
    syndrome_frequency: float = 0.0
    block_position: int = 0


class MetricsAggregator:
    """Collect trial results and produce summary statistics.

    Parameters
    ----------
    n_bootstrap : int
        Number of bootstrap resamples for CI computation (paper: 10,000).
    alpha : float
        Significance level for confidence intervals (paper: 0.05).
    """

    def __init__(self, n_bootstrap: int = 10_000, alpha: float = 0.05) -> None:
        self.n_bootstrap = n_bootstrap
        self.alpha = alpha
        self._records: List[TrialResult] = []

    def add(self, result: TrialResult) -> None:
        """Append a single trial result."""
        self._records.append(result)

    def add_many(self, results: List[TrialResult]) -> None:
        """Append multiple trial results."""
        self._records.extend(results)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert all records to a pandas DataFrame."""
        return pd.DataFrame([vars(r) for r in self._records])

    def summary(self) -> pd.DataFrame:
        """Return mean ± 95% CI for success probability and retention,
        grouped by (circuit, noise_profile, configuration).

        Mirrors Table 4 of the paper.
        """
        df = self.to_dataframe()
        rows = []
        for (circuit, noise, config), grp in df.groupby(
            ["circuit", "noise_profile", "configuration"]
        ):
            s_vals = grp["success_probability"].values
            r_vals = grp["retention"].values
            lat_vals = grp["latency_ms"].values

            s_mean = float(np.mean(s_vals))
            s_lo, s_hi = bootstrap_ci(s_vals, n_bootstrap=self.n_bootstrap, alpha=self.alpha)

            r_mean = float(np.mean(r_vals))
            r_lo, r_hi = bootstrap_ci(r_vals, n_bootstrap=self.n_bootstrap, alpha=self.alpha)

            lat_median = float(np.median(lat_vals))

            rows.append({
                "circuit": circuit,
                "noise_profile": noise,
                "configuration": config,
                "S_mean": round(s_mean, 3),
                "S_ci_lo": round(s_lo, 3),
                "S_ci_hi": round(s_hi, 3),
                "R_mean": round(r_mean, 3),
                "R_ci_lo": round(r_lo, 3),
                "R_ci_hi": round(r_hi, 3),
                "latency_median_ms": round(lat_median, 1),
                "n_trials": len(grp),
            })

        return pd.DataFrame(rows)

    def wilcoxon_table(self, baseline: str = "baseline") -> pd.DataFrame:
        """Run paired Wilcoxon signed-rank tests comparing each non-baseline
        configuration against the *baseline* for every (circuit, noise) group.

        Returns
        -------
        pd.DataFrame
            Columns: circuit, noise_profile, configuration, statistic, p_value.
        """
        df = self.to_dataframe()
        rows = []
        for (circuit, noise), grp in df.groupby(["circuit", "noise_profile"]):
            base_vals = grp[grp["configuration"] == baseline]["success_probability"].values
            if len(base_vals) == 0:
                continue
            for config, sub in grp.groupby("configuration"):
                if config == baseline:
                    continue
                alt_vals = sub["success_probability"].values
                n = min(len(base_vals), len(alt_vals))
                if n < 2:
                    continue
                stat, p = wilcoxon_test(base_vals[:n], alt_vals[:n])
                rows.append({
                    "circuit": circuit,
                    "noise_profile": noise,
                    "configuration": config,
                    "statistic": stat,
                    "p_value": p,
                    "significant_p01": p < 0.01,
                })
        return pd.DataFrame(rows)

    def save_csv(self, path: str) -> None:
        """Save the raw trial records to a CSV file."""
        self.to_dataframe().to_csv(path, index=False)

    def load_csv(self, path: str) -> None:
        """Load trial records from a CSV file."""
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            self._records.append(TrialResult(**row.to_dict()))
