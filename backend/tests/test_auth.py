"""Tests for /api/auth endpoints."""
import pytest
from conftest import register_and_login, auth, STRONG_PASSWORD


class TestRegister:
    def test_register_manufacturer(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'mfr@test.com',
            'password': STRONG_PASSWORD,
            'role': 'MANUFACTURER',
            'name': 'Honda Corp',
            'brand': 'Honda',
            'ssm_number': 'SSMTEST001',
        })
        assert r.status_code == 200
        data = r.get_json()
        assert 'access_token' in data
        assert data['user']['role'] == 'MANUFACTURER'
        assert data['user']['email'] == 'mfr@test.com'
        assert data['user']['brand'] == 'Honda'

    def test_register_service_center(self, client):
        """Independent SC registration requires no SSM and has no brand restriction."""
        r = client.post('/api/auth/register', json={
            'email': 'sc@test.com',
            'password': STRONG_PASSWORD,
            'role': 'SERVICE_CENTER',
            'name': 'Best Auto',
            'is_independent': True,
        })
        assert r.status_code == 200
        assert r.get_json()['user']['role'] == 'SERVICE_CENTER'

    def test_register_manufacturer_without_brand_fails(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'nobrand@test.com',
            'password': STRONG_PASSWORD,
            'role': 'MANUFACTURER',
            'name': 'No Brand Corp',
            'ssm_number': 'SSMTEST002',
        })
        assert r.status_code == 400
        assert 'brand' in r.get_json()['error'].lower()

    def test_register_brand_sc_without_ssm_fails(self, client):
        """Brand (non-independent) SC registration requires a pre-registered SSM number."""
        r = client.post('/api/auth/register', json={
            'email': 'nossm@test.com',
            'password': STRONG_PASSWORD,
            'role': 'SERVICE_CENTER',
            'name': 'No SSM SC',
        })
        assert r.status_code == 400
        assert 'ssm' in r.get_json()['error'].lower()

    def test_register_owner_without_brand_succeeds(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'owner@nobrand.com',
            'password': STRONG_PASSWORD,
            'role': 'OWNER',
            'name': 'Plain Owner',
            'consent_given': True,
        })
        assert r.status_code == 200

    def test_register_owner(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'owner@test.com',
            'password': STRONG_PASSWORD,
            'role': 'OWNER',
            'name': 'John Doe',
            'consent_given': True,
        })
        assert r.status_code == 200
        assert r.get_json()['user']['role'] == 'OWNER'

    def test_register_duplicate_email(self, client):
        payload = {'email': 'dup@test.com', 'password': STRONG_PASSWORD, 'role': 'OWNER', 'name': 'A', 'consent_given': True}
        r1 = client.post('/api/auth/register', json=payload)
        assert r1.status_code == 200
        r2 = client.post('/api/auth/register', json=payload)
        assert r2.status_code in (400, 409)

    def test_register_invalid_role(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'x@test.com',
            'password': STRONG_PASSWORD,
            'role': 'ADMIN',
            'name': 'X',
        })
        assert r.status_code == 400

    def test_register_missing_email(self, client):
        r = client.post('/api/auth/register', json={
            'password': STRONG_PASSWORD,
            'role': 'OWNER',
            'name': 'X',
        })
        assert r.status_code == 400

    def test_register_weak_password(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'weak@test.com',
            'password': 'pass1234',
            'role': 'OWNER',
            'name': 'Weak User',
        })
        assert r.status_code == 400

    def test_response_has_blockchain_address(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'bc@test.com',
            'password': STRONG_PASSWORD,
            'role': 'OWNER',
            'name': 'Chain User',
            'consent_given': True,
        })
        assert r.status_code == 200
        user = r.get_json()['user']
        assert 'blockchain_address' in user
        assert user['blockchain_address'].startswith('0x')

    def test_response_has_refresh_token(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'rt@test.com',
            'password': STRONG_PASSWORD,
            'role': 'OWNER',
            'name': 'Refresh User',
            'consent_given': True,
        })
        assert r.status_code == 200
        data = r.get_json()
        assert 'refresh_token' in data


