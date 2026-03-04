from pydantic import TypeAdapter, ValidationError

from app.domain.schemas.ai import AISummaryOut, AISummaryResponse
from app.infra.ai_client import generate_summary_stub


class AIService:
    def __init__(self):
        self._summary_adapter = TypeAdapter(AISummaryResponse)

    async def summary(self, metrics: dict) -> AISummaryOut:
        try:
            raw = generate_summary_stub(metrics)
            valid = self._summary_adapter.validate_python(raw.model_dump())
            return AISummaryOut(summary_json=valid, fallback_used=False)
        except (ValidationError, AttributeError, TypeError, ValueError):
            fallback = generate_summary_stub(metrics)
            return AISummaryOut(summary_json=fallback, fallback_used=True)
