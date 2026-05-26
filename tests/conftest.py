import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlmodel import Session, SQLModel

from aeros.main import app
from aeros.db import get_session
from aeros.services.auth_service import hash_password
from aeros.models.user import Role, User
from aeros.models.organization import OrgType, Organization
from aeros.models.user_defaults import UserDefaults
from aeros.models import *  # noqa: F401, F403 — register all models


@pytest.fixture(name="engine")
def fixture_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(name="session")
def fixture_session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def fixture_client(engine):
    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def buyer_org(session):
    org = Organization(name="TestBuyerOrg", type=OrgType.BUYER)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def buyer_user(session, buyer_org):
    user = User(
        email="buyer@test.com",
        password_hash=hash_password("test123"),
        role=Role.BUYER,
        display_name="Test Buyer",
        org_id=buyer_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(UserDefaults(user_id=user.id))
    session.commit()
    return user


@pytest.fixture
def vendor_user(session):
    vorg = Organization(name="TestVendorOrg", type=OrgType.VENDOR)
    session.add(vorg)
    session.commit()
    session.refresh(vorg)
    user = User(
        email="vendor@test.com",
        password_hash=hash_password("test123"),
        role=Role.VENDOR,
        display_name="Test Vendor",
        org_id=vorg.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def auth_client(client, buyer_user):
    resp = client.post("/api/auth/login", json={"email": "buyer@test.com", "password": "test123"})
    assert resp.status_code == 200
    return client
