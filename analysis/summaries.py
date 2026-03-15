"""
summaries.py
------------
Functions for computing trial-level, participant-level, and phase-level
summary statistics for the stimulus generalization experiment.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import numpy as np


def trial_level_summary(
    df: pd.DataFrame, block_size: int = 20
) -> pd.DataFrame:
    """Add computed columns to trial-level data.

    New columns:
    - ``block_number``: ``trial_index_global // block_size``
    - ``is_correct``: True when the participant responded to the target
      (S+) or withheld responding on a non-target trial.

    Parameters
    ----------
    df : pd.DataFrame
        Trial-level data.
    block_size : int
        Number of trials per block.

    Returns
    -------
    pd.DataFrame
        DataFrame with new columns appended.
    """
    df = df.copy()

    # Block number
    if "trial_index_global" in df.columns:
        df["block_number"] = (
            pd.to_numeric(df["trial_index_global"], errors="coerce") // block_size
        ).astype("Int64")
    else:
        df["block_number"] = pd.NA

    # Correctness
    response = df["response_occurred"].fillna(False).astype(bool) if "response_occurred" in df.columns else pd.Series(False, index=df.index)

    is_target = pd.Series(False, index=df.index)
    if "trial_type" in df.columns:
        is_target = df["trial_type"].isin(["target", "training"])
    elif "stimulus_label" in df.columns:
        is_target = df["stimulus_label"].str.lower().str.contains("target", na=False)

    # Correct = responded on target OR withheld on non-target
    df["is_correct"] = (response & is_target) | (~response & ~is_target)

    return df


def participant_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-participant summary statistics.

    Returns a DataFrame indexed by ``participant_id`` with:
    - ``n_trials``: total number of trials
    - ``n_training``: number of training trials
    - ``n_probe``: number of probe trials
    - ``response_rate_training``: fraction of training trials with a response
    - ``response_rate_probe``: fraction of probe trials with a response
    - ``mean_rt``: mean first-response RT (ms) across all responded trials
    - ``median_rt``: median first-response RT (ms)
    - ``phases_completed``: set of unique phase_ids
    - ``completed_all_phases``: whether the participant completed all phases

    Parameters
    ----------
    df : pd.DataFrame
        Trial-level data (ideally after cleaning).

    Returns
    -------
    pd.DataFrame
        One row per participant.
    """
    if "participant_id" not in df.columns:
        return pd.DataFrame()

    response = df["response_occurred"].fillna(False).astype(bool) if "response_occurred" in df.columns else pd.Series(False, index=df.index)
    rt = pd.to_numeric(df.get("first_response_rt_ms", pd.Series(dtype=float)), errors="coerce")

    is_training = pd.Series(False, index=df.index)
    is_probe = pd.Series(False, index=df.index)
    if "trial_type" in df.columns:
        is_training = df["trial_type"].isin(["training", "target"])
        is_probe = df["trial_type"] == "probe"

    all_phases = set(df["phase_id"].dropna().unique()) if "phase_id" in df.columns else set()

    records = []
    for pid, grp in df.groupby("participant_id"):
        g_resp = response.loc[grp.index]
        g_rt = rt.loc[grp.index]
        g_train = is_training.loc[grp.index]
        g_probe = is_probe.loc[grp.index]

        n_training = int(g_train.sum())
        n_probe = int(g_probe.sum())

        resp_rate_train = g_resp[g_train].mean() if n_training > 0 else np.nan
        resp_rate_probe = g_resp[g_probe].mean() if n_probe > 0 else np.nan

        responded_rts = g_rt[g_resp]
        phases = set(grp["phase_id"].dropna().unique()) if "phase_id" in grp.columns else set()

        records.append(
            {
                "participant_id": pid,
                "n_trials": len(grp),
                "n_training": n_training,
                "n_probe": n_probe,
                "response_rate_training": resp_rate_train,
                "response_rate_probe": resp_rate_probe,
                "mean_rt": responded_rts.mean() if len(responded_rts) > 0 else np.nan,
                "median_rt": responded_rts.median() if len(responded_rts) > 0 else np.nan,
                "phases_completed": phases,
                "completed_all_phases": phases == all_phases if all_phases else False,
            }
        )

    return pd.DataFrame(records).set_index("participant_id")


def phase_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-participant, per-phase summary statistics.

    Returns a DataFrame with columns:
    - ``participant_id``
    - ``phase_id``
    - ``n_trials``
    - ``n_responses``
    - ``response_rate``
    - ``mean_rt``
    - ``median_rt``
    - ``accuracy`` (if ``is_correct`` is available)

    Parameters
    ----------
    df : pd.DataFrame
        Trial-level data.

    Returns
    -------
    pd.DataFrame
        One row per participant-phase combination.
    """
    if "participant_id" not in df.columns or "phase_id" not in df.columns:
        return pd.DataFrame()

    response = df["response_occurred"].fillna(False).astype(bool) if "response_occurred" in df.columns else pd.Series(False, index=df.index)
    rt = pd.to_numeric(df.get("first_response_rt_ms", pd.Series(dtype=float)), errors="coerce")
    has_correct = "is_correct" in df.columns

    records = []
    for (pid, phase), grp in df.groupby(["participant_id", "phase_id"]):
        g_resp = response.loc[grp.index]
        g_rt = rt.loc[grp.index]
        responded_rts = g_rt[g_resp]

        rec = {
            "participant_id": pid,
            "phase_id": phase,
            "n_trials": len(grp),
            "n_responses": int(g_resp.sum()),
            "response_rate": g_resp.mean(),
            "mean_rt": responded_rts.mean() if len(responded_rts) > 0 else np.nan,
            "median_rt": responded_rts.median() if len(responded_rts) > 0 else np.nan,
        }
        if has_correct:
            rec["accuracy"] = grp["is_correct"].astype(float).mean()
        records.append(rec)

    return pd.DataFrame(records)
