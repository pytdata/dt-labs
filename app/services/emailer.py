from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Optional

from app.core.config import settings

def send_stage_email(
    to_email: str,
    patient_name: str,
    stage: str,
    order_id: int,
    test_name: Optional[str] = None,
) -> None:
    """Send stage change notification email using SMTP settings.
    This is called via FastAPI BackgroundTasks.
    """
    if not settings.SMTP_HOST:
        return

    subject = f"DT-LABS: Lab Order Update (Order #{order_id})"
    title = f"Hello {patient_name},"
    body_lines = [
        title,
        "",
        f"Your laboratory process has moved to: {stage.replace('_',' ').title()}",
        f"Order ID: {order_id}",
    ]
    if test_name:
        body_lines.append(f"Test: {test_name}")
    body_lines += [
        "",
        "Thank you.",
        settings.ORG_NAME or "DT-LABS",
    ]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER or ""
    msg["To"] = to_email
    msg.set_content("\n".join(body_lines))

    host = settings.SMTP_HOST
    port = settings.SMTP_PORT

    if settings.SMTP_TLS:
        server = smtplib.SMTP(host, port, timeout=15)
        server.starttls()
    else:
        server = smtplib.SMTP(host, port, timeout=15)

    try:
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass
