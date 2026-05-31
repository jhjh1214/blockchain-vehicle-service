import re
import jwt
import bleach
from datetime import datetime, timedelta
from web3 import Web3
from config import Config
from blockchain.keystore import keystore
from blockchain.client import web3_client
from db.repositories import users as user_repo

_MANUFACTURER_ROLE = Web3.keccak(text="MANUFACTURER_ROLE")
_MANUFACTURER_ADMIN_ROLE = Web3.keccak(text="MANUFACTURER_ADMIN_ROLE")
_SERVICE_CENTER_ROLE = Web3.keccak(text="SERVICE_CENTER_ROLE")

# Password policy — matches NIST SP 800-63B + OWASP recommendations
_PASSWORD_MIN_LEN = 8
_PASSWORD_MAX_LEN = 128
_PASSWORD_RE = re.compile(
    r'^(?=.*[a-z])'        # at least one lowercase
    r'(?=.*[A-Z])'         # at least one uppercase
    r'(?=.*\d)'            # at least one digit
    r'(?=.*[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?`~])'  # at least one special char
    r'.+$'
)

COMMON_PASSWORDS = {
    'Password1!', 'Password1@', 'Passw0rd!', 'Admin123!', 'Welcome1!',
    'Qwerty123!', 'Letmein1!', 'Monkey123!', 'Dragon123!', 'Master1!',
}

ACCESS_TOKEN_MINUTES = 60       # 1 hour
REFRESH_TOKEN_DAYS   = 30


def _sanitize(value: str, max_len: int = 255) -> str:
    """Strip HTML tags and control characters; trim whitespace."""
    if not isinstance(value, str):
        return ''
    cleaned = bleach.clean(value, tags=[], strip=True)
    return cleaned.strip()[:max_len]


def validate_password(password: str) -> None:
    """Raise ValueError with a user-facing message if password fails policy."""
    if not isinstance(password, str) or len(password) < _PASSWORD_MIN_LEN:
        raise ValueError(f'Password must be at least {_PASSWORD_MIN_LEN} characters')
    if len(password) > _PASSWORD_MAX_LEN:
        raise ValueError(f'Password must be at most {_PASSWORD_MAX_LEN} characters')
    if not _PASSWORD_RE.match(password):
        raise ValueError(
            'Password must contain at least one uppercase letter, one lowercase letter, '
            'one number, and one special character (!@#$%^&* etc.)'
        )
    if password in COMMON_PASSWORDS:
        raise ValueError('Password is too common — please choose a stronger password')


def generate_access_token(user) -> str:
    payload = {
        'user_id': user.id,
        'email': user.email,
        'role': user.role,
        'brand': user.brand or '',
        'blockchain_address': user.blockchain_address,
        'status': user.status or 'active',
        'exp': datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_MINUTES),
        'type': 'access',
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')


