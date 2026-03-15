"""Load and validate study configuration from YAML files.

Study configs are loaded from the backend/app/study_configs/ directory.
Once loaded, an immutable snapshot is stored in the database.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StudyConfig

CONFIGS_DIR = Path(__file__).parent.parent / "study_configs"

# Required top-level keys in a valid study config
REQUIRED_KEYS = {"name", "version", "stimulus", "phases", "timing", "feedback"}


def load_yaml(config_name: str) -> dict[str, Any]:
    """Load a study config YAML file by name (without extension)."""
    path = CONFIGS_DIR / f"{config_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Study config not found: {path}")
    with open(path) as f:
        config = yaml.safe_load(f)
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    """Validate that a study config has all required fields.

    Raises ValueError on invalid config — fail loudly.
    """
    missing = REQUIRED_KEYS - set(config.keys())
    if missing:
        raise ValueError(f"Study config missing required keys: {missing}")

    stim = config["stimulus"]
    if "target_x" not in stim:
        raise ValueError("stimulus.target_x is required")
    if not (0.0 <= stim["target_x"] <= 1.0):
        raise ValueError("stimulus.target_x must be in [0, 1]")

    for i, phase in enumerate(config["phases"]):
        if "id" not in phase:
            raise ValueError(f"Phase {i} missing 'id'")

    # Validate probe positions are in [0, 1]
    for p in stim.get("probe_positions", []):
        if not (0.0 <= p <= 1.0):
            raise ValueError(f"Probe position {p} out of [0, 1]")


def config_hash(config: dict[str, Any]) -> str:
    """Deterministic hash of the config for deduplication."""
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


async def ensure_study_config(db: AsyncSession, config_name: str) -> tuple[StudyConfig, dict]:
    """Load a study config, store it in the DB if new, and return the ORM object + dict.

    If a config with the same hash already exists, returns the existing row.
    """
    config_dict = load_yaml(config_name)
    h = config_hash(config_dict)

    existing = await db.execute(
        select(StudyConfig).where(StudyConfig.config_hash == h)
    )
    row = existing.scalar_one_or_none()
    if row:
        return row, config_dict

    sc = StudyConfig(
        name=config_dict["name"],
        version=config_dict["version"],
        config_hash=h,
        config_json=config_dict,
    )
    db.add(sc)
    await db.flush()
    return sc, config_dict
