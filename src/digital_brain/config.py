"""Centralized configuration using Pydantic Settings."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        populate_by_name=True,
        extra="ignore",
    )

    provider: str = "gemini"
    model: str = Field("gemini-2.0-flash", alias="LLM_MODEL")
    ollama_base_url: str = Field("http://localhost:11434", validation_alias="OLLAMA_BASE_URL")
    google_api_key: str = Field("", validation_alias="GOOGLE_API_KEY")
    openai_api_key: str = Field("", validation_alias="OPENAI_API_KEY")


class EmbedderSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EMBEDDER_",
        populate_by_name=True,
        extra="ignore",
    )

    provider: str = "ollama"
    model: str = "nomic-embed-text:latest"
    dims: int = Field(768, validation_alias="EMBEDDING_DIMS")
    ollama_base_url: str = Field("http://localhost:11434", validation_alias="OLLAMA_BASE_URL")


class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QDRANT_", extra="ignore")

    host: str = "localhost"
    port: int = 6333
    collection: str = "digital_brain_memories"


class Neo4jSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NEO4J_", extra="ignore")

    enabled: bool = False
    url: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"


class ReflectionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REFLECTION_", extra="ignore")

    schedule_hour: int = 3
    schedule_minute: int = 0
    lookback_hours: int = 24
    min_memories: int = 3


class PredictionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PREDICTION_", extra="ignore")

    confidence_threshold: float = 0.7
    max_preload_memories: int = 10


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="API_", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8000


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
    api: APISettings = Field(default_factory=APISettings)


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return cached settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
