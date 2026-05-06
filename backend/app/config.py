from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"
    anthropic_embedding_model: str = "voyage-3"
    voyage_api_key: str = ""

    database_url: str = "postgresql://localhost/priorauth"
    faiss_index_dir: Path = Path("./data/faiss_indexes")
    synthea_output_dir: Path = Path("./data/patients/synthea")
    gold_set_path: Path = Path("./data/gold_set/v1.jsonl")
    log_level: str = "INFO"

    gcp_project_id: str = "rotune-493315"
    artifact_registry: str = "us-central1-docker.pkg.dev/rotune-493315"


settings = Settings()
