"""
clean.py
--------
Data cleaning and participant exclusion functions for the stimulus
generalization experiment.
"""

from __future__ import annotations

from typing import Dict, Tuple

import pandas as pd
import numpy as np


def exclude_pilots(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows flagged as pilot data.

    If the DataFrame contains an ``is_pilot`` column, rows where
    ``is_pilot`` is truthy are dropped.

    Parameters
    ----------
    df : pd.DataFrame
        Trial-level data.

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame (copy).
    """
    if "is_pilot" in df.columns:
        mask = df["is_pilot"].astype(str).str.lower().isin(["true", "1", "yes"])
        return df.loc[~mask].copy()
    return df.copy()


def exclude_flagged(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows where ``exclusion_flag`` is truthy.

    Parameters
    ----------
    df : pd.DataFrame
        Trial-level data.

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame (copy).
    """
    if "exclusion_flag" not in df.columns:
        return df.copy()
    mask = df["exclusion_flag"].fillna(False).astype(bool)
    return df.loc[~mask].copy()


def exclude_practice(df: pd.DataFrame) -> pd.DataFrame:
    """Remove practice-phase trials.

    Parameters
    ----------
    df : pd.DataFrame
        Trial-level data.

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame (copy).
    """
    if "phase_id" not in df.columns:
        return df.copy()
    return df.loc[df["phase_id"] != "practice"].copy()


def flag_fast_rt(df: pd.DataFrame, min_rt_ms: float = 100) -> pd.DataFrame:
    """Add a ``too_fast`` boolean column for implausibly fast responses.

    Parameters
    ----------
    df : pd.DataFrame
        Trial-level data.  Must contain ``first_response_rt_ms``.
    min_rt_ms : float
        Minimum plausible reaction time in milliseconds.  Responses faster
        than this are flagged.

    Returns
    -------
    pd.DataFrame
        DataFrame with ``too_fast`` column added.
    """
    df = df.copy()
    if "first_response_rt_ms" in df.columns:
        rt = pd.to_numeric(df["first_response_rt_ms"], errors="coerce")
        df["too_fast"] = rt < min_rt_ms
    else:
        df["too_fast"] = False
    return df


def flag_missed_trials(
    df: pd.DataFrame, max_fraction: float = 0.5
) -> pd.DataFrame:
    """Flag participants who missed too many training trials.

    A *missed* trial is one in which the participant was supposed to
    respond (``reinforcement_available == True``) but did not
    (``response_occurred == False``).  If the fraction of missed
    training trials exceeds ``max_fraction`` the participant is
    flagged in a new ``excessive_misses`` column.

    Parameters
    ----------
    df : pd.DataFrame
        Trial-level data.
    max_fraction : float
        Maximum allowable fraction of missed training trials.

    Returns
    -------
    pd.DataFrame
        DataFrame with ``excessive_misses`` column added.
    """
    df = df.copy()
    training_mask = df["trial_type"].isin(["training", "target"]) if "trial_type" in df.columns else pd.Series(True, index=df.index)
    reinforcement_mask = df["reinforcement_available"].fillna(False).astype(bool) if "reinforcement_available" in df.columns else pd.Series(True, index=df.index)
    response_mask = df["response_occurred"].fillna(False).astype(bool) if "response_occurred" in df.columns else pd.Series(False, index=df.index)

    combined = training_mask & reinforcement_mask
    training_df = df.loc[combined]

    missed = training_df.groupby("participant_id").apply(
        lambda g: (~g["response_occurred"].fillna(False).astype(bool)).sum() / max(len(g), 1)
    )
    flagged_pids = set(missed[missed > max_fraction].index)
    df["excessive_misses"] = df["participant_id"].isin(flagged_pids)
    return df


def apply_all_exclusions(
    df: pd.DataFrame,
    min_rt_ms: float = 100,
    max_miss_fraction: float = 0.5,
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Apply the full exclusion pipeline and return a summary.

    Steps applied in order:
    1. Exclude pilots
    2. Exclude flagged rows
    3. Exclude practice trials
    4. Flag fast RTs
    5. Flag participants with excessive misses

    Parameters
    ----------
    df : pd.DataFrame
        Raw trial-level data.
    min_rt_ms : float
        Minimum RT threshold (ms) for ``flag_fast_rt``.
    max_miss_fraction : float
        Maximum miss fraction for ``flag_missed_trials``.

    Returns
    -------
    clean_df : pd.DataFrame
        Cleaned DataFrame with flagged rows removed.
    summary : dict
        Counts at each exclusion stage.
    """
    summary: Dict[str, int] = {}

    n_total = df["participant_id"].nunique() if "participant_id" in df.columns else 0
    summary["participants_total"] = n_total
    summary["trials_total"] = len(df)

    # Step 1 -- pilots
    df = exclude_pilots(df)
    n_after_pilots = df["participant_id"].nunique() if "participant_id" in df.columns else 0
    summary["participants_excluded_pilot"] = n_total - n_after_pilots
    summary["trials_after_pilot_exclusion"] = len(df)

    # Step 2 -- flagged
    n_before = df["participant_id"].nunique() if "participant_id" in df.columns else 0
    df = exclude_flagged(df)
    n_after = df["participant_id"].nunique() if "participant_id" in df.columns else 0
    summary["participants_excluded_flagged"] = n_before - n_after
    summary["trials_after_flag_exclusion"] = len(df)

    # Step 3 -- practice
    n_before_practice = len(df)
    df = exclude_practice(df)
    summary["trials_excluded_practice"] = n_before_practice - len(df)
    summary["trials_after_practice_exclusion"] = len(df)

    # Step 4 -- fast RT
    df = flag_fast_rt(df, min_rt_ms=min_rt_ms)
    summary["trials_flagged_too_fast"] = int(df["too_fast"].sum())

    # Step 5 -- excessive misses
    df = flag_missed_trials(df, max_fraction=max_miss_fraction)
    n_excessive = df.loc[df["excessive_misses"], "participant_id"].nunique()
    summary["participants_flagged_excessive_misses"] = int(n_excessive)

    # Build clean dataset: drop too-fast trials and excessive-miss participants
    clean_df = df.loc[~df["too_fast"] & ~df["excessive_misses"]].copy()
    summary["participants_final"] = clean_df["participant_id"].nunique() if "participant_id" in clean_df.columns else 0
    summary["trials_final"] = len(clean_df)

    return clean_df, summary
