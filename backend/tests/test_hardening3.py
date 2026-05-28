"""Tests for Group N hardening fixes (6 gaps)."""
import time
import pytest
from conftest import register_and_login, auth, STRONG_PASSWORD

VIN  = '1HGCM82633A004352'
VIN2 = '2HGCM82633A004352'
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
# Fix 1: deny_claim requires non-empty reason
# ---------------------------------------------------------------------------

class TestDenyClaimRequiresReason:
    def test_deny_without_reason_rejected(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/warranty/deny-claim', headers=auth(mfr_token), json={
            'vin': VIN, 'claim_index': 0,
        })
        assert r.status_code == 400
        assert 'reason' in r.get_json()['error'].lower()

    def test_deny_with_empty_reason_rejected(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/warranty/deny-claim', headers=auth(mfr_token), json={
            'vin': VIN, 'claim_index': 0, 'reason': '',
        })
        assert r.status_code == 400
        assert 'reason' in r.get_json()['error'].lower()

    def test_deny_with_reason_proceeds(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        # Submit a warranty claim first
        client.post('/api/warranty/submit-claim', headers=auth(owner_token), json={
            'vin': VIN, 'issue_description': 'Engine noise',
        })
        r = client.post('/api/warranty/deny-claim', headers=auth(mfr_token), json={
            'vin': VIN, 'claim_index': 0, 'reason': 'Not covered under warranty terms',
        })
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Fix 2: service_date sanitize cap raised to 35 chars (timezone-aware dates)
# ---------------------------------------------------------------------------

class TestServiceDateTruncation:
    def _setup_active_sc(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        return _activate_sc(client, mfr_token, sc_user)

    def test_timezone_aware_date_accepted(self, client):
        sc_token = self._setup_active_sc(client)
        # 2024-01-15T10:00:00+08:00 is 25 chars — would be truncated to 20 before the fix
        r = client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Oil Change',
            'service_date': '2024-01-15T02:00:00+00:00', 'mileage': 5000,
        })
        assert r.status_code == 200

    def test_z_suffix_date_still_accepted(self, client):
        sc_token = self._setup_active_sc(client)
        r = client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Oil Change',
            'service_date': '2020-06-15T09:30:00Z', 'mileage': 5000,
        })
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Fix 3: Multipart mileage with missing/invalid value returns 400 (not silent 0)
# ---------------------------------------------------------------------------

