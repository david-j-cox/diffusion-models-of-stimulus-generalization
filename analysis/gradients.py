"""
gradients.py
------------
Functions for computing stimulus generalization gradients -- the core
analytic quantity of the experiment.  A gradient is the function mapping
stimulus position (``stimulus_x_normalized``) to the probability of a
go response.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import numpy as np
from scipy import stats


def compute_gradient(
    df: pd.DataFrame,
    phase_id: Optional[str] = None,
) -> pd.DataFrame:
    """Compute the response-probability gradient across stimulus positions.

    Parameters
    ----------
    df : pd.DataFrame
        Trial-level data for a *single* participant (or pooled, if you
        want an overall gradient).  Must contain ``stimulus_x_normalized``
        and ``response_occurred``.
    phase_id : str, optional
        If given, restrict to trials in this phase.

    Returns
    -------
    pd.DataFrame
        Columns: ``stimulus_x``, ``response_probability``, ``n_trials``,
        ``se``, ``ci_lower``, ``ci_upper``.
    """
    df = df.copy()
    if phase_id is not None and "phase_id" in df.columns:
        df = df.loc[df["phase_id"] == phase_id]

    response = df["response_occurred"].fillna(False).astype(float)
    stim = pd.to_numeric(df["stimulus_x_normalized"], errors="coerce")

    grouped = pd.DataFrame({"stimulus_x": stim, "response": response}).groupby("stimulus_x")
    agg = grouped.agg(
        response_probability=("response", "mean"),
        n_trials=("response", "count"),
        se=("response", lambda x: x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else 0.0),
    ).reset_index()

    agg["ci_lower"] = agg["response_probability"] - 1.96 * agg["se"]
    agg["ci_upper"] = agg["response_probability"] + 1.96 * agg["se"]
    agg["ci_lower"] = agg["ci_lower"].clip(lower=0.0)
    agg["ci_upper"] = agg["ci_upper"].clip(upper=1.0)

    return agg.sort_values("stimulus_x").reset_index(drop=True)


def compute_gradient_by_block(
    df: pd.DataFrame,
    block_size: int = 20,
) -> pd.DataFrame:
    """Compute gradients separately for successive blocks of trials.

    Parameters
    ----------
    df : pd.DataFrame
        Trial-level data for a single participant.
    block_size : int
        Number of trials per block.

    Returns
    -------
    pd.DataFrame
        Columns: ``block``, ``stimulus_x``, ``response_probability``,
        ``n_trials``, ``se``, ``ci_lower``, ``ci_upper``.
    """
    df = df.copy()
    trial_idx = pd.to_numeric(df["trial_index_global"], errors="coerce")
    df["_block"] = (trial_idx // block_size).astype("Int64")

    records = []
    for block, bdf in df.groupby("_block"):
        grad = compute_gradient(bdf)
        grad.insert(0, "block", block)
        records.append(grad)

    if not records:
        return pd.DataFrame(columns=["block", "stimulus_x", "response_probability", "n_trials", "se", "ci_lower", "ci_upper"])
    return pd.concat(records, ignore_index=True)


def compute_gradient_over_time(
    df: pd.DataFrame,
    window_size: int = 30,
    step: int = 10,
) -> pd.DataFrame:
    """Compute gradients using a sliding window over trials.

    Parameters
    ----------
    df : pd.DataFrame
        Trial-level data for a single participant, sorted by trial order.
    window_size : int
        Number of trials in each window.
    step : int
        Step size (trials) between successive windows.

    Returns
    -------
    pd.DataFrame
        Columns: ``window_start``, ``window_end``, ``stimulus_x``,
        ``response_probability``, ``n_trials``.
    """
    df = df.sort_values("trial_index_global").reset_index(drop=True)
    n = len(df)
    records = []
    for start in range(0, max(n - window_size + 1, 1), step):
        end = min(start + window_size, n)
        window_df = df.iloc[start:end]
        grad = compute_gradient(window_df)
        grad.insert(0, "window_start", start)
        grad.insert(1, "window_end", end)
        records.append(grad)

    if not records:
        return pd.DataFrame(
            columns=["window_start", "window_end", "stimulus_x", "response_probability", "n_trials", "se", "ci_lower", "ci_upper"]
        )
    return pd.concat(records, ignore_index=True)


def group_mean_gradient(
    df: pd.DataFrame,
    phase_id: Optional[str] = None,
) -> pd.DataFrame:
    """Compute the group-level mean gradient with SEM across participants.

    For each stimulus position the function first computes the per-participant
    response probability, then averages across participants.

    Parameters
    ----------
    df : pd.DataFrame
        Trial-level data for *all* participants.
    phase_id : str, optional
        If given, restrict to trials in this phase.

    Returns
    -------
    pd.DataFrame
        Columns: ``stimulus_x``, ``response_probability``, ``se``,
        ``ci_lower``, ``ci_upper``, ``n_participants``, ``n_trials``.
    """
    df = df.copy()
    if phase_id is not None and "phase_id" in df.columns:
        df = df.loc[df["phase_id"] == phase_id]

    response = df["response_occurred"].fillna(False).astype(float)
    stim = pd.to_numeric(df["stimulus_x_normalized"], errors="coerce")

    per_part = (
        pd.DataFrame({
            "participant_id": df["participant_id"],
            "stimulus_x": stim,
            "response": response,
        })
        .groupby(["participant_id", "stimulus_x"])["response"]
        .mean()
        .reset_index()
        .rename(columns={"response": "resp_prob"})
    )

    group = per_part.groupby("stimulus_x")["resp_prob"].agg(
        response_probability="mean",
        se="sem",
        n_participants="count",
    ).reset_index()

    # Total trial counts at each stimulus position
    trial_counts = (
        pd.DataFrame({"stimulus_x": stim, "response": response})
        .groupby("stimulus_x")["response"]
        .count()
        .reset_index()
        .rename(columns={"response": "n_trials"})
    )
    group = group.merge(trial_counts, on="stimulus_x", how="left")

    group["se"] = group["se"].fillna(0.0)
    group["ci_lower"] = (group["response_probability"] - 1.96 * group["se"]).clip(lower=0.0)
    group["ci_upper"] = (group["response_probability"] + 1.96 * group["se"]).clip(upper=1.0)

    return group.sort_values("stimulus_x").reset_index(drop=True)
