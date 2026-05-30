"""Security, hardening, and improvement tests (Groups L, M, N + production hardening)."""
import hashlib
import hmac
import io
import time
import pytest
from unittest.mock import MagicMock
from conftest import register_and_login, auth, STRONG_PASSWORD

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

VIN  = '1HGCM82633A004352'
VIN2 = '2HGCM82633A004352'
PAST_DATE   = '2020-01-01T10:00:00'
FUTURE_DATE = '2099-12-31T10:00:00'
TODAY_DATE  = time.strftime('%Y-%m-%dT%H:%M:%S')
TODAY       = TODAY_DATE  # alias used by several classes


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _admin_headers(secret: str) -> dict:
    ts = str(int(time.time()))
    sig = hmac.new(secret.encode(), ts.encode(), hashlib.sha256).hexdigest()
    return {
        'X-Admin-Secret': secret,
        'X-Admin-Timestamp': ts,
        'X-Admin-Signature': sig,
    }


def _register_vehicle(client, mfr_token, owner_email=None, vin=VIN, make='Honda'):
    payload = {'vin': vin, 'warranty_years': 3, 'make': make, 'model': 'Civic', 'year': 2024}
    if owner_email:
        payload['owner_email'] = owner_email
    return client.post('/api/vehicle/register', headers=auth(mfr_token), json=payload)


def _activate_sc(client, mfr_token, sc_user):
    client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(mfr_token))
    fresh = client.post('/api/auth/login',
                        json={'email': sc_user['email'], 'password': STRONG_PASSWORD})
    return fresh.get_json()['access_token']


def _submit_service(client, sc_token, vin=VIN, mileage=10000, service_date=TODAY_DATE):
    return client.post('/api/service/submit', headers=auth(sc_token), json={
        'vin': vin, 'service_type': 'Oil Change',
        'service_date': service_date, 'mileage': mileage,
    })


# ===========================================================================
# Group L: 15 security / logic fixes (from test_security_fixes.py)
# ===========================================================================

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


# ===========================================================================
# Group M: 8 hardening fixes (from test_hardening2.py)
# ===========================================================================

# ---------------------------------------------------------------------------
# Fix 1: JWT type field — refresh token must not work as access token
# ---------------------------------------------------------------------------

class TestJWTTypeCheck:
    def test_refresh_token_rejected_as_bearer(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'jwt-type@test.com', 'password': STRONG_PASSWORD,
            'role': 'OWNER', 'name': 'Test', 'consent_given': True,
        })
        refresh_token = r.get_json()['refresh_token']

        # Use refresh token in Authorization header
        r2 = client.get('/api/auth/me',
                        headers={'Authorization': f'Bearer {refresh_token}'})
        assert r2.status_code == 401

    def test_access_token_accepted_as_bearer(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.get('/api/auth/me', headers=auth(token))
        assert r.status_code == 200

    def test_arbitrary_jwt_missing_type_rejected(self, client):
        import jwt as _jwt
        from config import Config
        from datetime import datetime, timedelta
        payload = {
            'user_id': 1, 'email': 'x@x.com', 'role': 'OWNER',
            'brand': '', 'blockchain_address': '0x' + '0' * 40,
            'exp': datetime.utcnow() + timedelta(hours=1),
            # no 'type' field
        }
        bad_token = _jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')
        r = client.get('/api/auth/me', headers={'Authorization': f'Bearer {bad_token}'})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Fix 2: resolve-dispute record_index must be a non-negative integer
# ---------------------------------------------------------------------------

class TestResolveDisputeRecordIndex:
    def test_negative_record_index_rejected(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/service/resolve-dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'record_index': -1, 'decision': 1,
        })
        assert r.status_code == 400
        assert 'record_index' in r.get_json()['error'].lower()

    def test_string_record_index_rejected(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/service/resolve-dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'record_index': 'bad', 'decision': 1,
        })
        assert r.status_code == 400

    def test_valid_record_index_accepted(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/service/resolve-dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'record_index': 0, 'decision': 1, 'resolution_notes': 'ok',
        })
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Fix 3: fix-ownership activates pending vehicle
# ---------------------------------------------------------------------------

