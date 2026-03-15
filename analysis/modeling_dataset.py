"""
modeling_dataset.py
-------------------
Functions for constructing the feature-rich modeling dataset used by
downstream models (logistic regression, diffusion models, etc.).

Each row remains a single trial, but many derived / history-based
features are added so that models can condition on the full
reinforcement history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd


@dataclass
class ModelingConfig:
    """Configuration for the modeling dataset builder."""

    lag_orders: List[int] = field(default_factory=lambda: [1, 2, 3])
    rolling_window: int = 10
    neighborhood_bins: int = 5
    gaussian_sigma: float = 0.1
    block_size: int = 20


def _add_block_number(df: pd.DataFrame, block_size: int) -> pd.DataFrame:
    """Add ``block_number`` based on ``trial_index_global``."""
    df["block_number"] = (
        pd.to_numeric(df["trial_index_global"], errors="coerce") // block_size
    ).astype("Int64")
    return df


def _add_phase(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure ``phase`` column exists (alias for ``phase_id``)."""
    if "phase" not in df.columns and "phase_id" in df.columns:
        df["phase"] = df["phase_id"]
    return df


def _add_lagged_features(
    df: pd.DataFrame, lag_orders: List[int]
) -> pd.DataFrame:
    """Add lagged response and reinforcement columns within each participant."""
    response = df["response_occurred"].fillna(False).astype(int)
    reinforcement = df["reinforcement_delivered"].fillna(False).astype(int)

    for lag in lag_orders:
        df[f"lagged_response_{lag}"] = df.groupby("participant_id")[
            "response_occurred"
        ].transform(lambda s: s.astype(float).shift(lag))
        df[f"lagged_reinforcement_{lag}"] = df.groupby("participant_id")[
            "reinforcement_delivered"
        ].transform(lambda s: s.astype(float).shift(lag))
    return df


def _add_cumulative_reinforcers_at_target(df: pd.DataFrame) -> pd.DataFrame:
    """Cumulative count of reinforcers delivered at the target stimulus."""
    reinf = df["reinforcement_delivered"].fillna(False).astype(int)
    is_target = df["trial_type"].isin(["target", "training"]) if "trial_type" in df.columns else pd.Series(False, index=df.index)
    target_reinf = (reinf * is_target.astype(int))
    df["cumulative_reinforcers_at_target"] = df.groupby("participant_id").apply(
        lambda g: target_reinf.loc[g.index].cumsum().shift(1, fill_value=0)
    ).droplevel(0) if "participant_id" in df.columns else target_reinf.cumsum().shift(1, fill_value=0)
    return df


def _add_cumulative_reinforcers_by_neighborhood(
    df: pd.DataFrame, n_bins: int
) -> pd.DataFrame:
    """Cumulative reinforcers binned by stimulus-space neighborhood."""
    stim = pd.to_numeric(df["stimulus_x_normalized"], errors="coerce")
    reinf = df["reinforcement_delivered"].fillna(False).astype(int)

    bin_edges = np.linspace(0, 1, n_bins + 1)
    bin_labels = [f"neighborhood_{i}" for i in range(n_bins)]
    df["_stim_bin"] = pd.cut(stim, bins=bin_edges, labels=bin_labels, include_lowest=True)

    # One-hot encode bins, multiply by reinforcement, cumsum per participant
    for label in bin_labels:
        in_bin = (df["_stim_bin"] == label).astype(int)
        col = f"cumulative_reinf_{label}"
        series = (in_bin * reinf)
        df[col] = df.groupby("participant_id").apply(
            lambda g: series.loc[g.index].cumsum().shift(1, fill_value=0)
        ).droplevel(0) if "participant_id" in df.columns else series.cumsum().shift(1, fill_value=0)

    df.drop(columns=["_stim_bin"], inplace=True)
    return df


