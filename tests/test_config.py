"""Tests for configuration module."""

from digital_brain.config import Settings


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.llm.provider == "gemini"
        assert s.qdrant.port == 6333
        assert s.neo4j.enabled is False
        assert s.reflection.schedule_hour == 3
        assert s.prediction.confidence_threshold == 0.7

    def test_embedder_defaults(self):
        s = Settings()
        assert s.embedder.provider == "ollama"
        assert s.embedder.dims == 768

    def test_api_defaults(self):
        s = Settings()
        assert s.api.host == "0.0.0.0"
        assert s.api.port == 8000

    def test_logging_defaults(self):
        s = Settings()
        assert s.logging.level == "INFO"
        assert s.logging.format == "json"

    def test_rate_limit_defaults(self):
        s = Settings()
        assert s.rate_limit.enabled is True
        assert s.rate_limit.requests_per_minute == 60

    def test_memory_defaults(self):
        s = Settings()
        assert s.memory.ttl_days == 0

    def test_prediction_max_preload_tokens(self):
        s = Settings()
        assert s.prediction.max_preload_tokens == 2000
