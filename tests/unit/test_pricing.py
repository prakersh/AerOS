"""Tests for AI model pricing and cost estimation."""

from aeros.ai.pricing import estimate_cost, is_free_tier


def test_estimate_cost_known_model():
    """Should calculate correct cost for a known model with per-token pricing."""
    # gpt-4o: input=$0.0025/1k, output=$0.01/1k
    cost = estimate_cost("gpt-4o", prompt_tokens=1000, completion_tokens=500)
    expected = (1000 / 1000) * 0.0025 + (500 / 1000) * 0.01
    assert cost == round(expected, 6)


def test_estimate_cost_unknown_model():
    """Should return 0.0 for a model not in the pricing table."""
    cost = estimate_cost("unknown-model-xyz", prompt_tokens=5000, completion_tokens=1000)
    assert cost == 0.0


def test_estimate_cost_free_tier_model():
    """Should return 0.0 for MiniMax models."""
    cost = estimate_cost(
        "MiniMax-M3",
        prompt_tokens=10000,
        completion_tokens=5000,
    )
    assert cost == 0.0


def test_estimate_cost_partial_match():
    """Should match by substring when exact key is not found."""
    cost = estimate_cost("gpt-4o-mini-2024-07-18", prompt_tokens=1000, completion_tokens=1000)
    # Should match gpt-4o-mini pricing
    expected = (1000 / 1000) * 0.00015 + (1000 / 1000) * 0.0006
    assert cost == round(expected, 6)


def test_is_free_tier_true():
    """Should return True for MiniMax and NVIDIA embed models with zero cost."""
    assert is_free_tier("MiniMax-M3") is True
    assert is_free_tier("nvidia/nv-embed-v1") is True


def test_is_free_tier_false():
    """Should return False for paid models."""
    assert is_free_tier("gpt-4o") is False
    assert is_free_tier("claude-sonnet-4-6") is False


def test_is_free_tier_unknown():
    """Should return False for unknown models (not in table)."""
    assert is_free_tier("some-unknown-model") is False
