import jwt
from functools import wraps
from flask import request, jsonify
from config import Config


def _extract_token() -> str | None:
    """Cookie first (web, HttpOnly), then Authorization header (Flutter/mobile)."""
    token = request.cookies.get('access_token')
    if not token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
    return token or None


def token_required(f):
    """Validates JWT and populates request.user. Use alone when no role check is needed."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        try:
            request.user = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid'}), 401
        if request.user.get('type') != 'access':
            return jsonify({'error': 'Token is invalid'}), 401
        return f(*args, **kwargs)
    return decorated


def role_required(*allowed_roles):
    """Validates JWT and enforces role. Implies token_required — do not stack both."""
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(*args, **kwargs):
            if request.user['role'] not in allowed_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            if request.user['role'] == 'SERVICE_CENTER' and request.user.get('status', 'active') != 'active':
                return jsonify({'error': 'Your service center account is not active'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
