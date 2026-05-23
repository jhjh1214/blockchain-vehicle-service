from flask import Blueprint, request, jsonify
from api.middleware import token_required
from core import auth_service

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    for field in ('email', 'password', 'role'):
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    name = data.get('name') or data['email'].split('@')[0]
    try:
        user, token = auth_service.register_user(
            email=data['email'],
            password=data['password'],
            role=data['role'],
            name=name,
            phone=data.get('phone', '')
        )
        return jsonify({'message': 'User registered successfully', 'token': token, 'user': user.to_dict()}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    if 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Email and password required'}), 400
    try:
        user, token = auth_service.login_user(data['email'], data['password'])
        return jsonify({'message': 'Login successful', 'token': token, 'user': user.to_dict()}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 401


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    user = auth_service.get_user_by_id(request.user['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict()), 200
