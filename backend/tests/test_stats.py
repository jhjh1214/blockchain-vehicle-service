"""Tests for stats, fleet and public-verify endpoints."""
import pytest
from conftest import register_and_login, auth

VIN = '1HGCM82633A004352'


class TestManufacturerStats:
    def test_manufacturer_gets_stats(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.get('/api/vehicle/stats', headers=auth(mfr_token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'total_vehicles' in data
        assert 'sc_total' in data
        assert 'sc_active' in data
        assert 'sc_pending' in data
        assert 'warranty_claims' in data

    def test_stats_reflect_registrations(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        register_and_login(client, 'SERVICE_CENTER')

        client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'owner_email': owner['email'],
            'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })

        r = client.get('/api/vehicle/stats', headers=auth(mfr_token))
        assert r.status_code == 200
        data = r.get_json()
        assert data['total_vehicles'] >= 1
        assert data['sc_total'] >= 1

    def test_stats_count_pending_vehicles(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        # Pre-register (no owner)
        client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })
        r = client.get('/api/vehicle/stats', headers=auth(mfr_token))
        assert r.get_json()['total_vehicles'] >= 1

    def test_stats_scoped_to_manufacturer(self, client):
        mfr1_token, _ = register_and_login(client, 'MANUFACTURER')
        mfr2_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')

        client.post('/api/vehicle/register', headers=auth(mfr1_token), json={
            'vin': VIN, 'owner_email': owner['email'],
            'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })

        r1 = client.get('/api/vehicle/stats', headers=auth(mfr1_token))
        r2 = client.get('/api/vehicle/stats', headers=auth(mfr2_token))
        assert r1.get_json()['total_vehicles'] >= 1
        assert r2.get_json()['total_vehicles'] == 0

    def test_non_manufacturer_forbidden(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.get('/api/vehicle/stats', headers=auth(sc_token))
        assert r.status_code == 403

    def test_stats_unauthenticated(self, client):
        r = client.get('/api/vehicle/stats')
        assert r.status_code == 401


class TestFleet:
    def test_manufacturer_gets_empty_fleet(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.get('/api/vehicle/fleet', headers=auth(mfr_token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'vehicles' in data
        assert 'pagination' in data
        assert len(data['vehicles']) == 0

    def test_fleet_after_register_with_owner(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'owner_email': owner['email'],
            'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })
        r = client.get('/api/vehicle/fleet', headers=auth(mfr_token))
        assert r.status_code == 200
        vehicles = r.get_json()['vehicles']
        assert len(vehicles) >= 1
        assert vehicles[0]['registration_status'] == 'active'

    def test_fleet_shows_pending_vehicles(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })
        r = client.get('/api/vehicle/fleet', headers=auth(mfr_token))
        vehicles = r.get_json()['vehicles']
        assert len(vehicles) == 1
        assert vehicles[0]['registration_status'] == 'pending'

    def test_fleet_scoped_to_manufacturer(self, client):
        mfr1_token, _ = register_and_login(client, 'MANUFACTURER')
        mfr2_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')

        client.post('/api/vehicle/register', headers=auth(mfr1_token), json={
            'vin': VIN, 'owner_email': owner['email'],
            'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })

        r1 = client.get('/api/vehicle/fleet', headers=auth(mfr1_token))
        r2 = client.get('/api/vehicle/fleet', headers=auth(mfr2_token))
        assert len(r1.get_json()['vehicles']) == 1
        assert len(r2.get_json()['vehicles']) == 0

    def test_non_manufacturer_forbidden(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.get('/api/vehicle/fleet', headers=auth(sc_token))
        assert r.status_code == 403


class TestDashboardStats:
    def test_manufacturer_gets_dashboard_stats(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.get('/api/vehicle/dashboard-stats', headers=auth(mfr_token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'total_vehicles' in data
        assert 'active_warranties' in data
        assert 'warranty_claims' in data
        assert 'services_this_month' in data
        assert 'service_type_distribution' in data
        assert 'warranty_claim_trend' in data
        assert 'top_service_centers' in data

    def test_claim_trend_has_six_months(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.get('/api/vehicle/dashboard-stats', headers=auth(mfr_token))
        trend = r.get_json()['warranty_claim_trend']
        assert len(trend) == 6
        for entry in trend:
            assert 'month' in entry
            assert 'count' in entry

    def test_non_manufacturer_forbidden(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.get('/api/vehicle/dashboard-stats', headers=auth(sc_token))
        assert r.status_code == 403

    def test_dashboard_stats_unauthenticated(self, client):
        r = client.get('/api/vehicle/dashboard-stats')
        assert r.status_code == 401


class TestActivityFeed:
    def test_manufacturer_gets_empty_feed(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.get('/api/vehicle/activity-feed', headers=auth(mfr_token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'feed' in data
        assert isinstance(data['feed'], list)

    def test_feed_includes_registration(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })
        r = client.get('/api/vehicle/activity-feed', headers=auth(mfr_token))
        feed = r.get_json()['feed']
        assert any(item['type'] == 'registration' and item['vin'] == VIN for item in feed)

    def test_feed_item_has_required_fields(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })
        item = client.get('/api/vehicle/activity-feed', headers=auth(mfr_token)).get_json()['feed'][0]
        assert 'type' in item
        assert 'vin' in item
        assert 'description' in item
        assert 'timestamp' in item

    def test_non_manufacturer_forbidden(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.get('/api/vehicle/activity-feed', headers=auth(sc_token))
        assert r.status_code == 403

    def test_activity_feed_unauthenticated(self, client):
        r = client.get('/api/vehicle/activity-feed')
        assert r.status_code == 401


class TestPublicVerify:
    def test_verify_registered_vehicle(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'owner_email': owner['email'],
            'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })
        r = client.get(f'/api/vehicle/public/{VIN}')
        assert r.status_code == 200
        data = r.get_json()
        assert data['vin'] == VIN
        assert data['make'] == 'Honda'
        assert 'warranty' in data
        assert 'service_records' in data

    def test_verify_pending_vehicle(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Toyota')
        client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'Toyota', 'model': 'Corolla', 'year': 2023,
        })
        r = client.get(f'/api/vehicle/public/{VIN}')
        assert r.status_code == 200
        assert r.get_json()['make'] == 'Toyota'

    def test_verify_unregistered_vehicle(self, client):
        r = client.get('/api/vehicle/public/UNKNOWNVIN000000X')
        assert r.status_code in (400, 404)
