"""Tests for /api/service endpoints."""
import time
import pytest
from conftest import register_and_login, auth

VIN = '1HGCM82633A004352'
SERVICE_DATE = time.strftime('%Y-%m-%dT%H:%M:%S')


def _register_vehicle(client, mfr_token, owner_email, make='Honda'):
    client.post('/api/vehicle/register', headers=auth(mfr_token), json={
        'vin': VIN, 'owner_email': owner_email,
        'warranty_years': 3, 'make': make, 'model': 'Civic', 'year': 2024,
    })


class TestSubmitService:
    def test_service_center_can_submit(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        _, owner = register_and_login(client, 'OWNER')
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER', brand='Honda')
        _register_vehicle(client, mfr_token, owner['email'], make='Honda')

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

    def test_sc_cannot_submit_for_wrong_brand(self, client):
        """Toyota SC cannot submit service for a Honda vehicle."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        _, owner = register_and_login(client, 'OWNER')
        toyota_sc_token, _ = register_and_login(client, 'SERVICE_CENTER', brand='Toyota')
        _register_vehicle(client, mfr_token, owner['email'], make='Honda')

        r = client.post('/api/service/submit', headers=auth(toyota_sc_token), json={
            'vin': VIN,
            'service_type': 'Oil Change',
            'service_date': SERVICE_DATE,
            'mileage': 15000,
        })
        assert r.status_code == 403
        assert 'brand' in r.get_json()['error'].lower()

    def test_sc_can_submit_case_insensitive_brand(self, client):
        """Brand check is case-insensitive (HONDA == honda)."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='HONDA')
        _, owner = register_and_login(client, 'OWNER')
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER', brand='honda')
        _register_vehicle(client, mfr_token, owner['email'], make='Honda')

        r = client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN,
            'service_type': 'Tyre Rotation',
            'service_date': SERVICE_DATE,
            'mileage': 20000,
        })
        assert r.status_code == 200

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

    def test_submit_service_with_photos(self, client):
        """Multipart/form-data submission including attached photo files."""
        import io
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        _, owner = register_and_login(client, 'OWNER')
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER', brand='Honda')
        _register_vehicle(client, mfr_token, owner['email'], make='Honda')

        photo = (io.BytesIO(b'\xff\xd8\xff\xe0' + b'\x00' * 16), 'engine.jpg')
        r = client.post('/api/service/submit',
            headers=auth(sc_token),
            data={
                'vin': VIN,
                'service_type': 'Oil Change',
                'service_date': SERVICE_DATE,
                'mileage': '15000',
                'technician_name': 'Bob',
                'photos': photo,
            },
            content_type='multipart/form-data',
        )
        assert r.status_code == 200
        data = r.get_json()
        assert 'metadata_hash' in data
        assert data['metadata_hash'].startswith('0x')


class TestDisputeResponse:
    """POST /api/service/dispute-response — SC rebuttal submission."""

    def _setup_disputed_record(self, client):
        """Register vehicle, submit service, mark disputed in DB."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        _, owner = register_and_login(client, 'OWNER')
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER', brand='Honda')
        _register_vehicle(client, mfr_token, owner['email'])

        # Submit service to create a ServiceMetadata row
        r = client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Oil Change',
            'service_date': SERVICE_DATE, 'mileage': 10000,
        })
        assert r.status_code == 200
        metadata_hash = r.get_json()['metadata_hash']

        # Mark it disputed directly in DB
        from db.models import db, ServiceMetadata
        with client.application.app_context():
            sm = ServiceMetadata.query.filter_by(metadata_hash=metadata_hash).first()
            sm.disputed = True
            db.session.commit()

        return sc_token, metadata_hash

    def test_sc_can_submit_rebuttal(self, client):
        sc_token, metadata_hash = self._setup_disputed_record(client)
        r = client.post('/api/service/dispute-response', headers=auth(sc_token), json={
            'vin': VIN,
            'metadata_hash': metadata_hash,
            'rebuttal_notes': 'The oil change was performed correctly per manufacturer spec.',
        })
        assert r.status_code == 200
        assert 'message' in r.get_json()

    def test_rebuttal_requires_auth(self, client):
        r = client.post('/api/service/dispute-response', json={
            'vin': VIN, 'metadata_hash': '0x' + 'aa' * 32, 'rebuttal_notes': 'test',
        })
        assert r.status_code == 401

    def test_non_sc_cannot_submit_rebuttal(self, client):
        owner_token, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/service/dispute-response', headers=auth(owner_token), json={
            'vin': VIN, 'metadata_hash': '0x' + 'aa' * 32, 'rebuttal_notes': 'test',
        })
        assert r.status_code == 403

    def test_rebuttal_missing_fields(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.post('/api/service/dispute-response', headers=auth(sc_token), json={
            'vin': VIN,
        })
        assert r.status_code == 400

    def test_rebuttal_record_not_found(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.post('/api/service/dispute-response', headers=auth(sc_token), json={
            'vin': VIN,
            'metadata_hash': '0x' + 'bb' * 32,
            'rebuttal_notes': 'This record does not exist.',
        })
        assert r.status_code == 404

    def test_rebuttal_not_disputed_record(self, client):
        """SC cannot submit rebuttal on a non-disputed record."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        _, owner = register_and_login(client, 'OWNER')
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER', brand='Honda')
        _register_vehicle(client, mfr_token, owner['email'])

        r = client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Tyre Rotation',
            'service_date': SERVICE_DATE, 'mileage': 5000,
        })
        assert r.status_code == 200
        metadata_hash = r.get_json()['metadata_hash']

        r = client.post('/api/service/dispute-response', headers=auth(sc_token), json={
            'vin': VIN,
            'metadata_hash': metadata_hash,
            'rebuttal_notes': 'No dispute exists for this record.',
        })
        assert r.status_code == 400
        assert 'not disputed' in r.get_json()['error'].lower()


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
            'vin': VIN, 'record_index': 0, 'decision': 4,
        })
        assert r.status_code == 400

    def test_decision_zero_rejected(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/service/resolve-dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'record_index': 0, 'decision': 0,
        })
        assert r.status_code == 400

    def test_manufacturer_can_resolve_modify(self, client):
        """Decision=3 (MODIFY) requests SC resubmission — record stays disputed."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/service/resolve-dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'record_index': 0, 'decision': 3, 'resolution_notes': 'Please resubmit with correct parts',
        })
        assert r.status_code == 200
        assert r.get_json()['decision'] == 'modify'

    def test_non_manufacturer_cannot_resolve(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.post('/api/service/resolve-dispute', headers=auth(sc_token), json={
            'vin': VIN, 'record_index': 0, 'decision': 1, 'resolution_notes': 'X',
        })
        assert r.status_code == 403

    def test_different_manufacturer_cannot_resolve_dispute(self, client):
        """Manufacturer B cannot resolve a dispute for a vehicle registered by manufacturer A."""
        mfr_a, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        mfr_b, _ = register_and_login(client, 'MANUFACTURER', brand='Toyota')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_a, owner['email'], make='Honda')

        r = client.post('/api/service/resolve-dispute', headers=auth(mfr_b), json={
            'vin': VIN, 'record_index': 0, 'decision': 1, 'resolution_notes': 'Not mine',
        })
        assert r.status_code == 403

    def test_registering_manufacturer_can_resolve_dispute(self, client):
        """The manufacturer who registered the vehicle can resolve disputes."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner['email'], make='Honda')

        r = client.post('/api/service/resolve-dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'record_index': 0, 'decision': 1, 'resolution_notes': 'Verified',
        })
        assert r.status_code == 200


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
