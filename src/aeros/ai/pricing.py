"""Per-model token pricing for LLM cost estimation."""

MODEL_PRICING: dict[str, dict[str, float]] = {
    # MiniMax M3
    "MiniMax-M3": {"input": 0.0, "output": 0.0},
    # NVIDIA NIM (embeddings only)
    "nvidia/nv-embed-v1": {"input": 0.0, "output": 0.0},
    # Groq (pay-per-use)
    # ASR pricing is per-minute, not tokens
    "whisper-large-v3-turbo": {"input": 0.0, "output": 0.0},
    # Anthropic (if used)
    "claude-sonnet-4-6": {"input": 0.003, "output": 0.015},
    "claude-haiku-4-5": {"input": 0.0008, "output": 0.004},
    # OpenAI compatible
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate USD cost for a given model and token counts.

    Args:
        model: The model identifier string.
        prompt_tokens: Number of input/prompt tokens.
        completion_tokens: Number of output/completion tokens.

    Returns:
        Estimated cost in USD, rounded to 6 decimal places.
    """
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        best_key: str | None = None
        for key in MODEL_PRICING:
            if (key in model or model in key) and (best_key is None or len(key) > len(best_key)):
                best_key = key
        if best_key is not None:
            pricing = MODEL_PRICING[best_key]
    if not pricing:
        return 0.0
    input_cost = (prompt_tokens / 1000) * pricing["input"]
    output_cost = (completion_tokens / 1000) * pricing["output"]
    return round(input_cost + output_cost, 6)


def is_free_tier(model: str) -> bool:
    """Check if a model is in the free/self-hosted tier.

    Args:
        model: The model identifier string.

    Returns:
        True if the model has zero cost for both input and output.
    """
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        return False
    return pricing["input"] == 0.0 and pricing["output"] == 0.0
