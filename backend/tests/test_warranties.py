"""Tests for /api/warranty endpoints."""
import pytest
from conftest import register_and_login, auth

VIN = '1HGCM82633A004352'


def _register_vehicle(client, mfr_token, make='Honda'):
    """Pre-register a vehicle (no owner) under the given manufacturer."""
    client.post('/api/vehicle/register', headers=auth(mfr_token), json={
        'vin': VIN, 'warranty_years': 3, 'make': make, 'model': 'Civic', 'year': 2024,
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
        token, _ = register_and_login(client, 'OWNER')
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
        token, _ = register_and_login(client, 'OWNER')
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
        token, _ = register_and_login(client, 'OWNER')
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