class TestMultipartMileageValidation:
    def _setup_active_sc(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        return _activate_sc(client, mfr_token, sc_user)

    def test_missing_mileage_in_multipart_returns_400(self, client):
        sc_token = self._setup_active_sc(client)
        r = client.post('/api/service/submit',
            headers=auth(sc_token),
            data={'vin': VIN, 'service_type': 'Oil Change', 'service_date': TODAY},
            content_type='multipart/form-data',
        )
        assert r.status_code == 400
        assert 'mileage' in r.get_json()['error'].lower()

    def test_non_numeric_mileage_in_multipart_returns_400(self, client):
        sc_token = self._setup_active_sc(client)
        r = client.post('/api/service/submit',
            headers=auth(sc_token),
            data={'vin': VIN, 'service_type': 'Oil Change',
                  'service_date': TODAY, 'mileage': 'bad'},
            content_type='multipart/form-data',
        )
        assert r.status_code == 400
        assert 'mileage' in r.get_json()['error'].lower()

    def test_valid_mileage_in_multipart_accepted(self, client):
        sc_token = self._setup_active_sc(client)
        r = client.post('/api/service/submit',
            headers=auth(sc_token),
            data={'vin': VIN, 'service_type': 'Oil Change',
                  'service_date': TODAY, 'mileage': '5000'},
            content_type='multipart/form-data',
        )
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Fix 4: Pending service records — access control by role
# ---------------------------------------------------------------------------

class TestPendingServicesAccessControl:
    def test_owner_of_vehicle_can_see_pending(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        r = client.get(f'/api/service/pending/{VIN}', headers=auth(owner_token))
        assert r.status_code == 200

    def test_non_owner_cannot_see_pending(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner_a = register_and_login(client, 'OWNER')
        owner_b_token, _ = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner_a['email'])
        r = client.get(f'/api/service/pending/{VIN}', headers=auth(owner_b_token))
        assert r.status_code == 403

    def test_same_brand_sc_can_see_pending(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        sc_token = _activate_sc(client, mfr_token, sc_user)
        r = client.get(f'/api/service/pending/{VIN}', headers=auth(sc_token))
        assert r.status_code == 200

    def test_different_brand_sc_cannot_see_pending(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])

        # Toyota SC has different brand
        toyota_mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Toyota')
        _, toyota_sc = register_and_login(client, 'SERVICE_CENTER', brand='Toyota')
        toyota_sc_token = _activate_sc(client, toyota_mfr_token, toyota_sc)

        r = client.get(f'/api/service/pending/{VIN}', headers=auth(toyota_sc_token))
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Fix 5: ecu_modules size and element-length limits
# ---------------------------------------------------------------------------

class TestEcuModulesValidation:
    def _setup_active_sc(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        return _activate_sc(client, mfr_token, sc_user)

    def test_too_many_ecu_modules_rejected(self, client):
        sc_token = self._setup_active_sc(client)
        r = client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Oil Change',
            'service_date': TODAY, 'mileage': 5000,
            'ecu_modules': [f'MODULE_{i}' for i in range(21)],
        })
        assert r.status_code == 400
        assert 'ecu_modules' in r.get_json()['error'].lower()

    def test_non_list_ecu_modules_rejected(self, client):
        sc_token = self._setup_active_sc(client)
        r = client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Oil Change',
            'service_date': TODAY, 'mileage': 5000,
            'ecu_modules': 'ECM',
        })
        assert r.status_code == 400

    def test_valid_ecu_modules_accepted(self, client):
        sc_token = self._setup_active_sc(client)
        r = client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Oil Change',
            'service_date': TODAY, 'mileage': 5000,
            'ecu_modules': ['ECM', 'TCM', 'ABS'],
        })
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Fix 6: fix-ownership with warranty_years populates warranty_expiry
# ---------------------------------------------------------------------------

class TestFixOwnershipWarranty:
    def test_fix_ownership_with_warranty_years_sets_expiry(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')

        r = client.post('/api/admin/fix-ownership', headers=auth(mfr_token), json={
            'vin': VIN, 'new_owner_email': owner['email'],
            'make': 'Honda', 'model': 'Civic', 'warranty_years': 3,
        })
        assert r.status_code == 200

        with app.app_context():
            from db.models import VehicleVINMapping
            mapping = VehicleVINMapping.query.filter_by(vin=VIN).first()
            assert mapping.warranty_expiry is not None
            assert mapping.warranty_expiry > int(time.time())

    def test_fix_ownership_without_warranty_years_leaves_expiry_null(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')

        r = client.post('/api/admin/fix-ownership', headers=auth(mfr_token), json={
            'vin': VIN, 'new_owner_email': owner['email'],
            'make': 'Honda', 'model': 'Civic',
        })
        assert r.status_code == 200

        with app.app_context():
            from db.models import VehicleVINMapping
            mapping = VehicleVINMapping.query.filter_by(vin=VIN).first()
            assert mapping.warranty_expiry is None

    def test_fix_ownership_invalid_warranty_years_rejected(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        r = client.post('/api/admin/fix-ownership', headers=auth(mfr_token), json={
            'vin': VIN, 'new_owner_email': owner['email'],
            'make': 'Honda', 'model': 'Civic', 'warranty_years': 99,
        })
        assert r.status_code == 400
        assert 'warranty_years' in r.get_json()['error'].lower()
