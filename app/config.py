from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

from app.env_utils import env_bool, env_float, env_int, env_str

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseModel):
    mistral_api_key: str = ""
    mistral_model: str = "mistral-small-latest"
    mistral_url: str = "https://api.mistral.ai/v1/chat/completions"
    mistral_timeout_seconds: float = 45.0
    mistral_max_tokens: int = 3500
    mistral_temperature: float = 0.1

    tavily_api_key: str = ""
    tavily_url: str = "https://api.tavily.com/search"
    tavily_timeout_seconds: float = 30.0
    tavily_max_results: int = 5
    tavily_search_depth: str = "basic"
    tavily_topic: str = "general"

    http_max_attempts: int = 3
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    database_path: str = str(PROJECT_ROOT / "data" / "guides.db")
    seed_guides_path: str = str(PROJECT_ROOT / "data" / "seed_guides.json")
    max_sources_for_model: int = 12
    max_source_chars: int = 1200
    log_secrets: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        return origins or ["http://localhost:3000", "http://localhost:5173"]

    def missing_live_keys(self) -> list[str]:
        missing: list[str] = []
        if not self.mistral_api_key.strip():
            missing.append("MISTRAL_API_KEY")
        if not self.tavily_api_key.strip():
            missing.append("TAVILY_API_KEY")
        return missing

    def secret_values(self) -> list[str]:
        return [value for value in (self.mistral_api_key, self.tavily_api_key) if value]


def build_settings() -> Settings:
    return Settings(
        mistral_api_key=env_str("MISTRAL_API_KEY"),
        mistral_model=env_str("MISTRAL_MODEL", "mistral-small-latest") or "mistral-small-latest",
        mistral_url=env_str("MISTRAL_URL", "https://api.mistral.ai/v1/chat/completions")
        or "https://api.mistral.ai/v1/chat/completions",
        mistral_timeout_seconds=env_float("MISTRAL_TIMEOUT_SECONDS", 45.0),
        mistral_max_tokens=env_int("MISTRAL_MAX_TOKENS", 3500),
        mistral_temperature=env_float("MISTRAL_TEMPERATURE", 0.1),
        tavily_api_key=env_str("TAVILY_API_KEY"),
        tavily_url=env_str("TAVILY_URL", "https://api.tavily.com/search") or "https://api.tavily.com/search",
        tavily_timeout_seconds=env_float("TAVILY_TIMEOUT_SECONDS", 30.0),
        tavily_max_results=max(1, min(env_int("TAVILY_MAX_RESULTS", 5), 10)),
        tavily_search_depth=env_str("TAVILY_SEARCH_DEPTH", "basic") or "basic",
        tavily_topic=env_str("TAVILY_TOPIC", "general") or "general",
        http_max_attempts=max(1, min(env_int("HTTP_MAX_ATTEMPTS", 3), 4)),
        cors_origins=env_str("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"),
        database_path=env_str("DATABASE_PATH", str(PROJECT_ROOT / "data" / "guides.db"))
        or str(PROJECT_ROOT / "data" / "guides.db"),
        seed_guides_path=env_str("SEED_GUIDES_PATH", str(PROJECT_ROOT / "data" / "seed_guides.json"))
        or str(PROJECT_ROOT / "data" / "seed_guides.json"),
        max_sources_for_model=env_int("MAX_SOURCES_FOR_MODEL", 12),
        max_source_chars=env_int("MAX_SOURCE_CHARS", 1200),
        log_secrets=env_bool("LOG_SECRETS", False),
    )


@lru_cache
def get_settings() -> Settings:
    return build_settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
