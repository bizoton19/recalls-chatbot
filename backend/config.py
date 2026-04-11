"""
Central settings — reads from environment variables.
All defaults are safe for local development.
Production values are set in the Railway dashboard.
"""
import os
from pathlib import Path

# Load project-root .env when running `uvicorn` from backend/ (local dev)
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Required environment variable {key!r} is not set.")
    return val


def get_database_url(async_driver: bool = True) -> str:
    """
    Railway injects DATABASE_URL as postgres:// or postgresql://.
    asyncpg requires postgresql+asyncpg://.
    psycopg2 requires postgresql://.
    """
    raw = os.getenv("DATABASE_URL", "")

    if not raw:
        # Fall back to individual vars (local dev)
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        user = os.getenv("DB_USER", "recalls_user")
        password = os.getenv("DB_PASSWORD", "recalls_dev_password")
        dbname = os.getenv("DB_NAME", "recalls")
        raw = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

    # Normalize postgres:// → postgresql://
    raw = raw.replace("postgres://", "postgresql://", 1)

    if async_driver:
        # Insert asyncpg driver
        return raw.replace("postgresql://", "postgresql+asyncpg://", 1)

    return raw


# Application settings
class Settings:
    # Database
    database_url: str = get_database_url(async_driver=True)
    database_url_sync: str = get_database_url(async_driver=False)

    # LLM
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "google")

    # API Keys (optional — only required if using that provider)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")

    # CORS — comma-separated list of allowed origins
    # In Railway, set to your frontend public URL:
    #   https://recalls-chatbot-frontend.up.railway.app
    cors_origins: list[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        if o.strip()
    ]

    # Admin
    admin_api_key: str = os.getenv("ADMIN_API_KEY", "dev-admin-key")

    # Ingestion
    ingestion_schedule_hours: int = int(os.getenv("INGESTION_SCHEDULE_HOURS", "6"))

    # Environment
    environment: str = os.getenv("RAILWAY_ENVIRONMENT", os.getenv("ENV", "development"))

    @property
    def is_production(self) -> bool:
        return self.environment in ("production", "staging")


settings = Settings()
