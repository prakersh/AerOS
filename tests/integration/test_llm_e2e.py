"""End-to-end integration tests that hit real LLM providers.

These tests verify:
1. MiniMax M3 chat connectivity + structured JSON output
2. MiniMax M3 vision connectivity
3. NVIDIA NIM embedding connectivity
4. IntakeAgent — buyer chat with fuzzy SKU names → structured RFx draft
5. VendorCopilotAgent — vendor gets help composing a quote
6. EvaluationAgent — extract structured offer from vendor text
7. SourcingAgent — compose RFQ invitation message
8. Full round-trip: chat → create RFx → vendor quote → extract offer

All tests use minimal tokens and real API keys from .env.
"""

import json

import pytest

from aeros.ai.base import ChatMessage
from aeros.ai.factory import get_chat_provider, get_embedding_provider, get_vision_provider
from aeros.config import settings
from aeros.models.user import Role
from aeros.security.auth_context import AuthContext

# These tests make real calls to the configured LLM provider. They run locally
# when AEROS_MIMO_API_KEY is set (via .env) and skip in keyless CI rather than
# erroring on client construction.
pytestmark = pytest.mark.skipif(
    not settings.mimo_api_key,
    reason="requires live LLM credentials (AEROS_MIMO_API_KEY)",
)


@pytest.fixture
def buyer_auth(buyer_user):
    return AuthContext(user_id=buyer_user.id, role=Role.BUYER, org_id=buyer_user.org_id)


@pytest.fixture
def vendor_auth(vendor_user):
    return AuthContext(user_id=vendor_user.id, role=Role.VENDOR, org_id=vendor_user.org_id)


@pytest.fixture
def food_category(session):
    from aeros.models.sku import Category

    cat = Category(name="Food Grains", sort_order=1)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


# ---------------------------------------------------------------------------
# 1. Provider Connectivity
# ---------------------------------------------------------------------------


