"""Tests for /api/warranty endpoints."""
import time
import pytest
from conftest import register_and_login, auth, STRONG_PASSWORD

VIN = '1HGCM82633A004352'


def _register_vehicle(client, mfr_token, make='Honda'):
    """Pre-register a vehicle (no owner) under the given manufacturer."""
    client.post('/api/vehicle/register', headers=auth(mfr_token), json={
        'vin': VIN, 'warranty_years': 3, 'make': make, 'model': 'Civic', 'year': 2024,
    })


def _register_vehicle_to_owner(client, owner_email, make='Honda'):
    """Register a vehicle directly to the given owner."""
    mfr_token, _ = register_and_login(client, 'MANUFACTURER')
    client.post('/api/vehicle/register', headers=auth(mfr_token), json={
        'vin': VIN, 'owner_email': owner_email,
        'warranty_years': 3, 'make': make, 'model': 'Civic', 'year': 2024,
    })


class TestCheckWarranty:
    def test_check_warranty_authenticated(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.get(f'/api/warranty/check/{VIN}', headers=auth(token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'valid' in data
        assert 'warranty_expiry' in data
        assert 'days_remaining' in data

    def test_check_warranty_unauthenticated(self, client):
        r = client.get(f'/api/warranty/check/{VIN}')
        assert r.status_code == 401


class TestSubmitClaim:
    def test_owner_can_submit_claim(self, client):
        token, owner = register_and_login(client, 'OWNER')
        _register_vehicle_to_owner(client, owner['email'])
        r = client.post('/api/warranty/submit-claim', headers=auth(token), json={
            'vin': VIN,
            'issue_description': 'Engine knocking noise at startup',
            'photos': [],
        })
        assert r.status_code == 200
        data = r.get_json()
        assert 'claim_hash' in data
        assert data['claim_hash'].startswith('0x')
        assert 'transaction' in data

    def test_non_owner_cannot_submit_claim(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.post('/api/warranty/submit-claim', headers=auth(sc_token), json={
            'vin': VIN,
            'issue_description': 'Unauthorized claim attempt',
        })
        assert r.status_code == 403

    def test_manufacturer_cannot_submit_claim(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/warranty/submit-claim', headers=auth(mfr_token), json={
            'vin': VIN,
            'issue_description': 'Manufacturer should not claim',
        })
        assert r.status_code == 403

    def test_submit_claim_requires_auth(self, client):
        r = client.post('/api/warranty/submit-claim', json={
            'vin': VIN, 'issue_description': 'Test',
        })
        assert r.status_code == 401

    def test_submit_claim_missing_issue(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/warranty/submit-claim', headers=auth(token), json={
            'vin': VIN,
        })
        assert r.status_code == 400

    def test_claim_hash_is_deterministic_for_same_input(self, client):
        """Two separate claims with same description produce different hashes (timestamp differs)."""
        token, owner = register_and_login(client, 'OWNER')
        _register_vehicle_to_owner(client, owner['email'])
        payload = {'vin': VIN, 'issue_description': 'Squeaky brakes', 'photos': []}
        r1 = client.post('/api/warranty/submit-claim', headers=auth(token), json=payload)
        r2 = client.post('/api/warranty/submit-claim', headers=auth(token), json=payload)
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Each claim includes a timestamp so hashes differ
        assert r1.get_json()['claim_hash'] != r2.get_json()['claim_hash']

    def test_submit_claim_with_photo(self, client):
        """Multipart/form-data submission with an attached photo file."""
        import io
        token, owner = register_and_login(client, 'OWNER')
        _register_vehicle_to_owner(client, owner['email'])
        photo = (io.BytesIO(b'\xff\xd8\xff\xe0' + b'\x00' * 16), 'damage.jpg')
        r = client.post('/api/warranty/submit-claim',
            headers=auth(token),
            data={
                'vin': VIN,
                'issue_description': 'Visible crack on windshield near the frame',
                'photos': photo,
            },
            content_type='multipart/form-data',
        )
        assert r.status_code == 200
        data = r.get_json()
        assert 'claim_hash' in data
        assert data['claim_hash'].startswith('0x')


class TestCheckEligibility:
    def test_authenticated_user_can_check_eligibility(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.get(f'/api/warranty/check-eligibility/{VIN}', headers=auth(token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'valid' in data
        assert 'eligible_to_claim' in data
        assert 'service_record_count' in data
        assert 'service_history_maintained' in data

    def test_eligibility_unauthenticated(self, client):
        r = client.get(f'/api/warranty/check-eligibility/{VIN}')
        assert r.status_code == 401

    def test_eligibility_invalid_vin(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.get('/api/warranty/check-eligibility/BADVIN', headers=auth(token))
        assert r.status_code == 400

    def test_eligibility_includes_service_count(self, client):
        """service_record_count reflects finalized services from the blockchain mock."""
        token, _ = register_and_login(client, 'OWNER')
        r = client.get(f'/api/warranty/check-eligibility/{VIN}', headers=auth(token))
        assert r.status_code == 200
        assert isinstance(r.get_json()['service_record_count'], int)


class TestGetClaims:
    def test_get_claims_authenticated(self, client):
        token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.get(f'/api/warranty/claims/{VIN}', headers=auth(token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'claims' in data
        assert 'pagination' in data

    def test_get_claims_unauthenticated(self, client):
        r = client.get(f'/api/warranty/claims/{VIN}')
        assert r.status_code == 401


class TestMfrAggregateClaims:
    """A manufacturer previously had to already know a VIN before seeing any claim
    for it — there was no way to discover one without an external prompt (e.g. an
    email). This covers the aggregate endpoint that fixes that."""

    def test_manufacturer_can_get_aggregate_claims(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.get('/api/warranty/manufacturer/claims', headers=auth(mfr_token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'claims' in data
        assert 'pagination' in data

    def test_non_manufacturer_cannot_access(self, client):
        owner_token, _ = register_and_login(client, 'OWNER')
        r = client.get('/api/warranty/manufacturer/claims', headers=auth(owner_token))
        assert r.status_code == 403

    def test_requires_auth(self, client):
        r = client.get('/api/warranty/manufacturer/claims')
        assert r.status_code == 401

    def test_includes_claim_for_registered_vehicle_with_plain_vin(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        _register_vehicle(client, mfr_token, make='Honda')

        from blockchain.adapters.warranty_tracker import warranty_tracker as wt
        wt.get_claims.return_value = [{
            'claim_details_hash': '0x' + 'aa' * 32,
            'timestamp': 1_700_000_000,
            'claimant': '0x' + '03' * 20,
            'resolution_notes_hash': None,
        }]

        try:
            r = client.get('/api/warranty/manufacturer/claims', headers=auth(mfr_token))
            assert r.status_code == 200
            claims = r.get_json()['claims']
            assert len(claims) == 1
            assert claims[0]['vin'] == VIN
            assert claims[0]['claim_index'] == 0
            assert claims[0]['status'] == 'pending'
            assert claims[0]['make'] == 'Honda'
        finally:
            wt.get_claims.return_value = []

    def test_does_not_see_other_manufacturers_claims(self, client):
        """Manufacturer B's vehicles shouldn't appear in manufacturer A's aggregate view."""
        mfr_a, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        mfr_b, _ = register_and_login(client, 'MANUFACTURER', brand='Toyota')
        _register_vehicle(client, mfr_a, make='Honda')

        from blockchain.adapters.warranty_tracker import warranty_tracker as wt
        wt.get_claims.return_value = [{
            'claim_details_hash': '0x' + 'bb' * 32,
            'timestamp': 1_700_000_000,
            'claimant': '0x' + '04' * 20,
            'resolution_notes_hash': None,
        }]

        try:
            r = client.get('/api/warranty/manufacturer/claims', headers=auth(mfr_b))
            assert r.status_code == 200
            assert r.get_json()['claims'] == []
        finally:
            wt.get_claims.return_value = []


class TestApproveClaim:
    def test_registering_manufacturer_can_approve(self, client):
        """Manufacturer who registered the vehicle can approve its warranty claims."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        _register_vehicle(client, mfr_token, make='Honda')
        r = client.post('/api/warranty/approve-claim', headers=auth(mfr_token), json={
            'vin': VIN, 'claim_index': 0,
        })
        assert r.status_code == 200
        assert 'transaction' in r.get_json()

    def test_different_manufacturer_cannot_approve(self, client):
        """Manufacturer B cannot approve claims for a vehicle registered by manufacturer A."""
        mfr_a, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        mfr_b, _ = register_and_login(client, 'MANUFACTURER', brand='Toyota')
        _register_vehicle(client, mfr_a, make='Honda')

        r = client.post('/api/warranty/approve-claim', headers=auth(mfr_b), json={
            'vin': VIN, 'claim_index': 0,
        })
        assert r.status_code == 403

    def test_manufacturer_can_approve_unregistered_vehicle(self, client):
        """Vehicle with no DB record (no registered_by) — no cross-manufacturer check."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/warranty/approve-claim', headers=auth(mfr_token), json={
            'vin': VIN, 'claim_index': 0,
        })
        assert r.status_code == 200

    def test_non_manufacturer_cannot_approve(self, client):
        owner_token, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/warranty/approve-claim', headers=auth(owner_token), json={
            'vin': VIN, 'claim_index': 0,
        })
        assert r.status_code == 403

    def test_approve_missing_params(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/warranty/approve-claim', headers=auth(mfr_token), json={
            'vin': VIN,  # missing claim_index
        })
        assert r.status_code == 400


class TestDenyClaim:
    def test_registering_manufacturer_can_deny(self, client):
        """Manufacturer who registered the vehicle can deny its warranty claims."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        _register_vehicle(client, mfr_token, make='Honda')
        r = client.post('/api/warranty/deny-claim', headers=auth(mfr_token), json={
            'vin': VIN, 'claim_index': 0, 'reason': 'Outside warranty scope',
        })
        assert r.status_code == 200
        assert 'transaction' in r.get_json()

    def test_different_manufacturer_cannot_deny(self, client):
        """Manufacturer B cannot deny claims for a vehicle registered by manufacturer A."""
        mfr_a, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        mfr_b, _ = register_and_login(client, 'MANUFACTURER', brand='Toyota')
        _register_vehicle(client, mfr_a, make='Honda')

        r = client.post('/api/warranty/deny-claim', headers=auth(mfr_b), json={
            'vin': VIN, 'claim_index': 0, 'reason': 'Not my vehicle',
        })
        assert r.status_code == 403

    def test_non_manufacturer_cannot_deny(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.post('/api/warranty/deny-claim', headers=auth(sc_token), json={
            'vin': VIN, 'claim_index': 0, 'reason': 'X',
        })
        assert r.status_code == 403


class TestOwnerClaims:
    def test_owner_can_get_their_claims(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.get('/api/warranty/owner/claims', headers=auth(token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'claims' in data

    def test_non_owner_cannot_access_owner_claims(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.get('/api/warranty/owner/claims', headers=auth(sc_token))
        assert r.status_code == 403

    def test_owner_claims_requires_auth(self, client):
        r = client.get('/api/warranty/owner/claims')
        assert r.status_code == 401


# ===========================================================================
# Warranty claim status persistence (from test_new_features.py)
# ===========================================================================

def _activate_sc_warranty(client, mfr_token, sc_user):
    client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(mfr_token))
    fresh = client.post('/api/auth/login',
                        json={'email': sc_user['email'], 'password': STRONG_PASSWORD})
    return fresh.get_json()['access_token']


def _register_vehicle_warranty(client, mfr_token, owner_email=None, vin=VIN):
    payload = {'vin': vin, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024}
    if owner_email:
        payload['owner_email'] = owner_email
    return client.post('/api/vehicle/register', headers=auth(mfr_token), json=payload)


class TestWarrantyClaimStatusPersistence:
    def _setup_claim(self, client):
        """Submit a claim and configure wt.get_claims to return the actual claim hash."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle_warranty(client, mfr_token, owner_email=owner['email'])

        r = client.post('/api/warranty/submit-claim', headers=auth(owner_token), json={
            'vin': VIN, 'issue_description': 'Gearbox grinding noise',
        })
        actual_hash = r.get_json()['claim_hash']

        # Point get_claims mock at the real hash so update_status can find the DB record
        from blockchain.adapters.warranty_tracker import warranty_tracker as wt
        wt.get_claims.return_value = [{'claim_details_hash': actual_hash, 'timestamp': 0}]

        return mfr_token, actual_hash

    def test_approve_claim_persists_approved_status(self, client, app):
        mfr_token, _ = self._setup_claim(client)

        client.post('/api/warranty/approve-claim', headers=auth(mfr_token), json={
            'vin': VIN, 'claim_index': 0,
        })

        with app.app_context():
            from db.models import WarrantyClaimMetadata
            record = WarrantyClaimMetadata.query.filter_by(vin=VIN).first()
            assert record is not None
            assert record.status == 'approved'

    def test_deny_claim_persists_denied_status(self, client, app):
        mfr_token, _ = self._setup_claim(client)

        client.post('/api/warranty/deny-claim', headers=auth(mfr_token), json={
            'vin': VIN, 'claim_index': 0, 'reason': 'Outside warranty scope',
        })

        with app.app_context():
            from db.models import WarrantyClaimMetadata
            record = WarrantyClaimMetadata.query.filter_by(vin=VIN).first()
            assert record is not None
            assert record.status == 'denied'

    def test_deny_claim_persists_reason_as_notes(self, client, app):
        mfr_token, _ = self._setup_claim(client)

        client.post('/api/warranty/deny-claim', headers=auth(mfr_token), json={
            'vin': VIN, 'claim_index': 0, 'reason': 'Vehicle was modified by owner',
        })

        with app.app_context():
            from db.models import WarrantyClaimMetadata
            record = WarrantyClaimMetadata.query.filter_by(vin=VIN).first()
            assert record.approved_notes == 'Vehicle was modified by owner'

    def test_new_claim_has_pending_status_by_default(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle_warranty(client, mfr_token, owner_email=owner['email'])

        client.post('/api/warranty/submit-claim', headers=auth(owner_token), json={
            'vin': VIN, 'issue_description': 'Strange rattle from dashboard',
        })

        with app.app_context():
            from db.models import WarrantyClaimMetadata
            record = WarrantyClaimMetadata.query.filter_by(vin=VIN).first()
            assert record is not None
            assert record.status == 'pending'

    def test_approve_sets_approved_at_timestamp(self, client, app):
        mfr_token, _ = self._setup_claim(client)

        client.post('/api/warranty/approve-claim', headers=auth(mfr_token), json={
            'vin': VIN, 'claim_index': 0,
        })

        with app.app_context():
            from db.models import WarrantyClaimMetadata
            record = WarrantyClaimMetadata.query.filter_by(vin=VIN).first()
            assert record.approved_at is not None

    def teardown_method(self, method):
        from blockchain.adapters.warranty_tracker import warranty_tracker as wt
        wt.get_claims.return_value = []


# ---------------------------------------------------------------------------
# WarrantyClaimMetadata model — new fields
# ---------------------------------------------------------------------------

class TestWarrantyClaimMetadataModel:
    def test_warranty_claim_to_dict_includes_status(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle_warranty(client, mfr_token, owner_email=owner['email'])
        client.post('/api/warranty/submit-claim', headers=auth(owner_token), json={
            'vin': VIN, 'issue_description': 'Oil leak',
        })

        with app.app_context():
            from db.models import WarrantyClaimMetadata
            record = WarrantyClaimMetadata.query.filter_by(vin=VIN).first()
            d = record.to_dict()
            assert 'status' in d
            assert 'approved_at' in d
            assert 'approved_notes' in d

    def test_warranty_claim_default_status_is_pending(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle_warranty(client, mfr_token, owner_email=owner['email'])
        client.post('/api/warranty/submit-claim', headers=auth(owner_token), json={
            'vin': VIN, 'issue_description': 'Coolant leak',
        })

        with app.app_context():
            from db.models import WarrantyClaimMetadata
            record = WarrantyClaimMetadata.query.filter_by(vin=VIN).first()
            assert record.status == 'pending'
            assert record.approved_at is None
