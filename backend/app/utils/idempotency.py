import uuid
from datetime import date


def report_key(org_id: str, week_start: date, location_id: uuid.UUID | None = None) -> str:
    if location_id is None:
        return f"reports/{org_id}/{week_start.isoformat()}.pdf"
    return f"reports/{org_id}/locations/{location_id}/{week_start.isoformat()}.pdf"