class TestLLMConnectivity:
    """Smoke tests — verify each provider responds with minimal tokens."""

    @pytest.mark.asyncio
    async def test_mimo_chat_responds(self):
        """MiniMax M3 should return a non-empty chat response."""
        provider = get_chat_provider()
        msg = ChatMessage(role="user", content="Reply with just the word OK.")
        resp = await provider.chat([msg], max_tokens=200)
        assert resp.content, "Chat provider returned empty content"
        assert resp.model, "Chat provider returned no model name"
        assert resp.input_tokens > 0

    @pytest.mark.asyncio
    async def test_mimo_chat_json_mode(self):
        """MiniMax M3 should return valid JSON when response_format is json_object."""
        provider = get_chat_provider()
        msg = ChatMessage(
            role="user",
            content='Return exactly: {"status": "ok"}',
        )
        resp = await provider.chat(
            [msg],
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        assert resp.content, "JSON mode returned empty"
        parsed = json.loads(resp.content)
        assert isinstance(parsed, dict)

    @pytest.mark.asyncio
    async def test_mimo_vision_accepts_image(self):
        """MiniMax M3 vision should accept an image input without error."""
        provider = get_vision_provider()
        # 1x1 red pixel PNG
        tiny_png = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
            "/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        )
        msg = ChatMessage(
            role="user",
            content=[
                {"type": "text", "text": "What color is this image? Reply in one word."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{tiny_png}"}},
            ],
        )
        resp = await provider.chat([msg], max_tokens=20)
        assert resp.model, "Vision returned no model"

    @pytest.mark.asyncio
    async def test_nvidia_embedding_returns_vector(self):
        """NVIDIA NIM should return a non-empty embedding vector."""
        provider = get_embedding_provider()
        result = await provider.embed(["procurement test"])
        assert len(result) > 0, "Embedding result is empty"
        assert len(result[0].embedding) > 100, "Embedding dimension too small"


# ---------------------------------------------------------------------------
# 2. IntakeAgent — Buyer Chat Flow
# ---------------------------------------------------------------------------


class TestIntakeAgentFlow:
    """Test IntakeAgent with real LLM — fuzzy SKU matching and draft generation."""

    @pytest.mark.asyncio
    async def test_intake_parses_fuzzy_item_names(self, session, buyer_auth, food_category):
        """IntakeAgent should understand fuzzy names like 'chawal' and match to Rice SKU."""
        from aeros.agents.base import AgentContext
        from aeros.agents.intake import IntakeAgent
        from aeros.models.sku import SKU

        sku = SKU(
            code="RICE-001",
            name="Basmati Rice",
            unit="kg",
            last_price=80.0,
            org_id=buyer_auth.org_id,
            category_id=food_category.id,
        )
        session.add(sku)
        session.commit()

        agent = IntakeAgent()
        ctx = AgentContext(
            session=session,
            caller=buyer_auth,
            chat_provider=get_chat_provider(),
            vision_provider=get_vision_provider(),
            metadata={"history": []},
        )

        result = await agent.run(ctx, "I need 100 kg chawal and 50 kg atta")
        assert result.success, f"IntakeAgent failed: {result.message}"
        assert result.data, "IntakeAgent returned no data"
        # The LLM should respond with something relevant
        assert len(result.message) > 10, "Response too short"

    @pytest.mark.asyncio
    async def test_intake_multi_turn_conversation(self, session, buyer_auth, food_category):
        """IntakeAgent should handle multi-turn conversation and build a draft."""
        from aeros.agents.base import AgentContext
        from aeros.agents.intake import IntakeAgent
        from aeros.models.sku import SKU

        sku = SKU(
            code="MILK-001",
            name="Full Cream Milk",
            unit="ltr",
            last_price=55.0,
            org_id=buyer_auth.org_id,
            category_id=food_category.id,
        )
        session.add(sku)
        session.commit()

        agent = IntakeAgent()
        chat_provider = get_chat_provider()

        # Turn 1: initial request
        ctx1 = AgentContext(
            session=session,
            caller=buyer_auth,
            chat_provider=chat_provider,
            vision_provider=get_vision_provider(),
            metadata={"history": []},
        )
        r1 = await agent.run(ctx1, "I need milk for my store")
        assert r1.success

        # Turn 2: provide quantity
        history = [
            {"role": "user", "content": "I need milk for my store"},
            {"role": "assistant", "content": r1.message},
        ]
        ctx2 = AgentContext(
            session=session,
            caller=buyer_auth,
            chat_provider=chat_provider,
            vision_provider=get_vision_provider(),
            metadata={"history": history},
        )
        r2 = await agent.run(ctx2, "200 litres of full cream milk")
        assert r2.success
        assert r2.data, "Second turn returned no data"


# ---------------------------------------------------------------------------
# 3. VendorCopilotAgent — Vendor Chat Flow
# ---------------------------------------------------------------------------


class TestVendorCopilotFlow:
    """Test VendorCopilotAgent with real LLM."""

    @pytest.mark.asyncio
    async def test_vendor_copilot_responds(self, session, vendor_auth):
        """VendorCopilot should provide helpful guidance."""
        from aeros.agents.base import AgentContext
        from aeros.agents.vendor_copilot import VendorCopilotAgent

        agent = VendorCopilotAgent()
        ctx = AgentContext(
            session=session,
            caller=vendor_auth,
            chat_provider=get_chat_provider(),
            vision_provider=get_vision_provider(),
            metadata={
                "history": [],
                "rfx_context": "RFQ for 100kg Basmati Rice, deadline 2026-06-01",
            },
        )

        result = await agent.run(ctx, "What should I quote for rice?")
        assert result.success, f"VendorCopilot failed: {result.message}"
        assert result.data, "VendorCopilot returned no data"
        assert "message" in result.data

    @pytest.mark.asyncio
    async def test_vendor_copilot_composes_reply(self, session, vendor_auth):
        """VendorCopilot should help compose a structured quote reply."""
        from aeros.agents.base import AgentContext
        from aeros.agents.vendor_copilot import VendorCopilotAgent

        agent = VendorCopilotAgent()
        ctx = AgentContext(
            session=session,
            caller=vendor_auth,
            chat_provider=get_chat_provider(),
            vision_provider=get_vision_provider(),
            metadata={
                "history": [],
                "rfx_context": (
                    "RFQ: 100kg Basmati Rice, 50kg Wheat Flour. Deadline: 2026-06-01. Terms: NET30."
                ),
            },
        )

        result = await agent.run(
            ctx,
            "I want to quote rice at 78/kg and wheat at 34/kg. Help me compose a reply.",
        )
        assert result.success
        msg = result.data.get("message", "")
        assert len(msg) > 10, "Vendor copilot reply too short"


# ---------------------------------------------------------------------------
# 4. EvaluationAgent — Offer Extraction
# ---------------------------------------------------------------------------


class TestEvaluationAgentFlow:
    """Test EvaluationAgent extracting structured offers from vendor text."""

    @pytest.mark.asyncio
    async def test_evaluation_extracts_offer_from_text(self, session, buyer_auth):
        """EvaluationAgent should extract line items from a vendor quote email."""
        from aeros.agents.base import AgentContext
        from aeros.agents.evaluation import EvaluationAgent
        from aeros.models.rfx import Message, RFxRun, Thread

        rfx = RFxRun(
            title="Rice Procurement",
            buyer_id=buyer_auth.user_id,
            org_id=buyer_auth.org_id,
            status="DISPATCHED",
        )
        session.add(rfx)
        session.commit()
        session.refresh(rfx)

        thread = Thread(rfx_id=rfx.id, vendor_id=1, status="open")
        session.add(thread)
        session.commit()
        session.refresh(thread)

        msg = Message(
            thread_id=thread.id,
            sender_kind="vendor",
            channel="email",
            body_text=(
                "Dear Buyer,\n\n"
                "Please find our quote:\n"
                "- Basmati Rice: 78 INR/kg, qty 100 kg = 7800 INR\n"
                "- Wheat Flour: 34 INR/kg, qty 50 kg = 1700 INR\n"
                "Total: 9500 INR\n"
                "Delivery: 3 days\n"
                "Payment: NET15\n\n"
                "Best regards, Vendor Co"
            ),
        )
        session.add(msg)
        session.commit()
        session.refresh(msg)

        agent = EvaluationAgent()
        ctx = AgentContext(
            session=session,
            caller=buyer_auth,
            chat_provider=get_chat_provider(),
            vision_provider=get_vision_provider(),
            rfx_id=rfx.id,
        )

        result = await agent.run(ctx, str(msg.id))
        assert result.success, f"Evaluation failed: {result.message}"
        assert result.data, "Evaluation returned no data"
        items = result.data.get("line_items", [])
        assert len(items) >= 1, f"Expected line items, got: {items}"


# ---------------------------------------------------------------------------
# 5. SourcingAgent — Compose RFQ Message
# ---------------------------------------------------------------------------


class TestSourcingAgentCompose:
    """Test SourcingAgent composing RFQ invitation via LLM."""

    @pytest.mark.asyncio
    async def test_sourcing_composes_rfq_message(self, session, buyer_auth):
        """SourcingAgent should compose a professional RFQ invitation."""
        from aeros.agents.base import AgentContext
        from aeros.agents.sourcing import SourcingAgent
        from aeros.models.rfx import RFxLineItem, RFxRun

        rfx = RFxRun(
            title="Milk Procurement Q2",
            buyer_id=buyer_auth.user_id,
            org_id=buyer_auth.org_id,
            status="DRAFTING",
            payment_terms_for_this_rfx="NET30",
            delivery_terms_for_this_rfx="doorstep",
            currency_for_this_rfx="INR",
        )
        session.add(rfx)
        session.commit()
        session.refresh(rfx)

        li = RFxLineItem(rfx_id=rfx.id, sku_id=1, qty=200, unit_override="ltr")
        session.add(li)
        session.commit()

        agent = SourcingAgent()
        ctx = AgentContext(
            session=session,
            caller=buyer_auth,
            chat_provider=get_chat_provider(),
            vision_provider=get_vision_provider(),
            rfx_id=rfx.id,
        )

        action = json.dumps(
            {
                "action": "confirm_dispatch",
                "rfx_id": rfx.id,
                "dispatch_plan": [],
            }
        )
        result = await agent.run(ctx, action)
        assert result.success, f"SourcingAgent failed: {result.message}"


# ---------------------------------------------------------------------------
# 6. Full Round-Trip: Chat → RFx → Quote → Extract
# ---------------------------------------------------------------------------


class TestFullRoundTrip:
    """End-to-end: buyer chats → RFx created → vendor quotes → offer extracted."""

    @pytest.mark.asyncio
    async def test_buyer_chat_to_rfx_creation(self, session, buyer_auth, food_category):
        """Buyer chat → intake agent → draft → create RFx."""
        from aeros.agents.base import AgentContext
        from aeros.agents.intake import IntakeAgent
        from aeros.models.sku import SKU
        from aeros.services import rfx_service

        sku = SKU(
            code="RICE-001",
            name="Basmati Rice",
            unit="kg",
            last_price=80.0,
            org_id=buyer_auth.org_id,
            category_id=food_category.id,
        )
        session.add(sku)
        session.commit()

        agent = IntakeAgent()
        ctx = AgentContext(
            session=session,
            caller=buyer_auth,
            chat_provider=get_chat_provider(),
            vision_provider=get_vision_provider(),
            metadata={"history": []},
        )
        chat_result = await agent.run(ctx, "I need 100kg basmati rice urgently")
        assert chat_result.success, f"Chat failed: {chat_result.message}"

        # Create RFx based on what the LLM returned
        draft = chat_result.data.get("draft", {})
        rfx = rfx_service.create_rfx(
            session,
            buyer_id=buyer_auth.user_id,
            title=(
                draft.get("title", "Basmati Rice Procurement")
                if draft
                else "Basmati Rice Procurement"
            ),
        )
        assert rfx.id is not None
        assert rfx.status in ("DRAFTING", "drafting")

    @pytest.mark.asyncio
    async def test_vendor_quote_to_extraction(self, session, buyer_auth):
        """Vendor sends quote → evaluation agent extracts structured offer."""
        from aeros.agents.base import AgentContext
        from aeros.agents.evaluation import EvaluationAgent
        from aeros.models.rfx import Message, RFxRun, Thread

        rfx = RFxRun(
            title="E2E Test RFx",
            buyer_id=buyer_auth.user_id,
            org_id=buyer_auth.org_id,
            status="DISPATCHED",
        )
        session.add(rfx)
        session.commit()
        session.refresh(rfx)

        thread = Thread(rfx_id=rfx.id, vendor_id=1, status="open")
        session.add(thread)
        session.commit()
        session.refresh(thread)

        msg = Message(
            thread_id=thread.id,
            sender_kind="vendor",
            channel="email",
            body_text=(
                "Hello,\n\n"
                "Quoting for your RFQ:\n"
                "1. Basmati Rice 1121 - Rs.82/kg x 100kg = Rs.8200\n"
                "2. Toor Dal - Rs.145/kg x 50kg = Rs.7250\n"
                "3. Mustard Oil - Rs.180/ltr x 20ltr = Rs.3600\n\n"
                "Grand Total: Rs.19050\n"
                "Delivery: 2-3 business days\n"
                "Payment: NET15\n"
                "Quote valid: 7 days\n\n"
                "Regards,\nFresh Foods Pvt Ltd"
            ),
        )
        session.add(msg)
        session.commit()
        session.refresh(msg)

        agent = EvaluationAgent()
        ctx = AgentContext(
            session=session,
            caller=buyer_auth,
            chat_provider=get_chat_provider(),
            vision_provider=get_vision_provider(),
            rfx_id=rfx.id,
        )

        result = await agent.run(ctx, str(msg.id))
        assert result.success, f"Extraction failed: {result.message}"

        data = result.data
        items = data.get("line_items", [])
        assert len(items) >= 2, f"Expected >=2 items, got {len(items)}: {items}"

        # Verify some pricing was extracted
        prices_found = any(item.get("unit_price") or item.get("price") for item in items)
        assert prices_found, f"No prices extracted from: {items}"
