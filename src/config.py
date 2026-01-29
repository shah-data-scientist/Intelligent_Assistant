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
    mistral_api_key: str = ""  # Optional if using Google

    # Google API (Gemini)
    google_api_key: str = ""  # Optional if using Mistral

    # LLM Backend: "mistral", "google", or "huggingface"
    llm_backend: str = "huggingface"  # Using HuggingFace while Mistral is rate limited

    # HuggingFace settings (for llm_backend="huggingface")
    hf_token: str | None = None  # Set HF_TOKEN env var or provide here
    hf_model: str = "Qwen/Qwen2.5-7B-Instruct"  # 7B model, good at JSON output

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
    vector_dimension: int = 1024  # Mistral mistral-embed dimension

    # ========================================
    # RETRIEVAL TUNING PARAMETERS
    # ========================================
    # These parameters control the hybrid search behavior.
    # Adjust these to tune retrieval quality without code changes.

    retrieval_geo_radius_km: float = 50.0  # Radius for "nearby" city matching
    retrieval_keyword_boost: float = 1.5  # Boost factor for keyword matches
    retrieval_rrf_k: int = 60  # Reciprocal Rank Fusion parameter
    retrieval_date_window_days: int = 7  # Days to expand for alternative dates

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
    evaluation_llm_backend: str = "huggingface"
    evaluation_hf_model: str = "meta-llama/Meta-Llama-3-8B-Instruct"  # For Hugging Face
    evaluation_hf_token: str | None = None  # Set HF_TOKEN env var or provide here
    evaluation_ollama_model: str = "mistral"  # For Ollama (local)
    evaluation_ollama_url: str = "http://localhost:11434"  # Ollama server URL

    # ========================================
    # CHATBOT IDENTITY & PERSONALITY
    # ========================================
    # Single source of truth for the chatbot's identity.
    # Change these values here to update across all components.

    chatbot_name: str = "Lumi"
    chatbot_tagline_fr: str = "votre guide culturelle pour l'Ile-de-France"
    chatbot_tagline_en: str = "your cultural guide for Ile-de-France"

    # Personality traits (used in prompts and responses)
    chatbot_personality_fr: str = """- Chaleureuse et amicale - parle comme une amie passionnee de culture
- Enthousiaste et positive - celebre les decouvertes culturelles
- Utilise un ton decontracte mais professionnel
- Phrases amicales: "Super question !", "Oh, j'ai trouve des pepites !", "Genial !"
- Si pas de resultats: reste positive et encourageante ("Hmm, pas exactement ca, mais j'ai des alternatives sympa !")
- Termine souvent avec une touche amicale ("Bonne decouverte !" ou "Amuse-toi bien !")
- NE PAS utiliser d'emojis (problemes d'encodage)"""

    chatbot_personality_en: str = """- Warm and friendly - speaks like a friend who's passionate about culture
- Enthusiastic and positive - celebrates cultural discoveries
- Uses a casual but professional tone
- Friendly phrases: "Great question!", "Ooh, I found some gems!", "Awesome!"
- If no results: stays positive and encouraging ("Hmm, not quite that, but I've got some cool alternatives!")
- Often ends with a friendly touch ("Happy exploring!" or "Enjoy the show!")
- DO NOT use emojis (encoding issues)"""


settings = Settings()