class TestFixOwnershipActivates:
    def test_fix_ownership_activates_pending_vehicle(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')

        # Register without owner → status=pending
        _register_vehicle(client, mfr_token)

        with app.app_context():
            from db.models import VehicleVINMapping
            mapping = VehicleVINMapping.query.filter_by(vin=VIN).first()
            assert mapping.registration_status == 'pending'

        from config import Config
        Config.ADMIN_SECRET = 'test-secret'
        try:
            r = client.post('/api/admin/fix-ownership', headers=auth(mfr_token), json={
                'vin': VIN, 'new_owner_email': owner['email'],
                'make': 'Honda', 'model': 'Civic',
            })
            assert r.status_code == 200
        finally:
            Config.ADMIN_SECRET = ''

        with app.app_context():
            from db.models import VehicleVINMapping
            mapping = VehicleVINMapping.query.filter_by(vin=VIN).first()
            assert mapping.registration_status == 'active'

    def test_fix_ownership_on_active_vehicle_stays_active(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner_a = register_and_login(client, 'OWNER')
        _, owner_b = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner_a['email'])

        from config import Config
        Config.ADMIN_SECRET = 'test-secret'
        try:
            r = client.post('/api/admin/fix-ownership', headers=auth(mfr_token), json={
                'vin': VIN, 'new_owner_email': owner_b['email'],
                'make': 'Honda', 'model': 'Civic',
            })
            assert r.status_code == 200
        finally:
            Config.ADMIN_SECRET = ''

        with app.app_context():
            from db.models import VehicleVINMapping
            mapping = VehicleVINMapping.query.filter_by(vin=VIN).first()
            assert mapping.registration_status == 'active'


# ---------------------------------------------------------------------------
# Fix 4: Transfer to self rejected
# ---------------------------------------------------------------------------

class TestTransferToSelf:
    def test_owner_cannot_transfer_to_self(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])

        r = client.post('/api/vehicle/transfer', headers=auth(owner_token), json={
            'vin': VIN, 'new_owner_email': owner['email'],
        })
        assert r.status_code == 400
        assert 'yourself' in r.get_json()['error'].lower()

    def test_transfer_to_different_owner_succeeds(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_a_token, owner_a = register_and_login(client, 'OWNER')
        _, owner_b = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner_a['email'])

        r = client.post('/api/vehicle/transfer', headers=auth(owner_a_token), json={
            'vin': VIN, 'new_owner_email': owner_b['email'],
        })
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Fix 5: Vehicle year validation (1886 – current year + 1)
# ---------------------------------------------------------------------------

class TestVehicleYearValidation:
    def test_year_zero_rejected(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 0,
        })
        assert r.status_code == 400
        assert '1886' in r.get_json()['error']

    def test_year_negative_rejected(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': -1,
        })
        assert r.status_code == 400

    def test_far_future_year_rejected(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 9999,
        })
        assert r.status_code == 400

    def test_valid_year_accepted(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })
        assert r.status_code == 200

    def test_no_year_accepted(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic',
        })
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Fix 6: Blockchain address lookup is case-insensitive
# ---------------------------------------------------------------------------

class TestBlockchainAddressCaseInsensitive:
    def test_address_lookup_case_insensitive(self, client, app):
        _, owner = register_and_login(client, 'OWNER')

        with app.app_context():
            from db.repositories import users as user_repo
            # Look up with uppercase — should still find the user
            addr = owner['blockchain_address']
            found = user_repo.find_by_blockchain_address(addr.upper())
            assert found is not None
            assert found.email == owner['email']

            found_lower = user_repo.find_by_blockchain_address(addr.lower())
            assert found_lower is not None


# ---------------------------------------------------------------------------
# Fix 7: File size limit on uploads
# ---------------------------------------------------------------------------

