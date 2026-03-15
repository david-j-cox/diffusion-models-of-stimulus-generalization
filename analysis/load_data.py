"""
load_data.py
------------
Functions for loading trial-level data from CSV files or the experiment API.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Union
from urllib.request import urlopen
from io import StringIO

import pandas as pd
import numpy as np


# Columns that should be parsed as booleans.
_BOOL_COLUMNS = [
    "reinforcement_available",
    "reinforcement_delivered",
    "response_occurred",
    "is_resumed",
    "is_attention_check",
    "exclusion_flag",
]

# Columns that contain ISO-8601 timestamps.
_TIMESTAMP_COLUMNS = [
    "trial_start_ts",
    "stimulus_onset_ts",
    "feedback_onset_ts",
    "trial_end_ts",
]

# Columns stored as JSON strings (arrays / objects).
_JSON_COLUMNS = [
    "all_response_timestamps_ms",
]


def _coerce_booleans(df: pd.DataFrame) -> pd.DataFrame:
    """Convert boolean-like columns to proper bool dtype."""
    for col in _BOOL_COLUMNS:
        if col not in df.columns:
            continue
        # Handle various representations: True/False, true/false, 1/0, "yes"/"no"
        mapping = {
            "true": True,
            "false": False,
            "yes": True,
            "no": False,
            "1": True,
            "0": False,
            1: True,
            0: False,
            1.0: True,
            0.0: False,
        }
        df[col] = (
            df[col]
            .map(lambda v: mapping.get(v if not isinstance(v, str) else v.lower(), v))
            .astype("boolean")
        )
    return df


def _parse_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Parse ISO-8601 timestamp columns into pandas Timestamps."""
    for col in _TIMESTAMP_COLUMNS:
        if col not in df.columns:
            continue
        df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    return df


def _parse_json_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Parse JSON-encoded string columns into Python objects (lists / dicts)."""
    for col in _JSON_COLUMNS:
        if col not in df.columns:
            continue
        df[col] = df[col].apply(_safe_json_parse)
    return df


def _safe_json_parse(value: object) -> object:
    """Return parsed JSON or the original value on failure."""
    if pd.isna(value):
        return np.nan
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    return value


def _postprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all standard post-load transformations."""
    df = _coerce_booleans(df)
    df = _parse_timestamps(df)
    df = _parse_json_columns(df)
    # Ensure key numeric columns are numeric
    for col in [
        "stimulus_x_normalized",
        "stimulus_render_value",
        "signed_distance_from_target",
        "absolute_distance_from_target",
        "similarity_gaussian",
        "similarity_exponential",
        "first_response_rt_ms",
        "response_count",
        "block_index",
        "trial_index_global",
        "trial_index_within_phase",
        "browser_tz_offset",
        "random_seed",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_trials(path: Union[str, Path]) -> pd.DataFrame:
    """Load trial-level data from a local CSV file.

    Parameters
    ----------
    path : str or Path
        Path to the CSV file exported from the experiment platform.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with parsed types.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Trial data file not found: {path}")
    df = pd.read_csv(path, dtype=str)  # Read everything as string first
    df = _postprocess(df)
    return df


def load_from_api(base_url: str) -> pd.DataFrame:
    """Fetch trial-level CSV data from the experiment API.

    Parameters
    ----------
    base_url : str
        Base URL of the experiment server (e.g., ``https://myserver.com``).
        The function will request ``{base_url}/api/admin/export/trials.csv``.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with parsed types.
    """
    url = f"{base_url.rstrip('/')}/api/admin/export/trials.csv"
    with urlopen(url) as response:
        text = response.read().decode("utf-8")
    df = pd.read_csv(StringIO(text), dtype=str)
    df = _postprocess(df)
    return df
