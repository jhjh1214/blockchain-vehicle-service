from datetime import datetime
from flask import Blueprint, request, jsonify
from api.middleware import token_required
from core import auth_service
from core.audit import log_event
from db.repositories import users as user_repo
from extensions import limiter

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
@limiter.limit('20 per minute')
def register():
    data = request.get_json() or {}
    for field in ('email', 'password', 'role'):
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    name = data.get('name') or data['email'].split('@')[0]
    try:
        user, access_token, refresh_token = auth_service.register_user(
            email=data['email'],
            password=data['password'],
            role=data['role'],
            name=name,
            phone=data.get('phone', ''),
            city=data.get('city', ''),
            state=data.get('state', ''),
            brand=data.get('brand', ''),
            consent_given=bool(data.get('consent_given', False)),
        )
        return jsonify({
            'message': 'User registered successfully',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@auth_bp.route('/login', methods=['POST'])
@limiter.limit('10 per minute')
def login():
    data = request.get_json() or {}
    if 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Email and password required'}), 400
    try:
        user, access_token, refresh_token = auth_service.login_user(
            data['email'], data['password']
        )
        log_event('login_success', user_id=user.id, detail={'email': data['email']})
        return jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        }), 200
    except ValueError as e:
        msg = str(e)
        log_event('login_failure', detail={'email': data.get('email'), 'reason': msg})
        status = 423 if 'locked' in msg.lower() else 401
        return jsonify({'error': msg}), status