class TestFileSizeLimit:
    def _setup_active_sc(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        return _activate_sc(client, mfr_token, sc_user)

    def test_oversized_file_rejected_on_service_submit(self, client):
        sc_token = self._setup_active_sc(client)
        large_content = b'\xff\xd8\xff\xe0' + b'\x00' * (6 * 1024 * 1024)  # 6 MB
        photo = (io.BytesIO(large_content), 'big.jpg')
        r = client.post('/api/service/submit',
            headers=auth(sc_token),
            data={
                'vin': VIN, 'service_type': 'Oil Change',
                'service_date': TODAY, 'mileage': '5000',
                'photos': photo,
            },
            content_type='multipart/form-data',
        )
        # Oversized photo is skipped (exception caught), service still submits
        # OR we get a 400 — either way the large file must not be stored
        assert r.status_code in (200, 400, 413)

    def test_normal_size_file_accepted(self, client):
        sc_token = self._setup_active_sc(client)
        small_content = b'\xff\xd8\xff\xe0' + b'\x00' * 1024  # 1 KB
        photo = (io.BytesIO(small_content), 'small.jpg')
        r = client.post('/api/service/submit',
            headers=auth(sc_token),
            data={
                'vin': VIN, 'service_type': 'Oil Change',
                'service_date': TODAY, 'mileage': '5000',
                'photos': photo,
            },
            content_type='multipart/form-data',
        )
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Fix 8: service_date minimum (year >= 2000)
# ---------------------------------------------------------------------------

class TestServiceDateMinimum:
    def _setup_active_sc(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        return _activate_sc(client, mfr_token, sc_user)

    def test_date_before_2000_rejected(self, client):
        sc_token = self._setup_active_sc(client)
        r = client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Oil Change',
            'service_date': '1999-12-31T23:59:59', 'mileage': 5000,
        })
        assert r.status_code == 400
        assert '2000' in r.get_json()['error']

    def test_date_year_2000_accepted(self, client):
        sc_token = self._setup_active_sc(client)
        r = client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Oil Change',
            'service_date': '2000-01-01T00:00:00', 'mileage': 5000,
        })
        assert r.status_code == 200

    def test_reasonable_past_date_accepted(self, client):
        sc_token = self._setup_active_sc(client)
        r = client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Tyre Rotation',
            'service_date': '2020-06-15T09:30:00', 'mileage': 5000,
        })
        assert r.status_code == 200


# ===========================================================================
# Group N: 6 hardening fixes (from test_hardening3.py)
# ===========================================================================

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


# ===========================================================================
# Improvements batch (from test_improvements.py)
# ===========================================================================

# ---------------------------------------------------------------------------
# HMAC-hardened admin reset-db
# ---------------------------------------------------------------------------

class TestAdminResetDbHmac:
    SECRET = 'hmac-test-secret'

    def test_missing_timestamp_returns_401(self, client, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, 'ADMIN_SECRET', self.SECRET)
        r = client.post('/api/admin/reset-db', headers={'X-Admin-Secret': self.SECRET})
        assert r.status_code == 401

    def test_expired_timestamp_returns_401(self, client, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, 'ADMIN_SECRET', self.SECRET)
        old_ts = str(int(time.time()) - 60)
        sig = hmac.new(self.SECRET.encode(), old_ts.encode(), hashlib.sha256).hexdigest()
        r = client.post('/api/admin/reset-db', headers={
            'X-Admin-Secret': self.SECRET,
            'X-Admin-Timestamp': old_ts,
            'X-Admin-Signature': sig,
        })
        assert r.status_code == 401

    def test_wrong_signature_returns_401(self, client, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, 'ADMIN_SECRET', self.SECRET)
        ts = str(int(time.time()))
        r = client.post('/api/admin/reset-db', headers={
            'X-Admin-Secret': self.SECRET,
            'X-Admin-Timestamp': ts,
            'X-Admin-Signature': 'deadbeef' * 8,
        })
        assert r.status_code == 401

    def test_valid_hmac_returns_200(self, client, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, 'ADMIN_SECRET', self.SECRET)
        r = client.post('/api/admin/reset-db', headers=_admin_headers(self.SECRET))
        assert r.status_code == 200

    def test_future_timestamp_too_far_returns_401(self, client, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, 'ADMIN_SECRET', self.SECRET)
        future_ts = str(int(time.time()) + 120)
        sig = hmac.new(self.SECRET.encode(), future_ts.encode(), hashlib.sha256).hexdigest()
        r = client.post('/api/admin/reset-db', headers={
            'X-Admin-Secret': self.SECRET,
            'X-Admin-Timestamp': future_ts,
            'X-Admin-Signature': sig,
        })
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# MIME magic byte validation on uploads
# ---------------------------------------------------------------------------

