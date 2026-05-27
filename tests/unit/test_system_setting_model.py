"""Tests for system_setting model and db module."""

from aeros.models.system_setting import SystemSetting


class TestSystemSetting:
    def test_create_setting(self, session):
        """Should create and persist a SystemSetting."""
        setting = SystemSetting(key="test_key", value="test_value")
        session.add(setting)
        session.commit()
        session.refresh(setting)
        assert setting.id is not None
        assert setting.key == "test_key"
        assert setting.value == "test_value"

    def test_setting_default_value(self, session):
        """Should have empty string as default value."""
        setting = SystemSetting(key="another_key")
        session.add(setting)
        session.commit()
        session.refresh(setting)
        assert setting.value == ""

    def test_setting_query(self, session):
        """Should be queryable by key."""
        from sqlmodel import select

        setting = SystemSetting(key="queryable", value="yes")
        session.add(setting)
        session.commit()

        result = session.exec(select(SystemSetting).where(SystemSetting.key == "queryable")).first()
        assert result is not None
        assert result.value == "yes"


class TestDBModule:
    def test_get_session_returns_session(self):
        """get_session should be a generator function."""
        from aeros.db import get_session

        gen = get_session()
        session = next(gen)
        assert session is not None
        # Clean up
        try:
            next(gen)
        except StopIteration:
            pass
