"""Tests for aeros.ai.normalization — unit/currency normalization utilities."""

import pytest

from aeros.ai.normalization import (
    UNIT_ALIASES,
    convert_quantity,
    normalize_currency,
    normalize_unit,
    parse_price_string,
)


# ---------- normalize_unit ----------


class TestNormalizeUnit:
    def test_canonical_unit_unchanged(self) -> None:
        assert normalize_unit("kg") == "kg"

    def test_plural_alias(self) -> None:
        assert normalize_unit("kgs") == "kg"

    def test_full_word(self) -> None:
        assert normalize_unit("kilograms") == "kg"

    def test_hindi_unit_kilo(self) -> None:
        """Hindi script unit name should normalise correctly."""
        assert normalize_unit("किलो") == "kg"

    def test_hindi_unit_litre(self) -> None:
        assert normalize_unit("लीटर") == "L"

    def test_litre_variants(self) -> None:
        assert normalize_unit("ltr") == "L"
        assert normalize_unit("litres") == "L"

    def test_pieces_aliases(self) -> None:
        assert normalize_unit("pcs") == "pcs"
        assert normalize_unit("nos") == "pcs"
        assert normalize_unit("piece") == "pcs"

    def test_case_insensitive(self) -> None:
        assert normalize_unit("KG") == "kg"
        assert normalize_unit("Litres") == "L"

    def test_unknown_unit_passthrough(self) -> None:
        assert normalize_unit("barrel") == "barrel"

    def test_whitespace_stripped(self) -> None:
        assert normalize_unit("  kg  ") == "kg"


# ---------- normalize_currency ----------


class TestNormalizeCurrency:
    def test_rupee_symbol(self) -> None:
        assert normalize_currency("₹") == "INR"

    def test_rs_abbreviation(self) -> None:
        assert normalize_currency("Rs") == "INR"

    def test_rs_with_dot(self) -> None:
        assert normalize_currency("Rs.") == "INR"

    def test_dollar_symbol(self) -> None:
        assert normalize_currency("$") == "USD"

    def test_euro_symbol(self) -> None:
        assert normalize_currency("€") == "EUR"

    def test_full_word_rupees(self) -> None:
        assert normalize_currency("rupees") == "INR"

    def test_unknown_currency_uppercased(self) -> None:
        assert normalize_currency("gbp") == "GBP"


# ---------- convert_quantity ----------


class TestConvertQuantity:
    def test_same_unit(self) -> None:
        assert convert_quantity(10.0, "kg", "kg") == 10.0

    def test_kg_to_g(self) -> None:
        result = convert_quantity(1.0, "kg", "g")
        assert result is not None
        assert abs(result - 1000.0) < 1e-6

    def test_g_to_kg(self) -> None:
        result = convert_quantity(500.0, "g", "kg")
        assert result is not None
        assert abs(result - 0.5) < 1e-6

    def test_ton_to_kg(self) -> None:
        result = convert_quantity(1.0, "ton", "kg")
        assert result is not None
        assert abs(result - 1000.0) < 1e-6

    def test_quintal_to_kg(self) -> None:
        result = convert_quantity(1.0, "quintal", "kg")
        assert result is not None
        assert abs(result - 100.0) < 1e-6

    def test_incompatible_units_returns_none(self) -> None:
        assert convert_quantity(10.0, "pcs", "kg") is None

    def test_alias_input(self) -> None:
        """Should handle aliases like 'kgs' -> 'kg'."""
        result = convert_quantity(2.0, "kgs", "g")
        assert result is not None
        assert abs(result - 2000.0) < 1e-6


# ---------- parse_price_string ----------


class TestParsePriceString:
    def test_inr_symbol(self) -> None:
        amount, currency = parse_price_string("₹250")
        assert amount == 250.0
        assert currency == "INR"

    def test_rs_prefix(self) -> None:
        amount, currency = parse_price_string("Rs. 1,500.50")
        assert amount == 1500.50
        assert currency == "INR"

    def test_dollar_prefix(self) -> None:
        amount, currency = parse_price_string("$99.99")
        assert amount == 99.99
        assert currency == "USD"

    def test_plain_number_defaults_inr(self) -> None:
        amount, currency = parse_price_string("300")
        assert amount == 300.0
        assert currency == "INR"

    def test_no_number_returns_none(self) -> None:
        amount, currency = parse_price_string("N/A")
        assert amount is None
        assert currency == "INR"

    def test_euro_symbol(self) -> None:
        amount, currency = parse_price_string("€42.00")
        assert amount == 42.0
        assert currency == "EUR"

    def test_whitespace_handling(self) -> None:
        amount, currency = parse_price_string("  ₹ 100  ")
        assert amount == 100.0
        assert currency == "INR"
