from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI Viva Examiner"
    APP_ENV: str = "development"
    SECRET_KEY: str = Field(default="dev-secret-key", env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Gemini (free tier — 1500 req/day)
    GEMINI_API_KEY: str = Field(default="", env="GEMINI_API_KEY")
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Groq Whisper — free voice transcription (get key at https://console.groq.com)
    GROQ_API_KEY: str = Field(default="", env="GROQ_API_KEY")

    # OpenAI (optional — kept for future use)
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4o", env="OPENAI_MODEL")

    # Database
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///./viva_dev.db", env="DATABASE_URL")

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # File Upload
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 50

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


settings = Settings()
