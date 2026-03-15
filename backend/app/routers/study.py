"""Study configuration endpoints — preview stimuli and inspect configs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.sequence import generate_full_sequence
from app.services.study_loader import ensure_study_config, load_yaml

router = APIRouter(prefix="/study", tags=["study"])


@router.get("/config")
async def get_study_config() -> dict:
    """Return the current default study configuration."""
    try:
        config = load_yaml(settings.default_study_config)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Default study config not found")
    return config


@router.get("/preview-sequence")
async def preview_sequence(
    target_x: float = 0.5,
    seed: int = 42,
) -> dict:
    """Preview the trial sequence for a given target and seed.

    Useful for verifying the experiment structure without registering.
    """
    config = load_yaml(settings.default_study_config)
    trials = generate_full_sequence(config, target_x, seed)
    return {
        "total_trials": len(trials),
        "phases": list({t["phase_id"] for t in trials}),
        "trials": trials,
    }


@router.get("/preview-stimulus")
async def preview_stimulus(x_normalized: float = 0.5) -> dict:
    """Return the rendered stimulus parameters for a given normalized position.

    Useful for the admin stimulus previewer.
    """
    config = load_yaml(settings.default_study_config)
    stim = config["stimulus"]
    axis_min = stim.get("axis_min", 20.0)
    axis_max = stim.get("axis_max", 160.0)
    render_value = axis_min + x_normalized * (axis_max - axis_min)
    return {
        "x_normalized": x_normalized,
        "render_value": render_value,
        "unit": stim.get("axis_unit", "degrees"),
        "family": stim.get("family", "orientation"),
    }
