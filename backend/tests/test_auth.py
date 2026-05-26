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
        })
        assert r.status_code == 200
        data = r.get_json()
        assert 'access_token' in data
        assert data['user']['role'] == 'MANUFACTURER'
        assert data['user']['email'] == 'mfr@test.com'
        assert data['user']['brand'] == 'Honda'

    def test_register_service_center(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'sc@test.com',
            'password': STRONG_PASSWORD,
            'role': 'SERVICE_CENTER',
            'name': 'Best Auto',
            'brand': 'Honda',
        })
        assert r.status_code == 200
        assert r.get_json()['user']['role'] == 'SERVICE_CENTER'
        assert r.get_json()['user']['brand'] == 'Honda'

    def test_register_manufacturer_without_brand_fails(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'nobrand@test.com',
            'password': STRONG_PASSWORD,
            'role': 'MANUFACTURER',
            'name': 'No Brand Corp',
        })
        assert r.status_code == 400
        assert 'brand' in r.get_json()['error'].lower()

    def test_register_sc_without_brand_fails(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'nobrandsc@test.com',
            'password': STRONG_PASSWORD,
            'role': 'SERVICE_CENTER',
            'name': 'No Brand SC',
        })
        assert r.status_code == 400
        assert 'brand' in r.get_json()['error'].lower()

    def test_register_owner_without_brand_succeeds(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'owner@nobrand.com',
            'password': STRONG_PASSWORD,
            'role': 'OWNER',
            'name': 'Plain Owner',
        })
        assert r.status_code == 200

    def test_register_owner(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'owner@test.com',
            'password': STRONG_PASSWORD,
            'role': 'OWNER',
            'name': 'John Doe',
        })
        assert r.status_code == 200
        assert r.get_json()['user']['role'] == 'OWNER'

    def test_register_duplicate_email(self, client):
        payload = {'email': 'dup@test.com', 'password': STRONG_PASSWORD, 'role': 'OWNER', 'name': 'A'}
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
        })
        assert r.status_code == 200
        data = r.get_json()
        assert 'refresh_token' in data


class TestLogin:
    def test_login_valid(self, client):
        client.post('/api/auth/register', json={
            'email': 'login@test.com', 'password': STRONG_PASSWORD,
            'role': 'OWNER', 'name': 'Login User',
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
            'role': 'OWNER', 'name': 'Lock User',
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
