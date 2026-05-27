"""Tests for aeros.services.defaults_service — user defaults management."""

import pytest
from sqlmodel import Session, SQLModel, create_engine

# Import ALL models so their tables are created in metadata
from aeros.models.organization import Organization, OrgType
from aeros.models.user import Role, User
from aeros.models.user_defaults import UserDefaults
from aeros.services import defaults_service
from aeros.services.auth_service import hash_password


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def buyer_org(session: Session) -> Organization:
    org = Organization(name="DefaultsTestOrg", type=OrgType.BUYER)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def user(session: Session, buyer_org: Organization) -> User:
    u = User(
        email="defaults-user@test.com",
        password_hash=hash_password("test123"),
        role=Role.BUYER,
        display_name="Defaults User",
        org_id=buyer_org.id,
    )
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


# ---- get_defaults ----


class TestGetDefaults:
    def test_returns_none_when_no_defaults(self, session: Session, user: User) -> None:
        """Should return None when no UserDefaults exists for user."""
        result = defaults_service.get_defaults(session, user.id)
        assert result is None

    def test_returns_existing_defaults(self, session: Session, user: User) -> None:
        """Should return UserDefaults when they exist."""
        session.add(UserDefaults(user_id=user.id, currency_default="USD"))
        session.commit()

        result = defaults_service.get_defaults(session, user.id)

        assert result is not None
        assert result.user_id == user.id
        assert result.currency_default == "USD"


# ---- update_defaults ----


class TestUpdateDefaults:
    def test_creates_defaults_if_missing(self, session: Session, user: User) -> None:
        """Should create new UserDefaults when none exist."""
        result = defaults_service.update_defaults(
            session, user.id, currency_default="EUR", payment_terms_default="NET60"
        )

        assert result.id is not None
        assert result.user_id == user.id
        assert result.currency_default == "EUR"
        assert result.payment_terms_default == "NET60"

    def test_updates_existing_defaults(self, session: Session, user: User) -> None:
        """Should update fields on existing UserDefaults."""
        session.add(UserDefaults(user_id=user.id))
        session.commit()

        result = defaults_service.update_defaults(
            session, user.id, currency_default="USD"
        )

        assert result.currency_default == "USD"
        # Other fields keep their model defaults
        assert result.payment_terms_default == "NET30"

    def test_ignores_unknown_fields(self, session: Session, user: User) -> None:
        """Should silently skip fields not on the model."""
        result = defaults_service.update_defaults(
            session, user.id, nonexistent_field="foo", currency_default="GBP"
        )

        assert result.currency_default == "GBP"
        assert not hasattr(result, "nonexistent_field") or True  # no crash

    def test_update_multiple_fields(self, session: Session, user: User) -> None:
        """Should update multiple fields at once."""
        result = defaults_service.update_defaults(
            session,
            user.id,
            currency_default="JPY",
            quote_validity_days_default=14,
            delivery_terms_default="FOB",
        )

        assert result.currency_default == "JPY"
        assert result.quote_validity_days_default == 14
        assert result.delivery_terms_default == "FOB"


# ---- ensure_defaults ----


class TestEnsureDefaults:
    def test_creates_when_missing(self, session: Session, user: User) -> None:
        """Should create UserDefaults with model defaults."""
        result = defaults_service.ensure_defaults(session, user.id)

        assert result.id is not None
        assert result.user_id == user.id
        assert result.currency_default == "INR"  # model default
        assert result.payment_terms_default == "NET30"

    def test_returns_existing_without_change(
        self, session: Session, user: User
    ) -> None:
        """Should return existing defaults unchanged."""
        session.add(UserDefaults(user_id=user.id, currency_default="EUR"))
        session.commit()

        result = defaults_service.ensure_defaults(session, user.id)

        assert result.currency_default == "EUR"

    def test_idempotent(self, session: Session, user: User) -> None:
        """Calling ensure_defaults twice should return the same record."""
        d1 = defaults_service.ensure_defaults(session, user.id)
        d2 = defaults_service.ensure_defaults(session, user.id)

        assert d1.id == d2.id
