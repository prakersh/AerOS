"""Tests for error recovery — LLM failures, malformed responses, service exceptions.

From TESTING_PLAN.md Section 5.2: Error Recovery.
"""

from unittest.mock import AsyncMock

import pytest

from aeros.agents.executor import execute_tool
from aeros.agents.procurement import (
    ProcurementAgent,
    _parse_tool_selections,
)
from aeros.models.organization import Organization, OrgType
from aeros.models.user import Role, User
from aeros.models.user_defaults import UserDefaults
from aeros.security.auth_context import AuthContext
from aeros.services.auth_service import hash_password


def _mock_chat_response(content: str):
    from aeros.ai.base import ChatResponse

    return ChatResponse(
        content=content,
        input_tokens=100,
        output_tokens=50,
        provider="mock",
        model="mock-model",
    )


@pytest.fixture
def err_org(session):
    org = Organization(name="ErrOrg", type=OrgType.BUYER)
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


@pytest.fixture
def err_buyer(session, err_org):
    user = User(
        email="err-buyer@test.com",
        password_hash=hash_password("test123"),
        role=Role.BUYER,
        display_name="Err Buyer",
        org_id=err_org.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(UserDefaults(user_id=user.id))
    session.commit()
    return user


@pytest.fixture
def err_buyer_ctx(err_buyer, err_org):
    return AuthContext(user_id=err_buyer.id, role=Role.BUYER, org_id=err_org.id)


class TestMalformedLLMResponses:
    """Agent should handle malformed LLM output gracefully."""

    def test_parse_random_text(self):
        """Random text should return empty list."""
        assert _parse_tool_selections("I am a banana") == []

    def test_parse_partial_json(self):
        """Truncated JSON should return empty list."""
        assert _parse_tool_selections('[{"tool": "list_rfx"') == []

    def test_parse_json_with_extra_text(self):
        """JSON embedded in text should still be parsed."""
        content = 'Sure! Here are the tools:\n[{"tool": "list_rfx", "params": {}}]\nLet me know!'
        result = _parse_tool_selections(content)
        assert len(result) == 1
        assert result[0][0] == "list_rfx"

    def test_parse_json_null(self):
        """JSON null should return empty list."""
        assert _parse_tool_selections("null") == []

    def test_parse_json_number(self):
        """JSON number should return empty list."""
        assert _parse_tool_selections("42") == []

    def test_parse_json_string(self):
        """JSON string should return empty list."""
        assert _parse_tool_selections('"hello"') == []


class TestLLMTimeoutRecovery:
    """Agent should recover from LLM timeouts."""

    @pytest.mark.asyncio
    async def test_llm_timeout_on_selection(self, session, err_buyer, err_buyer_ctx):
        """LLM timeout on tool selection should return fallback message."""
        mock_provider = AsyncMock()
        mock_provider.chat.side_effect = TimeoutError("LLM request timed out")

        from aeros.agents.base import AgentContext

        ctx = AgentContext(
            session=session,
            caller=err_buyer,
            chat_provider=mock_provider,
        )
        agent = ProcurementAgent()
        result = await agent.run(ctx, "show my RFx")

        assert result.success is True
        assert len(result.message) > 0

    @pytest.mark.asyncio
    async def test_llm_returns_empty_content(self, session, err_buyer, err_buyer_ctx):
        """LLM returning empty content should not crash."""
        mock_provider = AsyncMock()
        mock_provider.chat.return_value = _mock_chat_response("")

        from aeros.agents.base import AgentContext

        ctx = AgentContext(
            session=session,
            caller=err_buyer,
            chat_provider=mock_provider,
        )
        agent = ProcurementAgent()
        result = await agent.run(ctx, "hello")

        assert result.success is True


class TestToolExecutorErrorRecovery:
    """Tool executor should handle service failures gracefully."""

    def test_execute_unknown_tool(self, session, err_buyer_ctx):
        """Unknown tool should return error ToolResult."""
        result = execute_tool("nonexistent_tool", {}, session, err_buyer_ctx)
        assert result.success is False
        assert "Unknown tool" in result.message

    def test_execute_tool_with_bad_params(self, session, err_buyer_ctx):
        """Tool with missing required params should return error."""
        result = execute_tool("create_rfx", {}, session, err_buyer_ctx)
        # Missing 'title' should cause an error
        assert result.success is False

    def test_execute_tool_service_raises(self, session, err_buyer_ctx):
        """Service exception should be caught and returned as error."""
        result = execute_tool("get_rfx_details", {"rfx_id": 99999}, session, err_buyer_ctx)
        assert result.success is False

    def test_execute_tool_latency_always_positive(self, session, err_buyer_ctx):
        """Latency should always be positive even on error."""
        result = execute_tool("nonexistent_tool", {}, session, err_buyer_ctx)
        assert result.latency_ms >= 0

    def test_execute_cancel_rfx_nonexistent(self, session, err_buyer_ctx):
        """Cancelling nonexistent RFx should return error."""
        result = execute_tool(
            "cancel_rfx",
            {"rfx_id": 99999, "reason": "test"},
            session,
            err_buyer_ctx,
        )
        assert result.success is False

    def test_execute_dispatch_rfx_nonexistent(self, session, err_buyer_ctx):
        """Dispatching nonexistent RFx should return error."""
        result = execute_tool("dispatch_rfx", {"rfx_id": 99999}, session, err_buyer_ctx)
        assert result.success is False

    def test_execute_award_rfx_nonexistent(self, session, err_buyer_ctx):
        """Awarding nonexistent RFx should return error."""
        result = execute_tool(
            "award_rfx",
            {"rfx_id": 99999, "decisions": []},
            session,
            err_buyer_ctx,
        )
        assert result.success is False


class TestAliasResolution:
    """Tool aliases should resolve correctly."""

    def test_alias_search_resolves(self, session, err_buyer_ctx):
        """'search' should resolve to 'search_inventory'."""
        result = execute_tool("search", {"query": "test"}, session, err_buyer_ctx)
        assert result.tool == "search_inventory"

    def test_alias_vendors_resolves(self, session, err_buyer_ctx):
        """'vendors' should resolve to 'list_vendors'."""
        result = execute_tool("vendors", {}, session, err_buyer_ctx)
        assert result.tool == "list_vendors"

    def test_alias_rfx_resolves(self, session, err_buyer_ctx):
        """'rfx' should resolve to 'list_rfx'."""
        result = execute_tool("rfx", {}, session, err_buyer_ctx)
        assert result.tool == "list_rfx"

    def test_alias_send_resolves(self, session, err_buyer_ctx):
        """'send' should resolve to 'dispatch_rfx'."""
        result = execute_tool("send", {"rfx_id": 1}, session, err_buyer_ctx)
        assert result.tool == "dispatch_rfx"

    def test_alias_compare_resolves(self, session, err_buyer_ctx):
        """'compare' should resolve to 'evaluate_offers'."""
        result = execute_tool("compare", {"rfx_id": 1}, session, err_buyer_ctx)
        assert result.tool == "evaluate_offers"
