"""Tests for condition assignment logic (deterministic seed generation)."""

from __future__ import annotations

import os
import sys

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# Import the private helper directly — no database needed
from app.services.assignment import _deterministic_seed


def test_deterministic_seed_is_consistent() -> None:
    """Same inputs always produce the same seed."""
    external_id = "test_participant_001"
    config_hash = "abc123def456"

    seed_a = _deterministic_seed(external_id, config_hash)
    seed_b = _deterministic_seed(external_id, config_hash)

    assert seed_a == seed_b
    assert isinstance(seed_a, int)


def test_deterministic_seed_differs_for_different_ids() -> None:
    """Different external_ids produce different seeds."""
    config_hash = "abc123def456"

    seed_a = _deterministic_seed("participant_001", config_hash)
    seed_b = _deterministic_seed("participant_002", config_hash)

    assert seed_a != seed_b
