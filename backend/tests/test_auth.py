"""Tests for /api/auth endpoints."""
import pytest
from conftest import register_and_login, auth


class TestRegister:
    def test_register_manufacturer(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'mfr@test.com',
            'password': 'pass1234',
            'role': 'MANUFACTURER',
            'name': 'Honda Corp',
        })
        assert r.status_code == 200
        data = r.get_json()
        assert 'token' in data
        assert data['user']['role'] == 'MANUFACTURER'
        assert data['user']['email'] == 'mfr@test.com'

    def test_register_service_center(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'sc@test.com',
            'password': 'pass1234',
            'role': 'SERVICE_CENTER',
            'name': 'Best Auto',
        })
        assert r.status_code == 200
        assert r.get_json()['user']['role'] == 'SERVICE_CENTER'

    def test_register_owner(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'owner@test.com',
            'password': 'pass1234',
            'role': 'OWNER',
            'name': 'John Doe',
        })
        assert r.status_code == 200
        assert r.get_json()['user']['role'] == 'OWNER'

    def test_register_duplicate_email(self, client):
        payload = {'email': 'dup@test.com', 'password': 'pass', 'role': 'OWNER', 'name': 'A'}
        client.post('/api/auth/register', json=payload)
        r = client.post('/api/auth/register', json=payload)
        assert r.status_code in (400, 409)

    def test_register_invalid_role(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'x@test.com',
            'password': 'pass',
            'role': 'ADMIN',
            'name': 'X',
        })
        assert r.status_code == 400

    def test_register_missing_email(self, client):
        r = client.post('/api/auth/register', json={
            'password': 'pass',
            'role': 'OWNER',
            'name': 'X',
        })
        assert r.status_code == 400

    def test_response_has_blockchain_address(self, client):
        r = client.post('/api/auth/register', json={
            'email': 'bc@test.com',
            'password': 'pass1234',
            'role': 'OWNER',
            'name': 'Chain User',
        })
        assert r.status_code == 200
        user = r.get_json()['user']
        assert 'blockchain_address' in user
        assert user['blockchain_address'].startswith('0x')


class TestLogin:
    def test_login_valid(self, client):
        client.post('/api/auth/register', json={
            'email': 'login@test.com', 'password': 'pass1234',
            'role': 'OWNER', 'name': 'Login User',
        })
        r = client.post('/api/auth/login', json={
            'email': 'login@test.com', 'password': 'pass1234',
        })
        assert r.status_code == 200
        assert 'token' in r.get_json()

    def test_login_wrong_password(self, client):
        client.post('/api/auth/register', json={
            'email': 'wrongpw@test.com', 'password': 'correct',
            'role': 'OWNER', 'name': 'User',
        })
        r = client.post('/api/auth/login', json={
            'email': 'wrongpw@test.com', 'password': 'wrong',
        })
        assert r.status_code == 401

    def test_login_unknown_email(self, client):
        r = client.post('/api/auth/login', json={
            'email': 'nobody@test.com', 'password': 'pass',
        })
        assert r.status_code == 401


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
