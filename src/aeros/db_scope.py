"""Query-scope filter for 3-tier RBAC.

Applies WHERE clauses to SQLModel select statements based on the caller's role.
"""

from __future__ import annotations

from typing import Any

from sqlmodel import select

from aeros.models.user import Role
from aeros.security.auth_context import AuthContext


class MissingScopeError(Exception):
    """Raised when the caller's role is not recognised."""


def for_user(
    caller: AuthContext,
    statement: Any,
    *,
    org_field: str = "org_id",
    user_field: str | None = None,
    buyer_org_field: str | None = None,
) -> Any:
    """Apply RBAC scope filter to a SQLModel select statement.

    Args:
        caller: The authenticated user context.
        statement: A SQLModel ``select()`` statement.
        org_field: Column name for organisation filtering.
        user_field: Column name for user-level filtering (vendor).
        buyer_org_field: Column name for buyer org filtering.

    Returns:
        The (possibly filtered) statement.

    Raises:
        MissingScopeError: If the caller's role is unknown.
    """
    role = caller.role

    # Admin sees everything
    if role == Role.ADMIN or role == Role.ADMIN.value:
        return statement

    # Buyer — optionally filter by org
    if role == Role.BUYER or role == Role.BUYER.value:
        if buyer_org_field:
            entity = statement.column_descriptions[0]["entity"]
            return statement.where(
                getattr(entity, buyer_org_field) == caller.org_id
            )
        return statement  # buyer sees own org data (filtered at service level)

    # Vendor — optionally filter by user
    if role == Role.VENDOR or role == Role.VENDOR.value:
        if user_field:
            entity = statement.column_descriptions[0]["entity"]
            return statement.where(
                getattr(entity, user_field) == caller.user_id
            )
        return statement

    raise MissingScopeError(f"Unknown role: {role}")
