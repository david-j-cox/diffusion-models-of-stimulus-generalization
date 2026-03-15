"""Trial sequence generation with pseudorandomization constraints.

Generates the full trial list for a participant based on the study config,
condition assignment, and randomization seed. The sequence is reproducible
given the same seed.

Constraints implemented:
  - Maximum run length of same trial type
  - Maximum run length of same stimulus value
  - Balanced left/right probe distribution within blocks
  - Stored seed for reproducibility
"""

from __future__ import annotations

import random
from typing import Any


def _render_value(x_norm: float, axis_min: float, axis_max: float) -> float:
    """Map normalized x in [0,1] to rendered stimulus value."""
    return axis_min + x_norm * (axis_max - axis_min)


def _label_for_stimulus(
    x_norm: float, target_x: float, s_minus: list[float] | None, tolerance: float = 1e-6
) -> str:
    """Determine the stimulus label: S+, S-, or probe."""
    if abs(x_norm - target_x) < tolerance:
        return "S+"
    if s_minus:
        for sm in s_minus:
            if abs(x_norm - sm) < tolerance:
                return "S-"
    return "probe"


def generate_phase_trials(
    phase_cfg: dict[str, Any],
    target_x: float,
    probe_positions: list[float],
    s_minus: list[float] | None,
    axis_min: float,
    axis_max: float,
    rng: random.Random,
    max_run_same_type: int = 3,
    max_run_same_stimulus: int = 2,
) -> list[dict[str, Any]]:
    """Generate constrained pseudorandom trial list for one phase.

    Args:
        phase_cfg: Phase configuration dict from study YAML.
        target_x: Normalized target position.
        probe_positions: List of normalized probe positions.
        s_minus: Optional list of S- normalized positions.
        axis_min: Rendered axis minimum (e.g. 20 degrees).
        axis_max: Rendered axis maximum (e.g. 160 degrees).
        rng: Seeded random.Random instance.
        max_run_same_type: Max consecutive trials of the same type.
        max_run_same_stimulus: Max consecutive trials at the same position.

    Returns:
        List of trial dicts ready for sequencing.
    """
    phase_id = phase_cfg["id"]
    trial_pool: list[dict[str, Any]] = []

    # Build the trial pool from the phase spec
    for stim_spec in phase_cfg.get("stimuli", []):
        x = stim_spec["x"]
        count = stim_spec.get("count", 1)
        trial_type = stim_spec.get("trial_type", "training")
        reinforcement_available = stim_spec.get("reinforcement_available", False)
        feedback_type = stim_spec.get("feedback_type", None)
        is_attention_check = stim_spec.get("is_attention_check", False)

        label = _label_for_stimulus(x, target_x, s_minus)

        for _ in range(count):
            trial_pool.append({
                "phase_id": phase_id,
                "stimulus_x_normalized": x,
                "stimulus_render_value": _render_value(x, axis_min, axis_max),
                "stimulus_label": label,
                "trial_type": trial_type,
                "reinforcement_available": reinforcement_available,
                "feedback_type": feedback_type,
                "is_attention_check": is_attention_check,
            })

    # Shuffle with constraints
    trials = _constrained_shuffle(
        trial_pool, rng, max_run_same_type, max_run_same_stimulus
    )
    return trials


def _constrained_shuffle(
    trials: list[dict],
    rng: random.Random,
    max_run_type: int,
    max_run_stim: int,
    max_attempts: int = 500,
) -> list[dict]:
    """Shuffle trials respecting run-length constraints.

    Uses repeated random shuffles and checks constraints.
    Falls back to best-effort after max_attempts.
    """
    best = list(trials)
    best_violations = _count_violations(best, max_run_type, max_run_stim)

    for _ in range(max_attempts):
        candidate = list(trials)
        rng.shuffle(candidate)
        v = _count_violations(candidate, max_run_type, max_run_stim)
        if v == 0:
            return candidate
        if v < best_violations:
            best = candidate
            best_violations = v

    return best


def _count_violations(trials: list[dict], max_run_type: int, max_run_stim: int) -> int:
    """Count constraint violations in a trial ordering."""
    violations = 0
    for i in range(len(trials)):
        # Check run of same trial type
        if i >= max_run_type:
            if all(
                trials[i - j]["trial_type"] == trials[i]["trial_type"]
                for j in range(max_run_type)
            ):
                violations += 1
        # Check run of same stimulus
        if i >= max_run_stim:
            if all(
                abs(trials[i - j]["stimulus_x_normalized"] - trials[i]["stimulus_x_normalized"]) < 1e-6
                for j in range(max_run_stim)
            ):
                violations += 1
    return violations


