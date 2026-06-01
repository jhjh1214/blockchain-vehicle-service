"""APScheduler jobs — started once in app.py after the app is created."""
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_REMINDER_DAYS        = 30    # send reminder this many days before warranty expiry
_SEND_HOUR            = 8     # run daily at 08:00 UTC
_AUDIT_RETAIN_DAYS    = 365   # delete audit logs older than this many days
_SERVICE_OVERDUE_DAYS = 180   # flag vehicles not serviced in this many days
_NOTIF_RETAIN_DAYS    = 90    # delete notifications older than this many days


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


def _send_service_overdue_reminders(app):
    """Find vehicles not serviced in _SERVICE_OVERDUE_DAYS and push/email owners."""
    with app.app_context():
        try:
            from db.models import VehicleVINMapping, ServiceMetadata, User, db
            cutoff = datetime.utcnow() - timedelta(days=_SERVICE_OVERDUE_DAYS)

            # Get the most recent service date per VIN in one query
            from sqlalchemy import func as _func
            last_service = (
                db.session.query(
                    ServiceMetadata.vin,
                    _func.max(ServiceMetadata.service_date).label('last_date'),
                )
                .group_by(ServiceMetadata.vin)
                .subquery()
            )

            # VINs that have at least one service but none within the cutoff window
            overdue_with_service = (
                db.session.query(VehicleVINMapping)
                .join(last_service, VehicleVINMapping.vin == last_service.c.vin)
                .filter(
                    last_service.c.last_date < cutoff,
                    VehicleVINMapping.registration_status == 'active',
                    VehicleVINMapping.owner_address.isnot(None),
                )
                .all()
            )

            # VINs that have never been serviced and were registered > _SERVICE_OVERDUE_DAYS ago
            serviced_vins = db.session.query(ServiceMetadata.vin).distinct().subquery()
            never_serviced = (
                db.session.query(VehicleVINMapping)
                .filter(
                    VehicleVINMapping.vin.notin_(serviced_vins),
                    VehicleVINMapping.created_at < cutoff,
                    VehicleVINMapping.registration_status == 'active',
                    VehicleVINMapping.owner_address.isnot(None),
                )
                .all()
            )

            all_overdue = overdue_with_service + never_serviced
            logger.info('Service overdue check: %d vehicles flagged', len(all_overdue))

            for mapping in all_overdue:
                owner = User.query.filter_by(
                    blockchain_address=mapping.owner_address, role='OWNER'
                ).first()
                if not owner:
                    continue
                vehicle_str = f"{mapping.make or ''} {mapping.model or ''}".strip() or mapping.vin
                # FCM push
                try:
                    from core.notifications import send_to_user
                    send_to_user(
                        owner.id,
                        title='Service Due',
                        body=f'Your {vehicle_str} ({mapping.vin}) is due for a service. '
                             f'It has been over {_SERVICE_OVERDUE_DAYS} days since the last recorded service.',
                        data={'type': 'service_reminder', 'vin': mapping.vin},
                    )
                except Exception:
                    pass
                # Email
                try:
                    import os, resend
                    resend.api_key = os.getenv('RESEND_API_KEY', '')
                    if resend.api_key:
                        from config import Config
                        resend.Emails.send({
                            'from': os.getenv('MAIL_DEFAULT_SENDER', 'VehicleChain <noreply@vehiclechain.my>'),
                            'to': [owner.email],
                            'subject': f'Service reminder — {vehicle_str}',
                            'text': (
                                f'Hi {owner.name or owner.email},\n\n'
                                f'Your {vehicle_str} (VIN: {mapping.vin}) has not had a recorded service '
                                f'in over {_SERVICE_OVERDUE_DAYS} days.\n\n'
                                f'Regular servicing keeps your warranty valid and your vehicle safe. '
                                f'Book your next service through an authorised service centre.\n\n'
                                f'-- The VehicleChain Team'
                            ),
                        })
                except Exception:
                    pass

        except Exception:
            logger.exception('service overdue reminder job failed')


def _purge_old_notifications(app):
    """Delete notifications older than _NOTIF_RETAIN_DAYS to prevent unbounded table growth."""
    with app.app_context():
        try:
            from db.models import Notification, db
            cutoff = datetime.utcnow() - timedelta(days=_NOTIF_RETAIN_DAYS)
            deleted = Notification.query.filter(Notification.created_at < cutoff).delete(synchronize_session=False)
            db.session.commit()
            if deleted:
                logger.info('Purged %d notifications older than %d days', deleted, _NOTIF_RETAIN_DAYS)
        except Exception:
            logger.exception('notification purge job failed')


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
        scheduler.add_job(
            _send_service_overdue_reminders,
            trigger=CronTrigger(day_of_week='mon', hour=9, minute=0),  # Monday 09:00 UTC weekly
            args=[app],
            id='service_overdue_reminders',
            replace_existing=True,
        )
        scheduler.add_job(
            _purge_old_notifications,
            trigger=CronTrigger(hour=4, minute=0),  # 04:00 UTC daily
            args=[app],
            id='notification_purge',
            replace_existing=True,
        )
        scheduler.start()
        logger.info(
            'APScheduler started — warranty reminders at %02d:00 UTC, '
            'audit purge at 03:00 UTC, service overdue check Mondays at 09:00 UTC, '
            'notification purge at 04:00 UTC',
            _SEND_HOUR,
        )
    except Exception:
        logger.exception('Failed to start APScheduler')