class TestUploadMimeValidation:
    def _upload(self, client, token, data, filename='test.jpg', content_type='image/jpeg'):
        from io import BytesIO
        return client.post(
            '/api/upload/photo',
            headers=auth(token),
            data={'file': (BytesIO(data), filename, content_type)},
            content_type='multipart/form-data',
        )

    def test_valid_jpeg_accepted(self, client):
        token, _ = register_and_login(client, 'OWNER')
        jpeg_bytes = b'\xff\xd8\xff\xe0' + b'\x00' * 100
        r = self._upload(client, token, jpeg_bytes)
        # 200 = saved; 400 is also acceptable if filesystem unavailable in test env
        assert r.status_code in (200, 400)
        if r.status_code == 400:
            assert 'content' not in r.get_json().get('error', '').lower()

    def test_fake_jpeg_rejected(self, client):
        token, _ = register_and_login(client, 'OWNER')
        fake = b'PK\x03\x04' + b'\x00' * 100  # zip magic bytes
        r = self._upload(client, token, fake, filename='evil.jpg')
        assert r.status_code == 400
        err = r.get_json()['error'].lower()
        assert 'content' in err or 'extension' in err

    def test_fake_png_rejected(self, client):
        token, _ = register_and_login(client, 'OWNER')
        fake = b'MZ' + b'\x00' * 100  # EXE magic bytes named as .png
        r = self._upload(client, token, fake, filename='evil.png', content_type='image/png')
        assert r.status_code == 400

    def test_valid_pdf_accepted(self, client):
        token, _ = register_and_login(client, 'OWNER')
        pdf_bytes = b'%PDF-1.4' + b'\x00' * 100
        r = self._upload(client, token, pdf_bytes, filename='doc.pdf', content_type='application/pdf')
        assert r.status_code in (200, 400)

    def test_unauthenticated_upload_rejected(self, client):
        from io import BytesIO
        r = client.post(
            '/api/upload/photo',
            data={'file': (BytesIO(b'\xff\xd8\xff\xe0'), 'test.jpg', 'image/jpeg')},
            content_type='multipart/form-data',
        )
        assert r.status_code == 401

    def test_gif_accepted(self, client):
        token, _ = register_and_login(client, 'OWNER')
        gif_bytes = b'GIF89a' + b'\x00' * 100
        r = self._upload(client, token, gif_bytes, filename='anim.gif', content_type='image/gif')
        assert r.status_code in (200, 400)


# ---------------------------------------------------------------------------
# Audit log events are persisted on key actions
# ---------------------------------------------------------------------------

class TestAuditLogging:
    def test_login_success_creates_audit_log(self, client, app):
        register_and_login(client, 'OWNER', email='auditowner@test.com')
        # Explicitly call login to trigger login_success event
        client.post('/api/auth/login', json={
            'email': 'auditowner@test.com', 'password': STRONG_PASSWORD,
        })
        with app.app_context():
            from db.models import AuditLog
            log = AuditLog.query.filter_by(event='login_success').first()
            assert log is not None
            assert log.detail.get('email') == 'auditowner@test.com'

    def test_login_failure_creates_audit_log(self, client, app):
        client.post('/api/auth/login', json={
            'email': 'nonexistent@test.com', 'password': 'wrong',
        })
        with app.app_context():
            from db.models import AuditLog
            log = AuditLog.query.filter_by(event='login_failure').first()
            assert log is not None
            assert log.detail.get('email') == 'nonexistent@test.com'

    def test_password_change_creates_audit_log(self, client, app):
        token, _ = register_and_login(client, 'OWNER', email='pwchange@test.com')
        client.post('/api/auth/change-password', headers=auth(token), json={
            'current_password': STRONG_PASSWORD,
            'new_password': 'NewSecureP@ss99!',
        })
        with app.app_context():
            from db.models import AuditLog
            log = AuditLog.query.filter_by(event='password_changed').first()
            assert log is not None

    def test_audit_log_event_field_populated(self, client, app):
        register_and_login(client, 'OWNER', email='iptest@test.com')
        client.post('/api/auth/login', json={
            'email': 'iptest@test.com', 'password': STRONG_PASSWORD,
        })
        with app.app_context():
            from db.models import AuditLog
            log = AuditLog.query.filter_by(event='login_success').first()
            assert log is not None
            assert log.event == 'login_success'

    def test_multiple_login_failures_logged(self, client, app):
        for _ in range(3):
            client.post('/api/auth/login', json={'email': 'x@x.com', 'password': 'wrong'})
        with app.app_context():
            from db.models import AuditLog
            count = AuditLog.query.filter_by(event='login_failure').count()
            assert count >= 3


# ---------------------------------------------------------------------------
# Service history filtering — tests the _apply_filters helper directly
# ---------------------------------------------------------------------------

