"""
Application configuration with environment variable loading and fallbacks.
Supports offline operation; LLM is optional.
"""
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
    _project_root = Path(__file__).resolve().parent.parent
    load_dotenv(_project_root / ".env")
except ImportError:
    pass


class Settings(BaseModel):
    """Centralized settings for BattWise AI backend."""

    # API
    api_host: str = Field(default="0.0.0.0", description="Bind host for FastAPI")
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_prefix: str = Field(default="", description="URL prefix for API routes")

    # Gemini (optional; core logic works without it)
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")
    gemini_model: str = Field(default="gemini-2.0-flash", description="Gemini model name (e.g. gemini-2.0-flash, gemini-1.5-flash)")
    gemini_timeout_seconds: float = Field(default=15.0, ge=1.0, le=60.0)

    # Battery / simulation defaults
    battery_capacity_kwh: float = Field(default=10.0, ge=0.1, le=100.0)
    min_soc_percent: float = Field(default=20.0, ge=0.0, le=100.0)
    max_soc_percent: float = Field(default=95.0, ge=0.0, le=100.0)
    initial_soc_percent: float = Field(default=80.0, ge=0.0, le=100.0)

    # Paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment with safe fallbacks."""
        return cls(
            api_host=os.getenv("API_HOST", "0.0.0.0"),
            api_port=int(os.getenv("API_PORT", "8000")),
            api_prefix=os.getenv("API_PREFIX", "").strip(),
            gemini_api_key=(os.getenv("GEMINI_API_KEY") or "").strip().strip('"').strip("'") or None,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            gemini_timeout_seconds=float(os.getenv("GEMINI_TIMEOUT", "15")),
            battery_capacity_kwh=float(os.getenv("BATTERY_CAPACITY_KWH", "10")),
            min_soc_percent=float(os.getenv("MIN_SOC_PERCENT", "20")),
            max_soc_percent=float(os.getenv("MAX_SOC_PERCENT", "95")),
            initial_soc_percent=float(os.getenv("INITIAL_SOC_PERCENT", "80")),
        )

    @property
    def has_llm(self) -> bool:
        """True if Gemini API key is set and LLM layer can be used."""
        return bool(self.gemini_api_key and self.gemini_api_key.strip())


# Singleton used across the app
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Return application settings (lazy load from env)."""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings
