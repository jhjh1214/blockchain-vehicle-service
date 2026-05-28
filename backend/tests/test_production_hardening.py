"""Tests for production hardening fixes.

Covers: X-Request-ID propagation, health check DB field, security headers,
Config.validate() logic, and blockchain-first ordering in service/warranty submission.
"""
import time
import pytest
from unittest.mock import MagicMock
from conftest import register_and_login, auth, STRONG_PASSWORD

VIN   = '1HGCM82633A004352'
TODAY = time.strftime('%Y-%m-%dT%H:%M:%S')


def _register_vehicle(client, mfr_token, owner_email=None, vin=VIN):
    payload = {'vin': vin, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024}
    if owner_email:
        payload['owner_email'] = owner_email
    return client.post('/api/vehicle/register', headers=auth(mfr_token), json=payload)


def _activate_sc(client, mfr_token, sc_user):
    client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(mfr_token))
    fresh = client.post('/api/auth/login',
                        json={'email': sc_user['email'], 'password': STRONG_PASSWORD})
    return fresh.get_json()['access_token']


# ---------------------------------------------------------------------------
# X-Request-ID propagation
# ---------------------------------------------------------------------------

class TestRequestIDPropagation:
    def test_custom_request_id_echoed_in_response(self, client):
        custom_id = 'test-trace-id-12345'
        r = client.get('/api/health', headers={'X-Request-ID': custom_id})
        assert r.headers.get('X-Request-ID') == custom_id

    def test_generated_request_id_present_when_header_absent(self, client):
        r = client.get('/api/health')
        request_id = r.headers.get('X-Request-ID')
        assert request_id and len(request_id) > 0

    def test_request_id_propagated_on_error_responses(self, client):
        custom_id = 'error-trace-xyz'
        r = client.post('/api/auth/login',
                        json={'email': 'nobody@test.com', 'password': 'bad'},
                        headers={'X-Request-ID': custom_id})
        assert r.headers.get('X-Request-ID') == custom_id


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    def test_health_includes_db_status(self, client):
        r = client.get('/api/health')
        data = r.get_json()
        assert 'db' in data
        assert 'ok' in data['db']
        assert isinstance(data['db']['ok'], bool)

    def test_health_includes_blockchain_status(self, client):
        r = client.get('/api/health')
        data = r.get_json()
        assert 'blockchain' in data
        assert 'connected' in data['blockchain']

    def test_health_includes_overall_status_field(self, client):
        r = client.get('/api/health')
        data = r.get_json()
        assert data.get('status') in ('healthy', 'degraded')

    def test_health_returns_200_when_db_is_up(self, client):
        r = client.get('/api/health')
        # DB is in-memory SQLite — must be up
        assert r.status_code == 200
        assert r.get_json()['db']['ok'] is True


# ---------------------------------------------------------------------------
# Security response headers
# ---------------------------------------------------------------------------

class TestSecurityHeaders:
    def test_x_content_type_options_nosniff(self, client):
        r = client.get('/api/health')
        assert r.headers.get('X-Content-Type-Options') == 'nosniff'

    def test_x_frame_options_deny(self, client):
        r = client.get('/api/health')
        assert r.headers.get('X-Frame-Options') == 'DENY'

    def test_referrer_policy_set(self, client):
        r = client.get('/api/health')
        assert 'Referrer-Policy' in r.headers

    def test_permissions_policy_set(self, client):
        r = client.get('/api/health')
        assert 'Permissions-Policy' in r.headers

    def test_security_headers_on_api_error_responses(self, client):
        r = client.get('/api/vehicle/INVALIDVIN', headers={'Authorization': 'Bearer invalid'})
        assert r.headers.get('X-Content-Type-Options') == 'nosniff'


# ---------------------------------------------------------------------------
# Config.validate()
# ---------------------------------------------------------------------------

class TestConfigValidation:
    def test_validate_does_not_raise_in_development_mode(self):
        """In dev mode, insecure defaults produce a warning, not an exception."""
        import os
        orig = os.environ.get('FLASK_ENV', 'development')
        try:
            os.environ['FLASK_ENV'] = 'development'
            from config import Config
            Config.validate()  # must not raise
        finally:
            os.environ['FLASK_ENV'] = orig

    def test_validate_raises_in_production_with_insecure_defaults(self):
        """In production mode, keeping any insecure default must raise RuntimeError."""
        import os
        from config import Config
        orig_env = os.environ.get('FLASK_ENV', 'development')
        orig_key = Config.JWT_SECRET_KEY
        try:
            os.environ['FLASK_ENV'] = 'production'
            Config.JWT_SECRET_KEY = 'jwt-secret-change-in-production'
            with pytest.raises(RuntimeError, match='Insecure default'):
                Config.validate()
        finally:
            os.environ['FLASK_ENV'] = orig_env
            Config.JWT_SECRET_KEY = orig_key

    def test_validate_passes_with_custom_secrets(self):
        """validate() must not raise when custom values are in use."""
        import os
        from config import Config
        orig_env = os.environ.get('FLASK_ENV', 'development')
        orig_jwt = Config.JWT_SECRET_KEY
        orig_sk  = Config.SECRET_KEY
        orig_kp  = Config.KEYSTORE_PASSWORD
        try:
            os.environ['FLASK_ENV'] = 'production'
            Config.JWT_SECRET_KEY    = 'very-secret-prod-jwt-key-32chars!!'
            Config.SECRET_KEY        = 'very-secret-flask-key-32chars!!!'
            Config.KEYSTORE_PASSWORD = 'super-secret-keystore-password!!'
            Config.validate()  # must not raise
        finally:
            os.environ['FLASK_ENV'] = orig_env
            Config.JWT_SECRET_KEY    = orig_jwt
            Config.SECRET_KEY        = orig_sk
            Config.KEYSTORE_PASSWORD = orig_kp


