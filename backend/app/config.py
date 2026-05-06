from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # "anthropic" or "openrouter". Defaults to anthropic if a key is present,
    # else falls back to openrouter when its key is set.
    llm_provider: str = "anthropic"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"
    anthropic_embedding_model: str = "voyage-3"
    voyage_api_key: str = ""

    openrouter_api_key: str = ""
    openrouter_model: str = "qwen/qwen-2.5-72b-instruct"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_referer: str = "https://github.com/rohithkandula19/prior-auth-agent"
    openrouter_app_title: str = "Prior Authorization Agent"

    database_url: str = "postgresql://localhost/priorauth"
    faiss_index_dir: Path = Path("./data/faiss_indexes")
    synthea_output_dir: Path = Path("./data/patients/synthea")
    gold_set_path: Path = Path("./data/gold_set/v1.jsonl")
    log_level: str = "INFO"

    gcp_project_id: str = "rotune-493315"
    artifact_registry: str = "us-central1-docker.pkg.dev/rotune-493315"


settings = Settings()