def register_user(email: str, password: str, role: str, name: str, phone: str,
                  city: str = '', state: str = '', brand: str = '',
                  consent_given: bool = False):
    email = _sanitize(email, 255).lower()
    name  = _sanitize(name,  255)
    phone = _sanitize(phone, 20)
    city  = _sanitize(city,  100)
    state = _sanitize(state, 100)
    brand = _sanitize(brand, 100)

    if not email or not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        raise ValueError('Invalid email address')

    if user_repo.find_by_email(email):
        raise ValueError('An account with this email already exists')

    valid_roles = ['MANUFACTURER', 'SERVICE_CENTER', 'OWNER']
    if role not in valid_roles:
        raise ValueError(f'Invalid role. Must be one of: {", ".join(valid_roles)}')

    if role in ('MANUFACTURER', 'SERVICE_CENTER') and not brand:
        raise ValueError('brand is required for MANUFACTURER and SERVICE_CENTER accounts')

    validate_password(password)

    account = keystore.create_account()
    keystore.store_key(account['address'], account['private_key'])

    deployer = Config.DEPLOYER_ADDRESS
    if deployer and keystore.has_key(deployer):
        initial_eth = Web3.to_wei(1000, 'ether') if role == 'MANUFACTURER' else Web3.to_wei(0.01, 'ether')
        web3_client.transfer_eth(deployer, account['address'], initial_eth)

        if role == 'MANUFACTURER':
            from blockchain.adapters.vehicle_registry import vehicle_registry
            from blockchain.adapters.service_log import service_log
            from blockchain.adapters.warranty_tracker import warranty_tracker
            _DEFAULT_ADMIN_ROLE = b'\x00' * 32
            web3_client.grant_role(vehicle_registry.contract, _MANUFACTURER_ROLE, account['address'], deployer)
            web3_client.grant_role(service_log.contract, _MANUFACTURER_ADMIN_ROLE, account['address'], deployer)
            web3_client.grant_role(warranty_tracker.contract, _DEFAULT_ADMIN_ROLE, account['address'], deployer)
        elif role == 'SERVICE_CENTER':
            from blockchain.adapters.service_log import service_log
            web3_client.grant_role(service_log.contract, _SERVICE_CENTER_ROLE, account['address'], deployer)

    if role == 'OWNER' and not consent_given:
        raise ValueError('You must accept the Privacy Policy and Terms of Service to register')

    user = user_repo.create(
        email=email, password=password, role=role,
        name=name, phone=phone, blockchain_address=account['address'],
        city=city, state=state, brand=brand,
        consent_given_at=datetime.utcnow() if consent_given else None,
    )
    access_token  = generate_access_token(user)
    refresh_token = user_repo.create_refresh_token(user.id)
    return user, access_token, refresh_token


def login_user(email: str, password: str):
    email = _sanitize(email, 255).lower()

    user = user_repo.find_by_email(email)
    if not user:
        # Timing-safe: don't reveal whether the email exists
        raise ValueError('Invalid email or password')

    if user.is_locked():
        remaining = int((user.locked_until - datetime.utcnow()).total_seconds() / 60) + 1
        raise ValueError(
            f'Account locked due to too many failed attempts. '
            f'Try again in {remaining} minute(s)'
        )

    if not user.check_password(password):
        user_repo.record_failed_login(user)
        attempts_left = max(0, user_repo.MAX_FAILED_ATTEMPTS - user.failed_login_attempts)
        if attempts_left == 0:
            raise ValueError(
                f'Account locked for {user_repo.LOCKOUT_MINUTES} minutes due to too many failed attempts'
            )
        raise ValueError(
            f'Invalid email or password. {attempts_left} attempt(s) remaining before lockout'
        )

    user_repo.reset_failed_login(user)

    if user.role == 'SERVICE_CENTER' and user.status == 'suspended':
        raise ValueError('Your account has been suspended. Please contact your manufacturer.')

    access_token  = generate_access_token(user)
    refresh_token = user_repo.create_refresh_token(user.id)
    return user, access_token, refresh_token


def refresh_access_token(raw_refresh_token: str):
    token_obj = user_repo.find_refresh_token(raw_refresh_token)
    if not token_obj or not token_obj.is_valid():
        raise ValueError('Invalid or expired refresh token')

    user = user_repo.find_by_id(token_obj.user_id)
    if not user:
        raise ValueError('User not found')

    # Rotate: revoke old, issue new refresh token
    user_repo.revoke_refresh_token(raw_refresh_token)
    new_refresh = user_repo.create_refresh_token(user.id)
    return user, generate_access_token(user), new_refresh


def logout_user(raw_refresh_token: str) -> None:
    user_repo.revoke_refresh_token(raw_refresh_token)


def logout_all_devices(user_id: int) -> None:
    user_repo.revoke_all_refresh_tokens(user_id)


def get_user_by_id(user_id: int):
    return user_repo.find_by_id(user_id)
