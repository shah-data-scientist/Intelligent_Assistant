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
    chat_db_path: str = "./data/chat_history.db"

    # Vector Store
    faiss_index_path: str = "./data/faiss_index"
    vector_dimension: int = 1024

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Application Settings
    log_level: str = "INFO"
    max_events_to_fetch: int = 20000  # Increased to ensure enough IDF events
    retrieval_top_k: int = 10
    app_api_key: str = "dev-secret-key"  # Change this in production!

    # Data Ingestion
    min_events_required: int = 1000  # Target number of events
    initial_time_window_months: int = 12  # Start with 1 year
    max_time_window_months: int = 36  # Maximum 3 years if needed

    # Evaluation Settings
    golden_dataset_path: str = "./data/evaluation/golden_dataset.json"
    evaluation_llm_temperature: float = 0.0  # Deterministic for consistent scoring
    evaluation_cache_enabled: bool = True
    evaluation_latency_sla_ms: float = 2000.0  # 2 seconds
    evaluation_quality_sla: float = 0.8  # 80% quality score

    # Evaluation LLM Backend
    # Options: "mistral" (paid), "huggingface" (free tier), "ollama" (local free)
    evaluation_llm_backend: str = "mistral"
    evaluation_hf_model: str = "mistralai/Mistral-7B-Instruct-v0.2"  # For Hugging Face
    evaluation_hf_token: str | None = None  # Set HF_TOKEN env var or provide here
    evaluation_ollama_model: str = "mistral"  # For Ollama (local)
    evaluation_ollama_url: str = "http://localhost:11434"  # Ollama server URL


settings = Settings()
