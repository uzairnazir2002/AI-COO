import json

import httpx

from app.core.config import get_settings
from app.domain.schemas.ai import AISummaryResponse


def generate_summary_stub(metrics: dict) -> AISummaryResponse:
    kpis = metrics.get("kpis", {})
    risks = metrics.get("alerts", [])
    return AISummaryResponse(
        headline="Weekly COO Summary",
        highlights=[
            f"Revenue MTD is {kpis.get('revenue_mtd', 0)}",
            f"Expenses MTD is {kpis.get('expenses_mtd', 0)}",
        ],
        risks=[str(r.get("title", "")) for r in risks[:3]],
        actions=["Review top expense categories", "Address open runway and anomaly alerts"],
        confidence="high",
    )


def generate_summary(metrics: dict) -> AISummaryResponse:
    settings = get_settings()
    provider = (settings.ai_provider or "stub").strip().lower()
    if provider == "openai":
        return _generate_summary_openai(metrics)
    return generate_summary_stub(metrics)


def get_ai_provider_health(*, live_check: bool = False) -> dict[str, object]:
    settings = get_settings()
    provider = (settings.ai_provider or "stub").strip().lower()

    if provider != "openai":
        return {
            "provider": provider,
            "model": None,
            "configured": True,
            "healthy": True,
            "live_check_performed": False,
            "reason": None,
        }

    model = settings.ai_openai_model.strip() if settings.ai_openai_model else None
    configured = bool(settings.ai_openai_api_key and model)
    response: dict[str, object] = {
        "provider": provider,
        "model": model,
        "configured": configured,
        "healthy": configured,
        "live_check_performed": False,
        "reason": None,
    }
    if not configured:
        response["healthy"] = False
        response["reason"] = "AI_OPENAI_API_KEY and AI_OPENAI_MODEL are required for openai mode"
        return response

    if not live_check:
        return response

    response["live_check_performed"] = True
    try:
        _openai_live_health_check()
    except Exception as exc:  # pragma: no cover - exercised through API tests with monkeypatch
        response["healthy"] = False
        response["reason"] = str(exc)[:300]
    return response


def _generate_summary_openai(metrics: dict) -> AISummaryResponse:
    settings = get_settings()
    if not settings.ai_openai_api_key:
        raise ValueError("AI provider openai configured without AI_OPENAI_API_KEY")
    url = f"{settings.ai_openai_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.ai_openai_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Return JSON only with keys: headline, highlights, risks, actions, confidence. "
                    "Use only the provided metrics and alert titles. No fabricated data."
                ),
            },
            {"role": "user", "content": json.dumps(metrics)},
        ],
    }
    with httpx.Client(timeout=float(settings.ai_timeout_seconds)) as client:
        resp = client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.ai_openai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    resp.raise_for_status()
    body = resp.json()
    content = body.get("choices", [{}])[0].get("message", {}).get("content")
    if not content:
        raise ValueError("AI response missing content")
    return AISummaryResponse.model_validate(json.loads(content))


def _openai_live_health_check() -> None:
    settings = get_settings()
    url = f"{settings.ai_openai_base_url.rstrip('/')}/models/{settings.ai_openai_model}"
    with httpx.Client(timeout=float(settings.ai_timeout_seconds)) as client:
        response = client.get(
            url,
            headers={
                "Authorization": f"Bearer {settings.ai_openai_api_key}",
                "Content-Type": "application/json",
            },
        )
    response.raise_for_status()
