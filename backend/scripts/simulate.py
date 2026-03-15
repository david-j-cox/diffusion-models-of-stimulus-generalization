"""Generate realistic simulated participant data for the stimulus generalization experiment.

Outputs CSV files directly — no database connection required.

Usage:
    cd backend
    python -m scripts.simulate                   # 20 participants (default)
    python -m scripts.simulate --n-participants 50
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Resolve imports
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.services.similarity import (  # noqa: E402
    compute_similarities,
    exponential_similarity,
    gaussian_similarity,
)
from app.services.sequence import generate_full_sequence  # noqa: E402
from app.services.study_loader import config_hash, load_yaml  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CONFIG_NAME = "default_pilot"
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "outputs"

TRIAL_COLUMNS = [
    "participant_id",
    "external_id",
    "session_id",
    "study_config_id",
    "condition_id",
    "condition_name",
    "phase_id",
    "block_index",
    "trial_index_global",
    "trial_index_within_phase",
    "stimulus_x_normalized",
    "stimulus_render_value",
    "stimulus_label",
    "signed_distance_from_target",
    "absolute_distance_from_target",
    "similarity_gaussian",
    "similarity_exponential",
    "trial_type",
    "reinforcement_available",
    "reinforcement_delivered",
    "feedback_type",
    "response_occurred",
    "response_count",
    "first_response_rt_ms",
    "all_response_timestamps_ms",
    "trial_start_ts",
    "stimulus_onset_ts",
    "feedback_onset_ts",
    "trial_end_ts",
    "browser_tz_offset",
    "is_resumed",
    "is_attention_check",
    "exclusion_flag",
    "config_hash",
    "random_seed",
]

PARTICIPANT_COLUMNS = [
    "participant_id",
    "external_id",
    "condition_name",
    "condition_index",
    "target_x",
    "random_seed",
    "total_trials",
    "training_accuracy",
    "probe_response_rate",
    "mean_rt_ms",
    "sigma_estimate",
    "is_poor_performer",
    "exclusion_flag",
]


# ---------------------------------------------------------------------------
# Participant-level generalization model
# ---------------------------------------------------------------------------

class ParticipantModel:
    """Simulates a single participant's responding."""

    def __init__(
        self,
        participant_idx: int,
        target_x: float,
        sigma: float,
        base_rate: float,
        learning_rate: float,
        rt_intercept: float,
        rt_slope: float,
        rt_noise_sd: float,
        is_poor_performer: bool,
        rng: random.Random,
    ):
        self.participant_idx = participant_idx
        self.target_x = target_x
        self.sigma = sigma
        self.base_rate = base_rate
        self.learning_rate = learning_rate
        self.rt_intercept = rt_intercept
        self.rt_slope = rt_slope
        self.rt_noise_sd = rt_noise_sd
        self.is_poor_performer = is_poor_performer
        self.rng = rng
        self.training_trials_seen = 0

    def response_probability(self, x: float, trial_type: str) -> float:
        """Compute probability of a go response."""
        sim = gaussian_similarity(x, self.target_x, self.sigma)

        # Learning curve: logistic ramp over training trials
        if trial_type in ("training", "practice"):
            self.training_trials_seen += 1
            learning_boost = 1.0 / (1.0 + math.exp(-self.learning_rate * (self.training_trials_seen - 10)))
        else:
            learning_boost = 1.0  # probes happen after training

        p = self.base_rate * sim * learning_boost

        if self.is_poor_performer:
            # Poor performers: more random responding
            p = 0.3 + 0.2 * sim

        return max(0.0, min(1.0, p))

    def generate_rt(self, x: float) -> float:
        """Generate a reaction time in ms."""
        sim = gaussian_similarity(x, self.target_x, self.sigma)
        rt = self.rt_intercept + self.rt_slope * (1.0 - sim)
        rt += self.rng.gauss(0, self.rt_noise_sd)
        return max(100.0, rt)  # floor at 100ms


def _create_participant_model(
    idx: int, target_x: float, rng: random.Random, is_poor: bool
) -> ParticipantModel:
    """Create a participant model with individual differences."""
    if is_poor:
        sigma = rng.uniform(0.30, 0.50)  # very broad gradient
        base_rate = rng.uniform(0.40, 0.60)
        learning_rate = rng.uniform(0.05, 0.10)
    else:
        sigma = rng.uniform(0.08, 0.25)  # normal range
        base_rate = rng.uniform(0.80, 0.98)
        learning_rate = rng.uniform(0.15, 0.40)

    return ParticipantModel(
        participant_idx=idx,
        target_x=target_x,
        sigma=sigma,
        base_rate=base_rate,
        learning_rate=learning_rate,
        rt_intercept=rng.uniform(280, 350),
        rt_slope=rng.uniform(150, 250),
        rt_noise_sd=rng.uniform(30, 70),
        is_poor_performer=is_poor,
        rng=rng,
    )


