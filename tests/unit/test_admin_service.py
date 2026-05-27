"""Tests for admin_service — user suspension, org listing, health."""

import pytest

from aeros.models.organization import Organization
from aeros.models.user import Role, User, UserStatus
from aeros.services.admin_service import (
    get_system_health,
    list_organizations,
    reactivate_user,
    suspend_user,
)
from aeros.services.auth_service import hash_password


@pytest.fixture
def admin_user(session, buyer_org):
    user = User(
        email="admin@test.com",
        password_hash=hash_password("test123"),
        role=Role.ADMIN,
        display_name="Test Admin",
        org_id=buyer_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def target_user(session, buyer_org):
    user = User(
        email="target@test.com",
        password_hash=hash_password("test123"),
        role=Role.BUYER,
        display_name="Target User",
        org_id=buyer_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


class TestSuspendUser:
    def test_suspend_active_user(self, session, admin_user, target_user):
        """Should suspend an active user and set suspended_at."""
        result = suspend_user(session, target_user.id, admin_user.id, reason="Policy violation")
        assert result.status == UserStatus.SUSPENDED
        assert result.suspended_at is not None
        assert result.suspended_by_admin_id == admin_user.id

    def test_suspend_nonexistent_user(self, session, admin_user):
        """Should raise ValueError for nonexistent user."""
        with pytest.raises(ValueError, match="not found"):
            suspend_user(session, 99999, admin_user.id)

    def test_suspend_self_forbidden(self, session, admin_user):
        """Admin should not be able to suspend themselves."""
        with pytest.raises(ValueError, match="Cannot suspend yourself"):
            suspend_user(session, admin_user.id, admin_user.id)


class TestReactivateUser:
    def test_reactivate_suspended_user(self, session, admin_user, target_user):
        """Should reactivate a suspended user."""
        suspend_user(session, target_user.id, admin_user.id)
        result = reactivate_user(session, target_user.id, admin_user.id)
        assert result.status == UserStatus.ACTIVE
        assert result.suspended_at is None
        assert result.suspended_by_admin_id is None

    def test_reactivate_nonexistent_user(self, session, admin_user):
        """Should raise ValueError for nonexistent user."""
        with pytest.raises(ValueError, match="not found"):
            reactivate_user(session, 99999, admin_user.id)


class TestListOrganizations:
    def test_list_orgs(self, session, buyer_org):
        """Should return all organizations."""
        orgs = list_organizations(session)
        assert len(orgs) >= 1
        names = [o.name for o in orgs]
        assert "TestBuyerOrg" in names

    def test_list_orgs_ordered_by_id(self, session, buyer_org):
        """Organizations should be ordered by id."""
        orgs = list_organizations(session)
        ids = [o.id for o in orgs]
        assert ids == sorted(ids)


class TestGetSystemHealth:
    def test_health_returns_structure(self):
        """Should return health status for api, database, and ai_provider."""
        health = get_system_health()
        assert "api" in health
        assert "database" in health
        assert "ai_provider" in health
        assert health["api"]["status"] == "healthy"
