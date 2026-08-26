from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings


@dataclass(slots=True)
class SendEmailResult:
    status: str  # sent | sent_dry_run | failed
    provider: str
    provider_message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None


def _render_from_header() -> str:
    settings = get_settings()
    from_name = (settings.email_from_name or "").strip()
    from_addr = (settings.email_from_address or "").strip()
    if from_name and from_addr:
        return f"{from_name} <{from_addr}>"
    return from_addr or "noreply@aicoo.local"


def _send_smtp(*, to: str, subject: str, body_text: str, body_html: str | None) -> SendEmailResult:
    settings = get_settings()
    from_header = _render_from_header()
    if body_html:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))
    else:
        msg = MIMEText(body_text, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_header
    msg["To"] = to
    reply_to = (settings.email_reply_to or "").strip()
    if reply_to:
        msg["Reply-To"] = reply_to
    try:
        if settings.smtp_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.sendmail(from_header, [to], msg.as_string())
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
                if settings.smtp_starttls:
                    smtp.starttls()
                    smtp.ehlo()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.sendmail(from_header, [to], msg.as_string())
        return SendEmailResult(status="sent", provider="smtp")
    except Exception as exc:
        return SendEmailResult(
            status="failed",
            provider="smtp",
            error_code=exc.__class__.__name__,
            error_message=str(exc),
        )


def _send_resend(*, to: str, subject: str, body_text: str, body_html: str | None) -> SendEmailResult:
    settings = get_settings()
    try:
        import resend  # type: ignore
    except Exception as exc:
        return SendEmailResult(
            status="failed",
            provider="resend",
            error_code="ResendImportError",
            error_message=str(exc),
        )
    resend.api_key = settings.resend_api_key
    payload: resend.Emails.SendParams = {
        "from": _render_from_header(),
        "to": [to],
        "subject": subject,
        "text": body_text,
    }
    if body_html:
        payload["html"] = body_html
    reply_to = (settings.email_reply_to or "").strip()
    if reply_to:
        payload["reply_to"] = [reply_to]
    try:
        out = resend.Emails.send(payload)
        provider_id = None
        if isinstance(out, dict):
            provider_id = str(out.get("id") or out.get("message_id") or "")
        else:
            provider_id = str(getattr(out, "id", "") or getattr(out, "message_id", "") or "")
        return SendEmailResult(
            status="sent",
            provider="resend",
            provider_message_id=provider_id or None,
        )
    except Exception as exc:
        return SendEmailResult(
            status="failed",
            provider="resend",
            error_code=exc.__class__.__name__,
            error_message=str(exc),
        )


def send_email(to: str, subject: str, body: str, *, html_body: str | None = None) -> SendEmailResult:
    settings = get_settings()
    if settings.email_dry_run:
        return SendEmailResult(status="sent_dry_run", provider="dry_run")

    provider = (settings.email_provider or "smtp").strip().lower()
    if provider == "resend":
        return _send_resend(to=to, subject=subject, body_text=body, body_html=html_body)
    return _send_smtp(to=to, subject=subject, body_text=body, body_html=html_body)