def _add_trials_since_last_reinforcement(df: pd.DataFrame) -> pd.DataFrame:
    """Trials elapsed since the participant last received reinforcement."""
    def _compute(group: pd.Series) -> pd.Series:
        result = pd.Series(np.nan, index=group.index, dtype=float)
        last_reinf_idx = -1
        for i, (idx, val) in enumerate(group.items()):
            if last_reinf_idx >= 0:
                result.iloc[i] = i - last_reinf_idx
            else:
                result.iloc[i] = np.nan
            if val:
                last_reinf_idx = i
        return result

    reinf = df["reinforcement_delivered"].fillna(False).astype(bool)
    df["trials_since_last_reinforcement"] = reinf.groupby(
        df["participant_id"]
    ).transform(_compute) if "participant_id" in df.columns else _compute(reinf)
    return df


def _add_rolling_rates(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """Rolling response rate and reinforcement rate over the last *window* trials."""
    for col_src, col_dst in [
        ("response_occurred", "rolling_response_rate"),
        ("reinforcement_delivered", "rolling_reinforcement_rate"),
    ]:
        series = df[col_src].fillna(False).astype(float)
        df[col_dst] = df.groupby("participant_id")[col_src].transform(
            lambda s: s.astype(float).rolling(window, min_periods=1).mean().shift(1)
        ) if "participant_id" in df.columns else series.rolling(window, min_periods=1).mean().shift(1)
    return df


def _add_cumulative_similarity_weighted_reinforcement(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Cumulative sum of similarity * reinforcement over all prior trials.

    For each trial *t* and participant, this is:

        sum_{i=0}^{t-1}  similarity(x_i, x_t) * reinforcement_i

    where similarity is the Gaussian kernel already in the data.
    Computing the exact cross-trial sum is O(n^2) per participant;
    here we use the pre-computed ``similarity_gaussian`` column as an
    approximation (it is the similarity of the current stimulus to the
    target, not to every past stimulus).  A more exact version would
    iterate pair-wise, but for the starter pipeline this is sufficient.
    """
    sim = pd.to_numeric(df["similarity_gaussian"], errors="coerce").fillna(0)
    reinf = df["reinforcement_delivered"].fillna(False).astype(float)
    weighted = sim * reinf

    df["cumulative_similarity_weighted_reinforcement"] = df.groupby(
        "participant_id"
    ).apply(
        lambda g: weighted.loc[g.index].cumsum().shift(1, fill_value=0)
    ).droplevel(0) if "participant_id" in df.columns else weighted.cumsum().shift(1, fill_value=0)
    return df


def build_modeling_dataset(
    df: pd.DataFrame,
    config: Optional[ModelingConfig] = None,
) -> pd.DataFrame:
    """Construct the full modeling dataset with history-based features.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned trial-level data.
    config : ModelingConfig, optional
        Feature-engineering parameters.  Uses defaults if not provided.

    Returns
    -------
    pd.DataFrame
        Trial-level data augmented with derived features.
    """
    if config is None:
        config = ModelingConfig()

    df = df.copy()

    # Sort by participant and trial order
    if "participant_id" in df.columns and "trial_index_global" in df.columns:
        df = df.sort_values(["participant_id", "trial_index_global"]).reset_index(drop=True)

    # Ensure key columns are numeric / boolean
    for col in ["response_occurred", "reinforcement_delivered"]:
        if col in df.columns:
            df[col] = df[col].fillna(False).astype(bool)

    df = _add_block_number(df, config.block_size)
    df = _add_phase(df)
    df = _add_lagged_features(df, config.lag_orders)
    df = _add_cumulative_reinforcers_at_target(df)
    df = _add_cumulative_reinforcers_by_neighborhood(df, config.neighborhood_bins)
    df = _add_trials_since_last_reinforcement(df)
    df = _add_rolling_rates(df, config.rolling_window)
    df = _add_cumulative_similarity_weighted_reinforcement(df)

    # Ensure distance columns are present and numeric
    for col in [
        "signed_distance_from_target",
        "absolute_distance_from_target",
        "similarity_gaussian",
        "similarity_exponential",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def save_modeling_dataset(
    df: pd.DataFrame,
    path: Union[str, Path],
) -> Path:
    """Save the modeling dataset to a CSV file.

    Parameters
    ----------
    df : pd.DataFrame
        Modeling dataset (output of ``build_modeling_dataset``).
    path : str or Path
        Destination file path (CSV).

    Returns
    -------
    Path
        The path the file was written to.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path
