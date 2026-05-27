"""Tests for ai_config_service — AI provider listing and connectivity checks."""

from aeros.services import ai_config_service


class TestListProviders:
    def test_returns_list(self, session):
        """Should return a list of provider dicts."""
        providers = ai_config_service.list_providers(session)
        assert isinstance(providers, list)
        assert len(providers) >= 1

    def test_providers_have_required_fields(self, session):
        """Each provider should have id, provider_name, model_id, display_name, capability, status."""
        providers = ai_config_service.list_providers(session)
        for p in providers:
            assert "id" in p
            assert "provider_name" in p
            assert "model_id" in p
            assert "display_name" in p
            assert "capability" in p
            assert "status" in p

    def test_fallback_includes_nvidia_and_groq(self, session):
        """Env fallback should include nvidia_nim and groq providers."""
        providers = ai_config_service.list_providers(session)
        provider_names = {p["provider_name"] for p in providers}
        assert "nvidia_nim" in provider_names
        assert "groq" in provider_names

    def test_fallback_includes_all_capabilities(self, session):
        """Env fallback should cover chat, vision, embedding, and asr capabilities."""
        providers = ai_config_service.list_providers(session)
        capabilities = {p["capability"] for p in providers}
        assert "chat" in capabilities
        assert "vision" in capabilities
        assert "embedding" in capabilities
        assert "asr" in capabilities


class TestTestProviderConnection:
    def test_unknown_provider(self):
        """Unknown provider should return ok=False."""
        result = ai_config_service.test_provider_connection("nonexistent_provider")
        assert result["ok"] is False
        assert "Unknown provider" in result["error"]

    def test_nvidia_without_key(self, monkeypatch):
        """nvidia_nim without API key should report not set."""
        monkeypatch.setattr("aeros.services.ai_config_service.settings.nvidia_api_key", "")
        result = ai_config_service.test_provider_connection("nvidia_nim")
        assert result["ok"] is False
        assert "not set" in result["error"]

    def test_groq_without_key(self, monkeypatch):
        """groq without API key should report not set."""
        monkeypatch.setattr("aeros.services.ai_config_service.settings.groq_api_key", "")
        result = ai_config_service.test_provider_connection("groq")
        assert result["ok"] is False
        assert "not set" in result["error"]

    def test_nvidia_with_key(self, monkeypatch):
        """nvidia_nim with API key should return ok=True."""
        monkeypatch.setattr(
            "aeros.services.ai_config_service.settings.nvidia_api_key", "nvapi-test-key"
        )
        result = ai_config_service.test_provider_connection("nvidia_nim")
        assert result["ok"] is True

    def test_groq_with_key(self, monkeypatch):
        """groq with API key should return ok=True."""
        monkeypatch.setattr(
            "aeros.services.ai_config_service.settings.groq_api_key", "gsk_test_key"
        )
        result = ai_config_service.test_provider_connection("groq")
        assert result["ok"] is True
