"""Tests for /api/auth/profile and /api/auth/change-password endpoints."""
import pytest
from conftest import register_and_login, auth, STRONG_PASSWORD


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
