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


class TestBrandIsolation:
    """Manufacturer of brand A cannot see or manage SCs of brand B."""

    def test_manufacturer_only_sees_own_brand_scs(self, client):
        honda_mfr, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        toyota_mfr, _ = register_and_login(client, 'MANUFACTURER', brand='Toyota')
        register_and_login(client, 'SERVICE_CENTER', brand='Honda')
        register_and_login(client, 'SERVICE_CENTER', brand='Toyota')

        honda_list = client.get('/api/sc/service-centers', headers=auth(honda_mfr)).get_json()
        toyota_list = client.get('/api/sc/service-centers', headers=auth(toyota_mfr)).get_json()

        honda_brands = [sc['brand'] for sc in honda_list.get('items', [])]
        toyota_brands = [sc['brand'] for sc in toyota_list.get('items', [])]

        assert all(b and b.lower() == 'honda' for b in honda_brands)
        assert all(b and b.lower() == 'toyota' for b in toyota_brands)
        assert not any(b and b.lower() == 'toyota' for b in honda_brands)
        assert not any(b and b.lower() == 'honda' for b in toyota_brands)

    def test_different_brand_manufacturer_cannot_view_sc(self, client):
        _, honda_sc = register_and_login(client, 'SERVICE_CENTER', brand='Honda')
        toyota_mfr, _ = register_and_login(client, 'MANUFACTURER', brand='Toyota')

        r = client.get(f'/api/sc/service-centers/{honda_sc["id"]}', headers=auth(toyota_mfr))
        assert r.status_code == 403
        assert 'brand' in r.get_json()['error'].lower()

    def test_different_brand_manufacturer_cannot_activate_sc(self, client):
        _, honda_sc = register_and_login(client, 'SERVICE_CENTER', brand='Honda')
        toyota_mfr, _ = register_and_login(client, 'MANUFACTURER', brand='Toyota')

        r = client.post(f'/api/sc/service-centers/{honda_sc["id"]}/activate', headers=auth(toyota_mfr))
        assert r.status_code == 403

    def test_different_brand_manufacturer_cannot_suspend_sc(self, client):
        _, honda_sc = register_and_login(client, 'SERVICE_CENTER', brand='Honda')
        toyota_mfr, _ = register_and_login(client, 'MANUFACTURER', brand='Toyota')

        r = client.post(f'/api/sc/service-centers/{honda_sc["id"]}/suspend', headers=auth(toyota_mfr))
        assert r.status_code == 403

    def test_same_brand_manufacturer_can_activate_sc(self, client):
        honda_mfr, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        _, honda_sc = register_and_login(client, 'SERVICE_CENTER', brand='Honda')

        r = client.post(f'/api/sc/service-centers/{honda_sc["id"]}/activate', headers=auth(honda_mfr))
        assert r.status_code == 200
        assert r.get_json()['sc']['status'] == 'active'

    def test_fund_all_only_funds_own_brand_scs(self, client):
        honda_mfr, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        _, honda_sc = register_and_login(client, 'SERVICE_CENTER', brand='Honda')
        _, toyota_sc = register_and_login(client, 'SERVICE_CENTER', brand='Toyota')

        # Activate both SCs (Honda mfr activates Honda SC)
        client.post(f'/api/sc/service-centers/{honda_sc["id"]}/activate', headers=auth(honda_mfr))

        r = client.post('/api/sc/fund-all', headers=auth(honda_mfr), json={'amount_eth': 0.01})
        assert r.status_code == 200
        results = r.get_json()['results']
        funded_ids = [item['id'] for item in results]
        assert honda_sc['id'] in funded_ids
        assert toyota_sc['id'] not in funded_ids


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
