from collections.abc import Mapping

from fastapi import Request


_STATUS_CODE_MAP: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
}


def code_for_status(status_code: int) -> str:
    return _STATUS_CODE_MAP.get(status_code, "request_failed")


def error_payload(
    *,
    request: Request | None,
    status_code: int,
    message: str,
    details: object | None = None,
    code: str | None = None,
) -> dict[str, object]:
    request_id = getattr(getattr(request, "state", None), "request_id", None)
    payload: dict[str, object] = {
        "code": code or code_for_status(status_code),
        "message": message,
        "request_id": request_id,
        "details": details,
    }
    # Backward-compat field consumed by existing clients/tests.
    payload["detail"] = details if details is not None else message
    return payload


def detail_to_message(detail: object, default: str) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, Mapping):
        value = detail.get("message")
        if isinstance(value, str) and value:
            return value
    return default
