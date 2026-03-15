"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Server and database settings, loaded from env vars or .env file."""

    database_url: str = (
        "postgresql+asyncpg://stim_gen:changeme_dev@localhost:5432/stimulus_generalization"
    )
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_cors_origins: str = "http://localhost:5173,http://localhost:3000"
    secret_key: str = "dev-secret-key"
    environment: str = "development"
    default_study_config: str = "default_pilot"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
