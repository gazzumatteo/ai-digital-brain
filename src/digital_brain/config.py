"""Centralized configuration using Pydantic Settings."""

from __future__ import annotations

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Mapping: llm_provider -> (embedder_model, embedding_dims)
_EMBEDDER_DEFAULTS: dict[str, tuple[str, int]] = {
    "gemini": ("gemini-embedding-001", 3072),
    "openai": ("text-embedding-3-small", 1536),
    "ollama": ("nomic-embed-text:latest", 768),
}


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="LLM_",
        populate_by_name=True,
        extra="ignore",
    )

    provider: str = "gemini"
    model: str = Field("gemini-3-flash-preview", alias="LLM_MODEL")
    ollama_base_url: str = Field("http://localhost:11434", validation_alias="OLLAMA_BASE_URL")
    google_api_key: str = Field("", validation_alias="GOOGLE_API_KEY")
    openai_api_key: str = Field("", validation_alias="OPENAI_API_KEY")


class EmbedderSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="EMBEDDER_",
        populate_by_name=True,
        extra="ignore",
    )

    provider: str = "auto"
    model: str = "nomic-embed-text:latest"
    dims: int = Field(768, validation_alias="EMBEDDING_DIMS")
    ollama_base_url: str = Field("http://localhost:11434", validation_alias="OLLAMA_BASE_URL")


class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="QDRANT_", extra="ignore"
    )

    host: str = "localhost"
    port: int = 6333
    collection: str = "digital_brain_memories"


class Neo4jSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="NEO4J_", extra="ignore"
    )

    enabled: bool = False
    url: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"


class ReflectionSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="REFLECTION_", extra="ignore"
    )

    schedule_hour: int = 3
    schedule_minute: int = 0
    lookback_hours: int = 24
    min_memories: int = 3


class PredictionSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="PREDICTION_", extra="ignore"
    )

    confidence_threshold: float = 0.7
    max_preload_memories: int = 10
    max_preload_tokens: int = Field(2000, validation_alias="MAX_PRELOAD_TOKENS")


class MemorySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="MEMORY_", extra="ignore"
    )

    ttl_days: int = Field(0, description="Auto-expire memories after N days (0 = disabled)")


class LoggingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="LOG_", extra="ignore"
    )

    level: str = "INFO"
    format: str = Field("json", description="Log format: 'json' or 'text'")


class RateLimitSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="RATE_LIMIT_", extra="ignore"
    )

    enabled: bool = True
    requests_per_minute: int = 60


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="API_", extra="ignore"
    )

    host: str = "0.0.0.0"
    port: int = 8000


class TelegramSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="TELEGRAM_", extra="ignore"
    )

    enabled: bool = False
    bot_token: str = ""
    webhook_url: str = Field("", description="If empty, uses polling mode")
    webhook_secret: str = ""
    dm_policy: str = Field("pairing", description="open | pairing | disabled")
    allow_from: list[str] = Field(default_factory=list)
    debounce_ms: int = 1500


class MediaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="MEDIA_", extra="ignore"
    )

    max_file_size_mb: int = 20
    allowed_types: list[str] = Field(
        default_factory=lambda: ["image/*", "audio/*", "video/*", "application/pdf"]
    )


class Settings(BaseSettings):
    """Root settings aggregating all sub-configurations."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedder: EmbedderSettings = Field(default_factory=EmbedderSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    reflection: ReflectionSettings = Field(default_factory=ReflectionSettings)
    prediction: PredictionSettings = Field(default_factory=PredictionSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    api: APISettings = Field(default_factory=APISettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    media: MediaSettings = Field(default_factory=MediaSettings)

    @model_validator(mode="after")
    def _resolve_embedder_auto(self) -> Settings:
        """When EMBEDDER_PROVIDER is 'auto', mirror the LLM provider with sensible defaults."""
        if self.embedder.provider == "auto":
            provider = self.llm.provider
            model, dims = _EMBEDDER_DEFAULTS.get(provider, ("nomic-embed-text:latest", 768))
            self.embedder.provider = provider
            self.embedder.model = model
            self.embedder.dims = dims
        return self


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return cached settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
