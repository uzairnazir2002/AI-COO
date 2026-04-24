from app.domain.schemas.ai import AISummaryResponse
from app.domain.services.ai_grounding_validator import AISemanticGroundingValidator


def _metrics():
    return {
        "kpis": {
            "cash_balance": "10000.00",
            "revenue_mtd": "1000.00",
            "expenses_mtd": "900.00",
            "net_profit_mtd": "100.00",
            "burn_rate_monthly": "100.00",
            "alerts_count_open": 2,
        },
        "alerts": [{"title": "Runway low"}],
    }


def test_grounding_validator_accepts_grounded_response():
    validator = AISemanticGroundingValidator()
    summary = AISummaryResponse(
        headline="Weekly COO Summary",
        highlights=["Revenue is 1,000.00 and expenses are 900.00 for this period."],
        risks=["2 open alerts include runway risk."],
        actions=["Review expense categories and open alerts."],
        confidence="high",
    )

    violations = validator.validate(summary, _metrics())

    assert violations == []


def test_grounding_validator_rejects_unsupported_metric():
    validator = AISemanticGroundingValidator()
    summary = AISummaryResponse(
        headline="Weekly COO Summary",
        highlights=["EBITDA improved this period."],
        risks=[],
        actions=[],
        confidence="high",
    )

    violations = validator.validate(summary, _metrics())

    assert any(v.startswith("unsupported_metric") for v in violations)


def test_grounding_validator_rejects_mismatched_number():
    validator = AISemanticGroundingValidator()
    summary = AISummaryResponse(
        headline="Weekly COO Summary",
        highlights=["Revenue is 5,000.00 for this period."],
        risks=[],
        actions=[],
        confidence="high",
    )

    violations = validator.validate(summary, _metrics())

    assert any(v.startswith("unsupported_number") for v in violations)


def test_grounding_validator_rejects_unsupported_causal_sentence():
    validator = AISemanticGroundingValidator()
    summary = AISummaryResponse(
        headline="Weekly COO Summary",
        highlights=["Revenue dropped because marketing spend increased."],
        risks=[],
        actions=[],
        confidence="high",
    )

    violations = validator.validate(summary, _metrics())

    assert any(v.startswith("unsupported_causal_claim") for v in violations)


def test_grounding_validator_accepts_workforce_numbers_when_payload_present():
    validator = AISemanticGroundingValidator()
    metrics = {
        **_metrics(),
        "workforce": {
            "dashboard": {"present_today": 4, "pending_leave_requests": 2},
            "reports": {"payroll": {"total_net_pay_in_range": "1234.50"}},
        },
    }
    summary = AISummaryResponse(
        headline="Weekly COO Summary",
        highlights=["Workforce: 4 people present today; 2 pending leave requests; net pay in range 1,234.50."],
        risks=[],
        actions=[],
        confidence="high",
    )
    violations = validator.validate(summary, metrics)
    assert violations == []


def test_grounding_validator_rejects_mismatched_time_window():
    validator = AISemanticGroundingValidator()
    summary = AISummaryResponse(
        headline="Weekly COO Summary",
        highlights=["Year-over-year revenue improved."],
        risks=[],
        actions=[],
        confidence="high",
    )

    violations = validator.validate(summary, _metrics())

    assert any(v.startswith("unsupported_time_scope") for v in violations)
