"""Configuration management using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Mistral API
    mistral_api_key: str

    # OpenAgenda API (via Opendatasoft)
    openagenda_base_url: str = (
        "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
        "evenements-publics-openagenda/records"
    )

    # Storage
    db_path: str = "./data/events.db"

    # Vector Store
    faiss_index_path: str = "./data/faiss_index"
    vector_dimension: int = 1024

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Application Settings
    log_level: str = "INFO"
    max_events_to_fetch: int = 5000  # Increased for Île-de-France coverage
    retrieval_top_k: int = 5

    # Data Ingestion
    min_events_required: int = 400  # Minimum for RAG system (adjusted for data availability)
    initial_time_window_months: int = 12  # Start with 1 year
    max_time_window_months: int = 36  # Maximum 3 years if needed


settings = Settings()
