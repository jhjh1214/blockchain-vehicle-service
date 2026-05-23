"""Tests for /api/sc SC management endpoints."""
import pytest
from conftest import register_and_login, auth


def _register_sc(client, email=None, name='Test SC'):
    token, user = register_and_login(client, 'SERVICE_CENTER', email=email, name=name)
    return token, user


class TestListServiceCenters:
    def test_manufacturer_can_list(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _register_sc(client)
        r = client.get('/api/sc/service-centers', headers=auth(mfr_token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'items' in data or 'pagination' in data

    def test_non_manufacturer_forbidden(self, client):
        sc_token, _ = _register_sc(client)
        r = client.get('/api/sc/service-centers', headers=auth(sc_token))
        assert r.status_code == 403

    def test_unauthenticated_forbidden(self, client):
        r = client.get('/api/sc/service-centers')
        assert r.status_code == 401

    def test_filter_by_status(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _register_sc(client)
        r = client.get('/api/sc/service-centers?status=pending', headers=auth(mfr_token))
        assert r.status_code == 200

    def test_search_filter(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _register_sc(client, name='Speedfix Auto')
        r = client.get('/api/sc/service-centers?search=speedfix', headers=auth(mfr_token))
        assert r.status_code == 200


class TestGetServiceCenter:
    def test_get_existing_sc(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, sc_user = _register_sc(client)
        r = client.get(f'/api/sc/service-centers/{sc_user["id"]}', headers=auth(mfr_token))
        assert r.status_code == 200
        assert r.get_json()['id'] == sc_user['id']

    def test_get_nonexistent_sc(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.get('/api/sc/service-centers/99999', headers=auth(mfr_token))
        assert r.status_code == 404


class TestActivateSuspendSC:
    def test_activate_pending_sc(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, sc_user = _register_sc(client)
        r = client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(mfr_token))
        assert r.status_code == 200
        assert r.get_json()['sc']['status'] == 'active'

    def test_suspend_sc(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, sc_user = _register_sc(client)
        client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(mfr_token))
        r = client.post(f'/api/sc/service-centers/{sc_user["id"]}/suspend', headers=auth(mfr_token))
        assert r.status_code == 200
        assert r.get_json()['sc']['status'] == 'suspended'

    def test_non_manufacturer_cannot_activate(self, client):
        _, sc_user = _register_sc(client)
        sc2_token, _ = _register_sc(client)
        r = client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(sc2_token))
        assert r.status_code == 403

    def test_activate_nonexistent_sc(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/sc/service-centers/99999/activate', headers=auth(mfr_token))
        assert r.status_code == 404


class TestSCStats:
    def test_sc_can_get_stats(self, client):
        sc_token, _ = _register_sc(client)
        r = client.get('/api/sc/my-stats', headers=auth(sc_token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'services_submitted' in data
        assert 'eth_balance' in data

    def test_unauthenticated_cannot_get_stats(self, client):
        r = client.get('/api/sc/my-stats')
        assert r.status_code == 401
