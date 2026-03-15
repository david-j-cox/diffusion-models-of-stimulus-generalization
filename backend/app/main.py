"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import admin, participants, study, trials

app = FastAPI(
    title="Stimulus Generalization Experiment API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers under /api
app.include_router(participants.router, prefix="/api")
app.include_router(trials.router, prefix="/api")
app.include_router(study.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "environment": settings.environment}
