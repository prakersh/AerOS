"""Tests for deterministic intent detection in ProcurementAgent."""

from aeros.agents.procurement import detect_intent


class TestIntentDetectionCreateRfx:
    """Intent detection for RFx creation."""

    def test_create_rfx_english(self):
        """'I need 100kg rice' should detect create_rfx."""
        assert "create_rfx" in detect_intent("I need 100kg rice")

    def test_create_rfx_hindi(self):
        """'mujhe 50kg atta chahiye' should detect create_rfx."""
        assert "create_rfx" in detect_intent("mujhe 50kg atta chahiye")

    def test_create_rfx_order_pattern(self):
        """'order 200 pcs screws' should detect create_rfx."""
        assert "create_rfx" in detect_intent("order 200 pcs screws")

    def test_create_rfx_item_names(self):
        """'I need rice and dal' should detect create_rfx."""
        assert "create_rfx" in detect_intent("I need rice and dal")

    def test_create_rfx_buy_pattern(self):
        """'buy wheat flour' should detect create_rfx."""
        assert "create_rfx" in detect_intent("buy wheat flour")

    def test_create_rfx_case_insensitive(self):
        """'I NEED 100KG RICE' should detect create_rfx."""
        assert "create_rfx" in detect_intent("I NEED 100KG RICE")


class TestIntentDetectionOther:
    """Intent detection for other procurement actions."""

    def test_dispatch(self):
        """'dispatch the RFx' should detect dispatch_rfx."""
        assert "dispatch_rfx" in detect_intent("dispatch the RFx")

    def test_dispatch_hindi(self):
        """'bhejo' should detect dispatch_rfx."""
        assert "dispatch_rfx" in detect_intent("bhejo")

    def test_cancel(self):
        """'cancel RFx #5' should detect cancel_rfx."""
        assert "cancel_rfx" in detect_intent("cancel RFx #5")

    def test_cancel_hindi(self):
        """'band karo rfx' should detect cancel_rfx."""
        assert "cancel_rfx" in detect_intent("band karo rfx")

    def test_evaluate(self):
        """'compare quotes' should detect evaluate_offers."""
        assert "evaluate_offers" in detect_intent("compare quotes")

    def test_evaluate_hindi(self):
        """'sabse sasta' should detect evaluate_offers."""
        assert "evaluate_offers" in detect_intent("sabse sasta")

    def test_award(self):
        """'award to vendor #2' should detect award_rfx."""
        assert "award_rfx" in detect_intent("award to vendor #2")

    def test_decline(self):
        """'can't supply' should detect decline_rfx."""
        assert "decline_rfx" in detect_intent("can't supply")

    def test_decline_hindi(self):
        """'nahi de sakte' should detect decline_rfx."""
        assert "decline_rfx" in detect_intent("nahi de sakte")

    def test_submit_quote(self):
        """'quote 78/kg' should detect submit_quote."""
        assert "submit_quote" in detect_intent("quote 78/kg")

    def test_list_rfx(self):
        """'show my rfx' should detect list_rfx."""
        assert "list_rfx" in detect_intent("show my rfx")

    def test_list_vendors(self):
        """'show vendors' should detect list_vendors."""
        assert "list_vendors" in detect_intent("show vendors")

    def test_daily_summary(self):
        """'summary' should detect daily_summary."""
        assert "daily_summary" in detect_intent("give me a summary")


class TestIntentEdgeCases:
    """Edge cases for intent detection."""

    def test_greeting(self):
        """'hello' should return ['__greeting__']."""
        assert detect_intent("hello") == ["__greeting__"]

    def test_greeting_hindi(self):
        """'namaste' should return ['__greeting__']."""
        assert detect_intent("namaste") == ["__greeting__"]

    def test_no_match(self):
        """'the weather is nice' should return []."""
        assert detect_intent("the weather is nice") == []

    def test_empty_string(self):
        """Empty string should return []."""
        assert detect_intent("") == []

    def test_mixed_multiple(self):
        """'I need rice, dispatch to vendors' should detect both."""
        intents = detect_intent("I need rice, dispatch to vendors")
        assert "create_rfx" in intents
        assert "dispatch_rfx" in intents

    def test_deduplication(self):
        """Duplicate patterns should produce only one entry."""
        intents = detect_intent("I need 100kg rice, I need 50kg dal")
        assert intents.count("create_rfx") == 1

    def test_long_string_no_crash(self):
        """1000+ char string should not crash."""
        long_msg = "I need 100kg rice " * 100
        result = detect_intent(long_msg)
        assert isinstance(result, list)
