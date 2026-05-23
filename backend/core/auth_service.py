import jwt
from datetime import datetime, timedelta
from web3 import Web3
from config import Config
from blockchain.keystore import keystore
from blockchain.client import web3_client
from db.repositories import users as user_repo

_MANUFACTURER_ROLE = Web3.keccak(text="MANUFACTURER_ROLE")
_SERVICE_CENTER_ROLE = Web3.keccak(text="SERVICE_CENTER_ROLE")


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

    deployer = Config.DEPLOYER_ADDRESS
    if deployer and keystore.has_key(deployer):
        # Fund the new account so it can pay gas
        web3_client.transfer_eth(deployer, account['address'], Web3.to_wei(0.1, 'ether'))

        # Grant on-chain roles so the account can call role-protected contract functions
        if role == 'MANUFACTURER':
            from blockchain.adapters.vehicle_registry import vehicle_registry
            from blockchain.adapters.service_log import service_log
            from blockchain.adapters.warranty_tracker import warranty_tracker
            _DEFAULT_ADMIN_ROLE = b'\x00' * 32  # OpenZeppelin DEFAULT_ADMIN_ROLE = bytes32(0)
            web3_client.grant_role(vehicle_registry.contract, _MANUFACTURER_ROLE, account['address'], deployer)
            # resolveDispute requires DEFAULT_ADMIN_ROLE on ServiceLog
            web3_client.grant_role(service_log.contract, _DEFAULT_ADMIN_ROLE, account['address'], deployer)
            # approveClaim / denyClaim require DEFAULT_ADMIN_ROLE on WarrantyTracker
            web3_client.grant_role(warranty_tracker.contract, _DEFAULT_ADMIN_ROLE, account['address'], deployer)
        elif role == 'SERVICE_CENTER':
            from blockchain.adapters.service_log import service_log
            web3_client.grant_role(service_log.contract, _SERVICE_CENTER_ROLE, account['address'], deployer)

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
