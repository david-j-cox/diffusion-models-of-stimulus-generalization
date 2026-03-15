"""Seed the database with a default study config and test participants.

Usage:
    cd backend
    python -m scripts.seed

Requires DATABASE_URL env var or uses the default from app.config.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Resolve imports: ensure the backend package is on sys.path
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.config import settings  # noqa: E402
from app.models import Base, ConditionAssignment, Participant, StudyConfig  # noqa: E402
from app.services.study_loader import config_hash, load_yaml  # noqa: E402


DATABASE_URL = os.environ.get("DATABASE_URL", settings.database_url)

# ---------------------------------------------------------------------------
# Test participant specs
# ---------------------------------------------------------------------------
TEST_PARTICIPANTS = [
    {"external_id": "test_pilot_001", "is_pilot": True},
    {"external_id": "test_pilot_002", "is_pilot": True},
    {"external_id": "test_pilot_003", "is_pilot": True},
]

CONFIG_NAME = "default_pilot"


async def seed() -> None:
    """Create the default study config and three test participants."""

    engine = create_async_engine(DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        # Ensure tables exist (idempotent)
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as db:
        # --- Study Config ---------------------------------------------------
        cfg_dict = load_yaml(CONFIG_NAME)
        h = config_hash(cfg_dict)

        result = await db.execute(
            text("SELECT id FROM study_configs WHERE config_hash = :h"), {"h": h}
        )
        existing = result.first()

        if existing:
            sc_id = existing[0]
            print(f"Study config '{CONFIG_NAME}' already exists  (id={sc_id})")
        else:
            sc = StudyConfig(
                name=cfg_dict["name"],
                version=cfg_dict["version"],
                config_hash=h,
                config_json=cfg_dict,
            )
            db.add(sc)
            await db.flush()
            sc_id = sc.id
            print(f"Created study config '{CONFIG_NAME}'  (id={sc_id})")

        # --- Conditions list -------------------------------------------------
        conditions = cfg_dict.get("conditions", [])
        if not conditions:
            conditions = [
                {"name": "default", "target_x": cfg_dict["stimulus"]["target_x"]}
            ]

        # --- Participants ----------------------------------------------------
        for idx, spec in enumerate(TEST_PARTICIPANTS):
            ext_id = spec["external_id"]

            result = await db.execute(
                text("SELECT id FROM participants WHERE external_id = :eid"),
                {"eid": ext_id},
            )
            if result.first():
                print(f"  Participant '{ext_id}' already exists — skipping")
                continue

            p = Participant(
                external_id=ext_id,
                study_config_id=sc_id,
                is_pilot=spec["is_pilot"],
            )
            db.add(p)
            await db.flush()

            # Round-robin condition assignment
            cond_idx = idx % len(conditions)
            cond = conditions[cond_idx]
            target_x = cond.get("target_x", cfg_dict["stimulus"]["target_x"])

            import hashlib

            digest = hashlib.sha256(f"{ext_id}:{h}".encode()).hexdigest()
            seed_val = int(digest[:8], 16)

            ca = ConditionAssignment(
                participant_id=p.id,
                condition_name=cond["name"],
                condition_index=cond_idx,
                target_x=target_x,
                random_seed=seed_val,
                assignment_json=cond,
            )
            db.add(ca)
            await db.flush()

            print(
                f"  Created participant '{ext_id}'  "
                f"(id={p.id}, condition='{cond['name']}', seed={seed_val})"
            )

        await db.commit()

    await engine.dispose()
    print("\nSeed complete.")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