# ---------------------------------------------------------------------------
# Blockchain-first ordering: service submission
# ---------------------------------------------------------------------------

class TestServiceSubmitBlockchainFirstOrdering:
    """Verify that a blockchain failure leaves no orphaned DB record."""

    def _setup(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        sc_token = _activate_sc(client, mfr_token, sc_user)
        return sc_token

    def test_blockchain_failure_leaves_no_db_record(self, client, app):
        sc_token = self._setup(client)

        from blockchain.adapters.service_log import service_log as sl
        original = sl.submit_service
        sl.submit_service = MagicMock(side_effect=RuntimeError('node unreachable'))
        try:
            r = client.post('/api/service/submit', headers=auth(sc_token), json={
                'vin': VIN, 'service_type': 'Oil Change',
                'service_date': TODAY, 'mileage': 5000,
            })
            assert r.status_code == 500
        finally:
            sl.submit_service = original

        with app.app_context():
            from db.models import ServiceMetadata
            assert ServiceMetadata.query.filter_by(vin=VIN).count() == 0

    def test_blockchain_success_persists_db_record(self, client, app):
        sc_token = self._setup(client)

        r = client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Oil Change',
            'service_date': TODAY, 'mileage': 5000,
        })
        assert r.status_code == 200

        with app.app_context():
            from db.models import ServiceMetadata
            assert ServiceMetadata.query.filter_by(vin=VIN).count() == 1

    def test_blockchain_success_record_has_correct_vin_and_type(self, client, app):
        sc_token = self._setup(client)

        client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Brake Service',
            'service_date': TODAY, 'mileage': 5000,
        })

        with app.app_context():
            from db.models import ServiceMetadata
            record = ServiceMetadata.query.filter_by(vin=VIN).first()
            assert record is not None
            assert record.service_type == 'Brake Service'


# ---------------------------------------------------------------------------
# Blockchain-first ordering: warranty claim submission
# ---------------------------------------------------------------------------

class TestWarrantyClaimBlockchainFirstOrdering:
    """Verify that a blockchain failure leaves no orphaned warranty DB record."""

    def _setup(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        return owner_token

    def test_blockchain_failure_leaves_no_db_record(self, client, app):
        owner_token = self._setup(client)

        from blockchain.adapters.warranty_tracker import warranty_tracker as wt
        original = wt.submit_claim
        wt.submit_claim = MagicMock(side_effect=RuntimeError('node unreachable'))
        try:
            r = client.post('/api/warranty/submit-claim', headers=auth(owner_token), json={
                'vin': VIN, 'issue_description': 'Engine knocking noise',
            })
            assert r.status_code == 500
        finally:
            wt.submit_claim = original

        with app.app_context():
            from db.models import WarrantyClaimMetadata
            assert WarrantyClaimMetadata.query.filter_by(vin=VIN).count() == 0

    def test_blockchain_success_persists_db_record(self, client, app):
        owner_token = self._setup(client)

        r = client.post('/api/warranty/submit-claim', headers=auth(owner_token), json={
            'vin': VIN, 'issue_description': 'Engine knocking noise',
        })
        assert r.status_code == 200

        with app.app_context():
            from db.models import WarrantyClaimMetadata
            assert WarrantyClaimMetadata.query.filter_by(vin=VIN).count() == 1

    def test_blockchain_success_record_has_correct_description(self, client, app):
        owner_token = self._setup(client)

        client.post('/api/warranty/submit-claim', headers=auth(owner_token), json={
            'vin': VIN, 'issue_description': 'Airbag light on dashboard',
        })

        with app.app_context():
            from db.models import WarrantyClaimMetadata
            record = WarrantyClaimMetadata.query.filter_by(vin=VIN).first()
            assert record is not None
            assert record.issue_description == 'Airbag light on dashboard'


# ---------------------------------------------------------------------------
# Vehicle registration: DB rollback on DB failure
# ---------------------------------------------------------------------------

class TestVehicleRegistrationDbRollback:
    def test_db_failure_after_blockchain_returns_descriptive_500(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')

        from db.repositories import vehicles as vehicle_repo
        original = vehicle_repo.create
        vehicle_repo.create = MagicMock(side_effect=Exception('DB write failed'))
        try:
            r = client.post('/api/vehicle/register', headers=auth(mfr_token), json={
                'vin': VIN, 'warranty_years': 3, 'make': 'Honda',
                'model': 'Civic', 'year': 2024,
            })
            assert r.status_code == 500
            body = r.get_json()
            # Error message must contain VIN so support can identify the record
            assert VIN in body['error']
        finally:
            vehicle_repo.create = original

    def test_successful_registration_creates_db_record(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'Honda',
            'model': 'Civic', 'year': 2024,
        })
        assert r.status_code == 200

        with app.app_context():
            from db.models import VehicleVINMapping
            assert VehicleVINMapping.query.filter_by(vin=VIN).count() == 1
