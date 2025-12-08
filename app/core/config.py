"""
Configuration settings for Music-to-MIDI API
Loads settings from environment variables
"""

import os
from typing import Optional


class Settings:
    """Application settings loaded from environment variables"""

    # Security
    API_KEY: Optional[str] = os.getenv("API_KEY")

    # Server
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # Model Loading
    SKIP_MODEL_LOADING: bool = os.getenv("SKIP_MODEL_LOADING", "0") == "1"

    # Auto-reload
    ENABLE_RELOAD: bool = os.getenv("ENABLE_RELOAD", "0") == "1"

    # Processing
    BYPASS_DEMUCS: bool = os.getenv("BYPASS_DEMUCS", "0") == "1"

    # Upload Limits
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "500"))

    # CORS
    ALLOWED_ORIGINS: list = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:8000"
    ).split(",")

    # Performance
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "600"))


# Global settings instance
settings = Settings()
