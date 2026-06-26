"""Email alert utility using Resend API."""

import logging
import resend
from app.config import settings

logger = logging.getLogger(__name__)


async def send_error_email(error: Exception, context: str = "Scraper") -> None:
    if not settings.resend_api_key:
        logger.warning("Email alert skipped — RESEND_API_KEY not configured")
        return

    try:
        resend.api_key = settings.resend_api_key

        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": settings.alert_email_to,
            "subject": f"🚨 Job Scraper Failed — {context}",
            "html": f"""
                <html><body>
                <h2 style="color:red;">Job Scraper Error 🚨</h2>
                <table border="1" cellpadding="8" style="border-collapse:collapse;">
                    <tr><td><b>Context</b></td><td>{context}</td></tr>
                    <tr><td><b>Error Type</b></td><td>{type(error).__name__}</td></tr>
                    <tr><td><b>Message</b></td><td>{str(error)}</td></tr>
                </table>
                <p>Check Render logs for full details.</p>
                </body></html>
            """
        })
        logger.info("✅ Alert email sent!")

    except Exception as mail_err:
        logger.error("❌ Failed to send alert email: %s", mail_err)