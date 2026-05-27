"""Unit and currency normalization for procurement data."""

import re

UNIT_ALIASES: dict[str, str] = {
    # Weight — metric
    "kg": "kg",
    "kgs": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "किलो": "kg",
    "g": "g",
    "gm": "g",
    "gms": "g",
    "gram": "g",
    "grams": "g",
    # Volume
    "l": "L",
    "ltr": "L",
    "ltrs": "L",
    "litre": "L",
    "litres": "L",
    "liter": "L",
    "liters": "L",
    "लीटर": "L",
    "ml": "mL",
    "millilitre": "mL",
    # Counting
    "pcs": "pcs",
    "pc": "pcs",
    "piece": "pcs",
    "pieces": "pcs",
    "nos": "pcs",
    "no": "pcs",
    "dozen": "dozen",
    "dz": "dozen",
    # Packaging
    "box": "box",
    "boxes": "box",
    "bx": "box",
    "case": "case",
    "cases": "case",
    # Bulk
    "ton": "ton",
    "tons": "ton",
    "tonne": "ton",
    "tonnes": "ton",
    "quintal": "quintal",
    "qtl": "quintal",
    "bag": "bag",
    "bags": "bag",
    "crate": "crate",
    "crates": "crate",
    "bundle": "bundle",
    "bundles": "bundle",
}

UNIT_TO_KG: dict[str, float] = {
    "kg": 1.0,
    "g": 0.001,
    "ton": 1000.0,
    "quintal": 100.0,
    "L": 1.0,
    "mL": 0.001,
}

CURRENCY_SYMBOLS: dict[str, str] = {
    "₹": "INR",
    "rs": "INR",
    "rs.": "INR",
    "inr": "INR",
    "rupees": "INR",
    "rupee": "INR",
    "$": "USD",
    "usd": "USD",
    "dollars": "USD",
    "€": "EUR",
    "eur": "EUR",
    "euros": "EUR",
}


def normalize_unit(raw: str) -> str:
    """Normalize a unit string to its canonical form.

    Args:
        raw: The raw unit string (e.g. "kgs", "litres", "किलो").

    Returns:
        The canonical unit name, or the cleaned input if unknown.
    """
    cleaned = raw.strip().lower()
    return UNIT_ALIASES.get(cleaned, cleaned)


def normalize_currency(raw: str) -> str:
    """Normalize a currency string to its ISO 4217 code.

    Args:
        raw: The raw currency string (e.g. "Rs.", "$", "rupees").

    Returns:
        The ISO currency code (e.g. "INR", "USD"), or uppercased input.
    """
    cleaned = raw.strip().lower().rstrip(".")
    return CURRENCY_SYMBOLS.get(cleaned, raw.strip().upper())


def convert_quantity(
    qty: float, from_unit: str, to_unit: str
) -> float | None:
    """Convert a quantity between compatible units.

    Args:
        qty: The numeric quantity.
        from_unit: Source unit (raw or canonical).
        to_unit: Target unit (raw or canonical).

    Returns:
        The converted quantity, or None if units are incompatible.
    """
    from_norm = normalize_unit(from_unit)
    to_norm = normalize_unit(to_unit)
    if from_norm == to_norm:
        return qty
    from_factor = UNIT_TO_KG.get(from_norm)
    to_factor = UNIT_TO_KG.get(to_norm)
    if from_factor is None or to_factor is None:
        return None
    return qty * from_factor / to_factor


def parse_price_string(raw: str) -> tuple[float | None, str]:
    """Extract a numeric amount and currency from a price string.

    Args:
        raw: Free-text price (e.g. "Rs. 1,500.50", "$99", "₹250").

    Returns:
        A (amount, currency_code) tuple.  amount is None if no number found.
    """
    cleaned = raw.strip()
    currency = "INR"
    # Sort symbols longest-first so "rs." matches before "rs"
    for symbol, code in sorted(
        CURRENCY_SYMBOLS.items(), key=lambda kv: len(kv[0]), reverse=True
    ):
        if symbol in cleaned.lower():
            currency = code
            cleaned = re.sub(
                re.escape(symbol), "", cleaned, flags=re.IGNORECASE
            ).strip()
            break
    cleaned = cleaned.replace(",", "")
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    if match:
        return float(match.group()), currency
    return None, currency
