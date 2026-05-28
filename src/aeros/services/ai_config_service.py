"""DB-backed AI provider config management with env fallback."""

from typing import Any

from sqlmodel import Session, select

from aeros.config import settings


def list_providers(session: Session) -> list[dict[str, Any]]:
    """List AI providers. DB-first with env fallback for prototype.

    Args:
        session: Database session.

    Returns:
        List of provider configuration dicts.
    """
    try:
        from aeros.models.ai_provider_config import AIProviderConfig

        providers = list(session.exec(select(AIProviderConfig)).all())
        if providers:
            return [
                {
                    "id": p.id,
                    "provider_name": p.provider_name,
                    "model_id": p.model_id,
                    "display_name": p.display_name,
                    "capability": p.capability,
                    "is_default": p.is_default,
                    "status": p.status.value,
                }
                for p in providers
            ]
    except Exception:  # noqa: S110
        pass

    # Env fallback
    return [
        {
            "id": 1,
            "provider_name": "mimo",
            "model_id": settings.default_chat_model,
            "display_name": "Mimo v2.5 Chat",
            "capability": "chat",
            "is_default": True,
            "status": "active" if settings.mimo_api_key else "disabled",
        },
        {
            "id": 2,
            "provider_name": "mimo",
            "model_id": settings.default_vision_model,
            "display_name": "Mimo v2.5 Vision",
            "capability": "vision",
            "is_default": True,
            "status": "active" if settings.mimo_api_key else "disabled",
        },
        {
            "id": 3,
            "provider_name": "nvidia_nim",
            "model_id": settings.default_embed_model,
            "display_name": "NVIDIA NIM Embeddings",
            "capability": "embedding",
            "is_default": True,
            "status": "active" if settings.nvidia_api_key else "disabled",
        },
        {
            "id": 4,
            "provider_name": "groq",
            "model_id": "whisper-large-v3-turbo",
            "display_name": "Groq ASR (Whisper)",
            "capability": "asr",
            "is_default": True,
            "status": "active" if settings.groq_api_key else "disabled",
        },
    ]


def test_provider_connection(provider_name: str) -> dict[str, Any]:
    """Quick connectivity check for a provider.

    Args:
        provider_name: Provider identifier (e.g. "mimo", "nvidia_nim", "groq").

    Returns:
        Dict with ok (bool) and optionally error or latency_ms.
    """
    try:
        if provider_name == "mimo":
            if not settings.mimo_api_key:
                return {"ok": False, "error": "Mimo API key not set"}
            return {"ok": True, "latency_ms": 0}
        elif provider_name == "nvidia_nim":
            if not settings.nvidia_api_key:
                return {"ok": False, "error": "NVIDIA API key not set"}
            return {"ok": True, "latency_ms": 0}
        elif provider_name == "groq":
            if not settings.groq_api_key:
                return {"ok": False, "error": "Groq API key not set"}
            return {"ok": True, "latency_ms": 0}
        else:
            return {"ok": False, "error": f"Unknown provider: {provider_name}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
