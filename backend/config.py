import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///vehicle_service.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    GANACHE_URL = os.getenv('GANACHE_URL', 'http://127.0.0.1:8545')
    CHAIN_ID = int(os.getenv('CHAIN_ID', '1337'))
    
    VEHICLE_REGISTRY_ADDRESS = os.getenv('VEHICLE_REGISTRY_ADDRESS', '')
    SERVICE_LOG_ADDRESS = os.getenv('SERVICE_LOG_ADDRESS', '')
    WARRANTY_TRACKER_ADDRESS = os.getenv('WARRANTY_TRACKER_ADDRESS', '')

    DEPLOYER_ADDRESS = os.getenv('DEPLOYER_ADDRESS', '')
    DEPLOYER_PRIVATE_KEY = os.getenv('DEPLOYER_PRIVATE_KEY', '')

    ABI_DIR = os.path.join(os.path.dirname(__file__), 'abis')
    KEYSTORE_DIR = os.path.join(os.path.dirname(__file__), 'keystore')
    KEYSTORE_PASSWORD = os.getenv('KEYSTORE_PASSWORD', 'change-me-in-production')
    
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-change-in-production')
    JWT_EXPIRATION_HOURS = 24
    ADMIN_SECRET = os.getenv('ADMIN_SECRET', '')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB max request body