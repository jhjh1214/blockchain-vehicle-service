"""
Push notification service using Firebase Cloud Messaging (FCM).

Requires FIREBASE_CREDENTIALS_JSON env var containing the Firebase service account
JSON (as a string). If not set, all calls are no-ops — the app runs normally without
push notifications.
"""
import json
import logging
import os

logger = logging.getLogger(__name__)

_firebase_app = None
_initialized = False


def _get_app():
    global _firebase_app, _initialized
    if _initialized:
        return _firebase_app
    _initialized = True
    creds_json = os.getenv('FIREBASE_CREDENTIALS_JSON', '')
    if not creds_json:
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials
        creds = credentials.Certificate(json.loads(creds_json))
        _firebase_app = firebase_admin.initialize_app(creds)
        logger.info('Firebase Admin SDK initialized')
    except Exception:
        logger.exception('Failed to initialize Firebase Admin SDK — push notifications disabled')
    return _firebase_app


def _persist(user_id: int, title: str, body: str, notif_type: str | None, data: dict | None) -> None:
    """Save notification to DB so users can view their inbox later."""
    try:
        from db.models import db, Notification
        n = Notification(user_id=user_id, title=title, body=body, type=notif_type, data=data)
        db.session.add(n)
        db.session.commit()
    except Exception:
        logger.exception('Failed to persist notification for user %d', user_id)


def send_to_user(user_id: int, title: str, body: str, data: dict | None = None) -> None:
    """Send an FCM notification to all device tokens for a user and persist to inbox."""
    notif_type = (data or {}).get('type')
    _persist(user_id, title, body, notif_type, data)

    if _get_app() is None:
        return
    from db.repositories import users as user_repo
    tokens = user_repo.get_device_tokens(user_id)
    if not tokens:
        return
    try:
        from firebase_admin import messaging
        messages = [
            messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={k: str(v) for k, v in (data or {}).items()},
                token=token,
            )
            for token in tokens
        ]
        response = messaging.send_each(messages)
        logger.debug('FCM batch send: %d success, %d failure',
                     response.success_count, response.failure_count)
    except Exception:
        logger.exception('FCM send failed for user %d', user_id)


def notify_new_pending_service(owner_user_id: int, vin: str, service_type: str) -> None:
    send_to_user(
        owner_user_id,
        title='New Service Record Pending',
        body=f'{service_type} for {vin} — tap to verify or dispute.',
        data={'type': 'pending_service', 'vin': vin},
    )


def notify_warranty_claim_update(owner_user_id: int, vin: str, status: str) -> None:
    label = {'approved': 'approved ✓', 'denied': 'denied', 'pending': 'received'}.get(status, status)
    send_to_user(
        owner_user_id,
        title='Warranty Claim Update',
        body=f'Your warranty claim for {vin} has been {label}.',
        data={'type': 'warranty_claim', 'vin': vin, 'status': status},
    )


def broadcast_recall(title: str, body: str, issued_by: str) -> int:
    """Broadcast a recall notice to all owner devices and persist to inbox. Returns number of tokens targeted."""
    from db.repositories import users as user_repo
    # Persist to notification inbox for every owner so the web bell shows it
    for owner in user_repo.find_all_by_role('OWNER'):
        _persist(owner.id, title, body, 'recall', {'type': 'recall', 'issued_by': issued_by})

    if _get_app() is None:
        return 0
    tokens = user_repo.get_all_owner_device_tokens()
    if not tokens:
        return 0
    try:
        from firebase_admin import messaging
        messages = [
            messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={'type': 'recall', 'issued_by': issued_by},
                token=token,
            )
            for token in tokens
        ]
        response = messaging.send_each(messages)
        logger.info('Recall broadcast: %d success, %d failure', response.success_count, response.failure_count)
        return response.success_count
    except Exception:
        logger.exception('Recall broadcast failed')
        return 0


def notify_dispute_resolved(owner_user_id: int, vin: str, decision: int) -> None:
    labels = {1: 'accepted', 2: 'rejected', 3: 'modified'}
    label = labels.get(decision, 'resolved')
    send_to_user(
        owner_user_id,
        title='Dispute Resolved',
        body=f'The disputed service record for {vin} has been {label} by the manufacturer.',
        data={'type': 'dispute_resolved', 'vin': vin, 'decision': str(decision)},
    )


def notify_dispute_filed_sc(sc_user_id: int, vin: str) -> None:
    send_to_user(
        sc_user_id,
        title='Service Record Disputed',
        body=f'An owner has disputed a service record for {vin}. Log in to view and respond.',
        data={'type': 'dispute_filed', 'vin': vin},
    )


def notify_dispute_filed_mfr(mfr_user_id: int, vin: str) -> None:
    send_to_user(
        mfr_user_id,
        title='New Dispute Filed',
        body=f'A service record dispute has been filed for vehicle {vin}.',
        data={'type': 'dispute_filed', 'vin': vin},
    )


def notify_rebuttal_submitted(owner_user_id: int, vin: str) -> None:
    send_to_user(
        owner_user_id,
        title='Rebuttal Received',
        body=f'The service centre has responded to your dispute for {vin}.',
        data={'type': 'rebuttal_submitted', 'vin': vin},
    )


def notify_dispute_escalated(mfr_user_id: int, vin: str) -> None:
    send_to_user(
        mfr_user_id,
        title='Dispute Escalated',
        body=f'A dispute for vehicle {vin} has been escalated for priority review.',
        data={'type': 'dispute_escalated', 'vin': vin},
    )


def notify_dispute_message(recipient_user_id: int, sender_name: str, vin: str, record_index: int) -> None:
    send_to_user(
        recipient_user_id,
        title='New Dispute Message',
        body=f'{sender_name}: New message in the dispute thread for {vin}.',
        data={'type': 'dispute_message', 'vin': vin, 'record_index': str(record_index)},
    )
