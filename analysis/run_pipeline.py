"""
run_pipeline.py
---------------
Main entry point that orchestrates the full analysis pipeline:

    1. Load data (CSV or API)
    2. Clean and exclude
    3. Generate summaries
    4. Compute gradients
    5. Build modeling dataset
    6. Generate all plots
    7. Save outputs

Usage::

    python -m analysis.run_pipeline data/trials.csv
    python -m analysis.run_pipeline --api https://myserver.com
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import pandas as pd
import numpy as np

# Local modules
from .load_data import load_trials, load_from_api
from .clean import apply_all_exclusions
from .summaries import trial_level_summary, participant_summary, phase_summary
from .gradients import (
    compute_gradient,
    compute_gradient_by_block,
    group_mean_gradient,
)
from .modeling_dataset import build_modeling_dataset, save_modeling_dataset, ModelingConfig
from .plots import (
    plot_group_gradient,
    plot_individual_gradient,
    plot_gradient_evolution,
    plot_response_heatmap,
    plot_rt_by_distance,
    plot_participant_flow,
)


def _resolve_output_dir(base: Path) -> Path:
    """Return ``<repo_root>/outputs`` and create it if needed."""
    out = base / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    return out


def run(
    data_path: str | None = None,
    api_url: str | None = None,
    output_root: str | Path | None = None,
) -> None:
    """Execute the full analysis pipeline.

    Parameters
    ----------
    data_path : str, optional
        Path to a local CSV file with trial-level data.
    api_url : str, optional
        Base URL of the experiment server.  Used if *data_path* is None.
    output_root : str or Path, optional
        Root directory for outputs.  Defaults to ``../outputs`` relative
        to this file.
    """
    # ------------------------------------------------------------------
    # 0. Resolve paths
    # ------------------------------------------------------------------
    if output_root is None:
        output_root = Path(__file__).resolve().parent.parent / "outputs"
    else:
        output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Load data
    # ------------------------------------------------------------------
    print("=" * 60)
    print("STEP 1: Loading data")
    print("=" * 60)

    if data_path is not None:
        df_raw = load_trials(data_path)
        print(f"  Loaded {len(df_raw)} trials from {data_path}")
    elif api_url is not None:
        df_raw = load_from_api(api_url)
        print(f"  Loaded {len(df_raw)} trials from API ({api_url})")
    else:
        print("  ERROR: Provide either a CSV path or --api URL.")
        sys.exit(1)

    print(f"  Participants: {df_raw['participant_id'].nunique()}")
    print(f"  Phases: {sorted(df_raw['phase_id'].dropna().unique()) if 'phase_id' in df_raw.columns else 'N/A'}")
    print()

    # ------------------------------------------------------------------
    # 2. Clean and exclude
    # ------------------------------------------------------------------
    print("=" * 60)
    print("STEP 2: Cleaning and exclusions")
    print("=" * 60)

    df_clean, excl_summary = apply_all_exclusions(df_raw)

    for key, val in excl_summary.items():
        print(f"  {key}: {val}")
    print()

    # ------------------------------------------------------------------
    # 3. Trial-level summaries
    # ------------------------------------------------------------------
    print("=" * 60)
    print("STEP 3: Computing summaries")
    print("=" * 60)

    df_clean = trial_level_summary(df_clean)
    p_summary = participant_summary(df_clean)
    ph_summary = phase_summary(df_clean)

    print(f"  Participant summary: {len(p_summary)} participants")
    if len(p_summary) > 0:
        print(f"    Mean trials per participant: {p_summary['n_trials'].mean():.1f}")
        print(f"    Mean training response rate: {p_summary['response_rate_training'].mean():.3f}")
        print(f"    Mean probe response rate:    {p_summary['response_rate_probe'].mean():.3f}")
    print()

    # Save summaries
    p_summary.to_csv(output_root / "participant_summary.csv")
    ph_summary.to_csv(output_root / "phase_summary.csv", index=False)
    print(f"  Summaries saved to {output_root}/")
    print()

    # ------------------------------------------------------------------
    # 4. Gradients
    # ------------------------------------------------------------------
    print("=" * 60)
    print("STEP 4: Computing generalization gradients")
    print("=" * 60)

    group_grad = group_mean_gradient(df_clean)
    group_grad.to_csv(output_root / "group_gradient.csv", index=False)
    print(f"  Group gradient: {len(group_grad)} stimulus positions")

    # Per-phase gradients
    if "phase_id" in df_clean.columns:
        for phase in df_clean["phase_id"].dropna().unique():
            pg = group_mean_gradient(df_clean, phase_id=phase)
            pg.to_csv(output_root / f"group_gradient_{phase}.csv", index=False)
            print(f"  Phase '{phase}': {len(pg)} positions")

    # Per-participant gradients by block (for first few participants as example)
    pids = df_clean["participant_id"].unique()[:3] if "participant_id" in df_clean.columns else []
    for pid in pids:
        pdata = df_clean.loc[df_clean["participant_id"] == pid]
        gbb = compute_gradient_by_block(pdata)
        gbb.to_csv(output_root / f"gradient_by_block_{pid}.csv", index=False)
    print()

    # ------------------------------------------------------------------
    # 5. Modeling dataset
    # ------------------------------------------------------------------
    print("=" * 60)
    print("STEP 5: Building modeling dataset")
    print("=" * 60)

    config = ModelingConfig()
    df_model = build_modeling_dataset(df_clean, config)
    save_modeling_dataset(df_model, output_root / "modeling_dataset.csv")
    print(f"  Modeling dataset: {len(df_model)} trials x {len(df_model.columns)} features")
    print(f"  Saved to {output_root / 'modeling_dataset.csv'}")
    print()

    # ------------------------------------------------------------------
    # 6. Plots
    # ------------------------------------------------------------------
    print("=" * 60)
    print("STEP 6: Generating plots")
    print("=" * 60)

    out_str = str(output_root)

    # Group gradient
    fname = plot_group_gradient(group_grad, output_dir=out_str)
    print(f"  {fname}")

    # Individual gradients (first 3 participants)
    for pid in pids:
        fname = plot_individual_gradient(df_clean, str(pid), output_dir=out_str)
        print(f"  {fname}")

    # Gradient evolution (first participant with block data)
    if len(pids) > 0:
        pdata = df_clean.loc[df_clean["participant_id"] == pids[0]]
        gbb = compute_gradient_by_block(pdata)
        if len(gbb) > 0:
            fname = plot_gradient_evolution(gbb, output_dir=out_str)
            print(f"  {fname}")

    # Response heatmap (pooled)
    fname = plot_response_heatmap(df_clean, output_dir=out_str)
    print(f"  {fname}")

    # RT by distance
    fname = plot_rt_by_distance(df_clean, output_dir=out_str)
    print(f"  {fname}")

    # Participant flow
    fname = plot_participant_flow(excl_summary, output_dir=out_str)
    print(f"  {fname}")

    print()

    # ------------------------------------------------------------------
    # 7. Summary statistics
    # ------------------------------------------------------------------
    print("=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)
    print(f"  Total participants enrolled:   {excl_summary.get('participants_total', 'N/A')}")
    print(f"  Participants in final sample:  {excl_summary.get('participants_final', 'N/A')}")
    print(f"  Total trials in final sample:  {excl_summary.get('trials_final', 'N/A')}")

    if len(group_grad) > 0:
        peak_idx = group_grad["response_probability"].idxmax()
        peak_stim = group_grad.loc[peak_idx, "stimulus_x"]
        peak_prob = group_grad.loc[peak_idx, "response_probability"]
        print(f"  Peak gradient position:        {peak_stim:.2f} (P={peak_prob:.3f})")

    if len(p_summary) > 0:
        print(f"  Mean RT (responded trials):    {p_summary['mean_rt'].mean():.1f} ms")

    print()
    print(f"All outputs saved to: {output_root}")
    print("Pipeline complete.")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run the stimulus generalization analysis pipeline."
    )
    parser.add_argument(
        "data_path",
        nargs="?",
        default=None,
        help="Path to trial-level CSV file.",
    )
    parser.add_argument(
        "--api",
        dest="api_url",
        default=None,
        help="Base URL of the experiment API.",
    )
    parser.add_argument(
        "--output",
        dest="output_root",
        default=None,
        help="Output directory (default: ../outputs).",
    )
    args = parser.parse_args()

    run(
        data_path=args.data_path,
        api_url=args.api_url,
        output_root=args.output_root,
    )


if __name__ == "__main__":
    main()
