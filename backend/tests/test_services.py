"""Tests for /api/service endpoints."""
import time
import pytest
from conftest import register_and_login, auth, STRONG_PASSWORD


VIN = '1HGCM82633A004352'
SERVICE_DATE = time.strftime('%Y-%m-%dT%H:%M:%S')
FAKE_HASH = '0x' + 'ab' * 32  # 66-char hex placeholder used where real hash is not needed


def _register_vehicle(client, mfr_token, owner_email, make='Honda'):
    client.post('/api/vehicle/register', headers=auth(mfr_token), json={
        'vin': VIN, 'owner_email': owner_email,
        'warranty_years': 3, 'make': make, 'model': 'Civic', 'year': 2024,
    })


def _activate_sc_fresh_token(client, mfr_token, sc_user):
    """Activate SC and return a fresh access token with active status."""
    client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(mfr_token))
    fresh = client.post('/api/auth/login',
                        json={'email': sc_user['email'], 'password': STRONG_PASSWORD})
    return fresh.get_json()['access_token']


class TestSubmitService:
    def test_service_center_can_submit(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        _, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER', brand='Honda')
        _register_vehicle(client, mfr_token, owner['email'], make='Honda')
        sc_token = _activate_sc_fresh_token(client, mfr_token, sc_user)

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
        honda_mfr, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        toyota_mfr, _ = register_and_login(client, 'MANUFACTURER', brand='Toyota')
        _, owner = register_and_login(client, 'OWNER')
        _, toyota_sc = register_and_login(client, 'SERVICE_CENTER', brand='Toyota')
        _register_vehicle(client, honda_mfr, owner['email'], make='Honda')
        toyota_sc_token = _activate_sc_fresh_token(client, toyota_mfr, toyota_sc)

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
        _, sc_user = register_and_login(client, 'SERVICE_CENTER', brand='honda')
        _register_vehicle(client, mfr_token, owner['email'], make='Honda')
        sc_token = _activate_sc_fresh_token(client, mfr_token, sc_user)

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
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        sc_token = _activate_sc_fresh_token(client, mfr_token, sc_user)
        r = client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN,  # missing service_type, service_date, mileage
        })
        assert r.status_code == 400

    def test_submit_service_with_photos(self, client):
        """Multipart/form-data submission including attached photo files."""
        import io
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        _, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER', brand='Honda')
        _register_vehicle(client, mfr_token, owner['email'], make='Honda')
        sc_token = _activate_sc_fresh_token(client, mfr_token, sc_user)

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
        _, sc_user = register_and_login(client, 'SERVICE_CENTER', brand='Honda')
        _register_vehicle(client, mfr_token, owner['email'])
        sc_token = _activate_sc_fresh_token(client, mfr_token, sc_user)

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
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        sc_token = _activate_sc_fresh_token(client, mfr_token, sc_user)
        r = client.post('/api/service/dispute-response', headers=auth(sc_token), json={
            'vin': VIN,
        })
        assert r.status_code == 400

    def test_rebuttal_record_not_found(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        sc_token = _activate_sc_fresh_token(client, mfr_token, sc_user)
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
        _, sc_user = register_and_login(client, 'SERVICE_CENTER', brand='Honda')
        _register_vehicle(client, mfr_token, owner['email'])
        sc_token = _activate_sc_fresh_token(client, mfr_token, sc_user)

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
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
            'owner_email': owner['email'],
        })
        r = client.get(f'/api/service/pending/{VIN}', headers=auth(owner_token))
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
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner['email'])
        r = client.post('/api/service/verify', headers=auth(owner_token), json={
            'vin': VIN, 'metadata_hash': FAKE_HASH,
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
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner['email'])
        r = client.post('/api/service/dispute', headers=auth(owner_token), json={
            'vin': VIN, 'metadata_hash': FAKE_HASH, 'reason': 'Wrong parts used',
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
            'vin': VIN, 'metadata_hash': FAKE_HASH, 'decision': 1, 'resolution_notes': 'Verified correct',
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data['decision'] == 'approved'

    def test_manufacturer_can_resolve_reject(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/service/resolve-dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'metadata_hash': FAKE_HASH, 'decision': 2, 'resolution_notes': 'Parts wrong',
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
            'vin': VIN, 'metadata_hash': FAKE_HASH, 'decision': 3, 'resolution_notes': 'Please resubmit with correct parts',
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
            'vin': VIN, 'metadata_hash': FAKE_HASH, 'decision': 1, 'resolution_notes': 'Not mine',
        })
        assert r.status_code == 403

    def test_registering_manufacturer_can_resolve_dispute(self, client):
        """The manufacturer who registered the vehicle can resolve disputes."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner['email'], make='Honda')

        r = client.post('/api/service/resolve-dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'metadata_hash': FAKE_HASH, 'decision': 1, 'resolution_notes': 'Verified',
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
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner['email'])
        r = client.post('/api/service/owner/verify', headers=auth(owner_token), json={
            'vin': VIN, 'metadata_hash': FAKE_HASH,
        })
        assert r.status_code == 200

    def test_owner_dispute(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner['email'])
        r = client.post('/api/service/owner/dispute', headers=auth(owner_token), json={
            'vin': VIN, 'metadata_hash': FAKE_HASH, 'reason': 'Unauthorized service',
        })
        assert r.status_code == 200

    def test_non_owner_cannot_access_owner_endpoints(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.get('/api/service/owner/pending', headers=auth(sc_token))
        assert r.status_code == 403


class TestLegacyVerifyDisputeRoleEnforcement:
    """The legacy /verify and /dispute endpoints are now owner-only."""

    def test_sc_cannot_use_legacy_verify(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.post('/api/service/verify', headers=auth(sc_token), json={
            'vin': VIN, 'record_index': 0,
        })
        assert r.status_code == 403

    def test_manufacturer_cannot_use_legacy_verify(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/service/verify', headers=auth(mfr_token), json={
            'vin': VIN, 'record_index': 0,
        })
        assert r.status_code == 403

    def test_sc_cannot_use_legacy_dispute(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.post('/api/service/dispute', headers=auth(sc_token), json={
            'vin': VIN, 'record_index': 0, 'reason': 'test',
        })
        assert r.status_code == 403

    def test_manufacturer_cannot_use_legacy_dispute(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/service/dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'record_index': 0, 'reason': 'test',
        })
        assert r.status_code == 403

    def test_owner_can_use_legacy_verify(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner['email'])
        r = client.post('/api/service/verify', headers=auth(owner_token), json={
            'vin': VIN, 'metadata_hash': FAKE_HASH,
        })
        assert r.status_code == 200

    def test_owner_can_use_legacy_dispute(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner['email'])
        r = client.post('/api/service/dispute', headers=auth(owner_token), json={
            'vin': VIN, 'metadata_hash': FAKE_HASH, 'reason': 'Wrong parts used',
        })
        assert r.status_code == 200


class TestServiceOnPendingVehicle:
    """SC must not be able to submit a service record for an unclaimed vehicle."""

    def test_sc_cannot_submit_for_pending_vehicle(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER', brand='Honda')
        sc_token = _activate_sc_fresh_token(client, mfr_token, sc_user)

        # Pre-register with no owner (status=pending)
        client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })

        r = client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Oil Change',
            'service_date': SERVICE_DATE, 'mileage': 5000,
        })
        assert r.status_code == 400
        assert 'pending' in r.get_json()['error'].lower() or 'owner' in r.get_json()['error'].lower()

    def test_sc_can_submit_for_active_vehicle(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        _, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER', brand='Honda')
        _register_vehicle(client, mfr_token, owner['email'], make='Honda')
        sc_token = _activate_sc_fresh_token(client, mfr_token, sc_user)

        r = client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Oil Change',
            'service_date': SERVICE_DATE, 'mileage': 5000,
        })
        assert r.status_code == 200


class TestWarrantyClaimsAccess:
    """GET /api/warranty/claims/<vin> is now manufacturer-only with brand isolation."""

    def test_manufacturer_can_see_claims_for_own_vehicle(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        r = client.get(f'/api/warranty/claims/{VIN}', headers=auth(mfr_token))
        assert r.status_code == 200

    def test_sc_cannot_see_warranty_claims(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.get(f'/api/warranty/claims/{VIN}', headers=auth(sc_token))
        assert r.status_code == 403

    def test_owner_cannot_use_warranty_claims_endpoint(self, client):
        owner_token, _ = register_and_login(client, 'OWNER')
        r = client.get(f'/api/warranty/claims/{VIN}', headers=auth(owner_token))
        assert r.status_code == 403

    def test_different_brand_manufacturer_cannot_see_claims(self, client):
        honda_mfr, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        toyota_mfr, _ = register_and_login(client, 'MANUFACTURER', brand='Toyota')
        _, owner = register_and_login(client, 'OWNER')

        # Register a Honda VIN under Honda manufacturer
        client.post('/api/vehicle/register', headers=auth(honda_mfr), json={
            'vin': VIN, 'owner_email': owner['email'],
            'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })

        r = client.get(f'/api/warranty/claims/{VIN}', headers=auth(toyota_mfr))
        assert r.status_code == 403


# ===========================================================================
# Dispute messaging (from test_dispute_messages.py)
# ===========================================================================

def _setup_full_dispute(client):
    """Return (mfr_token, owner_token, sc_token, mfr_user, owner_user, sc_user)."""
    mfr_token,   mfr_user   = register_and_login(client, 'MANUFACTURER')
    owner_token, owner_user = register_and_login(client, 'OWNER')
    _,           sc_user    = register_and_login(client, 'SERVICE_CENTER')
    client.post('/api/vehicle/register', headers=auth(mfr_token), json={
        'vin': VIN, 'warranty_years': 3,
        'make': 'Honda', 'model': 'Civic', 'year': 2024,
        'owner_email': owner_user['email'],
    })
    client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(mfr_token))
    fresh = client.post('/api/auth/login',
                        json={'email': sc_user['email'], 'password': STRONG_PASSWORD})
    sc_token = fresh.get_json()['access_token']
    # Submit a service record so the SC has a row in ServiceMetadata for VIN
    client.post('/api/service/submit', headers=auth(sc_token), json={
        'vin': VIN, 'service_type': 'Oil Change',
        'service_date': SERVICE_DATE, 'mileage': 5000,
    })
    return mfr_token, owner_token, sc_token, mfr_user, owner_user, sc_user


# ---------------------------------------------------------------------------
# GET dispute-messages
# ---------------------------------------------------------------------------

class TestGetDisputeMessages:
    def test_owner_can_get_empty_thread(self, client):
        _, owner_token, _, _, _, _ = _setup_full_dispute(client)
        r = client.get(f'/api/service/dispute-messages/{VIN}/0',
                       headers=auth(owner_token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'messages' in data
        assert data['messages'] == []

    def test_manufacturer_can_get_thread(self, client):
        mfr_token, _, _, _, _, _ = _setup_full_dispute(client)
        r = client.get(f'/api/service/dispute-messages/{VIN}/0',
                       headers=auth(mfr_token))
        assert r.status_code == 200
        assert 'messages' in r.get_json()

    def test_sc_can_get_thread(self, client):
        _, _, sc_token, _, _, _ = _setup_full_dispute(client)
        r = client.get(f'/api/service/dispute-messages/{VIN}/0',
                       headers=auth(sc_token))
        assert r.status_code == 200

    def test_unauthenticated_returns_401(self, client):
        _setup_full_dispute(client)
        r = client.get(f'/api/service/dispute-messages/{VIN}/0')
        assert r.status_code == 401

    def test_unrelated_owner_cannot_access(self, client):
        _setup_full_dispute(client)
        other_token, _ = register_and_login(client, 'OWNER')
        r = client.get(f'/api/service/dispute-messages/{VIN}/0',
                       headers=auth(other_token))
        assert r.status_code == 403

    def test_invalid_vin_returns_400(self, client):
        _, owner_token, _, _, _, _ = _setup_full_dispute(client)
        r = client.get('/api/service/dispute-messages/BADVIN/0',
                       headers=auth(owner_token))
        assert r.status_code == 400

    def test_messages_ordered_by_created_at(self, client):
        _, owner_token, _, _, _, _ = _setup_full_dispute(client)
        for msg in ('First message', 'Second message', 'Third message'):
            client.post('/api/service/dispute-messages',
                        headers=auth(owner_token),
                        json={'vin': VIN, 'record_index': 0, 'message': msg})
        r = client.get(f'/api/service/dispute-messages/{VIN}/0',
                       headers=auth(owner_token))
        messages = r.get_json()['messages']
        assert len(messages) == 3
        assert messages[0]['message'] == 'First message'
        assert messages[2]['message'] == 'Third message'


# ---------------------------------------------------------------------------
# POST dispute-messages
# ---------------------------------------------------------------------------

class TestPostDisputeMessage:
    def test_owner_can_post_message(self, client):
        _, owner_token, _, _, _, _ = _setup_full_dispute(client)
        r = client.post('/api/service/dispute-messages',
                        headers=auth(owner_token),
                        json={'vin': VIN, 'record_index': 0, 'message': 'I dispute this.'})
        assert r.status_code == 201
        data = r.get_json()
        assert data['message'] == 'I dispute this.'
        assert data['sender_role'] == 'OWNER'

    def test_sc_can_post_message(self, client):
        _, _, sc_token, _, _, _ = _setup_full_dispute(client)
        r = client.post('/api/service/dispute-messages',
                        headers=auth(sc_token),
                        json={'vin': VIN, 'record_index': 0, 'message': 'Rebuttal from SC.'})
        assert r.status_code == 201
        assert r.get_json()['sender_role'] == 'SERVICE_CENTER'

    def test_manufacturer_can_post_message(self, client):
        mfr_token, _, _, _, _, _ = _setup_full_dispute(client)
        r = client.post('/api/service/dispute-messages',
                        headers=auth(mfr_token),
                        json={'vin': VIN, 'record_index': 0, 'message': 'Resolution: claim valid.'})
        assert r.status_code == 201
        assert r.get_json()['sender_role'] == 'MANUFACTURER'

    def test_unauthenticated_returns_401(self, client):
        _setup_full_dispute(client)
        r = client.post('/api/service/dispute-messages',
                        json={'vin': VIN, 'record_index': 0, 'message': 'No auth.'})
        assert r.status_code == 401

    def test_unrelated_owner_cannot_post(self, client):
        _setup_full_dispute(client)
        other_token, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/service/dispute-messages',
                        headers=auth(other_token),
                        json={'vin': VIN, 'record_index': 0, 'message': 'Intruder.'})
        assert r.status_code == 403

    def test_empty_message_returns_400(self, client):
        _, owner_token, _, _, _, _ = _setup_full_dispute(client)
        r = client.post('/api/service/dispute-messages',
                        headers=auth(owner_token),
                        json={'vin': VIN, 'record_index': 0, 'message': ''})
        assert r.status_code == 400

    def test_missing_message_returns_400(self, client):
        _, owner_token, _, _, _, _ = _setup_full_dispute(client)
        r = client.post('/api/service/dispute-messages',
                        headers=auth(owner_token),
                        json={'vin': VIN, 'record_index': 0})
        assert r.status_code == 400

    def test_missing_vin_returns_400(self, client):
        _, owner_token, _, _, _, _ = _setup_full_dispute(client)
        r = client.post('/api/service/dispute-messages',
                        headers=auth(owner_token),
                        json={'record_index': 0, 'message': 'No VIN.'})
        assert r.status_code == 400

    def test_invalid_vin_returns_400(self, client):
        _, owner_token, _, _, _, _ = _setup_full_dispute(client)
        r = client.post('/api/service/dispute-messages',
                        headers=auth(owner_token),
                        json={'vin': 'BAD', 'record_index': 0, 'message': 'Bad VIN.'})
        assert r.status_code == 400

    def test_negative_record_index_returns_400(self, client):
        _, owner_token, _, _, _, _ = _setup_full_dispute(client)
        r = client.post('/api/service/dispute-messages',
                        headers=auth(owner_token),
                        json={'vin': VIN, 'record_index': -1, 'message': 'Neg index.'})
        assert r.status_code == 400

    def test_posted_message_appears_in_get(self, client):
        _, owner_token, _, _, _, _ = _setup_full_dispute(client)
        client.post('/api/service/dispute-messages',
                    headers=auth(owner_token),
                    json={'vin': VIN, 'record_index': 0, 'message': 'Hello thread!'})
        r = client.get(f'/api/service/dispute-messages/{VIN}/0',
                       headers=auth(owner_token))
        messages = r.get_json()['messages']
        assert len(messages) == 1
        assert messages[0]['message'] == 'Hello thread!'

    def test_response_includes_all_expected_fields(self, client):
        _, owner_token, _, _, _, _ = _setup_full_dispute(client)
        r = client.post('/api/service/dispute-messages',
                        headers=auth(owner_token),
                        json={'vin': VIN, 'record_index': 0, 'message': 'Check fields.'})
        data = r.get_json()
        for field in ('id', 'vin', 'record_index', 'sender_id', 'sender_name',
                      'sender_role', 'message', 'created_at'):
            assert field in data, f'Missing field: {field}'

    def test_message_persisted_to_db(self, client, app):
        _, owner_token, _, _, _, _ = _setup_full_dispute(client)
        client.post('/api/service/dispute-messages',
                    headers=auth(owner_token),
                    json={'vin': VIN, 'record_index': 0, 'message': 'DB persist test.'})
        with app.app_context():
            from db.models import DisputeMessage
            msg = DisputeMessage.query.filter_by(vin=VIN, record_index=0).first()
            assert msg is not None
            assert msg.message == 'DB persist test.'
            assert msg.sender_role == 'OWNER'

    def test_multiple_messages_from_different_roles(self, client):
        mfr_token, owner_token, sc_token, _, _, _ = _setup_full_dispute(client)
        client.post('/api/service/dispute-messages', headers=auth(owner_token),
                    json={'vin': VIN, 'record_index': 0, 'message': 'Owner says X.'})
        client.post('/api/service/dispute-messages', headers=auth(sc_token),
                    json={'vin': VIN, 'record_index': 0, 'message': 'SC replies Y.'})
        client.post('/api/service/dispute-messages', headers=auth(mfr_token),
                    json={'vin': VIN, 'record_index': 0, 'message': 'MFR resolves Z.'})
        r = client.get(f'/api/service/dispute-messages/{VIN}/0',
                       headers=auth(owner_token))
        messages = r.get_json()['messages']
        assert len(messages) == 3
        roles = [m['sender_role'] for m in messages]
        assert 'OWNER' in roles
        assert 'SERVICE_CENTER' in roles
        assert 'MANUFACTURER' in roles


# ===========================================================================
# Service dispute resolution persistence (from test_new_features.py)
# ===========================================================================

def _activate_sc_services(client, mfr_token, sc_user):
    client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(mfr_token))
    fresh = client.post('/api/auth/login',
                        json={'email': sc_user['email'], 'password': STRONG_PASSWORD})
    return fresh.get_json()['access_token']


def _register_vehicle_services(client, mfr_token, owner_email=None, vin=VIN):
    payload = {'vin': vin, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024}
    if owner_email:
        payload['owner_email'] = owner_email
    return client.post('/api/vehicle/register', headers=auth(mfr_token), json=payload)


class TestServiceResolutionPersistence:
    def _setup_dispute(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle_services(client, mfr_token, owner_email=owner['email'])
        sc_token = _activate_sc_services(client, mfr_token, sc_user)

        client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Engine Service',
            'service_date': SERVICE_DATE, 'mileage': 30000,
        })

        with app.app_context():
            from db.models import ServiceMetadata
            record = ServiceMetadata.query.filter_by(vin=VIN).first()
            assert record is not None
            meta_hash = record.metadata_hash

        from blockchain.adapters.service_log import service_log as sl
        sl.get_pending_services.return_value = [{
            'metadata_hash': meta_hash,
            'verified': False,
            'disputed': True,
            'service_center': '0x' + '02' * 20,
        }]

        return mfr_token, meta_hash

    def test_resolve_dispute_persists_decision(self, client, app):
        mfr_token, meta_hash = self._setup_dispute(client, app)

        client.post('/api/service/resolve-dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'metadata_hash': meta_hash, 'decision': 1,
            'resolution_notes': 'Claim verified and approved',
        })

        with app.app_context():
            from db.models import ServiceMetadata
            record = ServiceMetadata.query.filter_by(vin=VIN).first()
            assert record.resolution_decision == 'approved'

    def test_resolve_dispute_persists_notes(self, client, app):
        mfr_token, meta_hash = self._setup_dispute(client, app)

        client.post('/api/service/resolve-dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'metadata_hash': meta_hash, 'decision': 2,
            'resolution_notes': 'No evidence of defect found',
        })

        with app.app_context():
            from db.models import ServiceMetadata
            record = ServiceMetadata.query.filter_by(vin=VIN).first()
            assert record.resolution_notes == 'No evidence of defect found'

    def test_resolve_dispute_sets_resolved_at(self, client, app):
        mfr_token, meta_hash = self._setup_dispute(client, app)

        client.post('/api/service/resolve-dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'metadata_hash': meta_hash, 'decision': 1,
            'resolution_notes': 'Resolved',
        })

        with app.app_context():
            from db.models import ServiceMetadata
            record = ServiceMetadata.query.filter_by(vin=VIN).first()
            assert record.resolved_at is not None

    def test_service_metadata_resolution_fields_in_to_dict(self, client, app):
        """ServiceMetadata.to_dict() must include resolution fields."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle_services(client, mfr_token, owner_email=owner['email'])
        sc_token = _activate_sc_services(client, mfr_token, sc_user)
        client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Tyre Rotation',
            'service_date': SERVICE_DATE, 'mileage': 8000,
        })

        with app.app_context():
            from db.models import ServiceMetadata
            record = ServiceMetadata.query.filter_by(vin=VIN).first()
            d = record.to_dict()
            assert 'resolution_decision' in d
            assert 'resolution_notes' in d
            assert 'resolved_at' in d

    def teardown_method(self, method):
        from blockchain.adapters.service_log import service_log as sl
        sl.get_pending_services.return_value = []


