"""APScheduler jobs — started once in app.py after the app is created."""
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_REMINDER_DAYS   = 30    # send reminder this many days before expiry
_SEND_HOUR       = 8     # run daily at 08:00
_AUDIT_RETAIN_DAYS = 365  # delete audit logs older than this many days


def _send_expiry_reminders(app):
    """Query vehicles expiring in ~30 days and email their owners."""
    with app.app_context():
        try:
            now    = int(time.time())
            window = _REMINDER_DAYS * 24 * 3600
            lower  = now + window - 3600      # ±1 h window to avoid missing due to scheduler drift
            upper  = now + window + 3600

            from db.models import VehicleVINMapping, User, db
            expiring = (
                VehicleVINMapping.query
                .filter(VehicleVINMapping.warranty_expiry >= lower,
                        VehicleVINMapping.warranty_expiry <= upper,
                        VehicleVINMapping.registration_status == 'active')
                .all()
            )
            for mapping in expiring:
                owner = User.query.filter_by(
                    blockchain_address=mapping.owner_address, role='OWNER'
                ).first()
                if owner:
                    _send_reminder_email(owner.email, owner.name or owner.email,
                                         mapping.vin, mapping.make, mapping.model,
                                         mapping.warranty_expiry)
        except Exception:
            logger.exception('warranty expiry reminder job failed')


def _send_reminder_email(to_email, name, vin, make, model, expiry_ts):
    import os
    import resend
    from config import Config

    expiry_date = datetime.utcfromtimestamp(expiry_ts).strftime('%d %b %Y')
    vehicle_str = f"{make or ''} {model or ''}".strip() or 'your vehicle'
    subject     = f'Warranty expiring soon — {vehicle_str} ({vin})'

    try:
        resend.api_key = os.getenv('RESEND_API_KEY', '')
        if not resend.api_key:
            logger.warning('RESEND_API_KEY not set — skipping warranty reminder email')
            return
        resend.Emails.send({
            'from': os.getenv('MAIL_DEFAULT_SENDER', 'VehicleChain <noreply@vehiclechain.my>'),
            'to': [to_email],
            'subject': subject,
            'text': (
                f"Hi {name},\n\n"
                f"The warranty for {vehicle_str} (VIN: {vin}) is expiring on {expiry_date}, "
                f"which is in approximately {_REMINDER_DAYS} days.\n\n"
                f"Log in to VehicleChain to review your warranty status or file a claim before it expires.\n\n"
                f"-- The VehicleChain Team"
            ),
            'html': (
                f"<p>Hi {name},</p>"
                f"<p>The warranty for <strong>{vehicle_str}</strong> (VIN: {vin}) is expiring on "
                f"<strong>{expiry_date}</strong> (~{_REMINDER_DAYS} days from now).</p>"
                f"<p><a href='{Config.FRONTEND_URL}' style='background:#1A73E8;color:#fff;"
                f"padding:10px 20px;border-radius:6px;text-decoration:none;display:inline-block;'>"
                f"Open VehicleChain</a></p>"
                f"<p style='color:#666;font-size:13px;'>Log in to review your warranty status or "
                f"file a claim before it expires.</p>"
            ),
        })
        logger.info('sent warranty expiry reminder to %s for VIN %s via Resend', to_email, vin)
    except Exception:
        logger.exception('failed to send warranty reminder email to %s', to_email)


def _purge_old_audit_logs(app):
    """Delete audit log entries older than _AUDIT_RETAIN_DAYS (PDPA retention policy)."""
    with app.app_context():
        try:
            from db.models import AuditLog, db
            cutoff = datetime.utcnow() - timedelta(days=_AUDIT_RETAIN_DAYS)
            deleted = AuditLog.query.filter(AuditLog.created_at < cutoff).delete(synchronize_session=False)
            db.session.commit()
            if deleted:
                logger.info('Purged %d audit log entries older than %d days', deleted, _AUDIT_RETAIN_DAYS)
        except Exception:
            logger.exception('audit log purge job failed')


def init_scheduler(app):
    """Start the background scheduler. Called from app.py after app creation."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        scheduler = BackgroundScheduler(timezone='UTC')
        scheduler.add_job(
            _send_expiry_reminders,
            trigger=CronTrigger(hour=_SEND_HOUR, minute=0),
            args=[app],
            id='warranty_expiry_reminders',
            replace_existing=True,
        )
        scheduler.add_job(
            _purge_old_audit_logs,
            trigger=CronTrigger(hour=3, minute=0),  # 03:00 UTC daily
            args=[app],
            id='audit_log_purge',
            replace_existing=True,
        )
        scheduler.start()
        logger.info('APScheduler started — warranty reminders at %02d:00 UTC, audit purge at 03:00 UTC', _SEND_HOUR)
    except Exception:
        logger.exception('Failed to start APScheduler')
