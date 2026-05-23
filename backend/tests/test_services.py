"""Tests for /api/service endpoints."""
import time
import pytest
from conftest import register_and_login, auth

VIN = '1HGCM82633A004352'
SERVICE_DATE = time.strftime('%Y-%m-%dT%H:%M:%S')


def _register_vehicle(client, mfr_token, owner_email):
    client.post('/api/vehicle/register', headers=auth(mfr_token), json={
        'vin': VIN, 'owner_email': owner_email,
        'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
    })


class TestSubmitService:
    def test_service_center_can_submit(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle(client, mfr_token, owner['email'])

        r = client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN,
            'service_type': 'Oil Change',
            'service_date': SERVICE_DATE,
            'mileage': 15000,
            'technician_name': 'Bob',
        })
        assert r.status_code == 200
        data = r.get_json()
        assert 'metadata_hash' in data
        assert data['metadata_hash'].startswith('0x')
        assert 'transaction' in data

    def test_non_service_center_cannot_submit(self, client):
        owner_token, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/service/submit', headers=auth(owner_token), json={
            'vin': VIN, 'service_type': 'Oil Change',
            'service_date': SERVICE_DATE, 'mileage': 1000,
        })
        assert r.status_code == 403

    def test_submit_requires_auth(self, client):
        r = client.post('/api/service/submit', json={
            'vin': VIN, 'service_type': 'Oil Change',
            'service_date': SERVICE_DATE, 'mileage': 1000,
        })
        assert r.status_code == 401

    def test_submit_missing_required_fields(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN,  # missing service_type, service_date, mileage
        })
        assert r.status_code == 400


class TestGetPendingServices:
    def test_get_pending_authenticated(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.get(f'/api/service/pending/{VIN}', headers=auth(token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'pending_services' in data
        assert 'pagination' in data

    def test_get_pending_unauthenticated(self, client):
        r = client.get(f'/api/service/pending/{VIN}')
        assert r.status_code == 401


class TestGetServiceHistory:
    def test_get_history_authenticated(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.get(f'/api/service/history/{VIN}', headers=auth(token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'service_history' in data

    def test_get_history_unauthenticated(self, client):
        r = client.get(f'/api/service/history/{VIN}')
        assert r.status_code == 401


class TestVerifyService:
    def test_verify_service(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/service/verify', headers=auth(token), json={
            'vin': VIN, 'record_index': 0,
        })
        assert r.status_code == 200
        data = r.get_json()
        assert 'transaction' in data

    def test_verify_missing_params(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/service/verify', headers=auth(token), json={'vin': VIN})
        assert r.status_code == 400


class TestDisputeService:
    def test_dispute_service(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/service/dispute', headers=auth(token), json={
            'vin': VIN, 'record_index': 0, 'reason': 'Wrong parts used',
        })
        assert r.status_code == 200
        data = r.get_json()
        assert 'transaction' in data

    def test_dispute_missing_reason(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/service/dispute', headers=auth(token), json={
            'vin': VIN, 'record_index': 0,
        })
        assert r.status_code == 400


class TestResolveDispute:
    def test_manufacturer_can_resolve_approve(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/service/resolve-dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'record_index': 0, 'decision': 1, 'resolution_notes': 'Verified correct',
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data['decision'] == 'approved'

    def test_manufacturer_can_resolve_reject(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/service/resolve-dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'record_index': 0, 'decision': 2, 'resolution_notes': 'Parts wrong',
        })
        assert r.status_code == 200
        assert r.get_json()['decision'] == 'rejected'

    def test_invalid_decision_value(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/service/resolve-dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'record_index': 0, 'decision': 3,
        })
        assert r.status_code == 400

    def test_decision_zero_rejected(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/service/resolve-dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'record_index': 0, 'decision': 0,
        })
        assert r.status_code == 400

    def test_non_manufacturer_cannot_resolve(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.post('/api/service/resolve-dispute', headers=auth(sc_token), json={
            'vin': VIN, 'record_index': 0, 'decision': 1, 'resolution_notes': 'X',
        })
        assert r.status_code == 403


class TestOwnerServiceEndpoints:
    def test_owner_pending(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.get('/api/service/owner/pending', headers=auth(token))
        assert r.status_code == 200
        assert 'pending_services' in r.get_json()

    def test_owner_history(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.get('/api/service/owner/history', headers=auth(token))
        assert r.status_code == 200
        assert 'service_history' in r.get_json()

    def test_owner_verify(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/service/owner/verify', headers=auth(token), json={
            'vin': VIN, 'record_index': 0,
        })
        assert r.status_code == 200

    def test_owner_dispute(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/service/owner/dispute', headers=auth(token), json={
            'vin': VIN, 'record_index': 0, 'reason': 'Unauthorized service',
        })
        assert r.status_code == 200

    def test_non_owner_cannot_access_owner_endpoints(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.get('/api/service/owner/pending', headers=auth(sc_token))
        assert r.status_code == 403