# ---------------------------------------------------------------------------
# Trial simulation
# ---------------------------------------------------------------------------

def simulate_participant(
    idx: int,
    config: dict[str, Any],
    cfg_hash: str,
    conditions: list[dict],
) -> tuple[list[dict], dict]:
    """Simulate all trials for one participant. Returns (trial_rows, summary)."""

    # Condition assignment (round-robin)
    cond_idx = idx % len(conditions)
    cond = conditions[cond_idx]
    target_x = cond.get("target_x", config["stimulus"]["target_x"])

    # IDs
    external_id = f"sim_{idx:04d}"
    participant_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    study_config_id = str(uuid.uuid4())
    condition_id = str(uuid.uuid4())

    # Deterministic seed
    digest = hashlib.sha256(f"{external_id}:{cfg_hash}".encode()).hexdigest()
    seed_val = int(digest[:8], 16)
    rng = random.Random(seed_val)

    # Decide if poor performer (~15% of participants)
    is_poor = (idx % 7 == 6)  # deterministic for reproducibility

    model = _create_participant_model(idx, target_x, rng, is_poor)

    # Generate trial sequence
    trials = generate_full_sequence(config, target_x, seed_val)

    # Similarity kernel params from config
    sigma_cfg = config["stimulus"]["similarity"]["gaussian_sigma"]
    tau_cfg = config["stimulus"]["similarity"]["exponential_tau"]

    # Simulate timestamps starting from a base time
    base_time = datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.utc) + timedelta(hours=idx)
    current_time = base_time
    iti_min = config["timing"]["iti_min_ms"]
    iti_max = config["timing"]["iti_max_ms"]
    fixation_ms = config["timing"]["fixation_ms"]
    stimulus_ms = config["timing"]["stimulus_ms"]
    feedback_ms = config["timing"]["feedback_ms"]

    trial_rows: list[dict] = []
    training_correct = 0
    training_total = 0
    probe_responses = 0
    probe_total = 0
    all_rts: list[float] = []

    for trial in trials:
        x = trial["stimulus_x_normalized"]
        trial_type = trial["trial_type"]
        phase_id = trial["phase_id"]
        reinforcement_available = trial["reinforcement_available"]

        # Compute similarities using config-level kernel params
        sims = compute_similarities(x, target_x, sigma_cfg, tau_cfg)

        # Simulate response
        p_resp = model.response_probability(x, trial_type)
        response_occurred = rng.random() < p_resp

        if response_occurred:
            rt = model.generate_rt(x)
            response_count = 1
            # Occasionally double-press
            if rng.random() < 0.05:
                response_count = 2
            first_response_rt_ms = round(rt, 1)
            all_rts.append(first_response_rt_ms)
            all_response_timestamps_ms = [first_response_rt_ms]
            if response_count == 2:
                second_rt = first_response_rt_ms + rng.uniform(80, 200)
                all_response_timestamps_ms.append(round(second_rt, 1))
        else:
            response_count = 0
            first_response_rt_ms = None
            all_response_timestamps_ms = []

        # Reinforcement logic
        reinforcement_delivered = reinforcement_available and response_occurred

        # Training accuracy tracking
        if trial_type == "training":
            training_total += 1
            is_target = abs(x - target_x) < 1e-6
            if is_target and response_occurred:
                training_correct += 1
            elif not is_target and not response_occurred:
                training_correct += 1

        if trial_type == "probe":
            probe_total += 1
            if response_occurred:
                probe_responses += 1

        # Timestamps
        trial_start = current_time
        stimulus_onset = trial_start + timedelta(milliseconds=fixation_ms)
        if response_occurred:
            feedback_onset = stimulus_onset + timedelta(milliseconds=first_response_rt_ms + 50)
        elif reinforcement_available:
            feedback_onset = stimulus_onset + timedelta(milliseconds=stimulus_ms)
        else:
            feedback_onset = None
        trial_end = stimulus_onset + timedelta(milliseconds=stimulus_ms + feedback_ms)

        # Exclusion flag for obviously bad data
        exclusion_flag = None
        if first_response_rt_ms is not None and first_response_rt_ms < 100:
            exclusion_flag = "rt_too_fast"

        row = {
            "participant_id": participant_id,
            "external_id": external_id,
            "session_id": session_id,
            "study_config_id": study_config_id,
            "condition_id": condition_id,
            "condition_name": cond["name"],
            "phase_id": phase_id,
            "block_index": trial["block_index"],
            "trial_index_global": trial["trial_index_global"],
            "trial_index_within_phase": trial["trial_index_within_phase"],
            "stimulus_x_normalized": round(x, 6),
            "stimulus_render_value": round(trial["stimulus_render_value"], 2),
            "stimulus_label": trial["stimulus_label"],
            "signed_distance_from_target": round(sims["signed_distance"], 6),
            "absolute_distance_from_target": round(sims["absolute_distance"], 6),
            "similarity_gaussian": round(sims["similarity_gaussian"], 6),
            "similarity_exponential": round(sims["similarity_exponential"], 6),
            "trial_type": trial_type,
            "reinforcement_available": reinforcement_available,
            "reinforcement_delivered": reinforcement_delivered,
            "feedback_type": trial.get("feedback_type", ""),
            "response_occurred": response_occurred,
            "response_count": response_count,
            "first_response_rt_ms": first_response_rt_ms if first_response_rt_ms is not None else "",
            "all_response_timestamps_ms": str(all_response_timestamps_ms),
            "trial_start_ts": trial_start.isoformat(),
            "stimulus_onset_ts": stimulus_onset.isoformat(),
            "feedback_onset_ts": feedback_onset.isoformat() if feedback_onset else "",
            "trial_end_ts": trial_end.isoformat(),
            "browser_tz_offset": -300,  # EST
            "is_resumed": False,
            "is_attention_check": trial.get("is_attention_check", False),
            "exclusion_flag": exclusion_flag if exclusion_flag else "",
            "config_hash": cfg_hash,
            "random_seed": seed_val,
        }
        trial_rows.append(row)

        # Advance time for next trial
        iti = rng.uniform(iti_min, iti_max)
        current_time = trial_end + timedelta(milliseconds=iti)

    # Participant summary
    training_acc = training_correct / training_total if training_total > 0 else 0.0
    probe_rate = probe_responses / probe_total if probe_total > 0 else 0.0
    mean_rt = sum(all_rts) / len(all_rts) if all_rts else 0.0

    # Flag for exclusion at participant level
    p_exclusion = ""
    if is_poor and training_acc < 0.50:
        p_exclusion = "low_training_accuracy"

    summary = {
        "participant_id": participant_id,
        "external_id": external_id,
        "condition_name": cond["name"],
        "condition_index": cond_idx,
        "target_x": target_x,
        "random_seed": seed_val,
        "total_trials": len(trial_rows),
        "training_accuracy": round(training_acc, 4),
        "probe_response_rate": round(probe_rate, 4),
        "mean_rt_ms": round(mean_rt, 1),
        "sigma_estimate": round(model.sigma, 4),
        "is_poor_performer": is_poor,
        "exclusion_flag": p_exclusion,
    }

    return trial_rows, summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate stimulus generalization experiment data")
    parser.add_argument(
        "--n-participants", type=int, default=20,
        help="Number of participants to simulate (default: 20)",
    )
    args = parser.parse_args()
    n_participants = args.n_participants

    # Load config
    config = load_yaml(CONFIG_NAME)
    cfg_hash_val = config_hash(config)

    conditions = config.get("conditions", [])
    if not conditions:
        conditions = [{"name": "default", "target_x": config["stimulus"]["target_x"]}]

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_trial_rows: list[dict] = []
    all_summaries: list[dict] = []

    print(f"Simulating {n_participants} participants...")
    print(f"  Config: {CONFIG_NAME} (hash={cfg_hash_val})")
    print(f"  Conditions: {[c['name'] for c in conditions]}")
    print()

    for idx in range(n_participants):
        trial_rows, summary = simulate_participant(idx, config, cfg_hash_val, conditions)
        all_trial_rows.extend(trial_rows)
        all_summaries.append(summary)

        marker = " [POOR]" if summary["is_poor_performer"] else ""
        print(
            f"  {summary['external_id']}: "
            f"{summary['total_trials']} trials, "
            f"train_acc={summary['training_accuracy']:.2f}, "
            f"probe_rate={summary['probe_response_rate']:.2f}, "
            f"sigma={summary['sigma_estimate']:.3f}"
            f"{marker}"
        )

    # Write trials CSV
    trials_path = OUTPUT_DIR / "simulated_trials.csv"
    with open(trials_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRIAL_COLUMNS)
        writer.writeheader()
        writer.writerows(all_trial_rows)

    # Write participant summaries CSV
    participants_path = OUTPUT_DIR / "simulated_participants.csv"
    with open(participants_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PARTICIPANT_COLUMNS)
        writer.writeheader()
        writer.writerows(all_summaries)

    # Summary
    print(f"\n{'='*60}")
    print(f"Generated {len(all_trial_rows)} total trials across {n_participants} participants")
    print(f"  Poor performers: {sum(1 for s in all_summaries if s['is_poor_performer'])}")
    print(f"  Flagged for exclusion: {sum(1 for s in all_summaries if s['exclusion_flag'])}")
    print(f"\nOutput files:")
    print(f"  {trials_path}")
    print(f"  {participants_path}")


if __name__ == "__main__":
    main()
