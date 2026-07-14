"""Transactional email helpers for password reset (SMTP + dev log fallback)."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from backend.config import Settings

logger = logging.getLogger(__name__)


def send_password_reset_email(*, to_email: str, reset_token: str, settings: Settings) -> None:
    """Send reset link via SMTP when configured; always log in development."""
    reset_url = (
        f"{settings.frontend_base_url.rstrip('/')}/forgot-password"
        f"?token={reset_token}"
    )
    subject = "LexAI password reset"
    body = (
        "You requested a password reset for your LexAI account.\n\n"
        f"Open this link (valid for 1 hour):\n{reset_url}\n\n"
        f"Or paste this token on the reset page:\n{reset_token}\n\n"
        "If you did not request this, you can ignore this email.\n"
    )

    if settings.is_development:
        logger.info(
            "DEV password-reset email to=%s token=%s url=%s",
            to_email,
            reset_token,
            reset_url,
        )

    if not settings.smtp_host:
        if settings.is_development:
            logger.warning(
                "SMTP not configured — reset token logged for local testing only"
            )
            return
        raise RuntimeError(
            "SMTP is not configured. Set COMPLIANCE_SMTP_HOST (and related vars) "
            "or run with COMPLIANCE_APP_ENV=development."
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_user and settings.smtp_password:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
    logger.info("Password-reset email sent to=%s", to_email)
