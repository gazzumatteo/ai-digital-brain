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
