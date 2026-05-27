"""Tests for aeros.db_scope — RBAC query-scope filter."""

import pytest
from sqlmodel import Field, Session, SQLModel, create_engine, select

from aeros.db_scope import MissingScopeError, for_user
from aeros.models.user import Role
from aeros.security.auth_context import AuthContext


# --- Dummy model for testing scope filters ---


class ScopedItem(SQLModel, table=True):
    __tablename__ = "scoped_item"

    id: int | None = Field(default=None, primary_key=True)
    org_id: int = 0
    owner_user_id: int = 0
    name: str = ""


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        # Seed data: two orgs, two users
        s.add(ScopedItem(id=1, org_id=10, owner_user_id=100, name="Org10-User100"))
        s.add(ScopedItem(id=2, org_id=10, owner_user_id=101, name="Org10-User101"))
        s.add(ScopedItem(id=3, org_id=20, owner_user_id=200, name="Org20-User200"))
        s.commit()
        yield s


class TestForUserAdmin:
    def test_admin_sees_all(self, session: Session) -> None:
        """Admin role should not apply any filter."""
        caller = AuthContext(user_id=999, role=Role.ADMIN, org_id=None)
        stmt = for_user(caller, select(ScopedItem))
        results = list(session.exec(stmt).all())
        assert len(results) == 3

    def test_admin_enum_value_string(self, session: Session) -> None:
        """Admin as raw string 'admin' should also work."""
        caller = AuthContext(user_id=999, role=Role.ADMIN, org_id=None)
        stmt = for_user(caller, select(ScopedItem))
        results = list(session.exec(stmt).all())
        assert len(results) == 3


class TestForUserBuyer:
    def test_buyer_no_buyer_org_field_returns_unfiltered(self, session: Session) -> None:
        """Without buyer_org_field, buyer sees unfiltered data (service-level filter)."""
        caller = AuthContext(user_id=100, role=Role.BUYER, org_id=10)
        stmt = for_user(caller, select(ScopedItem))
        results = list(session.exec(stmt).all())
        assert len(results) == 3

    def test_buyer_with_org_field(self, session: Session) -> None:
        """With buyer_org_field set, buyer should only see own org data."""
        caller = AuthContext(user_id=100, role=Role.BUYER, org_id=10)
        stmt = for_user(caller, select(ScopedItem), buyer_org_field="org_id")
        results = list(session.exec(stmt).all())
        assert len(results) == 2
        assert all(r.org_id == 10 for r in results)


class TestForUserVendor:
    def test_vendor_no_user_field_returns_unfiltered(self, session: Session) -> None:
        """Without user_field, vendor sees unfiltered data (service-level filter)."""
        caller = AuthContext(user_id=200, role=Role.VENDOR, org_id=20)
        stmt = for_user(caller, select(ScopedItem))
        results = list(session.exec(stmt).all())
        assert len(results) == 3

    def test_vendor_with_user_field(self, session: Session) -> None:
        """With user_field set, vendor should only see own records."""
        caller = AuthContext(user_id=200, role=Role.VENDOR, org_id=20)
        stmt = for_user(caller, select(ScopedItem), user_field="owner_user_id")
        results = list(session.exec(stmt).all())
        assert len(results) == 1
        assert results[0].owner_user_id == 200


class TestForUserUnknownRole:
    def test_unknown_role_raises(self, session: Session) -> None:
        """An unrecognised role should raise MissingScopeError."""
        caller = AuthContext(user_id=1, role="mystery", org_id=1)  # type: ignore[arg-type]
        with pytest.raises(MissingScopeError, match="Unknown role"):
            for_user(caller, select(ScopedItem))
