"""
plots.py
--------
Publication-quality matplotlib figures for the stimulus generalization
experiment.  All figures use a clean, minimal style suitable for journal
submission: white background, minimal gridlines, serif font.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Union

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import seaborn as sns

# ---------------------------------------------------------------------------
# Global style
# ---------------------------------------------------------------------------

_STYLE_APPLIED = False


def _apply_style() -> None:
    """Set matplotlib rcParams for publication-quality output."""
    global _STYLE_APPLIED
    if _STYLE_APPLIED:
        return
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#333333",
            "axes.grid": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.transparent": False,
        }
    )
    _STYLE_APPLIED = True


def _ensure_output_dir(output_dir: Union[str, Path]) -> Path:
    """Create the output directory if it does not exist."""
    p = Path(output_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
# Individual gradient
# ---------------------------------------------------------------------------


def plot_individual_gradient(
    df: pd.DataFrame,
    participant_id: str,
    phase_id: Optional[str] = None,
    output_dir: Union[str, Path] = "../outputs",
    show: bool = False,
) -> Path:
    """Plot the generalization gradient for a single participant.

    Parameters
    ----------
    df : pd.DataFrame
        Trial-level data (all participants is fine; filtered internally).
    participant_id : str
        The participant whose gradient to plot.
    phase_id : str, optional
        Restrict to a specific phase.
    output_dir : str or Path
        Directory in which to save the figure.
    show : bool
        If True, call ``plt.show()`` (useful in notebooks).

    Returns
    -------
    Path
        Path to the saved figure.
    """
    _apply_style()
    from .gradients import compute_gradient

    pdata = df.loc[df["participant_id"] == participant_id]
    grad = compute_gradient(pdata, phase_id=phase_id)

    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.plot(
        grad["stimulus_x"],
        grad["response_probability"],
        marker="o",
        markersize=5,
        linewidth=1.5,
        color="#2c7bb6",
    )
    ax.fill_between(
        grad["stimulus_x"],
        grad["ci_lower"],
        grad["ci_upper"],
        alpha=0.2,
        color="#2c7bb6",
    )
    ax.set_xlabel("Stimulus position (normalized)")
    ax.set_ylabel("P(response)")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title(f"Gradient -- {participant_id}")

    out = _ensure_output_dir(output_dir)
    fname = out / f"gradient_individual_{participant_id}.png"
    fig.savefig(fname)
    if show:
        plt.show()
    plt.close(fig)
    return fname


# ---------------------------------------------------------------------------
# Group gradient
# ---------------------------------------------------------------------------


def plot_group_gradient(
    gradient_df: pd.DataFrame,
    output_dir: Union[str, Path] = "../outputs",
    show: bool = False,
) -> Path:
    """Plot the group-mean generalization gradient with error bands.

    Parameters
    ----------
    gradient_df : pd.DataFrame
        Output of ``gradients.group_mean_gradient``.
    output_dir : str or Path
        Directory in which to save the figure.
    show : bool
        If True, call ``plt.show()``.

    Returns
    -------
    Path
        Path to the saved figure.
    """
    _apply_style()

    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.plot(
        gradient_df["stimulus_x"],
        gradient_df["response_probability"],
        marker="o",
        markersize=5,
        linewidth=1.8,
        color="#d7191c",
        label="Group mean",
    )
    ax.fill_between(
        gradient_df["stimulus_x"],
        gradient_df["ci_lower"],
        gradient_df["ci_upper"],
        alpha=0.2,
        color="#d7191c",
        label="95% CI",
    )
    ax.set_xlabel("Stimulus position (normalized)")
    ax.set_ylabel("P(response)")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Group generalization gradient")
    ax.legend(frameon=False)

    out = _ensure_output_dir(output_dir)
    fname = out / "gradient_group.png"
    fig.savefig(fname)
    if show:
        plt.show()
    plt.close(fig)
    return fname


# ---------------------------------------------------------------------------
# Gradient evolution over blocks
# ---------------------------------------------------------------------------


def plot_gradient_evolution(
    gradient_by_block_df: pd.DataFrame,
    output_dir: Union[str, Path] = "../outputs",
    show: bool = False,
) -> Path:
    """Plot how the gradient changes across blocks as a heatmap.

    Parameters
    ----------
    gradient_by_block_df : pd.DataFrame
        Output of ``gradients.compute_gradient_by_block``.
    output_dir : str or Path
        Directory in which to save the figure.
    show : bool
        If True, call ``plt.show()``.

    Returns
    -------
    Path
        Path to the saved figure.
    """
    _apply_style()

    pivot = gradient_by_block_df.pivot_table(
        index="block",
        columns="stimulus_x",
        values="response_probability",
        aggfunc="mean",
    )

    fig, ax = plt.subplots(figsize=(7, 4))
    im = ax.imshow(
        pivot.values,
        aspect="auto",
        origin="lower",
        cmap="YlOrRd",
        vmin=0,
        vmax=1,
        interpolation="nearest",
    )
    # Axis labels
    xticks = np.arange(pivot.shape[1])
    ax.set_xticks(xticks)
    ax.set_xticklabels([f"{v:.2f}" for v in pivot.columns], rotation=45, ha="right")
    yticks = np.arange(pivot.shape[0])
    ax.set_yticks(yticks)
    ax.set_yticklabels([int(b) for b in pivot.index])
    ax.set_xlabel("Stimulus position (normalized)")
    ax.set_ylabel("Block")
    ax.set_title("Gradient evolution over blocks")
    cbar = fig.colorbar(im, ax=ax, label="P(response)")

    out = _ensure_output_dir(output_dir)
    fname = out / "gradient_evolution.png"
    fig.savefig(fname)
    if show:
        plt.show()
    plt.close(fig)
    return fname


# ---------------------------------------------------------------------------
# Response heatmap
# ---------------------------------------------------------------------------


def plot_response_heatmap(
    df: pd.DataFrame,
    block_size: int = 20,
    output_dir: Union[str, Path] = "../outputs",
    show: bool = False,
) -> Path:
    """Heatmap with stimulus on x-axis, block on y-axis, color = P(response).

    Parameters
    ----------
    df : pd.DataFrame
        Trial-level data (single participant or pooled).
    block_size : int
        Trials per block.
    output_dir : str or Path
        Where to save the figure.
    show : bool
        If True, call ``plt.show()``.

    Returns
    -------
    Path
        Path to the saved figure.
    """
    _apply_style()

    df = df.copy()
    trial_idx = pd.to_numeric(df["trial_index_global"], errors="coerce")
    df["_block"] = (trial_idx // block_size).astype("Int64")
    stim = pd.to_numeric(df["stimulus_x_normalized"], errors="coerce")
    resp = df["response_occurred"].fillna(False).astype(float)

    pivot = (
        pd.DataFrame({"block": df["_block"], "stimulus_x": stim, "response": resp})
        .groupby(["block", "stimulus_x"])["response"]
        .mean()
        .reset_index()
        .pivot_table(index="block", columns="stimulus_x", values="response", aggfunc="mean")
    )

    fig, ax = plt.subplots(figsize=(7, 4))
    im = ax.imshow(
        pivot.values,
        aspect="auto",
        origin="lower",
        cmap="YlOrRd",
        vmin=0,
        vmax=1,
        interpolation="nearest",
    )
    xticks = np.arange(pivot.shape[1])
    ax.set_xticks(xticks)
    ax.set_xticklabels([f"{v:.2f}" for v in pivot.columns], rotation=45, ha="right")
    yticks = np.arange(pivot.shape[0])
    ax.set_yticks(yticks)
    ax.set_yticklabels([int(b) for b in pivot.index])
    ax.set_xlabel("Stimulus position (normalized)")
    ax.set_ylabel("Block")
    ax.set_title("Response heatmap")
    fig.colorbar(im, ax=ax, label="P(response)")

    out = _ensure_output_dir(output_dir)
    fname = out / "response_heatmap.png"
    fig.savefig(fname)
    if show:
        plt.show()
    plt.close(fig)
    return fname


# ---------------------------------------------------------------------------
# RT by distance
# ---------------------------------------------------------------------------


def plot_rt_by_distance(
    df: pd.DataFrame,
    output_dir: Union[str, Path] = "../outputs",
    show: bool = False,
) -> Path:
    """Plot reaction time as a function of distance from the target (S+).

    Parameters
    ----------
    df : pd.DataFrame
        Trial-level data.  Uses ``absolute_distance_from_target`` and
        ``first_response_rt_ms``.
    output_dir : str or Path
        Where to save the figure.
    show : bool
        If True, call ``plt.show()``.

    Returns
    -------
    Path
        Path to the saved figure.
    """
    _apply_style()

    dist = pd.to_numeric(df["absolute_distance_from_target"], errors="coerce")
    rt = pd.to_numeric(df["first_response_rt_ms"], errors="coerce")
    responded = df["response_occurred"].fillna(False).astype(bool) if "response_occurred" in df.columns else pd.Series(True, index=df.index)

    plot_df = pd.DataFrame({"distance": dist, "rt": rt, "responded": responded})
    plot_df = plot_df.loc[plot_df["responded"] & plot_df["rt"].notna()].copy()

    # Bin distances for cleaner visualization
    plot_df["dist_bin"] = pd.cut(plot_df["distance"], bins=10)
    bin_stats = (
        plot_df.groupby("dist_bin", observed=True)["rt"]
        .agg(["mean", "sem", "count"])
        .reset_index()
    )
    bin_stats["midpoint"] = bin_stats["dist_bin"].apply(lambda iv: iv.mid)

    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.errorbar(
        bin_stats["midpoint"],
        bin_stats["mean"],
        yerr=1.96 * bin_stats["sem"].fillna(0),
        marker="o",
        markersize=5,
        linewidth=1.5,
        capsize=3,
        color="#2c7bb6",
    )
    ax.set_xlabel("Distance from target (normalized units)")
    ax.set_ylabel("RT (ms)")
    ax.set_title("Reaction time by distance from S+")

    out = _ensure_output_dir(output_dir)
    fname = out / "rt_by_distance.png"
    fig.savefig(fname)
    if show:
        plt.show()
    plt.close(fig)
    return fname


# ---------------------------------------------------------------------------
# Participant flow (CONSORT-style)
# ---------------------------------------------------------------------------


def plot_participant_flow(
    exclusion_summary: Dict[str, int],
    output_dir: Union[str, Path] = "../outputs",
    show: bool = False,
) -> Path:
    """Create a simple CONSORT-style flow diagram of participant exclusions.

    Parameters
    ----------
    exclusion_summary : dict
        Dictionary produced by ``clean.apply_all_exclusions``.
    output_dir : str or Path
        Where to save the figure.
    show : bool
        If True, call ``plt.show()``.

    Returns
    -------
    Path
        Path to the saved figure.
    """
    _apply_style()

    s = exclusion_summary
    total = s.get("participants_total", 0)
    excl_pilot = s.get("participants_excluded_pilot", 0)
    excl_flag = s.get("participants_excluded_flagged", 0)
    excl_miss = s.get("participants_flagged_excessive_misses", 0)
    trials_fast = s.get("trials_flagged_too_fast", 0)
    final = s.get("participants_final", 0)

    fig, ax = plt.subplots(figsize=(4, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    box_props = dict(boxstyle="round,pad=0.4", facecolor="#f0f0f0", edgecolor="#333333", linewidth=1.2)

    # Boxes from top to bottom
    boxes = [
        (5, 9.0, f"Enrolled\nn = {total}"),
        (5, 7.0, f"After pilot exclusion\nn = {total - excl_pilot}"),
        (5, 5.0, f"After flag exclusion\nn = {total - excl_pilot - excl_flag}"),
        (5, 3.0, f"After miss/RT exclusion\nn = {final}"),
        (5, 1.0, f"Final sample\nn = {final}"),
    ]

    exclusion_labels = [
        (8.5, 8.0, f"Pilots: {excl_pilot}"),
        (8.5, 6.0, f"Flagged: {excl_flag}"),
        (8.5, 4.0, f"Excess misses: {excl_miss}\nFast RTs: {trials_fast} trials"),
    ]

    for x, y, text in boxes:
        ax.text(x, y, text, ha="center", va="center", fontsize=9, bbox=box_props)

    for i in range(len(boxes) - 1):
        ax.annotate(
            "",
            xy=(boxes[i + 1][0], boxes[i + 1][1] + 0.45),
            xytext=(boxes[i][0], boxes[i][1] - 0.45),
            arrowprops=dict(arrowstyle="->", color="#333333", lw=1.2),
        )

    for x, y, text in exclusion_labels:
        ax.text(x, y, text, ha="center", va="center", fontsize=8, color="#aa3333")

    ax.set_title("Participant flow", fontsize=12, pad=10)

    out = _ensure_output_dir(output_dir)
    fname = out / "participant_flow.png"
    fig.savefig(fname)
    if show:
        plt.show()
    plt.close(fig)
    return fname
