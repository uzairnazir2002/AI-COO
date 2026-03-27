import re
from decimal import Decimal, InvalidOperation

from app.domain.schemas.ai import AISummaryResponse

_NUMBER_RE = re.compile(r"(?<!\w)(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)(%?)")

# Explicitly disallow unsupported business metrics not present in current computed KPI payload.
_UNSUPPORTED_METRIC_TERMS = (
    "ebitda",
    "arr",
    "mrr",
    "cac",
    "ltv",
    "gross margin",
    "churn",
    "nrr",
    "run rate",
)

_UNSUPPORTED_TIME_TERMS = (
    "yoy",
    "year-over-year",
    "qoq",
    "quarter-over-quarter",
    "last year",
    "annual",
    "yearly",
    "q1",
    "q2",
    "q3",
    "q4",
)

_CAUSAL_TERMS = (
    "because",
    "due to",
    "caused by",
    "driven by",
    "as a result of",
)

_METRIC_KEYWORDS_BY_KPI = {
    "cash_balance": {"cash", "cash balance"},
    "revenue_mtd": {"revenue"},
    "expenses_mtd": {"expense", "expenses", "spend", "cost"},
    "net_profit_mtd": {"net", "net profit", "profit"},
    "burn_rate_monthly": {"burn", "burn rate"},
    "alerts_count_open": {"alert", "alerts"},
}


class AISemanticGroundingValidator:
    def validate(self, summary: AISummaryResponse, metrics: dict) -> list[str]:
        violations: list[str] = []
        lines = [summary.headline, *summary.highlights, *summary.risks, *summary.actions]
        allowed_numbers = self._collect_allowed_numbers(metrics)
        allowed_metric_terms = self._collect_allowed_metric_terms(metrics)

        for line in lines:
            lowered = line.lower()

            for term in _UNSUPPORTED_METRIC_TERMS:
                if term in lowered:
                    violations.append(f"unsupported_metric:{term}")
                    break

            for term in _UNSUPPORTED_TIME_TERMS:
                if term in lowered:
                    violations.append(f"unsupported_time_scope:{term}")
                    break

            for term in _CAUSAL_TERMS:
                if term in lowered:
                    violations.append(f"unsupported_causal_claim:{term}")
                    break

            mentioned_supported_metric_terms = {
                metric_term
                for terms in _METRIC_KEYWORDS_BY_KPI.values()
                for metric_term in terms
                if metric_term in lowered
            }
            if mentioned_supported_metric_terms and not (mentioned_supported_metric_terms & allowed_metric_terms):
                violations.append("unsupported_metric_reference")

            for numeric_raw, _percent_suffix in _NUMBER_RE.findall(line):
                parsed = self._parse_decimal(numeric_raw)
                if parsed is None:
                    continue
                if not self._matches_allowed_number(parsed, allowed_numbers):
                    violations.append(f"unsupported_number:{numeric_raw}")

        return violations

    @staticmethod
    def _parse_decimal(raw: str) -> Decimal | None:
        try:
            return Decimal(raw.replace(",", ""))
        except (InvalidOperation, AttributeError):
            return None

    def _collect_allowed_numbers(self, metrics: dict) -> set[Decimal]:
        out: set[Decimal] = set()
        kpis = metrics.get("kpis", {}) or {}
        for value in kpis.values():
            dec = self._parse_decimal(str(value))
            if dec is not None:
                out.add(dec)
        for alert in metrics.get("alerts", []) or []:
            for num_raw, _ in _NUMBER_RE.findall(str(alert.get("title", ""))):
                dec = self._parse_decimal(num_raw)
                if dec is not None:
                    out.add(dec)
        return out

    def _collect_allowed_metric_terms(self, metrics: dict) -> set[str]:
        allowed: set[str] = set()
        kpis = metrics.get("kpis", {}) or {}
        for key, terms in _METRIC_KEYWORDS_BY_KPI.items():
            if key in kpis:
                allowed.update(terms)
        for alert in metrics.get("alerts", []) or []:
            title = str(alert.get("title", "")).lower()
            for terms in _METRIC_KEYWORDS_BY_KPI.values():
                for term in terms:
                    if term in title:
                        allowed.add(term)
        return allowed

    @staticmethod
    def _matches_allowed_number(candidate: Decimal, allowed_numbers: set[Decimal]) -> bool:
        for allowed in allowed_numbers:
            tolerance = max(Decimal("0.50"), (abs(allowed) * Decimal("0.01")))
            if abs(candidate - allowed) <= tolerance:
                return True
        return False
