"""Shared Resend email utility used by the event monitor and API endpoints."""
import logging
import os

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, text: str, html: str | None = None) -> bool:
    """Send a transactional email via Resend. Returns True on success, False if skipped/failed."""
    try:
        import resend
        resend.api_key = os.getenv('RESEND_API_KEY', '')
        if not resend.api_key:
            logger.warning('RESEND_API_KEY not set — skipping email to %s', to)
            return False
        payload: dict = {
            'from': os.getenv('MAIL_DEFAULT_SENDER', 'VehicleChain <noreply@vehiclechain.my>'),
            'to': [to],
            'subject': subject,
            'text': text,
        }
        if html:
            payload['html'] = html
        resend.Emails.send(payload)
        logger.info('Email sent to %s: %s', to, subject)
        return True
    except Exception:
        logger.exception('Failed to send email to %s', to)
        return False
