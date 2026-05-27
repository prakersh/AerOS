"""Tests for system_settings_service — settings management with defaults."""

from aeros.services.system_settings_service import (
    DEFAULT_SETTINGS,
    get_all_settings,
    get_setting,
    update_setting,
)


class TestGetSetting:
    def test_get_default_setting(self, session):
        """Should return default value for a known key."""
        value = get_setting(session, "max_upload_size_mb")
        assert value == "25"

    def test_get_unknown_setting(self, session):
        """Should return None for unknown key."""
        value = get_setting(session, "nonexistent_key")
        assert value is None

    def test_get_rate_limit(self, session):
        """Should return the default rate limit value."""
        value = get_setting(session, "rate_limit_rpm")
        assert value == "60"


class TestGetAllSettings:
    def test_returns_all_defaults(self, session):
        """Should return all default settings."""
        settings = get_all_settings(session)
        assert len(settings) == len(DEFAULT_SETTINGS)

    def test_settings_have_required_fields(self, session):
        """Each setting should have key, value, type, description, source."""
        settings = get_all_settings(session)
        for s in settings:
            assert "key" in s
            assert "value" in s
            assert "type" in s
            assert "description" in s
            assert "source" in s

    def test_defaults_source_is_default(self, session):
        """All fallback settings should have source='default'."""
        settings = get_all_settings(session)
        for s in settings:
            assert s["source"] == "default"

    def test_known_keys_present(self, session):
        """All known setting keys should be present."""
        settings = get_all_settings(session)
        keys = {s["key"] for s in settings}
        assert "max_upload_size_mb" in keys
        assert "rate_limit_rpm" in keys
        assert "ai_budget_per_rfx" in keys
        assert "session_timeout_minutes" in keys


class TestUpdateSetting:
    def test_update_returns_dict(self, session):
        """update_setting should return a dict with key and value."""
        result = update_setting(session, "max_upload_size_mb", "50", user_id=1)
        assert result["key"] == "max_upload_size_mb"
        assert result["value"] == "50"

    def test_update_nonexistent_model_graceful(self, session):
        """Should handle missing SystemSetting model gracefully."""
        # This test verifies the try/except fallback works
        result = update_setting(session, "rate_limit_rpm", "120", user_id=1)
        assert result["key"] == "rate_limit_rpm"
        assert result["value"] == "120"


class TestDefaultSettings:
    def test_defaults_not_empty(self):
        """DEFAULT_SETTINGS should have entries."""
        assert len(DEFAULT_SETTINGS) > 0

    def test_each_default_has_value_and_type(self):
        """Each default should have value, type, and description."""
        for key, default in DEFAULT_SETTINGS.items():
            assert "value" in default, f"{key} missing 'value'"
            assert "type" in default, f"{key} missing 'type'"
            assert "description" in default, f"{key} missing 'description'"
