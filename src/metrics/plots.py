"""
Publication-quality plotting routines reproducing all paper figures (§6).

All figures match the style and colour scheme of the paper.  Figures are
saved to the ``figures/`` directory by default.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

# Consistent colour palette
COLOURS = {
    "baseline":    "#888888",
    "mapper_only": "#E07B39",
    "qed_only":    "#2E9B5F",
    "joint":       "#2B6CB0",
    "superconducting": "#1F78B4",
    "trapped_ion":     "#FF7F00",
    "adversarial":     "#D62728",
}

LABELS = {
    "baseline":    "Baseline (SABRE)",
    "mapper_only": "Compiler Mapping-Only",
    "qed_only":    "QED Scheduling-Only",
    "joint":       "Joint Co-Design System",
}


def _save(fig: plt.Figure, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


class ResultPlotter:
    """Generate all paper figures from a MetricsAggregator summary."""

    def __init__(self, output_dir: str = "figures") -> None:
        self.output_dir = output_dir

    # ------------------------------------------------------------------
    # Fig 5: Success probability vs syndrome frequency
    # ------------------------------------------------------------------

    def plot_success_vs_syndrome_freq(
        self,
        freq_data: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]],
        circuit_name: str = "VQE-H2",
    ) -> None:
        """Plot S vs f for three noise profiles with bootstrap CI bands.

        Parameters
        ----------
        freq_data : dict
            Keys are noise profile names; values are
            (freqs, means, std_errors) arrays.
        """
        fig, ax = plt.subplots(figsize=(7, 4.5))

        markers = {"superconducting": "o", "trapped_ion": "s", "adversarial": "^"}
        labels_map = {
            "superconducting": "IBM Quantum (Superconducting)",
            "trapped_ion": "Trapped-Ion",
            "adversarial": "Adversarial Noise",
        }

        for profile, (freqs, means, stds) in freq_data.items():
            color = COLOURS.get(profile, "black")
            marker = markers.get(profile, "o")
            ax.plot(freqs, means, marker=marker, color=color,
                    label=labels_map.get(profile, profile), linewidth=1.8)
            ax.fill_between(freqs, means - 1.96 * stds, means + 1.96 * stds,
                            color=color, alpha=0.18)

        ax.set_xlabel("Syndrome Measurement Frequency (f)", fontsize=11)
        ax.set_ylabel("Algorithmic Success Probability (S)", fontsize=11)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.legend(fontsize=9)
        ax.grid(True, linestyle="--", alpha=0.4)
        fig.tight_layout()
        _save(fig, f"{self.output_dir}/fig5_success_vs_syndrome_freq_{circuit_name}.pdf")

    # ------------------------------------------------------------------
    # Fig 6: Latency vs success improvement
    # ------------------------------------------------------------------

    def plot_latency_vs_improvement(
        self,
        latency_data: Dict[str, Tuple[np.ndarray, np.ndarray]],
    ) -> None:
        """ΔS vs compilation latency for 8, 12, 16 qubit circuits."""
        fig, ax = plt.subplots(figsize=(7, 4.5))
        styles = {"8":  ("o", "--", "#1F78B4"),
                  "12": ("s", "-.", "#FF7F00"),
                  "16": ("^", ":",  "#2CA02C")}

        for n_qubits, (latencies, delta_s) in latency_data.items():
            m, ls, c = styles.get(str(n_qubits), ("o", "-", "gray"))
            ax.plot(latencies, delta_s, marker=m, linestyle=ls, color=c,
                    label=f"{n_qubits} Qubits", linewidth=1.8)

        ax.set_xlabel("Classical Compilation + Inference Latency (ms)", fontsize=11)
        ax.set_ylabel("Success Probability Improvement (ΔS)", fontsize=11)
        ax.legend(fontsize=10)
        ax.grid(True, linestyle="--", alpha=0.4)
        fig.tight_layout()
        _save(fig, f"{self.output_dir}/fig6_latency_vs_improvement.pdf")

    # ------------------------------------------------------------------
    # Fig 7: Retention-success Pareto scatter
    # ------------------------------------------------------------------

    def plot_pareto_scatter(
        self,
        retention_vals: np.ndarray,
        success_vals: np.ndarray,
        pareto_r: np.ndarray,
        pareto_s: np.ndarray,
        ml_point: Tuple[float, float],
        baseline_point: Tuple[float, float],
    ) -> None:
        """Retention-success Pareto frontier scatter (Fig. 7)."""
        fig, ax = plt.subplots(figsize=(6, 5))

        ax.scatter(retention_vals, success_vals, color="#AAAAAA",
                   alpha=0.5, s=25, label="Explored Parameter Space")
        ax.axvspan(0, 0.05, alpha=0.12, color="#FF7F7F", label="Sampling Failure Zone (R < 5%)")
        ax.plot(pareto_r, pareto_s, color="#FF7F00", linewidth=2.2,
                label="Empirical Pareto Frontier")
        ax.scatter(*baseline_point, marker="X", color="#D62728", s=120, zorder=5,
                   label="Unmitigated Baseline")
        ax.scatter(*ml_point, marker="*", color="#1F78B4", s=200, zorder=6,
                   label="ML-Scheduled Co-Design Node")

        ax.set_xlabel("Post-Selection Retention Fraction (R)", fontsize=11)
        ax.set_ylabel("Algorithm Success Probability (S)", fontsize=11)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.legend(fontsize=8, loc="upper left")
        ax.grid(True, linestyle="--", alpha=0.4)
        fig.tight_layout()
        _save(fig, f"{self.output_dir}/fig7_pareto_scatter.pdf")

    # ------------------------------------------------------------------
    # Fig 8: Ablation bar chart
    # ------------------------------------------------------------------

    def plot_ablation_bars(self, ablation_df: pd.DataFrame) -> None:
        """Per-benchmark ablation bar chart (Fig. 8)."""
        circuits = ablation_df["circuit"].unique()
        configs = ["baseline", "mapper_only", "qed_only", "joint"]
        x = np.arange(len(circuits))
        width = 0.18

        fig, ax = plt.subplots(figsize=(9, 5))
        for i, cfg in enumerate(configs):
            vals = [
                ablation_df.loc[
                    ablation_df["circuit"] == c, cfg
                ].values[0]
                for c in circuits
            ]
            offset = (i - 1.5) * width
            bars = ax.bar(x + offset, vals, width, color=COLOURS[cfg],
                          label=LABELS[cfg])

        ax.set_xticks(x)
        ax.set_xticklabels(circuits, fontsize=11)
        ax.set_ylabel("Success Probability (S)", fontsize=11)
        ax.set_ylim(0, 1)
        ax.legend(fontsize=9)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        fig.tight_layout()
        _save(fig, f"{self.output_dir}/fig8_ablation_bars.pdf")

    # ------------------------------------------------------------------
    # Fig 9: Scaling
    # ------------------------------------------------------------------

    def plot_scaling(
        self,
        qubit_counts: np.ndarray,
        sabre_s: np.ndarray,
        joint_s: np.ndarray,
        depth_vals: np.ndarray,
        ml_s_depth: np.ndarray,
        uniform_s_depth: np.ndarray,
        noqed_s_depth: np.ndarray,
    ) -> None:
        """Qubit-count and depth scaling (Fig. 9a, 9b)."""
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

        # Panel (a): success vs qubit count
        axes[0].plot(qubit_counts, sabre_s, "o--", color=COLOURS["baseline"],
                     label="Baseline (SABRE)", linewidth=1.8)
        axes[0].plot(qubit_counts, joint_s, "o-", color=COLOURS["joint"],
                     label="Joint Co-Design Pipeline", linewidth=1.8)
        axes[0].set_xlabel("Physical Qubit Count", fontsize=11)
        axes[0].set_ylabel("Algorithmic Success Probability (S)", fontsize=11)
        axes[0].legend(fontsize=9)
        axes[0].grid(True, linestyle="--", alpha=0.4)

        # Panel (b): success vs gate depth
        axes[1].plot(depth_vals, ml_s_depth, "-", color="#1F78B4",
                     label="ML-Scheduled Placements", linewidth=1.8)
        axes[1].plot(depth_vals, uniform_s_depth, "-", color="#FF7F00",
                     label="Uniform QED Insertion", linewidth=1.8)
        axes[1].plot(depth_vals, noqed_s_depth, "-", color="#888888",
                     label="No QED Mitigations", linewidth=1.8)
        axes[1].set_xlabel("Gate Depth (Logical Circuit)", fontsize=11)
        axes[1].set_ylabel("Algorithmic Success Probability (S)", fontsize=11)
        axes[1].legend(fontsize=9)
        axes[1].grid(True, linestyle="--", alpha=0.4)

        fig.tight_layout()
        _save(fig, f"{self.output_dir}/fig9_scaling.pdf")

    # ------------------------------------------------------------------
    # Fig 10: Overhead and runtime decomposition
    # ------------------------------------------------------------------

    def plot_overhead_runtime(
        self,
        ancilla_counts: np.ndarray,
        retention_by_circuit: Dict[str, np.ndarray],
        runtime_components: pd.DataFrame,
    ) -> None:
        """Retention vs ancilla count and runtime breakdown (Fig. 10)."""
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

        # Panel (a): retention vs ancilla count
        circ_colors = {"VQE-H2 (8Q)": "#1F78B4", "VQE-LiH (12Q)": "#FF7F00",
                       "QPE-12 (12Q)": "#2CA02C"}
        for label, ret_vals in retention_by_circuit.items():
            c = circ_colors.get(label, "gray")
            axes[0].plot(ancilla_counts, ret_vals, marker="o", color=c,
                         label=label, linewidth=1.8)
        axes[0].axhline(0.05, color="red", linestyle="--", linewidth=1.5,
                        label="Minimum Viable Sampling Floor (5%)")
        axes[0].set_xlabel("Allocated Extraction Ancilla Count", fontsize=11)
        axes[0].set_ylabel("Post-Selection Retention Rate (R)", fontsize=11)
        axes[0].legend(fontsize=8)
        axes[0].grid(True, linestyle="--", alpha=0.4)

        # Panel (b): stacked runtime bar chart
        circuits_list = runtime_components["circuit"].tolist()
        comp_pass = runtime_components["hardware_compilation_pass_ms"].values
        ml_inf = runtime_components["ml_inference_phase_ms"].values
        gpu_sim = runtime_components["gpu_simulation_engine_ms"].values
        io_oh = runtime_components["io_overhead_ms"].values

        x = np.arange(len(circuits_list))
        bar_kw = dict(width=0.5)
        axes[1].bar(x, comp_pass, **bar_kw, label="Hardware Compilation Pass",
                    color="#1F78B4")
        axes[1].bar(x, ml_inf, bottom=comp_pass, **bar_kw,
                    label="ML-Inference Phase", color="#FF7F00")
        axes[1].bar(x, gpu_sim, bottom=comp_pass + ml_inf, **bar_kw,
                    label="GPU Simulation Engine", color="#D62728")
        axes[1].bar(x, io_oh, bottom=comp_pass + ml_inf + gpu_sim, **bar_kw,
                    label="I/O Overhead", color="#AAAAAA")
        axes[1].set_xticks(x); axes[1].set_xticklabels(circuits_list, fontsize=10)
        axes[1].set_ylabel("Execution Latency Breakdown (ms)", fontsize=11)
        axes[1].legend(fontsize=8)
        axes[1].grid(axis="y", linestyle="--", alpha=0.4)

        fig.tight_layout()
        _save(fig, f"{self.output_dir}/fig10_overhead_runtime.pdf")

    # ------------------------------------------------------------------
    # Fig 12: Simulation vs hardware
    # ------------------------------------------------------------------

    def plot_sim_vs_hardware(
        self,
        circuits: List[str],
        sim_s: np.ndarray,
        hw_s: np.ndarray,
    ) -> None:
        """Bar chart comparing simulation against IBM Eagle hardware (Fig. 12)."""
        x = np.arange(len(circuits))
        width = 0.35

        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.bar(x - width / 2, sim_s, width, label="Noisy Simulation Loop",
               color="#1F78B4")
        ax.bar(x + width / 2, hw_s, width, label="Physical Quantum Backend",
               color="#FF7F00")

        ax.set_xticks(x); ax.set_xticklabels(circuits, fontsize=11)
        ax.set_ylabel("Optimised Success Probability (S)", fontsize=11)
        ax.set_ylim(0, 1)
        ax.legend(fontsize=10)
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.text(0.5, -0.13,
                "*Note: Divergence stems from experimental drift and spectators "
                "cross-talk unmodeled in classical simulation.",
                ha="center", transform=ax.transAxes, fontsize=7, color="gray")
        fig.tight_layout()
        _save(fig, f"{self.output_dir}/fig12_sim_vs_hardware.pdf")
