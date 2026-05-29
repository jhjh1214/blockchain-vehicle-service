import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_INSECURE_DEFAULTS = {
    'JWT_SECRET_KEY': 'jwt-secret-change-in-production',
    'SECRET_KEY': 'your-secret-key-change-in-production',
    'KEYSTORE_PASSWORD': 'change-me-in-production',
}


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
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

    # Comma-separated list of allowed CORS origins; defaults to localhost dev origins
    CORS_ORIGINS = os.getenv(
        'CORS_ORIGINS',
        'http://localhost:4200,http://localhost:3000'
    )

    # Flask-Mail (SMTP) configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', MAIL_USERNAME)
    MAIL_SUPPRESS_SEND = os.getenv('MAIL_SUPPRESS_SEND', 'false').lower() == 'true'

    # Frontend base URL used in email links
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:4200')

    # Set USE_HTTPS=true in production to enable HSTS header
    USE_HTTPS = os.getenv('USE_HTTPS', 'false').lower() == 'true'

    # How long (minutes) a password-reset token stays valid
    PASSWORD_RESET_EXPIRY_MINUTES = int(os.getenv('PASSWORD_RESET_EXPIRY_MINUTES', '60'))

    @classmethod
    def validate(cls):
        """Check for insecure defaults.

        In production (FLASK_ENV=production) insecure defaults are fatal.
        In development they emit warnings so devs are reminded to configure properly.
        """
        is_prod = os.getenv('FLASK_ENV', 'development') == 'production'
        problems = [
            attr
            for attr, bad in _INSECURE_DEFAULTS.items()
            if getattr(cls, attr) == bad
        ]
        if not problems:
            return
        msg = (
            'Insecure default values detected for: '
            + ', '.join(problems)
            + '. Set these via environment variables before deploying to production.'
        )
        if is_prod:
            raise RuntimeError(msg)
        logger.warning(msg)
