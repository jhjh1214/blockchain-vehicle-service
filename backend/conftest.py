"""
Root conftest.py — lives in backend/ so pytest finds it when run from backend/.

Mocks all blockchain I/O so tests run with no Ganache node.
Session-scoped: adapters are patched once; DB is recreated per test via clean_db fixture.
"""
import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'  # must be set before config is imported

import itertools
import time
import pytest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Shared mock values
# ---------------------------------------------------------------------------
MOCK_TX = {
    'tx_hash': '0x' + 'aa' * 32,
    'block_number': 1,
    'gas_used': 21000,
    'status': 1,
}

_addr_counter = itertools.count(1)


def _next_addr():
    n = next(_addr_counter)
    return f'0x{n:040x}'


# ---------------------------------------------------------------------------
# Session-scoped Flask app (created once, adapters mocked at method level)
# ---------------------------------------------------------------------------
@pytest.fixture(scope='session')
def app():
    # Prevent the event monitor daemon thread from attempting Ganache connections
    with patch('blockchain.event_monitor.init_event_monitor'):
        from app import create_app
        flask_app = create_app()

    flask_app.config['TESTING'] = True
    flask_app.config['RATELIMIT_ENABLED'] = False

    from extensions import limiter
    limiter.enabled = False  # Flask-Limiter 4.x reads self.enabled at request time

    # ------------------------------------------------------------------
    # Mock adapter singleton methods directly on the live objects.
    # These objects were created when the modules were first imported
    # (inside create_app).  Replacing their methods here affects every
    # consumer because they all share the same singleton reference.
    # ------------------------------------------------------------------
    from blockchain.adapters.vehicle_registry import vehicle_registry as vr
    from blockchain.adapters.service_log import service_log as sl
    from blockchain.adapters.warranty_tracker import warranty_tracker as wt
    from blockchain.keystore import keystore as ks
    from blockchain.client import web3_client as wc

    # Keystore — each create_account call returns a unique address
    ks.create_account = MagicMock(side_effect=lambda: {'address': _next_addr(), 'private_key': 'mock_private_key'})
    ks.store_key = MagicMock()
    ks.get_key = MagicMock(return_value='mock_private_key')
    ks.has_key = MagicMock(return_value=False)  # skip blockchain setup in register_user

    # Web3 client — mock transfer and role-grant so register_user needs no Ganache
    wc.transfer_eth = MagicMock()
    wc.grant_role = MagicMock()

    # VehicleRegistry adapter
    vr.register_vehicle = MagicMock(return_value=MOCK_TX)
    vr.transfer_ownership = MagicMock(return_value=MOCK_TX)
    vr.admin_transfer_ownership = MagicMock(return_value=MOCK_TX)
    vr.get_owned_vehicles = MagicMock(return_value=[])
    vr.get_vehicle = MagicMock(return_value={
        'owner': _next_addr(),
        'warranty_start': int(time.time()),
        'warranty_expiry': int(time.time()) + 3 * 365 * 24 * 3600,
        'service_hashes': [],
        'exists': True,
    })

    # ServiceLog adapter
    sl.submit_service = MagicMock(return_value=MOCK_TX)
    sl.verify_service = MagicMock(return_value=MOCK_TX)
    sl.dispute_service = MagicMock(return_value=MOCK_TX)
    sl.resolve_dispute = MagicMock(return_value=MOCK_TX)
    sl.get_pending_services = MagicMock(return_value=[])
    sl.get_finalized_services = MagicMock(return_value=[])

    # WarrantyTracker adapter
    wt.is_warranty_valid = MagicMock(return_value={'valid': True, 'reason': 'Warranty is valid'})
    wt.submit_claim = MagicMock(return_value=MOCK_TX)
    wt.approve_claim = MagicMock(return_value=MOCK_TX)
    wt.deny_claim = MagicMock(return_value=MOCK_TX)
    wt.get_claims = MagicMock(return_value=[])

    with flask_app.app_context():
        from db.models import db
        db.create_all()
        yield flask_app
        db.drop_all()


# ---------------------------------------------------------------------------
# Per-test client
# ---------------------------------------------------------------------------
@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Per-test DB cleanup — wipe all rows before AND after each test
# ---------------------------------------------------------------------------
def _wipe_db(app):
    with app.app_context():
        from db.models import db, User, ServiceMetadata, WarrantyClaimMetadata, VehicleVINMapping, RefreshToken, DeviceToken
        db.session.query(ServiceMetadata).delete()
        db.session.query(WarrantyClaimMetadata).delete()
        db.session.query(VehicleVINMapping).delete()
        db.session.query(RefreshToken).delete()
        db.session.query(DeviceToken).delete()
        db.session.query(User).delete()
        db.session.commit()


@pytest.fixture(autouse=True)
def clean_db(app):
    _wipe_db(app)   # ensure clean state before test
    yield
    _wipe_db(app)   # clean up after test


# ---------------------------------------------------------------------------
# Helpers used across multiple test modules
# ---------------------------------------------------------------------------
STRONG_PASSWORD = 'TestPass1!'


def register_and_login(client, role, email=None, password=STRONG_PASSWORD, name='Test User'):
    """Register a user and return (access_token, user_dict)."""
    email = email or f'{role.lower()}-{next(_addr_counter)}@test.com'
    r = client.post('/api/auth/register', json={
        'email': email,
        'password': password,
        'role': role,
        'name': name,
    })
    assert r.status_code == 200, f'Register failed: {r.get_json()}'
    data = r.get_json()
    return data['access_token'], data['user']


def auth(token):
    """Return Authorization header dict."""
    return {'Authorization': f'Bearer {token}'}
