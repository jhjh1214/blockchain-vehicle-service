import logging
from flask import request as flask_request
from db.models import db, AuditLog

logger = logging.getLogger(__name__)


def log_event(event: str, user_id: int = None, detail: dict = None) -> None:
    """Persist an audit event and emit a structured log line."""
    try:
        ip = (flask_request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
              or flask_request.remote_addr)
        entry = AuditLog(
            event=event,
            user_id=user_id,
            detail=detail or {},
            ip_address=ip,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error('audit log write failed for event=%s: %s', event, exc)

    logger.info('AUDIT event=%s user_id=%s detail=%s', event, user_id, detail)
