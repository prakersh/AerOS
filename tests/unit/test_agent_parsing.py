"""Tests for tool selection parsing in ProcurementAgent."""

from aeros.agents.procurement import _parse_tool_selections


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

    def test_legacy_dict_format(self):
        """Legacy format: {"create_rfx": {"title": "X"}}."""
        content = '{"create_rfx": {"title": "X"}, "list_vendors": {}}'
        result = _parse_tool_selections(content)
        assert len(result) == 2
        tool_names = [r[0] for r in result]
        assert "create_rfx" in tool_names
        assert "list_vendors" in tool_names

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