@auth_bp.route('/refresh', methods=['POST'])
@limiter.limit('30 per minute')
def refresh():
    data = request.get_json() or {}
    raw = data.get('refresh_token')
    if not raw:
        return jsonify({'error': 'refresh_token required'}), 400
    try:
        user, access_token, new_refresh = auth_service.refresh_access_token(raw)
        return jsonify({
            'access_token': access_token,
            'refresh_token': new_refresh,
            'user': user.to_dict()
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 401


@auth_bp.route('/logout', methods=['POST'])
def logout():
    data = request.get_json() or {}
    raw = data.get('refresh_token')
    if raw:
        auth_service.logout_user(raw)
    return jsonify({'message': 'Logged out'}), 200


@auth_bp.route('/logout-all', methods=['POST'])
@token_required
def logout_all():
    auth_service.logout_all_devices(request.user['user_id'])
    return jsonify({'message': 'All sessions revoked'}), 200


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    user = auth_service.get_user_by_id(request.user['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict()), 200


@auth_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile():
    data = request.get_json() or {}
    from api.utils import sanitize
    if 'brand' in data and request.user.get('role') in ('MANUFACTURER', 'SERVICE_CENTER'):
        return jsonify({'error': 'Brand cannot be changed for MANUFACTURER or SERVICE_CENTER accounts'}), 400
    name  = sanitize(data['name'],  255) if 'name'  in data else None
    phone = sanitize(data['phone'],  20) if 'phone' in data else None
    city  = sanitize(data['city'],  100) if 'city'  in data else None
    state = sanitize(data['state'], 100) if 'state' in data else None
    brand = sanitize(data['brand'], 100) if 'brand' in data else None
    user = user_repo.update_profile(request.user['user_id'], name=name, phone=phone,
                                    city=city, state=state, brand=brand)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'message': 'Profile updated', 'user': user.to_dict()}), 200


@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password():
    data = request.get_json() or {}
    current = data.get('current_password', '')
    new_pw  = data.get('new_password', '')
    if not current or not new_pw:
        return jsonify({'error': 'current_password and new_password required'}), 400
    user = auth_service.get_user_by_id(request.user['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if not user.check_password(current):
        return jsonify({'error': 'Current password is incorrect'}), 401
    try:
        auth_service.validate_password(new_pw)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    user.set_password(new_pw)
    from db.models import db
    db.session.commit()
    user_repo.revoke_all_refresh_tokens(user.id)
    log_event('password_changed', user_id=user.id)
    return jsonify({'message': 'Password changed. Please log in again.'}), 200


@auth_bp.route('/forgot-password', methods=['POST'])
@limiter.limit('5 per minute')
def forgot_password():
    from api.utils import sanitize
    from config import Config
    from db.models import db, PasswordResetToken
    from datetime import timedelta
    import hashlib
    data = request.get_json() or {}
    email = sanitize(data.get('email', ''), 255).lower().strip()
    if not email or '@' not in email:
        return jsonify({'error': 'A valid email address is required'}), 400

    user = user_repo.find_by_email(email)
    # Always return 200 to prevent email enumeration
    if user:
        # Invalidate any existing tokens
        PasswordResetToken.query.filter_by(user_id=user.id, used=False).update({'used': True})
        raw_token = PasswordResetToken.generate()
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expiry = datetime.utcnow() + timedelta(minutes=Config.PASSWORD_RESET_EXPIRY_MINUTES)
        reset_token = PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expiry)
        db.session.add(reset_token)
        db.session.commit()

        reset_url = f"{Config.FRONTEND_URL}/reset-password?token={raw_token}"
        import threading
        from flask import current_app
        app = current_app._get_current_object()
        t = threading.Thread(
            target=_send_reset_email,
            args=(app, user.email, user.name or user.email, reset_url, Config.PASSWORD_RESET_EXPIRY_MINUTES),
            daemon=True,
        )
        t.start()

    return jsonify({'message': 'If an account with that email exists, reset instructions have been sent.'}), 200


def _send_reset_email(app, to_email: str, name: str, reset_url: str, expiry_minutes: int) -> None:
    import logging
    import os
    import resend
    logger = logging.getLogger(__name__)
    try:
        resend.api_key = os.getenv('RESEND_API_KEY', '')
        if not resend.api_key:
            logger.warning('RESEND_API_KEY not set — skipping password reset email')
            return
        resend.Emails.send({
            'from': os.getenv('MAIL_DEFAULT_SENDER', 'VehicleChain <noreply@vehiclechain.my>'),
            'to': [to_email],
            'subject': 'Reset your VehicleChain password',
            'text': (
                f"Hi {name},\n\n"
                f"We received a request to reset your VehicleChain password.\n\n"
                f"Click the link below to set a new password (valid for {expiry_minutes} minutes):\n\n"
                f"{reset_url}\n\n"
                f"If you didn't request this, you can safely ignore this email.\n\n"
                f"— The VehicleChain Team"
            ),
            'html': (
                f"<p>Hi {name},</p>"
                f"<p>We received a request to reset your <strong>VehicleChain</strong> password.</p>"
                f"<p><a href='{reset_url}' style='background:#1A73E8;color:#fff;padding:10px 20px;"
                f"border-radius:6px;text-decoration:none;display:inline-block;'>Reset Password</a></p>"
                f"<p style='color:#666;font-size:13px;'>This link is valid for {expiry_minutes} minutes.</p>"
                f"<p style='color:#666;font-size:13px;'>If you didn't request this, you can safely ignore this email.</p>"
            ),
        })
        logger.info('Password reset email sent to %s via Resend', to_email)
    except Exception:
        logger.exception('Failed to send password reset email to %s', to_email)


@auth_bp.route('/reset-password', methods=['POST'])
@limiter.limit('10 per minute')
def reset_password():
    from api.utils import sanitize
    from db.models import db, PasswordResetToken
    import hashlib
    data = request.get_json() or {}
    raw_token = (data.get('token') or '').strip()
    new_pw = data.get('new_password', '')
    if not raw_token:
        return jsonify({'error': 'Token is required'}), 400
    if not new_pw:
        return jsonify({'error': 'new_password is required'}), 400
    try:
        auth_service.validate_password(new_pw)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    reset_token = PasswordResetToken.query.filter_by(token_hash=token_hash).first()
    if not reset_token or not reset_token.is_valid():
        return jsonify({'error': 'Invalid or expired reset link. Please request a new one.'}), 400

    user = reset_token.user
    user.set_password(new_pw)
    reset_token.used = True
    db.session.commit()
    user_repo.revoke_all_refresh_tokens(user.id)
    log_event('password_reset', user_id=user.id)
    return jsonify({'message': 'Password reset successfully. Please log in with your new password.'}), 200


@auth_bp.route('/account', methods=['DELETE'])
@limiter.limit('5 per minute')
@token_required
def delete_account():
    """PDPA right to erasure — permanently delete the caller's account and personal data."""
    data = request.get_json() or {}
    password = data.get('password', '')
    if not password:
        return jsonify({'error': 'Password is required to confirm account deletion'}), 400

    from db.models import db, AuditLog, DisputeMessage, VehicleVINMapping

    user = auth_service.get_user_by_id(request.user['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if not user.check_password(password):
        log_event('account_deletion_failed', user_id=user.id, detail={'reason': 'wrong_password'})
        return jsonify({'error': 'Incorrect password'}), 401

    # Record deletion before wiping the row
    log_event('account_deleted', user_id=user.id, detail={'email': user.email, 'role': user.role})

    # Erase personal data from audit logs (ip_address, detail) before user row is gone
    AuditLog.query.filter_by(user_id=user.id).delete(synchronize_session=False)

    # Erase dispute messages authored by this user
    DisputeMessage.query.filter_by(sender_id=user.id).delete(synchronize_session=False)

    # Clear intended_owner_email on any pending vehicle pre-registrations for this email
    VehicleVINMapping.query.filter_by(
        intended_owner_email=user.email
    ).update({'intended_owner_email': None}, synchronize_session=False)

    # Delete the user — RefreshToken, DeviceToken, PasswordResetToken all CASCADE
    db.session.delete(user)
    db.session.commit()

    return jsonify({'message': 'Account and personal data deleted successfully.'}), 200


@auth_bp.route('/data-export', methods=['GET'])
@limiter.limit('10 per minute')
@token_required
def data_export():
    """PDPA right of access — return all personal data held about the caller."""
    from db.models import AuditLog, DisputeMessage, VehicleVINMapping, ServiceMetadata, WarrantyClaimMetadata

    user = auth_service.get_user_by_id(request.user['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    addr = user.blockchain_address.lower() if user.blockchain_address else ''

    export = {
        'exported_at': datetime.utcnow().isoformat() + 'Z',
        'profile': user.to_dict(),
        'audit_logs': [
            a.to_dict() for a in
            AuditLog.query.filter_by(user_id=user.id).order_by(AuditLog.created_at.desc()).all()
        ],
        'dispute_messages_sent': [
            m.to_dict() for m in
            DisputeMessage.query.filter_by(sender_id=user.id).order_by(DisputeMessage.created_at.desc()).all()
        ],
    }

    if user.role == 'OWNER':
        mappings = VehicleVINMapping.query.filter(
            VehicleVINMapping.owner_address.ilike(addr)
        ).all()
        vins = [m.vin for m in mappings]
        claims = []
        if vins:
            claims = WarrantyClaimMetadata.query.filter(
                WarrantyClaimMetadata.vin.in_(vins)
            ).order_by(WarrantyClaimMetadata.created_at.desc()).all()
        export['vehicles'] = [m.to_dict() for m in mappings]
        export['warranty_claims'] = [c.to_dict() for c in claims]

    elif user.role == 'SERVICE_CENTER':
        records = ServiceMetadata.query.filter(
            ServiceMetadata.service_center_address.ilike(addr)
        ).order_by(ServiceMetadata.created_at.desc()).all()
        export['service_records_submitted'] = [r.to_dict() for r in records]

    log_event('data_export', user_id=user.id)
    return jsonify(export), 200


@auth_bp.route('/privacy-policy', methods=['GET'])
def get_privacy_policy():
    """Returns the Privacy Policy text for display in client apps."""
    return jsonify(PRIVACY_POLICY), 200


@auth_bp.route('/terms', methods=['GET'])
def get_terms():
    """Returns the Terms of Service text for display in client apps."""
    return jsonify(TERMS_OF_SERVICE), 200


PRIVACY_POLICY = {
    'version': '1.1',
    'effective_date': '2025-06-01',
    'title': 'Privacy Policy',
    'sections': [
        {
            'heading': 'Data Controller',
            'body': (
                'VehicleChain ("we", "us", or "our") is the data controller responsible for '
                'personal data collected through this platform. We are committed to protecting '
                'your personal data in compliance with the Personal Data Protection Act 2010 '
                '(PDPA) of Malaysia.'
            ),
        },
        {
            'heading': 'Personal Data We Collect',
            'body': (
                'We collect and process the following personal data:\n'
                '• Identity data: full name, email address, phone number\n'
                '• Account data: password hash (never stored in plain text)\n'
                '• Vehicle data: VIN numbers, ownership records, service history\n'
                '• Technical data: blockchain wallet address, device tokens for push notifications\n'
                '• Usage data: login timestamps, IP addresses (audit logs, retained for 365 days)\n'
                '• Consent records: date and time you agreed to this policy\n'
                '• Media: photos and images you upload with warranty claims or service records. '
                'These may incidentally contain identifiable information (e.g. licence plates). '
                'Upload only images directly relevant to your vehicle service or warranty claim.'
            ),
        },
        {
            'heading': 'Purpose of Processing',
            'body': (
                'We process your personal data for the following purposes:\n'
                '• To provide and manage your vehicle service management account\n'
                '• To record and verify vehicle service history on the blockchain\n'
                '• To process warranty claims and dispute resolutions\n'
                '• To send important notifications about your vehicles and warranties\n'
                '• To comply with legal obligations\n'
                '• To detect and prevent fraud or security incidents'
            ),
        },
        {
            'heading': 'Legal Basis for Processing',
            'body': (
                'Under the PDPA 2010, we process your personal data based on:\n'
                '• Your explicit consent given at registration (vehicle owners)\n'
                '• Performance of the contract between you and VehicleChain (all roles)\n'
                '• Our legitimate interests in operating a secure platform\n'
                '• Compliance with legal obligations'
            ),
        },
        {
            'heading': 'Blockchain and Data Immutability',
            'body': (
                'Please note that vehicle service records submitted to the blockchain are '
                'stored permanently and cannot be deleted. These records contain your vehicle '
                'VIN hash and service metadata hash only — no directly identifying personal '
                'information is stored on-chain. Your personal details (name, email) are '
                'stored only in our secure off-chain database.'
            ),
        },
        {
            'heading': 'Data Sharing and Disclosure',
            'body': (
                'We may share your personal data with:\n'
                '• Service centres you authorise to submit service records for your vehicle\n'
                '• Manufacturers who registered your vehicle\n'
                '• The following third-party infrastructure providers who process data on our behalf:\n'
                '  – Railway (cloud hosting, United States) — hosts the application server and database\n'
                '  – Resend (email delivery, United States) — used to send password reset emails\n'
                '  – Google Firebase / FCM (push notifications, United States) — used to deliver '
                'in-app push notifications to mobile devices\n\n'
                'These providers are bound by their respective data processing agreements and '
                'privacy policies. By using VehicleChain you consent to the transfer of your '
                'personal data to these providers, including transfer outside of Malaysia as '
                'permitted under PDPA 2010 s.129.\n\n'
                'We do not sell your personal data to third parties.'
            ),
        },
        {
            'heading': 'Data Retention',
            'body': (
                'We retain your personal data for as long as your account is active:\n'
                '• Account profile and vehicle records: retained until account deletion\n'
                '• Security audit logs (IP addresses, login events): automatically deleted after 365 days\n'
                '• Password reset tokens: expire after use or within 60 minutes, then purged automatically\n\n'
                'If you delete your account via the app, your personal data is erased immediately '
                'from our database. Blockchain records (VIN hashes, service hashes) cannot be '
                'deleted due to their immutable nature, but contain no directly identifying information.'
            ),
        },
        {
            'heading': 'Your Rights Under PDPA',
            'body': (
                'You have the right to:\n'
                '• Access the personal data we hold about you — use the "Export My Data" feature in the app, '
                'or call GET /api/auth/data-export\n'
                '• Correct inaccurate or incomplete personal data — use the Profile screen in the app\n'
                '• Withdraw consent and delete your account — use the "Delete Account" option in the app '
                '(DELETE /api/auth/account). Deletion is immediate and irreversible.\n'
                '• Lodge a complaint with the Personal Data Protection Commissioner of Malaysia '
                '(www.pdp.gov.my)\n\n'
                'To exercise your rights or for any privacy-related queries:\n'
                'Email: privacy@vehiclechain.up.railway.app\n'
                'Platform: https://vehiclechain.up.railway.app'
            ),
        },
        {
            'heading': 'Security',
            'body': (
                'We implement appropriate technical and organisational measures to protect your '
                'personal data, including encryption at rest, TLS in transit, password hashing '
                'using bcrypt, rate limiting, account lockout after failed attempts, and '
                'blockchain immutability for service record audit trails.'
            ),
        },
        {
            'heading': 'Contact Us',
            'body': (
                'For any privacy-related queries or to exercise your rights under PDPA:\n'
                'Email: privacy@vehiclechain.up.railway.app\n'
                'Platform: https://vehiclechain.up.railway.app'
            ),
        },
    ],
}

TERMS_OF_SERVICE = {
    'version': '1.0',
    'effective_date': '2024-01-01',
    'title': 'Terms of Service',
    'sections': [
        {
            'heading': 'Acceptance of Terms',
            'body': (
                'By creating an account, you agree to these Terms of Service and our '
                'Privacy Policy. If you do not agree, you must not use this platform.'
            ),
        },
        {
            'heading': 'Use of the Service',
            'body': (
                'VehicleChain is a vehicle service management platform that uses blockchain '
                'technology to create tamper-proof service records. You agree to:\n'
                '• Provide accurate and complete registration information\n'
                '• Maintain the security of your account credentials\n'
                '• Use the platform only for lawful purposes\n'
                '• Not attempt to manipulate, falsify, or tamper with service records'
            ),
        },
        {
            'heading': 'Blockchain Records',
            'body': (
                'Service records submitted to the blockchain are permanent and immutable. '
                'Once a record is verified or disputed on-chain, it cannot be erased. '
                'You are responsible for ensuring the accuracy of information before submitting '
                'or approving any service record.'
            ),
        },
        {
            'heading': 'Limitation of Liability',
            'body': (
                'VehicleChain is provided "as is". We are not liable for any loss or damage '
                'arising from your use of the platform, including but not limited to errors '
                'in blockchain transactions, network outages, or unauthorised access resulting '
                'from your failure to protect your credentials.'
            ),
        },
        {
            'heading': 'Governing Law',
            'body': (
                'These Terms are governed by the laws of Malaysia. Any disputes shall be '
                'subject to the exclusive jurisdiction of the courts of Malaysia.'
            ),
        },
    ],
}


@auth_bp.route('/device-token', methods=['POST'])
@token_required
def register_device_token():
    data = request.get_json() or {}
    token    = data.get('token', '').strip()
    platform = data.get('platform', '').strip().lower()
    if not token:
        return jsonify({'error': 'token required'}), 400
    if platform not in ('ios', 'android'):
        return jsonify({'error': "platform must be 'ios' or 'android'"}), 400
    user_repo.upsert_device_token(request.user['user_id'], token, platform)
    return jsonify({'message': 'Device token registered'}), 200
