from flask import Blueprint, request, jsonify
from api.middleware import token_required
from core import auth_service
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
        return jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        }), 200
    except ValueError as e:
        msg = str(e)
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
    return jsonify({'message': 'Password changed. Please log in again.'}), 200


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
