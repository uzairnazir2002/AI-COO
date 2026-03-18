from pydantic import TypeAdapter, ValidationError
import structlog

from app.domain.schemas.ai import AISummaryOut, AISummaryResponse
from app.domain.services.ai_grounding_validator import AISemanticGroundingValidator
from app.infra.ai_client import generate_summary, generate_summary_stub

logger = structlog.get_logger(__name__)


class AIService:
    def __init__(self):
        self._summary_adapter = TypeAdapter(AISummaryResponse)
        self._grounding_validator = AISemanticGroundingValidator()

    async def summary(self, metrics: dict) -> AISummaryOut:
        try:
            raw = generate_summary(metrics)
            valid = self._summary_adapter.validate_python(raw.model_dump())
            violations = self._grounding_validator.validate(valid, metrics)
            if violations:
                logger.warning("ai_summary_grounding_validation_failed", violations=violations[:10])
                raise ValueError("AI summary grounding validation failed")
            return AISummaryOut(summary_json=valid, fallback_used=False)
        except (ValidationError, AttributeError, TypeError, ValueError):
            fallback = generate_summary_stub(metrics)
            return AISummaryOut(summary_json=fallback, fallback_used=True)