class TestLogin:
    def test_login_valid(self, client):
        client.post('/api/auth/register', json={
            'email': 'login@test.com', 'password': STRONG_PASSWORD,
            'role': 'OWNER', 'name': 'Login User', 'consent_given': True,
        })
        r = client.post('/api/auth/login', json={
            'email': 'login@test.com', 'password': STRONG_PASSWORD,
        })
        assert r.status_code == 200
        data = r.get_json()
        assert 'access_token' in data
        assert 'refresh_token' in data

    def test_login_wrong_password(self, client):
        client.post('/api/auth/register', json={
            'email': 'wrongpw@test.com', 'password': STRONG_PASSWORD,
            'role': 'OWNER', 'name': 'User',
        })
        r = client.post('/api/auth/login', json={
            'email': 'wrongpw@test.com', 'password': 'WrongPass9!',
        })
        assert r.status_code == 401

    def test_login_unknown_email(self, client):
        r = client.post('/api/auth/login', json={
            'email': 'nobody@test.com', 'password': STRONG_PASSWORD,
        })
        assert r.status_code == 401

    def test_login_increments_failed_attempts(self, client):
        client.post('/api/auth/register', json={
            'email': 'lockme@test.com', 'password': STRONG_PASSWORD,
            'role': 'OWNER', 'name': 'Lock User', 'consent_given': True,
        })
        for _ in range(3):
            client.post('/api/auth/login', json={
                'email': 'lockme@test.com', 'password': 'BadPass9!',
            })
        r = client.post('/api/auth/login', json={
            'email': 'lockme@test.com', 'password': 'BadPass9!',
        })
        assert r.status_code in (401, 423)


class TestMe:
    def test_me_with_token(self, client):
        token, user = register_and_login(client, 'MANUFACTURER')
        r = client.get('/api/auth/me', headers=auth(token))
        assert r.status_code == 200
        data = r.get_json()
        assert data['email'] == user['email']

    def test_me_without_token(self, client):
        r = client.get('/api/auth/me')
        assert r.status_code == 401

    def test_me_invalid_token(self, client):
        r = client.get('/api/auth/me', headers={'Authorization': 'Bearer invalid.token.here'})
        assert r.status_code == 401


class TestForgotPassword:
    def test_nonexistent_email_still_returns_200(self, client):
        """Anti-enumeration: always 200 regardless of whether email exists."""
        r = client.post('/api/auth/forgot-password', json={'email': 'nobody@example.com'})
        assert r.status_code == 200
        assert 'message' in r.get_json()

    def test_registered_email_also_returns_200(self, client):
        """Registered users also receive 200 — no difference observable to caller."""
        client.post('/api/auth/register', json={
            'email': 'reg@test.com', 'password': STRONG_PASSWORD,
            'role': 'OWNER', 'name': 'Reg User', 'consent_given': True,
        })
        r = client.post('/api/auth/forgot-password', json={'email': 'reg@test.com'})
        assert r.status_code == 200
        assert 'message' in r.get_json()

    def test_invalid_email_format_returns_400(self, client):
        r = client.post('/api/auth/forgot-password', json={'email': 'notanemail'})
        assert r.status_code == 400

    def test_empty_email_returns_400(self, client):
        r = client.post('/api/auth/forgot-password', json={'email': ''})
        assert r.status_code == 400

    def test_missing_email_field_returns_400(self, client):
        r = client.post('/api/auth/forgot-password', json={})
        assert r.status_code == 400

    def test_forgot_password_creates_db_token_for_registered_user(self, client, app):
        """A PasswordResetToken row must be created for a registered user."""
        client.post('/api/auth/register', json={
            'email': 'tokencreate@test.com', 'password': STRONG_PASSWORD,
            'role': 'OWNER', 'name': 'Token User', 'consent_given': True,
        })
        client.post('/api/auth/forgot-password', json={'email': 'tokencreate@test.com'})
        with app.app_context():
            from db.models import PasswordResetToken, User
            user = User.query.filter_by(email='tokencreate@test.com').first()
            token = PasswordResetToken.query.filter_by(user_id=user.id, used=False).first()
            assert token is not None

    def test_forgot_password_no_token_created_for_unknown_email(self, client, app):
        """No DB record created for an address that was never registered."""
        client.post('/api/auth/forgot-password', json={'email': 'ghost@test.com'})
        with app.app_context():
            from db.models import PasswordResetToken
            assert PasswordResetToken.query.count() == 0

    def test_second_forgot_invalidates_first_token(self, client, app):
        """Second request marks the first token as used and issues a new one."""
        client.post('/api/auth/register', json={
            'email': 'double@test.com', 'password': STRONG_PASSWORD,
            'role': 'OWNER', 'name': 'Double User', 'consent_given': True,
        })
        client.post('/api/auth/forgot-password', json={'email': 'double@test.com'})
        client.post('/api/auth/forgot-password', json={'email': 'double@test.com'})
        with app.app_context():
            from db.models import PasswordResetToken, User
            user = User.query.filter_by(email='double@test.com').first()
            # Only one active (unused) token should exist
            active = PasswordResetToken.query.filter_by(user_id=user.id, used=False).count()
            assert active == 1


