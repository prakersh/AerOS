"""Tests for tool registry — role filtering, TOON serialization, keyword filtering."""

from aeros.agents.tools import (
    TOOL_CATALOG,
    ToolDef,
    ToolType,
    filter_tools_by_keywords,
    get_tools_for_role,
    tools_to_toon,
)


class TestRoleFiltering:
    """Role-based tool filtering."""

    def test_buyer_excludes_vendor_only(self):
        """Buyer role should not see vendor_only tools."""
        tools = get_tools_for_role("buyer")
        for tool in tools:
            assert not tool.vendor_only, f"{tool.name} is vendor_only but visible to buyer"

    def test_vendor_excludes_buyer_only(self):
        """Vendor role should not see buyer_only tools."""
        tools = get_tools_for_role("vendor")
        for tool in tools:
            assert not tool.buyer_only, f"{tool.name} is buyer_only but visible to vendor"

    def test_admin_gets_all(self):
        """Admin role should see all tools."""
        tools = get_tools_for_role("admin")
        assert len(tools) == len(TOOL_CATALOG)


class TestToolCatalogIntegrity:
    """Tool catalog structural integrity."""

    def test_all_tools_have_required_fields(self):
        """Every tool must have name, description, tool_type, and non-empty keywords."""
        for name, tool in TOOL_CATALOG.items():
            assert isinstance(tool, ToolDef), f"{name} is not a ToolDef"
            assert tool.name, f"{name} has empty name"
            assert tool.description, f"{name} has empty description"
            assert isinstance(tool.tool_type, ToolType), f"{name} has invalid tool_type"
            assert len(tool.keywords) > 0, f"{name} has no keywords"

    def test_no_duplicate_names(self):
        """TOOL_CATALOG keys should match tool .name fields."""
        for key, tool in TOOL_CATALOG.items():
            assert key == tool.name, f"Key '{key}' != tool.name '{tool.name}'"

    def test_catalog_has_expected_tools(self):
        """Catalog should contain core procurement tools."""
        expected = [
            "search_inventory",
            "create_rfx",
            "add_line_items",
            "list_rfx",
            "dispatch_rfx",
            "evaluate_offers",
            "award_rfx",
            "submit_quote",
            "decline_rfx",
            "daily_summary",
        ]
        for name in expected:
            assert name in TOOL_CATALOG, f"Missing tool: {name}"


class TestToonSerialization:
    """TOON format serialization."""

    def test_tools_to_toon_returns_string(self):
        """tools_to_toon should return a non-empty string."""
        tools = get_tools_for_role("buyer")
        result = tools_to_toon(tools)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_tools_to_toon_smaller_than_json(self):
        """TOON output should be smaller than JSON equivalent."""
        import json

        tools = get_tools_for_role("buyer")
        toon_output = tools_to_toon(tools)
        json_output = json.dumps([t.to_catalog_row() for t in tools])
        assert len(toon_output) <= len(json_output)


class TestKeywordFiltering:
    """Keyword-based tool filtering."""

    def test_filter_by_exact_keyword(self):
        """Exact keyword match should return matching tool."""
        tools = get_tools_for_role("buyer")
        filtered = filter_tools_by_keywords("dispatch", tools)
        tool_names = [t.name for t in filtered]
        assert "dispatch_rfx" in tool_names

    def test_filter_no_match_fallback(self):
        """No keyword match should return first N tools."""
        tools = get_tools_for_role("buyer")
        filtered = filter_tools_by_keywords("xyzzy123", tools, max_tools=3)
        assert len(filtered) == 3

    def test_filter_max_limit(self):
        """max_tools should limit results."""
        tools = get_tools_for_role("buyer")
        filtered = filter_tools_by_keywords("rfx vendor quote", tools, max_tools=2)
        assert len(filtered) <= 2

    def test_filter_multi_word_keyword(self):
        """Multi-word keywords should match substring."""
        tools = get_tools_for_role("buyer")
        filtered = filter_tools_by_keywords("search inventory items", tools)
        tool_names = [t.name for t in filtered]
        assert "search_inventory" in tool_names
