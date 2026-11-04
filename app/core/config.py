import os
import json
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "NEIRO YOMI API"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "neiro-yomi-super-secret-key-2026-audiophile-listening")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database (Supabase PostgreSQL / SQLite fallback)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        os.getenv("SUPABASE_DB_URL", "sqlite:///./data/neiro_yomi.db")
    )

    # Supabase Integration (Backend Admin / Service Role)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_BUCKET_AUDIO: str = os.getenv("SUPABASE_BUCKET_AUDIO", "neiro-audio")
    SUPABASE_BUCKET_ARTWORK: str = os.getenv("SUPABASE_BUCKET_ARTWORK", "neiro-artwork")

    # Storage Provider: "local", "supabase", "s3"
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "supabase" if os.getenv("SUPABASE_URL") else "local")
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", "./storage")
    AUDIO_DIR: str = os.path.join(STORAGE_DIR, "audio")
    ARTWORK_DIR: str = os.path.join(STORAGE_DIR, "artwork")
    MAX_UPLOAD_SIZE_BYTES: int = 500 * 1024 * 1024  # 500MB

    # CORS Whitelist (String format to prevent Pydantic JSON decoding issues with '*')
    CORS_ORIGINS: str = "*"

    @property
    def cors_origins_list(self) -> List[str]:
        val = self.CORS_ORIGINS.strip() if self.CORS_ORIGINS else ""
        if not val or val == "*":
            return ["*"]
        if val.startswith("[") and val.endswith("]"):
            try:
                return json.loads(val)
            except Exception:
                pass
        return [i.strip() for i in val.split(",") if i.strip()]

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="allow")

settings = Settings()

# Ensure local storage directories exist (used for cache/fallback)
os.makedirs(settings.AUDIO_DIR, exist_ok=True)
os.makedirs(settings.ARTWORK_DIR, exist_ok=True)
os.makedirs("./data", exist_ok=True)
