import asyncio
import smtplib
from email.message import EmailMessage

from app.auth.password_reset import PasswordResetTokenIssue
from app.core.config import settings


async def deliver_password_reset(issue: PasswordResetTokenIssue) -> bool:
    if settings.smtp_host is None or settings.smtp_from_email is None:
        return False

    message = EmailMessage()
    message["Subject"] = "Reset your Seasonly password"
    message["From"] = settings.smtp_from_email
    message["To"] = issue.user.email
    body = (
        "Use the following one-time token in the Seasonly app to reset your password:\n\n"
        + issue.token
        + "\n\nThis token expires in "
        + str(settings.auth_password_reset_token_expire_minutes)
        + " minutes."
    )
    message.set_content(body)
    await asyncio.to_thread(_send_message, message)
    return True


def _send_message(message: EmailMessage) -> None:
    if settings.smtp_host is None:
        raise ValueError("SMTP_HOST is required")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
        if settings.smtp_starttls:
            _ = client.starttls()
        if settings.smtp_username is not None and settings.smtp_password is not None:
            _ = client.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        _ = client.send_message(message)
