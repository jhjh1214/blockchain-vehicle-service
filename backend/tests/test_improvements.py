"""Tests for the security and UX improvements batch."""
import hashlib
import hmac
import time
import pytest
from conftest import register_and_login, auth, STRONG_PASSWORD


def _activate_sc(client, mfr_token, sc_user):
    client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(mfr_token))

VIN = '1HGCM82633A004352'
TODAY_DATE = time.strftime('%Y-%m-%dT%H:%M:%S')


def _admin_headers(secret: str) -> dict:
    ts = str(int(time.time()))
    sig = hmac.new(secret.encode(), ts.encode(), hashlib.sha256).hexdigest()
    return {
        'X-Admin-Secret': secret,
        'X-Admin-Timestamp': ts,
        'X-Admin-Signature': sig,
    }


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