class TestResetPassword:
    def _get_raw_token(self, client, app, email='reset@test.com'):
        """Register a user, trigger forgot-password, return the raw token from the DB."""
        import hashlib
        client.post('/api/auth/register', json={
            'email': email, 'password': STRONG_PASSWORD,
            'role': 'OWNER', 'name': 'Reset User', 'consent_given': True,
        })
        client.post('/api/auth/forgot-password', json={'email': email})
        with app.app_context():
            from db.models import PasswordResetToken, User
            user = User.query.filter_by(email=email).first()
            token_row = PasswordResetToken.query.filter_by(user_id=user.id, used=False).first()
            # The DB stores the hash; we need to recreate the raw token — but we can't reverse it.
            # Instead, generate a fresh known raw token and patch it directly.
            raw = 'testrawtoken_' + email
            token_row.token_hash = hashlib.sha256(raw.encode()).hexdigest()
            from db.models import db
            db.session.commit()
            return raw

    def test_valid_token_resets_password(self, client, app):
        raw = self._get_raw_token(client, app, 'vp@test.com')
        new_pw = 'NewPass99!'
        r = client.post('/api/auth/reset-password', json={'token': raw, 'new_password': new_pw})
        assert r.status_code == 200
        assert 'message' in r.get_json()

    def test_after_reset_login_with_new_password_succeeds(self, client, app):
        email = 'newlogin@test.com'
        raw = self._get_raw_token(client, app, email)
        new_pw = 'NewPass99!'
        client.post('/api/auth/reset-password', json={'token': raw, 'new_password': new_pw})
        r = client.post('/api/auth/login', json={'email': email, 'password': new_pw})
        assert r.status_code == 200

    def test_after_reset_old_password_no_longer_works(self, client, app):
        email = 'oldpw@test.com'
        raw = self._get_raw_token(client, app, email)
        client.post('/api/auth/reset-password', json={'token': raw, 'new_password': 'NewPass99!'})
        r = client.post('/api/auth/login', json={'email': email, 'password': STRONG_PASSWORD})
        assert r.status_code == 401

    def test_token_marked_used_after_reset(self, client, app):
        import hashlib
        email = 'usedtoken@test.com'
        raw = self._get_raw_token(client, app, email)
        client.post('/api/auth/reset-password', json={'token': raw, 'new_password': 'NewPass99!'})
        with app.app_context():
            from db.models import PasswordResetToken
            token_hash = hashlib.sha256(raw.encode()).hexdigest()
            t = PasswordResetToken.query.filter_by(token_hash=token_hash).first()
            assert t.used is True

    def test_used_token_cannot_be_reused(self, client, app):
        raw = self._get_raw_token(client, app, 'reuse@test.com')
        client.post('/api/auth/reset-password', json={'token': raw, 'new_password': 'NewPass99!'})
        r = client.post('/api/auth/reset-password', json={'token': raw, 'new_password': 'AnotherPass1!'})
        assert r.status_code == 400

    def test_invalid_token_returns_400(self, client):
        r = client.post('/api/auth/reset-password', json={
            'token': 'totally_fake_token', 'new_password': 'NewPass99!',
        })
        assert r.status_code == 400

    def test_missing_token_returns_400(self, client):
        r = client.post('/api/auth/reset-password', json={'new_password': 'NewPass99!'})
        assert r.status_code == 400

    def test_missing_new_password_returns_400(self, client):
        r = client.post('/api/auth/reset-password', json={'token': 'sometoken'})
        assert r.status_code == 400

    def test_weak_new_password_returns_400(self, client, app):
        raw = self._get_raw_token(client, app, 'weakpw@test.com')
        r = client.post('/api/auth/reset-password', json={'token': raw, 'new_password': 'weak'})
        assert r.status_code == 400

    def test_expired_token_returns_400(self, client, app):
        import hashlib
        from datetime import datetime, timedelta
        email = 'expired@test.com'
        raw = self._get_raw_token(client, app, email)
        with app.app_context():
            from db.models import PasswordResetToken, db
            token_hash = hashlib.sha256(raw.encode()).hexdigest()
            t = PasswordResetToken.query.filter_by(token_hash=token_hash).first()
            t.expires_at = datetime.utcnow() - timedelta(minutes=1)
            db.session.commit()
        r = client.post('/api/auth/reset-password', json={'token': raw, 'new_password': 'NewPass99!'})
        assert r.status_code == 400