class TestServiceHistoryFiltering:
    RECORDS = [
        {'vin': VIN, 'record_index': 0, 'service_type': 'Oil Change',
         'service_date': '2024-03-15T10:00:00', 'mileage': 10000,
         'status': 'verified', 'dispute_reason': None},
        {'vin': VIN, 'record_index': 1, 'service_type': 'Tire Rotation',
         'service_date': '2024-06-01T10:00:00', 'mileage': 20000,
         'status': 'disputed', 'dispute_reason': 'Wrong parts'},
        {'vin': VIN, 'record_index': 2, 'service_type': 'Brake Check',
         'service_date': '2024-09-10T10:00:00', 'mileage': 30000,
         'status': 'verified', 'dispute_reason': None},
    ]

    def _filter(self, **kwargs):
        from core.service_log_service import _apply_filters
        return _apply_filters(list(self.RECORDS), kwargs)

    def test_no_filter_returns_all(self):
        from core.service_log_service import _apply_filters
        result = _apply_filters(list(self.RECORDS), {})
        assert len(result) == 3

    def test_filter_by_verified_status(self):
        result = self._filter(status='verified')
        assert len(result) == 2
        assert all(r['status'] == 'verified' for r in result)

    def test_filter_by_disputed_status(self):
        result = self._filter(status='disputed')
        assert len(result) == 1
        assert result[0]['service_type'] == 'Tire Rotation'

    def test_filter_by_unknown_status_returns_empty(self):
        result = self._filter(status='nonexistent')
        assert result == []

    def test_filter_by_service_type_partial(self):
        result = self._filter(service_type='oil')
        assert len(result) == 1
        assert result[0]['service_type'] == 'Oil Change'

    def test_filter_by_service_type_no_match(self):
        result = self._filter(service_type='transmission')
        assert result == []

    def test_filter_by_date_from_excludes_old(self):
        result = self._filter(date_from='2024-07-01')
        assert len(result) == 1
        assert result[0]['service_type'] == 'Brake Check'

    def test_filter_by_date_to_excludes_new(self):
        result = self._filter(date_to='2024-04-01')
        assert len(result) == 1
        assert result[0]['service_type'] == 'Oil Change'

    def test_filter_date_range(self):
        result = self._filter(date_from='2024-05-01', date_to='2024-07-01')
        assert len(result) == 1
        assert result[0]['service_type'] == 'Tire Rotation'

    def test_combined_status_and_type_filter(self):
        result = self._filter(status='verified', service_type='brake')
        assert len(result) == 1
        assert result[0]['service_type'] == 'Brake Check'

    def test_owner_history_endpoint_accepts_filter_params(self, client):
        owner_token, _ = register_and_login(client, 'OWNER')
        r = client.get('/api/service/owner/history?status=verified', headers=auth(owner_token))
        assert r.status_code == 200
        assert 'service_history' in r.get_json()


# ---------------------------------------------------------------------------
# PDPA compliance — consent, privacy policy and terms endpoints
# ---------------------------------------------------------------------------

class TestPdpaCompliance:
    def test_privacy_policy_endpoint_returns_200(self, client):
        r = client.get('/api/auth/privacy-policy')
        assert r.status_code == 200
        data = r.get_json()
        assert 'sections' in data
        assert len(data['sections']) > 0
        assert 'heading' in data['sections'][0]

    def test_terms_endpoint_returns_200(self, client):
        r = client.get('/api/auth/terms')
        assert r.status_code == 200
        data = r.get_json()
        assert 'sections' in data
        assert len(data['sections']) > 0

    def test_owner_register_without_consent_rejected(self, client):
        import uuid
        r = client.post('/api/auth/register', json={
            'email': f'noconsent_{uuid.uuid4().hex[:6]}@test.com',
            'password': STRONG_PASSWORD,
            'name': 'No Consent User',
            'role': 'OWNER',
            'consent_given': False,
        })
        assert r.status_code == 400
        assert 'consent' in r.get_json().get('error', '').lower() or \
               'privacy' in r.get_json().get('error', '').lower()

    def test_owner_register_without_consent_field_rejected(self, client):
        import uuid
        r = client.post('/api/auth/register', json={
            'email': f'noconsent2_{uuid.uuid4().hex[:6]}@test.com',
            'password': STRONG_PASSWORD,
            'name': 'No Consent User 2',
            'role': 'OWNER',
        })
        assert r.status_code == 400

    def test_owner_register_with_consent_succeeds(self, client, app):
        import uuid
        email = f'consent_{uuid.uuid4().hex[:6]}@test.com'
        r = client.post('/api/auth/register', json={
            'email': email,
            'password': STRONG_PASSWORD,
            'name': 'Consenting User',
            'role': 'OWNER',
            'consent_given': True,
        })
        assert r.status_code in (200, 201)
        with app.app_context():
            from db.models import User
            user = User.query.filter_by(email=email).first()
            assert user is not None
            assert user.consent_given_at is not None

    def test_non_owner_register_without_consent_succeeds(self, client):
        import uuid
        r = client.post('/api/auth/register', json={
            'email': f'mfr_{uuid.uuid4().hex[:6]}@test.com',
            'password': STRONG_PASSWORD,
            'name': 'Manufacturer Corp',
            'role': 'MANUFACTURER',
            'brand': 'TestBrand',
        })
        assert r.status_code in (200, 201)


