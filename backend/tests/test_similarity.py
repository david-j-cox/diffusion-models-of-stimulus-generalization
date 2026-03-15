"""Tests for similarity kernel functions."""

from __future__ import annotations

import os
import sys

import pytest

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.services.similarity import (
    compute_similarities,
    exponential_similarity,
    gaussian_similarity,
)


TARGET = 0.50


def test_gaussian_at_target_is_one() -> None:
    """Gaussian similarity at the target position equals 1.0."""
    assert gaussian_similarity(TARGET, TARGET) == pytest.approx(1.0)


def test_exponential_at_target_is_one() -> None:
    """Exponential similarity at the target position equals 1.0."""
    assert exponential_similarity(TARGET, TARGET) == pytest.approx(1.0)


def test_gaussian_decreases_with_distance() -> None:
    """Gaussian similarity decreases as stimulus moves away from target."""
    distances = [0.0, 0.1, 0.2, 0.3, 0.4]
    values = [gaussian_similarity(TARGET + d, TARGET) for d in distances]

    for i in range(len(values) - 1):
        assert values[i] > values[i + 1], (
            f"Gaussian did not decrease: f({distances[i]})={values[i]} "
            f"vs f({distances[i+1]})={values[i+1]}"
        )


def test_exponential_decreases_with_distance() -> None:
    """Exponential similarity decreases as stimulus moves away from target."""
    distances = [0.0, 0.1, 0.2, 0.3, 0.4]
    values = [exponential_similarity(TARGET + d, TARGET) for d in distances]

    for i in range(len(values) - 1):
        assert values[i] > values[i + 1], (
            f"Exponential did not decrease: f({distances[i]})={values[i]} "
            f"vs f({distances[i+1]})={values[i+1]}"
        )


def test_gaussian_is_symmetric() -> None:
    """Gaussian similarity is symmetric around the target."""
    offset = 0.2
    left = gaussian_similarity(TARGET - offset, TARGET)
    right = gaussian_similarity(TARGET + offset, TARGET)
    assert left == pytest.approx(right)


def test_compute_similarities_returns_all_keys() -> None:
    """compute_similarities returns all expected keys with correct types."""
    result = compute_similarities(0.3, TARGET)

    expected_keys = {
        "signed_distance",
        "absolute_distance",
        "similarity_gaussian",
        "similarity_exponential",
    }
    assert set(result.keys()) == expected_keys

    # signed_distance should be negative (0.3 < 0.5)
    assert result["signed_distance"] == pytest.approx(-0.2)
    # absolute_distance should be positive
    assert result["absolute_distance"] == pytest.approx(0.2)
    # Similarities should be in (0, 1]
    assert 0.0 < result["similarity_gaussian"] <= 1.0
    assert 0.0 < result["similarity_exponential"] <= 1.0