class TestDeviceToken:
    def test_register_android_token(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/auth/device-token',
                        headers=auth(token),
                        json={'token': 'fcm_token_abc123', 'platform': 'android'})
        assert r.status_code == 200
        assert 'message' in r.get_json()

    def test_register_ios_token(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/auth/device-token',
                        headers=auth(token),
                        json={'token': 'apns_token_xyz789', 'platform': 'ios'})
        assert r.status_code == 200

    def test_requires_auth(self, client):
        r = client.post('/api/auth/device-token',
                        json={'token': 'fcm_abc', 'platform': 'android'})
        assert r.status_code == 401

    def test_missing_token_returns_400(self, client):
        access, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/auth/device-token',
                        headers=auth(access),
                        json={'platform': 'android'})
        assert r.status_code == 400

    def test_empty_token_returns_400(self, client):
        access, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/auth/device-token',
                        headers=auth(access),
                        json={'token': '', 'platform': 'android'})
        assert r.status_code == 400

    def test_invalid_platform_returns_400(self, client):
        access, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/auth/device-token',
                        headers=auth(access),
                        json={'token': 'fcm_abc', 'platform': 'windows'})
        assert r.status_code == 400

    def test_missing_platform_returns_400(self, client):
        access, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/auth/device-token',
                        headers=auth(access),
                        json={'token': 'fcm_abc'})
        assert r.status_code == 400

    def test_device_token_persisted_to_db(self, client, app):
        access, user = register_and_login(client, 'OWNER')
        client.post('/api/auth/device-token',
                    headers=auth(access),
                    json={'token': 'persist_test_token', 'platform': 'android'})
        with app.app_context():
            from db.models import DeviceToken
            dt = DeviceToken.query.filter_by(token='persist_test_token').first()
            assert dt is not None
            assert dt.platform == 'android'

    def test_upsert_same_platform_updates_token(self, client, app):
        access, _ = register_and_login(client, 'OWNER')
        client.post('/api/auth/device-token',
                    headers=auth(access),
                    json={'token': 'first_token', 'platform': 'android'})
        client.post('/api/auth/device-token',
                    headers=auth(access),
                    json={'token': 'updated_token', 'platform': 'android'})
        with app.app_context():
            from db.models import DeviceToken
            rows = DeviceToken.query.filter_by(platform='android').all()
            assert len(rows) == 1
            assert rows[0].token == 'updated_token'


class TestUpdateProfile:
    def test_update_name(self, client):
        token, _ = register_and_login(client, 'MANUFACTURER', name='Old Name')
        r = client.put('/api/auth/profile', headers=auth(token), json={'name': 'New Name'})
        assert r.status_code == 200
        data = r.get_json()
        assert data['user']['name'] == 'New Name'

    def test_update_phone(self, client):
        token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.put('/api/auth/profile', headers=auth(token), json={'phone': '+601234567890'})
        assert r.status_code == 200
        assert r.get_json()['user']['phone'] == '+601234567890'

    def test_update_city_and_state(self, client):
        token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.put('/api/auth/profile', headers=auth(token), json={
            'city': 'Kuala Lumpur', 'state': 'Wilayah Persekutuan'
        })
        assert r.status_code == 200
        user = r.get_json()['user']
        assert user['city'] == 'Kuala Lumpur'
        assert user['state'] == 'Wilayah Persekutuan'

    def test_partial_update_preserves_other_fields(self, client):
        token, user = register_and_login(client, 'MANUFACTURER', name='Keep Me')
        r = client.put('/api/auth/profile', headers=auth(token), json={'phone': '123'})
        assert r.status_code == 200
        assert r.get_json()['user']['name'] == 'Keep Me'

    def test_requires_auth(self, client):
        r = client.put('/api/auth/profile', json={'name': 'X'})
        assert r.status_code == 401

    def test_empty_body_is_ok(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.put('/api/auth/profile', headers=auth(token), json={})
        assert r.status_code == 200


class TestChangePassword:
    def test_successful_change(self, client):
        token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/auth/change-password', headers=auth(token), json={
            'current_password': STRONG_PASSWORD,
            'new_password': 'NewSecure9@',
        })
        assert r.status_code == 200

    def test_wrong_current_password(self, client):
        token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/auth/change-password', headers=auth(token), json={
            'current_password': 'WrongPass1!',
            'new_password': 'NewSecure9@',
        })
        assert r.status_code == 401

    def test_weak_new_password_rejected(self, client):
        token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/auth/change-password', headers=auth(token), json={
            'current_password': STRONG_PASSWORD,
            'new_password': 'weak',
        })
        assert r.status_code == 400

    def test_missing_fields_returns_400(self, client):
        token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/auth/change-password', headers=auth(token), json={
            'current_password': STRONG_PASSWORD,
        })
        assert r.status_code == 400

    def test_requires_auth(self, client):
        r = client.post('/api/auth/change-password', json={
            'current_password': STRONG_PASSWORD,
            'new_password': 'NewSecure9@',
        })
        assert r.status_code == 401
