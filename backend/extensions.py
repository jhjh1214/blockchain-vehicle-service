import os
from flask import request
from flask_limiter import Limiter

# Comma-separated list of trusted proxy CIDRs/IPs set via env var.
# On Railway the proxy terminates TLS — we only honour X-Forwarded-For when
# the immediate socket connection comes from a trusted proxy address.
# If TRUSTED_PROXY_IPS is not set we fall back to trusting XFF unconditionally
# (backwards-compatible for local dev), but a warning is logged on startup.
_TRUSTED_PROXIES = {
    ip.strip() for ip in os.getenv('TRUSTED_PROXY_IPS', '').split(',') if ip.strip()
}


def _get_real_ip() -> str:
    """
    Return the originating client IP, guarded against X-Forwarded-For spoofing.
    XFF is only trusted when the direct socket peer is a known proxy IP.
    Falls back to socket IP for local dev or when TRUSTED_PROXY_IPS is unset.
    """
    remote = request.remote_addr or '127.0.0.1'
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded and (_TRUSTED_PROXIES and remote in _TRUSTED_PROXIES):
        return forwarded.split(',')[0].strip()
    return remote


limiter = Limiter(
    key_func=_get_real_ip,
    default_limits=['60 per minute'],
    storage_uri='memory://',
)
