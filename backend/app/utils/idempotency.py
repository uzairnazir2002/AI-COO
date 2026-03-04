from datetime import date


def report_key(org_id: str, week_start: date) -> str:
    return f"reports/{org_id}/{week_start.isoformat()}.pdf"
