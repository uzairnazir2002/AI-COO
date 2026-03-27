import json
import re

import httpx
import structlog

from app.core.config import get_settings
from app.domain.schemas.ai import AISummaryResponse

logger = structlog.get_logger(__name__)


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

    primary_prompt = _build_ollama_summary_prompt(metrics)
    ai_text = _call_ollama_server_prompt(primary_prompt)
    parse_error: Exception | None = None
    try:
        parsed = _extract_json_object(ai_text)
        normalized = _normalize_summary_payload(parsed)
        return AISummaryResponse.model_validate(normalized)
    except Exception as exc:  # noqa: BLE001
        parse_error = exc
        logger.warning(
            "ai_ollama_summary_primary_parse_failed",
            reason=str(exc)[:300],
            ai_text_excerpt=_safe_excerpt(ai_text),
        )

    repair_prompt = _build_ollama_repair_prompt(metrics, ai_text)
    repaired_text = _call_ollama_server_prompt(repair_prompt)
    try:
        parsed = _extract_json_object(repaired_text)
        normalized = _normalize_summary_payload(parsed)
        return AISummaryResponse.model_validate(normalized)
    except Exception as repair_exc:  # noqa: BLE001
        logger.warning(
            "ai_ollama_summary_repair_parse_failed",
            reason=str(repair_exc)[:300],
            repaired_text_excerpt=_safe_excerpt(repaired_text),
        )
        if parse_error is not None:
            raise ValueError(f"{parse_error}; repair_failed={repair_exc}") from repair_exc
        raise


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
        "Do not include markdown code fences.\n"
        "Use only values present in the metrics payload (no inferred percentages, no unsupported metrics).\n"
        "If uncertain, keep statements generic and avoid numeric claims.\n"
        'Output example: {"headline":"...","highlights":["..."],"risks":["..."],"actions":["..."],"confidence":"medium"}\n'
        f"Metrics payload: {json.dumps(metrics)}"
    )


def _build_ollama_repair_prompt(metrics: dict, raw_output: str) -> str:
    return (
        "You are fixing malformed output.\n"
        "Convert the provided content into valid JSON only with keys:\n"
        "headline, highlights, risks, actions, confidence.\n"
        "- highlights, risks, actions must be arrays of strings.\n"
        "- confidence must be low|medium|high.\n"
        "- Do not use markdown code fences.\n"
        "- Use only facts from metrics payload. If unknown, keep generic.\n"
        f"Metrics payload: {json.dumps(metrics)}\n"
        f"Malformed content to repair: {raw_output}"
    )


def _call_ollama_server_prompt(prompt: str) -> str:
    settings = get_settings()
    payload = {"prompt": prompt}
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
    return ai_text


def _extract_ai_text(body: object) -> str:
    if not isinstance(body, dict):
        return ""
    for key in ("aiText", "response", "text", "output"):
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_json_object(text: str) -> dict:
    candidate = text.strip().replace("\\n", "\n")
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()

    parsed = _try_parse_json_dict(candidate)
    if parsed is not None:
        return parsed

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end <= start:
        relaxed = _parse_relaxed_summary(candidate)
        if relaxed is not None:
            return relaxed
        raise ValueError("AI response missing JSON object")

    json_candidate = candidate[start : end + 1]
    parsed = _try_parse_json_dict(json_candidate)
    if parsed is not None:
        return parsed

    relaxed = _parse_relaxed_summary(json_candidate)
    if relaxed is not None:
        return relaxed

    raise ValueError("AI JSON response root must be an object")


def _try_parse_json_dict(candidate: str) -> dict | None:
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None
    return None


def _parse_relaxed_summary(text: str) -> dict | None:
    # Normalize common malformed payloads observed from small local models.
    candidate = text.strip()
    candidate = candidate.replace("\\n", "\n")
    candidate = candidate.replace("\\t", "\t")
    candidate = candidate.replace('\\"', '"')
    candidate = candidate.replace("\\", " ")
    candidate = re.sub(r"[\u201c\u201d]", '"', candidate)
    candidate = re.sub(r"[\u2018\u2019]", "'", candidate)
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
    candidate = re.sub(r"\n{3,}", "\n\n", candidate)

    keys_pattern = re.compile(r"\b(headline|highlights|risks|actions|confidence)\b", flags=re.IGNORECASE)
    key_matches = list(keys_pattern.finditer(candidate))
    if not key_matches:
        return None

    out: dict[str, object] = {}
    for idx, match in enumerate(key_matches):
        key = match.group(1).lower()
        value_start = match.end()
        value_end = key_matches[idx + 1].start() if idx + 1 < len(key_matches) else len(candidate)
        raw_value = candidate[value_start:value_end]
        clean = _clean_relaxed_value(raw_value)
        if not clean:
            continue
        if key in {"highlights", "risks", "actions"}:
            out[key] = _split_relaxed_list(clean)
        else:
            out[key] = clean

    return out or None


def _clean_relaxed_value(raw: str) -> str:
    value = raw.strip()
    value = value.strip(",")
    value = re.sub(r"^[\s:=>\\\-\[\{\(]+", "", value)
    value = re.sub(r"[\]\}\)\s,]+$", "", value)
    value = value.strip('"').strip("'")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _split_relaxed_list(raw: str) -> list[str]:
    value = raw.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1].strip()

    if not value:
        return []

    if any(marker in value for marker in ("\n-", "\n*", ";", "|")):
        parts = re.split(r"\n-\s*|\n\*\s*|;\s*|\|\s*", value)
    else:
        parts = [value]

    cleaned: list[str] = []
    for part in parts:
        item = _clean_relaxed_value(part)
        if item:
            cleaned.append(item)
    return cleaned


def _normalize_summary_payload(raw: dict) -> dict:
    headline = _normalize_string(raw.get("headline"), fallback="Weekly COO Summary")
    highlights = _normalize_string_list(raw.get("highlights"), fallback=["Revenue and expense metrics reviewed."])
    risks = _normalize_string_list(raw.get("risks"), fallback=[])
    actions = _normalize_string_list(raw.get("actions"), fallback=["Review top expense categories."])
    confidence = _normalize_confidence(raw.get("confidence"))
    return {
        "headline": headline,
        "highlights": highlights[:4],
        "risks": risks[:4],
        "actions": actions[:4],
        "confidence": confidence,
    }


def _normalize_string(value: object, *, fallback: str) -> str:
    if isinstance(value, str):
        text = value.strip()
        if text:
            return text
    return fallback


def _normalize_string_list(value: object, *, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        out = [str(item).strip() for item in value if str(item).strip()]
        return out or fallback
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return fallback
        if any(marker in text for marker in ("\n-", "\n*", ";", "|")):
            parts = re.split(r"\n-\s*|\n\*\s*|;\s*|\|\s*", text)
            out = [part.strip() for part in parts if part.strip()]
            return out or fallback
        return [text]
    return fallback


def _normalize_confidence(value: object) -> str:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"low", "medium", "high"}:
            return lowered
    return "medium"


def _safe_excerpt(text: str, *, max_len: int = 400) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 3] + "..."


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
