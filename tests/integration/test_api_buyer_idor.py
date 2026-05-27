"""Tests for buyer IDOR (Insecure Direct Object Reference) protection.

Verify that one buyer cannot view, cancel, or award another buyer's RFx,
while admins retain full access.
"""

import pytest

from aeros.models.rfx import RFxRun, RFxStatus
from aeros.models.user import Role, User
from aeros.services.auth_service import hash_password


class TestBuyerIDOR:
    @pytest.fixture
    def second_buyer(self, session, buyer_org):
        """A second buyer in the same org."""
        user = User(
            email="buyer2@test.com",
            password_hash=hash_password("test12345"),
            role=Role.BUYER,
            display_name="Second Buyer",
            org_id=buyer_org.id,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    @pytest.fixture
    def rfx_owned_by_first_buyer(self, session, buyer_user):
        """An RFx owned by the first buyer."""
        rfx = RFxRun(
            buyer_id=buyer_user.id,
            title="First buyer's RFx",
            status=RFxStatus.DISPATCHED,
        )
        session.add(rfx)
        session.commit()
        session.refresh(rfx)
        return rfx

    @pytest.fixture
    def second_buyer_client(self, client, second_buyer):
        """A test client authenticated as the second buyer."""
        resp = client.post(
            "/api/auth/login",
            json={"email": "buyer2@test.com", "password": "test12345"},
        )
        assert resp.status_code == 200
        return client

    def test_buyer_cannot_view_others_rfx(
        self, second_buyer_client, rfx_owned_by_first_buyer
    ):
        """Second buyer should get 403 when viewing first buyer's RFx."""
        resp = second_buyer_client.get(
            f"/api/buyer/rfx/{rfx_owned_by_first_buyer.id}"
        )
        assert resp.status_code == 403

    def test_buyer_cannot_cancel_others_rfx(
        self, second_buyer_client, rfx_owned_by_first_buyer
    ):
        """Second buyer should get 403 when cancelling first buyer's RFx."""
        resp = second_buyer_client.post(
            f"/api/buyer/rfx/{rfx_owned_by_first_buyer.id}/cancel",
            json={"reason": "malicious cancel"},
        )
        assert resp.status_code == 403

    def test_buyer_cannot_award_others_rfx(
        self, second_buyer_client, rfx_owned_by_first_buyer
    ):
        """Second buyer should get 403 when awarding first buyer's RFx."""
        resp = second_buyer_client.post(
            f"/api/buyer/rfx/{rfx_owned_by_first_buyer.id}/award",
            json={"decisions": []},
        )
        assert resp.status_code == 403

    def test_admin_can_view_any_rfx(
        self, session, client, buyer_org, rfx_owned_by_first_buyer
    ):
        """Admin should be able to view any buyer's RFx."""
        admin = User(
            email="admin_idor@test.com",
            password_hash=hash_password("test12345"),
            role=Role.ADMIN,
            display_name="IDOR Admin",
            org_id=buyer_org.id,
        )
        session.add(admin)
        session.commit()
        client.post(
            "/api/auth/login",
            json={"email": "admin_idor@test.com", "password": "test12345"},
        )
        resp = client.get(
            f"/api/buyer/rfx/{rfx_owned_by_first_buyer.id}"
        )
        assert resp.status_code == 200
