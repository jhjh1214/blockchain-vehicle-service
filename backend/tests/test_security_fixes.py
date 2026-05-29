"""Tests for all 15 security / logic fixes (Group L)."""
import hashlib
import hmac
import time
import pytest
from conftest import register_and_login, auth, STRONG_PASSWORD


def _admin_headers(secret: str) -> dict:
    ts = str(int(time.time()))
    sig = hmac.new(secret.encode(), ts.encode(), hashlib.sha256).hexdigest()
    return {
        'X-Admin-Secret': secret,
        'X-Admin-Timestamp': ts,
        'X-Admin-Signature': sig,
    }

VIN  = '1HGCM82633A004352'
VIN2 = '2HGCM82633A004352'
PAST_DATE   = '2020-01-01T10:00:00'
FUTURE_DATE = '2099-12-31T10:00:00'
TODAY_DATE  = time.strftime('%Y-%m-%dT%H:%M:%S')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_vehicle(client, mfr_token, owner_email=None, vin=VIN, make='Honda'):
    payload = {'vin': vin, 'warranty_years': 3, 'make': make, 'model': 'Civic', 'year': 2024}
    if owner_email:
        payload['owner_email'] = owner_email
    return client.post('/api/vehicle/register', headers=auth(mfr_token), json=payload)


def _submit_service(client, sc_token, vin=VIN, mileage=10000, service_date=TODAY_DATE):
    return client.post('/api/service/submit', headers=auth(sc_token), json={
        'vin': vin, 'service_type': 'Oil Change',
        'service_date': service_date, 'mileage': mileage,
    })


# ---------------------------------------------------------------------------
# Fix 1: admin/reset-db protected by X-Admin-Secret
# ---------------------------------------------------------------------------

class TestAdminResetDbSecret:
    def test_no_secret_returns_401(self, client):
        r = client.post('/api/admin/reset-db')
        assert r.status_code == 401

    def test_wrong_secret_returns_401(self, client):
        r = client.post('/api/admin/reset-db', headers={'X-Admin-Secret': 'wrong'})
        assert r.status_code == 401

    def test_correct_secret_allowed(self, client):
        from config import Config
        original = Config.ADMIN_SECRET
        Config.ADMIN_SECRET = 'test-admin-secret'
        try:
            r = client.post('/api/admin/reset-db',
                            headers=_admin_headers('test-admin-secret'))
            assert r.status_code == 200
        finally:
            Config.ADMIN_SECRET = original

    def test_empty_configured_secret_always_401(self, client):
        from config import Config
        original = Config.ADMIN_SECRET
        Config.ADMIN_SECRET = ''
        try:
            r = client.post('/api/admin/reset-db',
                            headers={'X-Admin-Secret': ''})
            assert r.status_code == 401
        finally:
            Config.ADMIN_SECRET = original


# ---------------------------------------------------------------------------
# Fix 2/14: admin/fix-ownership requires OWNER role for target user
# ---------------------------------------------------------------------------

