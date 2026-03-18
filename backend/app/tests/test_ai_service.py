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
