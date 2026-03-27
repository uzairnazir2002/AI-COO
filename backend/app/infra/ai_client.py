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
    if provider in {"ollama_server", "ollama"}:
        return _generate_summary_ollama_server(metrics)
    return generate_summary_stub(metrics)


def get_ai_provider_health(*, live_check: bool = False) -> dict[str, object]:
    settings = get_settings()
    provider = (settings.ai_provider or "stub").strip().lower()

    if provider not in {"openai", "ollama_server", "ollama"}:
        return {
            "provider": provider,
            "model": None,
            "configured": True,
            "healthy": True,
            "live_check_performed": False,
            "reason": None,
        }

    if provider == "openai":
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

    model = settings.ai_ollama_server_model.strip() if settings.ai_ollama_server_model else None
    configured = bool(settings.ai_ollama_server_url.strip() and settings.ai_ollama_server_api_key.strip())
    response: dict[str, object] = {
        "provider": "ollama_server",
        "model": model,
        "configured": configured,
        "healthy": configured,
        "live_check_performed": False,
        "reason": None,
    }
    if not configured:
        response["healthy"] = False
        response["reason"] = "AI_OLLAMA_SERVER_URL and AI_OLLAMA_SERVER_API_KEY are required for ollama_server mode"
        return response

    if not live_check:
        return response

    response["live_check_performed"] = True
    try:
        _ollama_server_live_health_check()
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


def _generate_summary_ollama_server(metrics: dict) -> AISummaryResponse:
    settings = get_settings()
    if not settings.ai_ollama_server_url.strip():
        raise ValueError("AI provider ollama_server configured without AI_OLLAMA_SERVER_URL")
    if not settings.ai_ollama_server_api_key.strip():
        raise ValueError("AI provider ollama_server configured without AI_OLLAMA_SERVER_API_KEY")

    payload = {"prompt": _build_ollama_summary_prompt(metrics)}
    if settings.ai_ollama_server_model.strip():
        payload["model"] = settings.ai_ollama_server_model.strip()

    with httpx.Client(timeout=float(settings.ai_timeout_seconds)) as client:
        resp = client.post(
            settings.ai_ollama_server_url.strip(),
            headers={
                "x-api-key": settings.ai_ollama_server_api_key.strip(),
                "Content-Type": "application/json",
            },
            json=payload,
        )
    resp.raise_for_status()
    body = resp.json()
    ai_text = _extract_ai_text(body)
    if not ai_text:
        raise ValueError("ollama_server response missing ai text")
    parsed = _extract_json_object(ai_text)
    return AISummaryResponse.model_validate(parsed)


def _build_ollama_summary_prompt(metrics: dict) -> str:
    return (
        "You are an AI COO assistant.\n"
        "Return valid JSON only with exactly these keys:\n"
        "headline, highlights, risks, actions, confidence.\n"
        "- headline: string\n"
        "- highlights: array of strings (max 4)\n"
        "- risks: array of strings (max 4)\n"
        "- actions: array of strings (max 4)\n"
        "- confidence: one of low|medium|high\n"
        "Do not add extra keys. Do not fabricate data.\n"
        f"Metrics payload: {json.dumps(metrics)}"
    )


def _extract_ai_text(body: object) -> str:
    if not isinstance(body, dict):
        return ""
    for key in ("aiText", "response", "text", "output"):
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_json_object(text: str) -> dict:
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()

    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("AI response missing JSON object")
    parsed = json.loads(candidate[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("AI JSON response root must be an object")
    return parsed


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


def _ollama_server_live_health_check() -> None:
    settings = get_settings()
    payload = {"prompt": "Reply with OK"}
    if settings.ai_ollama_server_model.strip():
        payload["model"] = settings.ai_ollama_server_model.strip()

    with httpx.Client(timeout=float(settings.ai_timeout_seconds)) as client:
        response = client.post(
            settings.ai_ollama_server_url.strip(),
            headers={
                "x-api-key": settings.ai_ollama_server_api_key.strip(),
                "Content-Type": "application/json",
            },
            json=payload,
        )
    response.raise_for_status()
    ai_text = _extract_ai_text(response.json())
    if not ai_text:
        raise ValueError("ollama_server live health check received empty ai text")