class TestFixOwnershipValidation:
    def test_target_must_be_owner_role(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        r = client.post('/api/admin/fix-ownership', headers=auth(mfr_token), json={
            'vin': VIN, 'new_owner_email': sc_user['email'],
            'make': 'Honda', 'model': 'Civic',
        })
        assert r.status_code == 400
        assert 'owner' in r.get_json()['error'].lower()

    def test_brand_mismatch_rejected(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        _, owner = register_and_login(client, 'OWNER')
        r = client.post('/api/admin/fix-ownership', headers=auth(mfr_token), json={
            'vin': VIN, 'new_owner_email': owner['email'],
            'make': 'Toyota', 'model': 'Camry',
        })
        assert r.status_code == 403
        assert 'brand' in r.get_json()['error'].lower()


# ---------------------------------------------------------------------------
# Fix 3: Status included in JWT / SC login blocked when suspended
# ---------------------------------------------------------------------------

class TestSCStatusJWT:
    def test_suspended_sc_cannot_login(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        sc_email = 'susp-sc@test.com'
        _, sc_user = register_and_login(client, 'SERVICE_CENTER', email=sc_email)
        client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(mfr_token))
        client.post(f'/api/sc/service-centers/{sc_user["id"]}/suspend', headers=auth(mfr_token))

        r = client.post('/api/auth/login', json={'email': sc_email, 'password': STRONG_PASSWORD})
        assert r.status_code in (400, 401, 423)
        assert 'suspended' in r.get_json()['error'].lower()

    def test_active_sc_can_login(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        sc_email = 'active-sc@test.com'
        _, sc_user = register_and_login(client, 'SERVICE_CENTER', email=sc_email)
        client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(mfr_token))

        r = client.post('/api/auth/login', json={'email': sc_email, 'password': STRONG_PASSWORD})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Fix 4: Middleware blocks pending/suspended SCs from SC-role endpoints
# ---------------------------------------------------------------------------

class TestSCMiddlewareStatusCheck:
    def test_pending_sc_blocked_from_submit(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')  # pending
        _register_vehicle(client, mfr_token, owner['email'])
        r = _submit_service(client, sc_token)
        assert r.status_code == 403
        assert 'not active' in r.get_json()['error'].lower()

    def test_pending_sc_blocked_from_my_stats(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.get('/api/sc/my-stats', headers=auth(sc_token))
        assert r.status_code == 403

    def test_active_sc_can_access_my_stats(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(mfr_token))

        # Re-login to get fresh token with status=active
        sc_email = sc_user['email']
        login_r = client.post('/api/auth/login', json={'email': sc_email, 'password': STRONG_PASSWORD})
        fresh_token = login_r.get_json()['access_token']

        r = client.get('/api/sc/my-stats', headers=auth(fresh_token))
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Fix 5: Brand change blocked for MANUFACTURER and SERVICE_CENTER
# ---------------------------------------------------------------------------

class TestBrandChangeBlocked:
    def test_manufacturer_cannot_change_brand(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.put('/api/auth/profile', headers=auth(mfr_token), json={'brand': 'Toyota'})
        assert r.status_code == 400
        assert 'brand' in r.get_json()['error'].lower()

    def test_service_center_cannot_change_brand(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.put('/api/auth/profile', headers=auth(sc_token), json={'brand': 'Toyota'})
        assert r.status_code == 400
        assert 'brand' in r.get_json()['error'].lower()

    def test_owner_can_update_profile_without_brand_restriction(self, client):
        owner_token, _ = register_and_login(client, 'OWNER')
        r = client.put('/api/auth/profile', headers=auth(owner_token), json={'name': 'New Name'})
        assert r.status_code == 200

    def test_manufacturer_can_update_non_brand_fields(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.put('/api/auth/profile', headers=auth(mfr_token), json={'name': 'New Name'})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Fix 6: Duplicate VIN returns 400 not 500
# ---------------------------------------------------------------------------

class TestDuplicateVIN:
    def test_duplicate_vin_returns_400(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner['email'])

        r = _register_vehicle(client, mfr_token, owner['email'])
        assert r.status_code == 400
        assert 'already' in r.get_json()['error'].lower()

    def test_different_vins_both_succeed(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        r1 = _register_vehicle(client, mfr_token, owner['email'], vin=VIN)
        r2 = _register_vehicle(client, mfr_token, owner['email'], vin=VIN2)
        assert r1.status_code == 200
        assert r2.status_code == 200


# ---------------------------------------------------------------------------
# Fix 7: Transfer requires VIN ownership
# ---------------------------------------------------------------------------

class TestTransferOwnership:
    def test_non_owner_cannot_transfer(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner_a = register_and_login(client, 'OWNER')
        _, owner_b = register_and_login(client, 'OWNER')
        other_owner_token, _ = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_a['email'])

        r = client.post('/api/vehicle/transfer', headers=auth(other_owner_token), json={
            'vin': VIN, 'new_owner_email': owner_b['email'],
        })
        assert r.status_code in (400, 403)


# ---------------------------------------------------------------------------
# Fix 8: Suspension revokes refresh tokens
# ---------------------------------------------------------------------------

class TestSuspensionRevokesTokens:
    def test_refresh_token_invalidated_after_suspension(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        sc_email = 'revoke-test-sc@test.com'
        sc_token, sc_user = register_and_login(client, 'SERVICE_CENTER', email=sc_email)

        login_r = client.post('/api/auth/login', json={
            'email': sc_email, 'password': STRONG_PASSWORD,
        })
        assert login_r.status_code == 200
        refresh_token = login_r.get_json()['refresh_token']

        client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(mfr_token))
        client.post(f'/api/sc/service-centers/{sc_user["id"]}/suspend', headers=auth(mfr_token))

        r = client.post('/api/auth/refresh', json={'refresh_token': refresh_token})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Fix 9: Duplicate VIN / intended_owner_email cleared on transfer
# ---------------------------------------------------------------------------

class TestIntendedOwnerEmailClearedOnTransfer:
    def test_intended_email_cleared_after_claim_and_transfer(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_a_email = 'owner-a@test.com'
        owner_a_token, owner_a = register_and_login(client, 'OWNER', email=owner_a_email)
        _, owner_b = register_and_login(client, 'OWNER')

        # Pre-register with intended owner
        client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
            'intended_owner_email': owner_a_email,
        })
        client.post('/api/vehicle/claim', headers=auth(owner_a_token), json={'vin': VIN})

        # Transfer to owner_b
        client.post('/api/vehicle/transfer', headers=auth(owner_a_token), json={
            'vin': VIN, 'new_owner_email': owner_b['email'],
        })

        with app.app_context():
            from db.models import VehicleVINMapping
            mapping = VehicleVINMapping.query.filter_by(vin=VIN).first()
            assert mapping is not None
            assert mapping.intended_owner_email is None


# ---------------------------------------------------------------------------
# Fix 10: Expired warranty claim rejected
# ---------------------------------------------------------------------------

class TestWarrantyExpiry:
    def test_expired_warranty_claim_rejected(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner['email'])

        with app.app_context():
            from db.models import db, VehicleVINMapping
            mapping = VehicleVINMapping.query.filter_by(vin=VIN).first()
            mapping.warranty_expiry = int(time.time()) - 1000
            db.session.commit()

        r = client.post('/api/warranty/submit-claim', headers=auth(owner_token), json={
            'vin': VIN, 'issue_description': 'Engine issue', 'photos': [],
        })
        assert r.status_code == 400
        assert 'expired' in r.get_json()['error'].lower()

    def test_valid_warranty_claim_accepted(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner['email'])

        r = client.post('/api/warranty/submit-claim', headers=auth(owner_token), json={
            'vin': VIN, 'issue_description': 'Engine issue', 'photos': [],
        })
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Fix 11: warranty_years cap (1-20)
# ---------------------------------------------------------------------------

class TestWarrantyYearsCap:
    def test_warranty_years_zero_rejected(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 0, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })
        assert r.status_code == 400

    def test_warranty_years_21_rejected(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 21, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })
        assert r.status_code == 400

    def test_warranty_years_1_accepted(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 1, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })
        assert r.status_code == 200

    def test_warranty_years_20_accepted(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 20, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Fix 12: record_index must be a non-negative integer
# ---------------------------------------------------------------------------

class TestRecordIndexValidation:
    def _setup(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner['email'])
        return owner_token

    def test_negative_record_index_rejected_verify(self, client):
        owner_token = self._setup(client)
        r = client.post('/api/service/verify', headers=auth(owner_token), json={
            'vin': VIN, 'record_index': -1,
        })
        assert r.status_code == 400
        assert 'record_index' in r.get_json()['error'].lower()

    def test_string_record_index_rejected_verify(self, client):
        owner_token = self._setup(client)
        r = client.post('/api/service/verify', headers=auth(owner_token), json={
            'vin': VIN, 'record_index': 'bad',
        })
        assert r.status_code == 400

    def test_negative_record_index_rejected_dispute(self, client):
        owner_token = self._setup(client)
        r = client.post('/api/service/dispute', headers=auth(owner_token), json={
            'vin': VIN, 'record_index': -1, 'reason': 'Service never performed',
        })
        assert r.status_code == 400

    def test_negative_record_index_rejected_owner_verify(self, client):
        owner_token = self._setup(client)
        r = client.post('/api/service/owner/verify', headers=auth(owner_token), json={
            'vin': VIN, 'record_index': -1,
        })
        assert r.status_code == 400

    def test_negative_record_index_rejected_owner_dispute(self, client):
        owner_token = self._setup(client)
        r = client.post('/api/service/owner/dispute', headers=auth(owner_token), json={
            'vin': VIN, 'record_index': -1, 'reason': 'Issue',
        })
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Fix 13: service_date cannot be in the future
# ---------------------------------------------------------------------------

class TestServiceDateValidation:
    def _setup_active_sc(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle(client, mfr_token, owner['email'])
        client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(mfr_token))
        fresh_login = client.post('/api/auth/login',
                                  json={'email': sc_user['email'], 'password': STRONG_PASSWORD})
        return fresh_login.get_json()['access_token']

    def test_future_service_date_rejected(self, client):
        sc_token = self._setup_active_sc(client)
        r = _submit_service(client, sc_token, service_date=FUTURE_DATE)
        assert r.status_code == 400
        assert 'future' in r.get_json()['error'].lower()

    def test_invalid_date_format_rejected(self, client):
        sc_token = self._setup_active_sc(client)
        r = _submit_service(client, sc_token, service_date='not-a-date')
        assert r.status_code == 400
        assert 'format' in r.get_json()['error'].lower() or 'invalid' in r.get_json()['error'].lower()

    def test_past_service_date_accepted(self, client):
        sc_token = self._setup_active_sc(client)
        r = _submit_service(client, sc_token, service_date=PAST_DATE)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Fix 14: claim_index must be non-negative integer
# ---------------------------------------------------------------------------

class TestClaimIndexValidation:
    def _setup_mfr(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner['email'])
        return mfr_token

    def test_negative_claim_index_rejected_approve(self, client):
        mfr_token = self._setup_mfr(client)
        r = client.post('/api/warranty/approve-claim', headers=auth(mfr_token), json={
            'vin': VIN, 'claim_index': -1,
        })
        assert r.status_code == 400
        assert 'claim_index' in r.get_json()['error'].lower()

    def test_string_claim_index_rejected_approve(self, client):
        mfr_token = self._setup_mfr(client)
        r = client.post('/api/warranty/approve-claim', headers=auth(mfr_token), json={
            'vin': VIN, 'claim_index': 'bad',
        })
        assert r.status_code == 400

    def test_negative_claim_index_rejected_deny(self, client):
        mfr_token = self._setup_mfr(client)
        r = client.post('/api/warranty/deny-claim', headers=auth(mfr_token), json={
            'vin': VIN, 'claim_index': -1, 'reason': 'Not covered',
        })
        assert r.status_code == 400
        assert 'claim_index' in r.get_json()['error'].lower()


# ---------------------------------------------------------------------------
# Fix 15: Mileage cannot decrease between service records
# ---------------------------------------------------------------------------

class TestMileageRollback:
    def _activate_sc_and_get_token(self, client, mfr_token, sc_user):
        client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(mfr_token))
        login_r = client.post('/api/auth/login', json={
            'email': sc_user['email'], 'password': STRONG_PASSWORD,
        })
        return login_r.get_json()['access_token']

    def test_mileage_decrease_rejected(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        sc_token_raw, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle(client, mfr_token, owner['email'])
        sc_token = self._activate_sc_and_get_token(client, mfr_token, sc_user)

        r1 = _submit_service(client, sc_token, mileage=20000)
        assert r1.status_code == 200

        r2 = _submit_service(client, sc_token, mileage=15000)
        assert r2.status_code == 400
        assert 'mileage' in r2.get_json()['error'].lower()
        assert 'decrease' in r2.get_json()['error'].lower()

    def test_mileage_increase_accepted(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        sc_token_raw, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle(client, mfr_token, owner['email'])
        sc_token = self._activate_sc_and_get_token(client, mfr_token, sc_user)

        r1 = _submit_service(client, sc_token, mileage=20000)
        assert r1.status_code == 200

        r2 = _submit_service(client, sc_token, mileage=25000)
        assert r2.status_code == 200

    def test_same_mileage_accepted(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        sc_token_raw, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle(client, mfr_token, owner['email'])
        sc_token = self._activate_sc_and_get_token(client, mfr_token, sc_user)

        r1 = _submit_service(client, sc_token, mileage=20000)
        assert r1.status_code == 200

        r2 = _submit_service(client, sc_token, mileage=20000)
        assert r2.status_code == 200


# ---------------------------------------------------------------------------
# Verify/Dispute ownership checks
# ---------------------------------------------------------------------------

class TestVerifyDisputeOwnership:
    def _setup(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner_a = register_and_login(client, 'OWNER')
        other_owner_token, _ = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_a['email'])
        return other_owner_token

    def test_non_owner_cannot_verify(self, client):
        other_token = self._setup(client)
        r = client.post('/api/service/verify', headers=auth(other_token), json={
            'vin': VIN, 'record_index': 0,
        })
        assert r.status_code == 403
        assert 'own' in r.get_json()['error'].lower()

    def test_non_owner_cannot_dispute(self, client):
        other_token = self._setup(client)
        r = client.post('/api/service/dispute', headers=auth(other_token), json={
            'vin': VIN, 'record_index': 0, 'reason': 'Fraudulent',
        })
        assert r.status_code == 403
        assert 'own' in r.get_json()['error'].lower()

    def test_non_owner_cannot_owner_verify(self, client):
        other_token = self._setup(client)
        r = client.post('/api/service/owner/verify', headers=auth(other_token), json={
            'vin': VIN, 'record_index': 0,
        })
        assert r.status_code == 403

    def test_non_owner_cannot_owner_dispute(self, client):
        other_token = self._setup(client)
        r = client.post('/api/service/owner/dispute', headers=auth(other_token), json={
            'vin': VIN, 'record_index': 0, 'reason': 'Test',
        })
        assert r.status_code == 403
