import smtplib
from email.mime.text import MIMEText

from app.core.config import get_settings


def send_email(to: str, subject: str, body: str) -> None:
    settings = get_settings()
    if settings.email_dry_run:
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "noreply@aicoo.local"
    msg["To"] = to
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.sendmail(msg["From"], [to], msg.as_string())
