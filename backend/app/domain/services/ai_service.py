from dataclasses import dataclass

from pydantic import TypeAdapter, ValidationError
import structlog

from app.domain.schemas.ai import AISummaryOut, AISummaryResponse
from app.domain.services.ai_grounding_validator import AISemanticGroundingValidator
from app.infra.ai_client import generate_summary, generate_summary_stub

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class AIChatGeneration:
    answer: str
    fallback_used: bool
    grounding_violations: list[str]


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
        except (ValidationError, AttributeError, TypeError, ValueError) as exc:
            logger.warning("ai_summary_fallback_used", reason=str(exc)[:300])
            fallback = generate_summary_stub(metrics)
            return AISummaryOut(summary_json=fallback, fallback_used=True)

    async def chat(self, user_message: str, metrics: dict) -> AIChatGeneration:
        violations: list[str] = []
        fallback_used = False
        try:
            raw = generate_summary(metrics)
            valid = self._summary_adapter.validate_python(raw.model_dump())
            violations = self._grounding_validator.validate(valid, metrics)
            if violations:
                logger.warning("ai_chat_grounding_validation_failed", violations=violations[:10])
                raise ValueError("AI chat grounding validation failed")
            summary = valid
        except (ValidationError, AttributeError, TypeError, ValueError) as exc:
            logger.warning("ai_chat_fallback_used", reason=str(exc)[:300])
            fallback_used = True
            summary = generate_summary_stub(metrics)

        return AIChatGeneration(
            answer=self._compose_chat_answer(user_message=user_message, summary=summary),
            fallback_used=fallback_used,
            grounding_violations=violations[:10],
        )

    @staticmethod
    def _compose_chat_answer(*, user_message: str, summary: AISummaryResponse) -> str:
        highlights = "; ".join(summary.highlights[:2]) or "No highlights available."
        risks = "; ".join(summary.risks[:2]) or "No critical risks flagged."
        actions = "; ".join(summary.actions[:2]) or "No immediate action items."
        return (
            f'Question: "{user_message}"\n'
            f"{summary.headline}\n"
            f"Highlights: {highlights}\n"
            f"Risks: {risks}\n"
            f"Recommended actions: {actions}\n"
            f"Confidence: {summary.confidence}"
        )
