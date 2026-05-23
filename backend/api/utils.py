"""Shared helpers for API request validation and sanitization."""
import re
import bleach

_VIN_RE = re.compile(r'^[A-HJ-NPR-Z0-9]{17}$', re.IGNORECASE)


def sanitize(value, max_len: int = 500) -> str:
    """Strip HTML/JS, trim whitespace, enforce max length."""
    if not isinstance(value, str):
        return ''
    return bleach.clean(value, tags=[], strip=True).strip()[:max_len]


def validate_vin(vin: str) -> str:
    """Return cleaned VIN or raise ValueError."""
    vin = sanitize(vin, 17).upper()
    if not _VIN_RE.match(vin):
        raise ValueError('VIN must be exactly 17 alphanumeric characters (I, O, Q not allowed)')
    return vin


def validate_mileage(value) -> int:
    try:
        m = int(value)
    except (TypeError, ValueError):
        raise ValueError('Mileage must be a positive integer')
    if m < 0 or m > 9_999_999:
        raise ValueError('Mileage out of range (0 – 9,999,999)')
    return m


def paginate(query_list: list, request_args) -> dict:
    """Slice a list with ?page=1&limit=20 query params."""
    try:
        page  = max(1, int(request_args.get('page', 1)))
        limit = min(100, max(1, int(request_args.get('limit', 20))))
    except (TypeError, ValueError):
        page, limit = 1, 20
    total  = len(query_list)
    start  = (page - 1) * limit
    items  = query_list[start:start + limit]
    return {
        'items': items,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'pages': max(1, -(-total // limit)),  # ceiling division
        }
    }
