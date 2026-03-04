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
