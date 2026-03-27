from types import SimpleNamespace

import pytest

from app.domain.services.ai_service import AIService
from app.domain.schemas.ai import AISummaryResponse
from app.infra import ai_client


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeHttpClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, headers, json):
        _ = (url, headers, json)
        return _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"headline":"Weekly COO Summary","highlights":["Revenue steady"],"risks":["Runway low"],"actions":["Reduce spend"],"confidence":"medium"}'
                        }
                    }
                ]
            }
        )


class _FakeOllamaHttpClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, headers, json):
        _ = (url, headers, json)
        return _FakeResponse(
            {
                "aiText": '{"headline":"Weekly COO Summary","highlights":["Revenue stable"],"risks":["Runway watch"],"actions":["Trim non-essential spend"],"confidence":"medium"}'
            }
        )


def test_generate_summary_openai_success(monkeypatch):
    monkeypatch.setattr(
        ai_client,
        "get_settings",
        lambda: SimpleNamespace(
            ai_provider="openai",
            ai_openai_api_key="test-key",
            ai_openai_model="gpt-4o-mini",
            ai_openai_base_url="https://api.openai.com/v1",
            ai_timeout_seconds=10,
        ),
    )
    monkeypatch.setattr(ai_client.httpx, "Client", _FakeHttpClient)

    out = ai_client.generate_summary({"kpis": {}, "alerts": []})

    assert out.headline == "Weekly COO Summary"
    assert out.confidence == "medium"


def test_generate_summary_ollama_server_success(monkeypatch):
    monkeypatch.setattr(
        ai_client,
        "get_settings",
        lambda: SimpleNamespace(
            ai_provider="ollama_server",
            ai_ollama_server_url="http://localhost:5000/ai",
            ai_ollama_server_api_key="shared-secret-key",
            ai_ollama_server_model="gemma3:1b",
            ai_timeout_seconds=10,
        ),
    )
    monkeypatch.setattr(ai_client.httpx, "Client", _FakeOllamaHttpClient)

    out = ai_client.generate_summary({"kpis": {}, "alerts": []})

    assert out.headline == "Weekly COO Summary"
    assert out.highlights[0] == "Revenue stable"


def test_ai_provider_health_ollama_server_config_missing(monkeypatch):
    monkeypatch.setattr(
        ai_client,
        "get_settings",
        lambda: SimpleNamespace(
            ai_provider="ollama_server",
            ai_ollama_server_url="http://localhost:5000/ai",
            ai_ollama_server_api_key="",
            ai_ollama_server_model="gemma3:1b",
            ai_timeout_seconds=10,
        ),
    )

    health = ai_client.get_ai_provider_health(live_check=False)

    assert health["provider"] == "ollama_server"
    assert health["configured"] is False
    assert health["healthy"] is False
    assert "AI_OLLAMA_SERVER_URL and AI_OLLAMA_SERVER_API_KEY" in str(health["reason"])


def test_ai_provider_health_ollama_server_live_check(monkeypatch):
    monkeypatch.setattr(
        ai_client,
        "get_settings",
        lambda: SimpleNamespace(
            ai_provider="ollama_server",
            ai_ollama_server_url="http://localhost:5000/ai",
            ai_ollama_server_api_key="shared-secret-key",
            ai_ollama_server_model="gemma3:1b",
            ai_timeout_seconds=10,
        ),
    )
    monkeypatch.setattr(ai_client, "_ollama_server_live_health_check", lambda: None)

    health = ai_client.get_ai_provider_health(live_check=True)

    assert health["provider"] == "ollama_server"
    assert health["configured"] is True
    assert health["healthy"] is True
    assert health["live_check_performed"] is True


@pytest.mark.asyncio
async def test_ai_service_falls_back_on_provider_error(monkeypatch, sample_metrics):
    monkeypatch.setattr("app.domain.services.ai_service.generate_summary", lambda _metrics: (_ for _ in ()).throw(ValueError("boom")))

    out = await AIService().summary(sample_metrics)

    assert out.fallback_used is True
    assert out.summary_json.headline == "Weekly COO Summary"


@pytest.mark.asyncio
async def test_ai_service_falls_back_on_grounding_violation(monkeypatch, sample_metrics):
    monkeypatch.setattr(
        "app.domain.services.ai_service.generate_summary",
        lambda _metrics: AISummaryResponse(
            headline="Weekly COO Summary",
            highlights=["EBITDA improved this period."],
            risks=[],
            actions=[],
            confidence="high",
        ),
    )

    out = await AIService().summary(sample_metrics)

    assert out.fallback_used is True
    assert out.summary_json.headline == "Weekly COO Summary"


@pytest.mark.asyncio
async def test_ai_chat_uses_grounded_summary(monkeypatch, sample_metrics):
    monkeypatch.setattr(
        "app.domain.services.ai_service.generate_summary",
        lambda _metrics: AISummaryResponse(
            headline="Weekly COO Summary",
            highlights=["Revenue remains steady this period."],
            risks=["Runway risk remains visible."],
            actions=["Reduce discretionary spend."],
            confidence="high",
        ),
    )

    out = await AIService().chat("What should I focus on this week?", sample_metrics)

    assert out.fallback_used is False
    assert out.grounding_violations == []
    assert "What should I focus on this week?" in out.answer


@pytest.mark.asyncio
async def test_ai_chat_falls_back_on_grounding_violation(monkeypatch, sample_metrics):
    monkeypatch.setattr(
        "app.domain.services.ai_service.generate_summary",
        lambda _metrics: AISummaryResponse(
            headline="Weekly COO Summary",
            highlights=["EBITDA improved significantly."],
            risks=[],
            actions=[],
            confidence="high",
        ),
    )

    out = await AIService().chat("Is margin healthy?", sample_metrics)

    assert out.fallback_used is True
    assert any(v.startswith("unsupported_metric") for v in out.grounding_violations)
    assert "Question: \"Is margin healthy?\"" in out.answer
