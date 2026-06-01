"""Application configuration loaded from environment / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5433/pdm_copilot"

    # Auth
    secret_key: str = "dev-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # Groq LLM
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    llm_stub_mode: bool = False

    # MLflow
    mlflow_tracking_uri: str = "file:./mlruns"
    mlflow_experiment: str = "pdm-anomaly-detection"

    # RAG
    chroma_dir: str = "./chroma_store"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Storage
    upload_dir: str = "./uploads"

    # Anomaly detection defaults
    zscore_threshold: float = 3.0
    rolling_window: int = 10

    # --- Phase 4: async jobs + Spark ---
    # When true, uploads dispatch to Celery; otherwise FastAPI BackgroundTasks.
    use_celery: bool = False
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ETL engine: "pandas" (default) or "spark".
    etl_engine: str = "pandas"
    # Set so PySpark finds the JVM + Hadoop winutils on native Windows.
    java_home: str = ""
    hadoop_home: str = ""

    # --- Phase 6: energy & carbon defaults ---
    # Default region (selects the grid emission factor) and currency for new records.
    default_region: str = "IN"
    default_currency: str = "INR"
    # Fallback electricity tariff (currency per kWh) for savings estimates when no
    # utility bill is available to derive an effective tariff from.
    electricity_tariff: float = 8.0
    # Efficiency penalty (fraction of energy wasted) assumed per worst-severity bucket
    # for a degrading machine. Conservative, clearly-labelled estimates.
    waste_penalty_high: float = 0.08
    waste_penalty_medium: float = 0.04
    waste_penalty_monitor: float = 0.015

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
