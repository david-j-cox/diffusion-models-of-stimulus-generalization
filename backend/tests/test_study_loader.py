"""Tests for study config loading and validation."""

from __future__ import annotations

import copy
import os
import sys

import pytest

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.services.study_loader import config_hash, load_yaml, validate_config


def test_load_default_config_succeeds() -> None:
    """The default_pilot config loads without errors and has expected fields."""
    config = load_yaml("default_pilot")

    assert config["name"] == "default_pilot"
    assert "stimulus" in config
    assert "phases" in config
    assert config["stimulus"]["target_x"] == 0.50
    assert len(config["stimulus"]["probe_positions"]) == 11


def test_validate_config_catches_missing_keys() -> None:
    """validate_config raises ValueError when required keys are absent."""
    incomplete = {
        "name": "test",
        "version": "1.0",
        "stimulus": {"target_x": 0.5},
        # missing: phases, timing, feedback
    }
    with pytest.raises(ValueError, match="missing required keys"):
        validate_config(incomplete)


def test_config_hash_is_deterministic() -> None:
    """Same config dict always produces the same hash."""
    config = load_yaml("default_pilot")

    hash_a = config_hash(config)
    hash_b = config_hash(config)

    assert hash_a == hash_b
    assert isinstance(hash_a, str)
    assert len(hash_a) == 16  # sha256 truncated to 16 hex chars


def test_config_hash_changes_with_content() -> None:
    """Modifying the config produces a different hash."""
    config_original = load_yaml("default_pilot")
    config_modified = copy.deepcopy(config_original)
    config_modified["stimulus"]["target_x"] = 0.75

    hash_original = config_hash(config_original)
    hash_modified = config_hash(config_modified)

    assert hash_original != hash_modified
