"""
Bootstrap confidence intervals and Wilcoxon signed-rank tests.

Used throughout §6 to produce 95% CIs and verify statistical significance
at p < 0.01 (n = 100 paired trials, B = 10,000 bootstrap resamples).
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
from scipy.stats import wilcoxon


def bootstrap_ci(
    data: np.ndarray,
    n_bootstrap: int = 10_000,
    alpha: float = 0.05,
    statistic: callable = np.mean,
    seed: int = 42,
) -> Tuple[float, float]:
    """Compute a percentile bootstrap confidence interval.

    Parameters
    ----------
    data : np.ndarray, shape (n,)
        Observed sample.
    n_bootstrap : int
        Number of bootstrap resamples (paper: 10,000).
    alpha : float
        Significance level (paper: 0.05 → 95% CI).
    statistic : callable
        Summary statistic to bootstrap (default: mean).
    seed : int
        NumPy RNG seed.

    Returns
    -------
    lower : float
    upper : float
        Lower and upper bounds of the (1 - alpha) CI.
    """
    rng = np.random.default_rng(seed)
    data = np.asarray(data, dtype=float)
    n = len(data)
    if n == 0:
        return (0.0, 0.0)

    bootstrap_stats = np.array([
        statistic(rng.choice(data, size=n, replace=True))
        for _ in range(n_bootstrap)
    ])

    lower = float(np.percentile(bootstrap_stats, 100 * alpha / 2))
    upper = float(np.percentile(bootstrap_stats, 100 * (1 - alpha / 2)))
    return lower, upper


def wilcoxon_test(
    baseline: np.ndarray,
    alternative: np.ndarray,
    alternative_hypothesis: str = "two-sided",
) -> Tuple[float, float]:
    """Paired Wilcoxon signed-rank test.

    Parameters
    ----------
    baseline : np.ndarray
        Success probabilities under the baseline configuration.
    alternative : np.ndarray
        Success probabilities under the alternative configuration.
    alternative_hypothesis : str
        One of ``'two-sided'``, ``'greater'``, ``'less'``.

    Returns
    -------
    statistic : float
    p_value : float
    """
    baseline = np.asarray(baseline, dtype=float)
    alternative = np.asarray(alternative, dtype=float)

    if len(baseline) != len(alternative):
        raise ValueError(
            f"Arrays must be the same length; got {len(baseline)} vs {len(alternative)}."
        )

    result = wilcoxon(baseline, alternative, alternative=alternative_hypothesis)
    return float(result.statistic), float(result.pvalue)