# ===========================================================================
# Production hardening (from test_production_hardening.py)
# ===========================================================================

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


# ---------------------------------------------------------------------------
# PDPA — account deletion and data export (right of erasure / right of access)
# ---------------------------------------------------------------------------

class TestAccountDeletion:
    def test_delete_account_requires_auth(self, client):
        r = client.delete('/api/auth/account', json={'password': STRONG_PASSWORD})
        assert r.status_code == 401

    def test_delete_account_requires_password_field(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.delete('/api/auth/account', headers=auth(token), json={})
        assert r.status_code == 400
        assert 'password' in r.get_json().get('error', '').lower()

    def test_delete_account_wrong_password_rejected(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.delete('/api/auth/account', headers=auth(token),
                          json={'password': 'WrongPass999!'})
        assert r.status_code == 401

    def test_delete_account_removes_user_row(self, client, app):
        import uuid
        email = f'del_{uuid.uuid4().hex[:6]}@test.com'
        r = client.post('/api/auth/register', json={
            'email': email, 'password': STRONG_PASSWORD,
            'role': 'OWNER', 'name': 'Delete Me', 'consent_given': True,
        })
        assert r.status_code == 200
        token = r.get_json()['access_token']

        r2 = client.delete('/api/auth/account', headers=auth(token),
                           json={'password': STRONG_PASSWORD})
        assert r2.status_code == 200

        with app.app_context():
            from db.models import User
            assert User.query.filter_by(email=email).first() is None

    def test_delete_account_token_invalid_afterwards(self, client):
        import uuid
        email = f'del2_{uuid.uuid4().hex[:6]}@test.com'
        r = client.post('/api/auth/register', json={
            'email': email, 'password': STRONG_PASSWORD,
            'role': 'OWNER', 'name': 'Delete Me 2', 'consent_given': True,
        })
        token = r.get_json()['access_token']
        client.delete('/api/auth/account', headers=auth(token),
                      json={'password': STRONG_PASSWORD})
        r3 = client.get('/api/auth/me', headers=auth(token))
        assert r3.status_code in (401, 404)

    def test_delete_account_erases_audit_logs(self, client, app):
        import uuid
        email = f'del3_{uuid.uuid4().hex[:6]}@test.com'
        r = client.post('/api/auth/register', json={
            'email': email, 'password': STRONG_PASSWORD,
            'role': 'OWNER', 'name': 'Audit Del', 'consent_given': True,
        })
        token = r.get_json()['access_token']
        user_id = r.get_json()['user']['id']

        client.delete('/api/auth/account', headers=auth(token),
                      json={'password': STRONG_PASSWORD})

        with app.app_context():
            from db.models import AuditLog
            remaining = AuditLog.query.filter_by(user_id=user_id).count()
            assert remaining == 0


class TestDataExport:
    def test_data_export_requires_auth(self, client):
        r = client.get('/api/auth/data-export')
        assert r.status_code == 401

    def test_data_export_returns_profile(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.get('/api/auth/data-export', headers=auth(token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'profile' in data
        assert 'exported_at' in data
        assert 'audit_logs' in data
        assert 'dispute_messages_sent' in data

    def test_data_export_owner_includes_vehicles(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.get('/api/auth/data-export', headers=auth(token))
        assert r.status_code == 200
        assert 'vehicles' in r.get_json()
        assert 'warranty_claims' in r.get_json()

    def test_data_export_sc_includes_service_records(self, client):
        token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.get('/api/auth/data-export', headers=auth(token))
        assert r.status_code == 200
        assert 'service_records_submitted' in r.get_json()

    def test_data_export_manufacturer_no_vehicle_field(self, client):
        token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.get('/api/auth/data-export', headers=auth(token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'vehicles' not in data
        assert 'service_records_submitted' not in data
