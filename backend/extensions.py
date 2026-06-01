from flask import request
from flask_limiter import Limiter


def _get_real_ip() -> str:
    """
    Return the originating client IP.
    Railway (and most PaaS) terminate TLS at a proxy and forward the real IP
    in X-Forwarded-For. We take the leftmost value (the original client), not
    the rightmost (the last trusted proxy), to avoid all users sharing one IP.
    Falls back to request.remote_addr for local dev without a proxy.
    """
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'


limiter = Limiter(
    key_func=_get_real_ip,
    default_limits=['60 per minute'],
    storage_uri='memory://',
)