class TestManufacturerDisputedAggregate:
    """The manufacturer previously had no way to discover a dispute without already
    knowing its VIN, and the VIN-search path returned the on-chain VIN hash instead of
    the plain VIN in `record['vin']` — breaking thread/resolve calls downstream. This
    covers the new aggregate endpoint that fixes both."""

    def _setup_dispute(self, client, app, mfr_token, owner_email, vin=VIN, escalated=False, timestamp=1_700_000_000):
        _register_vehicle_services(client, mfr_token, owner_email=owner_email, vin=vin)
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        sc_token = _activate_sc_services(client, mfr_token, sc_user)
        client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': vin, 'service_type': 'Engine Service',
            'service_date': SERVICE_DATE, 'mileage': 30000,
        })
        with app.app_context():
            from db.models import ServiceMetadata
            record = ServiceMetadata.query.filter_by(vin=vin).first()
            meta_hash = record.metadata_hash
            if escalated:
                record.escalated = True
                from db.models import db as _db
                _db.session.commit()

        from blockchain.adapters.service_log import service_log as sl
        sl.get_pending_services.return_value = [{
            'metadata_hash': meta_hash,
            'verified': False,
            'disputed': True,
            'service_center': '0x' + '02' * 20,
            'timestamp': timestamp,
        }]
        return meta_hash

    def teardown_method(self, method):
        from blockchain.adapters.service_log import service_log as sl
        sl.get_pending_services.return_value = []

    def test_manufacturer_sees_disputed_record_with_plain_vin(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        self._setup_dispute(client, app, mfr_token, owner['email'])

        r = client.get('/api/service/manufacturer/disputed', headers=auth(mfr_token))
        assert r.status_code == 200
        records = r.get_json()['disputed_services']
        assert len(records) == 1
        # Must be the plain 17-char VIN, not the on-chain keccak256 hash —
        # that hash previously broke every thread/resolve call for this record.
        assert records[0]['vin'] == VIN
        assert records[0]['record_index'] == 0
        assert records[0]['disputed'] is True

    def test_non_manufacturer_cannot_access(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.get('/api/service/manufacturer/disputed', headers=auth(sc_token))
        assert r.status_code == 403

    def test_other_manufacturer_does_not_see_unrelated_brand_dispute(self, client, app):
        mfr_a, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        mfr_b, _ = register_and_login(client, 'MANUFACTURER', brand='Toyota')
        _, owner = register_and_login(client, 'OWNER')
        self._setup_dispute(client, app, mfr_a, owner['email'])

        r = client.get('/api/service/manufacturer/disputed', headers=auth(mfr_b))
        assert r.status_code == 200
        assert r.get_json()['disputed_services'] == []

    def test_escalated_disputes_sorted_first(self, client, app):
        """A newer, non-escalated dispute and an older, escalated one on a different
        VIN — the escalated one must surface first regardless of recency."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        vin2 = '2HGCM82633A004352'

        _register_vehicle_services(client, mfr_token, owner_email=owner['email'], vin=VIN)
        _register_vehicle_services(client, mfr_token, owner_email=owner['email'], vin=vin2)
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        sc_token = _activate_sc_services(client, mfr_token, sc_user)
        client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Engine Service', 'service_date': SERVICE_DATE, 'mileage': 30000,
        })
        client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': vin2, 'service_type': 'Brake Service', 'service_date': SERVICE_DATE, 'mileage': 12000,
        })

        with app.app_context():
            from db.models import ServiceMetadata, db as _db
            rec1 = ServiceMetadata.query.filter_by(vin=VIN).first()
            rec2 = ServiceMetadata.query.filter_by(vin=vin2).first()
            hash1, hash2 = rec1.metadata_hash, rec2.metadata_hash
            rec2.escalated = True
            _db.session.commit()

        from blockchain.adapters.service_log import service_log as sl
        sc_addr = '0x' + '02' * 20
        def fake_pending(vin):
            if vin == VIN:
                return [{'metadata_hash': hash1, 'verified': False, 'disputed': True,
                          'service_center': sc_addr, 'timestamp': 1_700_000_500}]
            if vin == vin2:
                return [{'metadata_hash': hash2, 'verified': False, 'disputed': True,
                          'service_center': sc_addr, 'timestamp': 1_600_000_000}]
            return []
        sl.get_pending_services.side_effect = fake_pending

        try:
            r = client.get('/api/service/manufacturer/disputed', headers=auth(mfr_token))
            assert r.status_code == 200
            records = r.get_json()['disputed_services']
            assert len(records) == 2
            assert records[0]['vin'] == vin2
            assert records[0]['escalated'] is True
        finally:
            sl.get_pending_services.side_effect = None
