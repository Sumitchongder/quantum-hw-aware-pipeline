"""Metrics aggregation, statistical testing, and plotting utilities."""
from .aggregator import MetricsAggregator
from .statistical_tests import bootstrap_ci, wilcoxon_test
from .plots import ResultPlotter

__all__ = ["MetricsAggregator", "bootstrap_ci", "wilcoxon_test", "ResultPlotter"]
