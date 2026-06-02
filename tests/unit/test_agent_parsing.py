"""Tests for tool selection parsing in ProcurementAgent."""

from types import SimpleNamespace

from aeros.agents.procurement import (
    _active_rfx_add_calls,
    _parse_item_refs,
    _parse_tool_selections,
)


class TestParseValidFormats:
    """Parsing valid JSON formats from LLM output."""

    def test_valid_json_array(self):
        """Standard tool selection format."""
        content = '[{"tool": "create_rfx", "params": {"title": "Test"}}]'
        result = _parse_tool_selections(content)
        assert len(result) == 1
        assert result[0][0] == "create_rfx"
        assert result[0][1] == {"title": "Test"}

    def test_valid_single_dict(self):
        """Single tool format."""
        content = '{"tool": "list_rfx", "params": {}}'
        result = _parse_tool_selections(content)
        assert len(result) == 1
        assert result[0][0] == "list_rfx"

    def test_empty_object(self):
        """Empty object should return empty list."""
        result = _parse_tool_selections("{}")
        assert result == []

    def test_empty_array(self):
        """Empty array should return empty list."""
        result = _parse_tool_selections("[]")
        assert result == []


class TestParseEdgeCases:
    """Parsing edge cases and malformed LLM output."""

    def test_markdown_wrapped(self):
        """JSON wrapped in markdown code blocks."""
        content = '```json\n[{"tool": "list_rfx", "params": {}}]\n```'
        result = _parse_tool_selections(content)
        assert len(result) == 1
        assert result[0][0] == "list_rfx"

    def test_llm_preamble(self):
        """LLM adds text before JSON."""
        content = 'Here are the tools:\n[{"tool": "create_rfx", "params": {"title": "X"}}]'
        result = _parse_tool_selections(content)
        assert len(result) == 1
        assert result[0][0] == "create_rfx"

    def test_tool_calls_wrapper_format(self):
        """LLM wraps tools in {"thoughts": "...", "tool_calls": [...]}."""
        content = (
            '{"thoughts": "user needs rice", '
            '"tool_calls": [{"tool": "create_rfx", "params": {"title": "Rice"}}]}'
        )
        result = _parse_tool_selections(content)
        assert len(result) == 1
        assert result[0][0] == "create_rfx"

    def test_tools_wrapper_format(self):
        """LLM wraps tools in {"tools": [...]}."""
        content = '{"tools": [{"tool": "list_vendors", "params": {}}]}'
        result = _parse_tool_selections(content)
        assert len(result) == 1
        assert result[0][0] == "list_vendors"

    def test_unknown_dict_keys_return_empty(self):
        """Arbitrary dict keys should NOT be treated as tool names."""
        content = '{"random_key": {"title": "X"}, "another_key": {}}'
        result = _parse_tool_selections(content)
        assert len(result) == 0

    def test_invalid_json(self):
        """Random text should return empty list."""
        result = _parse_tool_selections("this is not json")
        assert result == []

    def test_deduplication(self):
        """Duplicate tools should be collapsed."""
        content = '[{"tool": "list_rfx", "params": {}}, {"tool": "list_rfx", "params": {}}]'
        result = _parse_tool_selections(content)
        assert len(result) == 1

    def test_missing_tool_key(self):
        """Item without 'tool' key should be skipped."""
        content = '[{"params": {"title": "X"}}]'
        result = _parse_tool_selections(content)
        assert result == []

    def test_non_dict_items(self):
        """Non-dict items in array should be skipped."""
        content = '[{"tool": "list_rfx"}, "invalid", 42]'
        result = _parse_tool_selections(content)
        assert len(result) == 1
        assert result[0][0] == "list_rfx"


class TestParseItemRefs:
    """Free-text -> line item refs for the deterministic add path."""

    def test_qty_unit_name(self):
        items = _parse_item_refs("add 10 pcs ashirwad aata")
        assert items == [{"sku_id": "ashirwad aata", "qty": 10.0, "unit_override": "pcs"}]

    def test_name_qty_unit(self):
        items = _parse_item_refs("Add bisleri 1L 100 pcs")
        assert items and items[0]["qty"] == 100.0
        assert "bisleri" in items[0]["sku_id"].lower()

    def test_sku_code_with_quantity(self):
        items = _parse_item_refs("Add line item PF001 with quantity 10")
        assert items == [{"sku_id": "PF001", "qty": 10.0, "unit_override": None}]

    def test_unitless_quantity(self):
        items = _parse_item_refs("Add line item: 60 bananas")
        assert items == [{"sku_id": "bananas", "qty": 60.0, "unit_override": None}]

    def test_quantity_keyword(self):
        items = _parse_item_refs("Add line item milk with quantity 5")
        assert items == [{"sku_id": "milk", "qty": 5.0, "unit_override": None}]

    def test_no_items(self):
        assert _parse_item_refs("hello there") == []

    def test_dozen_abbreviation(self):
        items = _parse_item_refs("add 10 doz banana")
        assert items == [{"sku_id": "banana", "qty": 10.0, "unit_override": "doz"}]


class TestActiveRfxAddCalls:
    """Deterministic add_line_items only fires inside an RFx with an add cue."""

    def test_fires_with_rfx_and_add_cue(self):
        ctx = SimpleNamespace(rfx_id=5)
        calls = _active_rfx_add_calls("add 10 pcs ashirwad aata", ctx)
        assert len(calls) == 1
        tool, params = calls[0]
        assert tool == "add_line_items"
        assert params["rfx_id"] == 5
        assert params["items"][0]["sku_id"] == "ashirwad aata"

    def test_no_rfx_context(self):
        ctx = SimpleNamespace(rfx_id=None)
        assert _active_rfx_add_calls("add 10 pcs rice", ctx) == []

    def test_no_add_cue(self):
        ctx = SimpleNamespace(rfx_id=5)
        # No add/include/etc. cue -> don't hijack the message.
        assert _active_rfx_add_calls("what is the status of 10 pcs rice", ctx) == []

    def test_add_cue_but_no_items(self):
        ctx = SimpleNamespace(rfx_id=5)
        assert _active_rfx_add_calls("add something please", ctx) == []
