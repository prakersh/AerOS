"""Tests for offer_fusion_service — multi-attachment extraction fusion."""

from aeros.services.offer_fusion_service import _match_key, fuse_extractions


class TestMatchKey:
    """Tests for _match_key() — matching extracted items to RFx line items."""

    def test_exact_code_match(self):
        """Should match by exact SKU code."""
        item = {"sku_code": "DAI-001", "name": "Milk"}
        rfx_items = [{"code": "DAI-001", "name": "Fresh Milk"}]
        assert _match_key(item, rfx_items) == "dai-001"

    def test_exact_name_match(self):
        """Should match by exact name when no code."""
        item = {"name": "Butter", "sku_code": ""}
        rfx_items = [{"code": "", "name": "Butter"}]
        assert _match_key(item, rfx_items) == "butter"

    def test_partial_name_match(self):
        """Should match when extracted name is contained in RFx name."""
        item = {"name": "Milk"}
        rfx_items = [{"code": "", "name": "Fresh Milk 500ml"}]
        assert _match_key(item, rfx_items) == "fresh milk 500ml"

    def test_no_match_returns_none(self):
        """Should return None when no match found."""
        item = {"name": "Unknown Product"}
        rfx_items = [{"code": "X-1", "name": "Totally Different"}]
        assert _match_key(item, rfx_items) is None

    def test_empty_rfx_items(self):
        """Should return None with empty RFx items list."""
        item = {"name": "Something"}
        assert _match_key(item, []) is None


class TestFuseExtractions:
    """Tests for fuse_extractions() — merging multiple extraction results."""

    def test_single_extraction_passthrough(self):
        """Single extraction should pass through unchanged."""
        extractions = [
            {
                "line_items": [{"name": "Milk", "qty": 100, "price": 50, "confidence": 0.9}],
                "currency": "INR",
                "payment_terms": "NET30",
            }
        ]
        result = fuse_extractions(extractions, rfx_line_items=[])
        assert len(result["line_items"]) == 1
        assert result["currency"] == "INR"
        assert result["payment_terms"] == "NET30"
        assert result["source_count"] == 1

    def test_higher_confidence_wins(self):
        """When same item appears in multiple files, higher confidence wins."""
        rfx_items = [{"code": "DAI-001", "name": "Milk"}]
        extractions = [
            {
                "line_items": [
                    {"name": "Milk", "sku_code": "DAI-001", "price": 48, "confidence": 0.7}
                ],
            },
            {
                "line_items": [
                    {"name": "Milk", "sku_code": "DAI-001", "price": 50, "confidence": 0.95}
                ],
            },
        ]
        result = fuse_extractions(extractions, rfx_items)
        assert len(result["line_items"]) == 1
        assert result["line_items"][0]["price"] == 50
        assert result["line_items"][0]["confidence"] == 0.95

    def test_different_items_merged(self):
        """Items from different files should all appear in result."""
        extractions = [
            {
                "line_items": [{"name": "Milk", "price": 50, "confidence": 0.9}],
            },
            {
                "line_items": [{"name": "Butter", "price": 200, "confidence": 0.85}],
            },
        ]
        result = fuse_extractions(extractions, rfx_line_items=[])
        assert len(result["line_items"]) == 2

    def test_metadata_merged_from_first_available(self):
        """Metadata should be taken from the first extraction that has it."""
        extractions = [
            {"line_items": [], "currency": "USD"},
            {"line_items": [], "currency": "INR", "delivery_terms": "FOB"},
        ]
        result = fuse_extractions(extractions, rfx_line_items=[])
        assert result["currency"] == "USD"  # first wins
        assert result["delivery_terms"] == "FOB"  # filled from second

    def test_empty_extractions(self):
        """Empty extractions list should produce empty result."""
        result = fuse_extractions([], rfx_line_items=[])
        assert result["line_items"] == []
        assert result["source_count"] == 0

    def test_notes_accumulated(self):
        """Notes from multiple extractions should be accumulated."""
        extractions = [
            {"line_items": [], "notes": "Note A"},
            {"line_items": [], "notes": "Note B"},
        ]
        result = fuse_extractions(extractions, rfx_line_items=[])
        assert len(result["notes"]) == 2
        assert "Note A" in result["notes"]
        assert "Note B" in result["notes"]

    def test_items_key_uses_sku_name_fallback(self):
        """Items without matching RFx items should use name or sku as key."""
        extractions = [
            {
                "items": [  # "items" key instead of "line_items"
                    {"sku": "PROD-A", "price": 100, "confidence": 0.8}
                ],
            },
        ]
        result = fuse_extractions(extractions, rfx_line_items=[])
        assert len(result["line_items"]) == 1

    def test_lower_confidence_does_not_overwrite(self):
        """A later extraction with lower confidence should not overwrite."""
        rfx_items = [{"code": "", "name": "Widget"}]
        extractions = [
            {
                "line_items": [{"name": "Widget", "price": 100, "confidence": 0.95}],
            },
            {
                "line_items": [{"name": "Widget", "price": 80, "confidence": 0.6}],
            },
        ]
        result = fuse_extractions(extractions, rfx_items)
        assert len(result["line_items"]) == 1
        assert result["line_items"][0]["price"] == 100
