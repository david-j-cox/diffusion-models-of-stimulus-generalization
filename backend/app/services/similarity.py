"""Similarity kernel functions for stimulus generalization.

Two kernels are implemented:
  - Gaussian: exp(-d^2 / (2 * sigma^2))
  - Exponential (Shepard): exp(-d / tau)

Both operate on the normalized stimulus axis [0, 1].
"""

from __future__ import annotations

import math


def gaussian_similarity(x: float, target: float, sigma: float = 0.15) -> float:
    """Gaussian similarity kernel.

    Args:
        x: Stimulus position on [0, 1].
        target: Target (S+) position on [0, 1].
        sigma: Width parameter. Larger = broader generalization.

    Returns:
        Similarity in (0, 1].
    """
    d = x - target
    return math.exp(-(d ** 2) / (2 * sigma ** 2))


def exponential_similarity(x: float, target: float, tau: float = 0.10) -> float:
    """Exponential (Shepard-style) similarity kernel.

    Args:
        x: Stimulus position on [0, 1].
        target: Target (S+) position on [0, 1].
        tau: Scale parameter. Larger = broader generalization.

    Returns:
        Similarity in (0, 1].
    """
    d = abs(x - target)
    return math.exp(-d / tau)


def compute_similarities(
    x: float,
    target: float,
    sigma: float = 0.15,
    tau: float = 0.10,
) -> dict[str, float]:
    """Compute both similarity kernels and distance metrics.

    Returns:
        Dict with keys: signed_distance, absolute_distance,
        similarity_gaussian, similarity_exponential.
    """
    return {
        "signed_distance": x - target,
        "absolute_distance": abs(x - target),
        "similarity_gaussian": gaussian_similarity(x, target, sigma),
        "similarity_exponential": exponential_similarity(x, target, tau),
    }
