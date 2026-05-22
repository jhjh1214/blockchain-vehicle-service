import jwt
from datetime import datetime, timedelta
from config import Config
from blockchain.keystore import keystore
from db.repositories import users as user_repo


def generate_token(user) -> str:
    payload = {
        'user_id': user.id,
        'email': user.email,
        'role': user.role,
        'blockchain_address': user.blockchain_address,
        'exp': datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')


def register_user(email: str, password: str, role: str, name: str, phone: str):
    if user_repo.find_by_email(email):
        raise ValueError('User already exists')

    valid_roles = ['MANUFACTURER', 'SERVICE_CENTER', 'OWNER']
    if role not in valid_roles:
        raise ValueError(f"Invalid role. Must be one of: {', '.join(valid_roles)}")

    account = keystore.create_account()
    keystore.store_key(account['address'], account['private_key'])

    user = user_repo.create(
        email=email, password=password, role=role,
        name=name, phone=phone, blockchain_address=account['address']
    )
    return user, generate_token(user)


def login_user(email: str, password: str):
    user = user_repo.find_by_email(email)
    if not user or not user.check_password(password):
        raise ValueError('Invalid credentials')
    return user, generate_token(user)


def get_user_by_id(user_id: int):
    return user_repo.find_by_id(user_id)