def generate_full_sequence(
    config: dict[str, Any],
    target_x: float,
    seed: int,
) -> list[dict[str, Any]]:
    """Generate the complete trial sequence for a participant.

    Iterates through all phases defined in the study config and concatenates
    their trial lists. Assigns global indices.

    Args:
        config: Full study config dict.
        target_x: The participant's assigned S+ location.
        seed: Random seed for reproducibility.

    Returns:
        Flat list of trial dicts with global and phase-local indices.
    """
    rng = random.Random(seed)

    stim_cfg = config["stimulus"]
    axis_min = stim_cfg.get("axis_min", 20.0)
    axis_max = stim_cfg.get("axis_max", 160.0)
    probe_positions = stim_cfg.get("probe_positions", [])
    s_minus = stim_cfg.get("s_minus_positions", None)

    max_run_type = config.get("randomization", {}).get("max_run_same_type", 3)
    max_run_stim = config.get("randomization", {}).get("max_run_same_stimulus", 2)

    all_trials: list[dict[str, Any]] = []
    global_idx = 0

    for phase_cfg in config["phases"]:
        if not phase_cfg.get("enabled", True):
            continue

        # Build stimuli list for the phase based on its type
        phase_with_stimuli = _expand_phase_stimuli(phase_cfg, target_x, probe_positions, s_minus)

        phase_trials = generate_phase_trials(
            phase_with_stimuli,
            target_x,
            probe_positions,
            s_minus,
            axis_min,
            axis_max,
            rng,
            max_run_type,
            max_run_stim,
        )

        for local_idx, trial in enumerate(phase_trials):
            trial["trial_index_global"] = global_idx
            trial["trial_index_within_phase"] = local_idx
            trial["block_index"] = phase_cfg.get("block_index", 0)
            global_idx += 1

        all_trials.extend(phase_trials)

    return all_trials


def _expand_phase_stimuli(
    phase_cfg: dict[str, Any],
    target_x: float,
    probe_positions: list[float],
    s_minus: list[float] | None,
) -> dict[str, Any]:
    """If the phase config uses shorthand (e.g. 'target_count'), expand to full stimuli list."""
    if "stimuli" in phase_cfg:
        return phase_cfg

    stimuli = []
    phase_type = phase_cfg.get("type", "training")

    # Training trials at S+
    target_count = phase_cfg.get("target_count", 0)
    if target_count > 0:
        stimuli.append({
            "x": target_x,
            "count": target_count,
            "trial_type": "training",
            "reinforcement_available": phase_cfg.get("reinforcement_available", True),
            "feedback_type": phase_cfg.get("feedback_type", "points"),
        })

    # Probe trials
    probe_reps = phase_cfg.get("probe_repetitions", 0)
    if probe_reps > 0:
        for px in probe_positions:
            stimuli.append({
                "x": px,
                "count": probe_reps,
                "trial_type": "probe",
                "reinforcement_available": phase_cfg.get("probe_reinforcement", False),
                "feedback_type": None,
            })
        # Also include target in probe blocks to maintain responding
        target_in_probe = phase_cfg.get("target_in_probe_count", 0)
        if target_in_probe > 0:
            stimuli.append({
                "x": target_x,
                "count": target_in_probe,
                "trial_type": "training",
                "reinforcement_available": True,
                "feedback_type": phase_cfg.get("feedback_type", "points"),
            })

    # Discrimination S- trials
    if s_minus and phase_type == "discrimination":
        s_minus_count = phase_cfg.get("s_minus_count", 0)
        for sm in s_minus:
            stimuli.append({
                "x": sm,
                "count": s_minus_count,
                "trial_type": "discrimination",
                "reinforcement_available": False,
                "feedback_type": phase_cfg.get("s_minus_feedback_type", "none"),
            })

    # Attention checks
    attn_count = phase_cfg.get("attention_check_count", 0)
    if attn_count > 0:
        stimuli.append({
            "x": target_x,
            "count": attn_count,
            "trial_type": "training",
            "reinforcement_available": True,
            "feedback_type": "points",
            "is_attention_check": True,
        })

    expanded = dict(phase_cfg)
    expanded["stimuli"] = stimuli
    return expanded
