"""Tests for stats, fleet and public-verify endpoints."""
import time
import pytest
from conftest import register_and_login, auth, STRONG_PASSWORD

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


# ===========================================================================
# New features: dashboard, fleet stats, PDF export, public verify enrichment
# (from test_new_features.py)
# ===========================================================================

TODAY_STATS = time.strftime('%Y-%m-%dT%H:%M:%S')


def _register_vehicle_stats(client, mfr_token, owner_email=None, vin=VIN):
    payload = {'vin': vin, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024}
    if owner_email:
        payload['owner_email'] = owner_email
    return client.post('/api/vehicle/register', headers=auth(mfr_token), json=payload)


def _activate_sc_stats(client, mfr_token, sc_user):
    client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(mfr_token))
    fresh = client.post('/api/auth/login',
                        json={'email': sc_user['email'], 'password': STRONG_PASSWORD})
    return fresh.get_json()['access_token']


# ---------------------------------------------------------------------------
# Dashboard stats — fleet_health_score and manufacturer_eth_balance
# ---------------------------------------------------------------------------

class TestDashboardStatsNewFields:
    def test_fleet_health_score_present(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.get('/api/vehicle/dashboard-stats', headers=auth(mfr_token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'fleet_health_score' in data
        assert isinstance(data['fleet_health_score'], (int, float))

    def test_fleet_health_score_range(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.get('/api/vehicle/dashboard-stats', headers=auth(mfr_token))
        score = r.get_json()['fleet_health_score']
        assert 0 <= score <= 100

    def test_fleet_health_score_zero_with_no_vehicles(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.get('/api/vehicle/dashboard-stats', headers=auth(mfr_token))
        assert r.get_json()['fleet_health_score'] == 0

    def test_manufacturer_eth_balance_field_present(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.get('/api/vehicle/dashboard-stats', headers=auth(mfr_token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'manufacturer_eth_balance' in data

    def test_manufacturer_eth_balance_is_number_or_null(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.get('/api/vehicle/dashboard-stats', headers=auth(mfr_token))
        bal = r.get_json()['manufacturer_eth_balance']
        assert bal is None or isinstance(bal, (int, float))

    def test_fleet_health_increases_with_active_warranty(self, client):
        """Registering a vehicle with active warranty raises fleet_health_score above 0."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle_stats(client, mfr_token, owner_email=owner['email'])

        r = client.get('/api/vehicle/dashboard-stats', headers=auth(mfr_token))
        score = r.get_json()['fleet_health_score']
        # With one active-warranty vehicle and no recent service: score = 50
        assert score > 0


# ---------------------------------------------------------------------------
# Fleet endpoint — service stats columns
# ---------------------------------------------------------------------------

class TestFleetServiceStats:
    def test_fleet_vehicle_has_service_count(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle_stats(client, mfr_token, owner_email=owner['email'])

        r = client.get('/api/vehicle/fleet', headers=auth(mfr_token))
        assert r.status_code == 200
        vehicle = r.get_json()['vehicles'][0]
        assert 'service_count' in vehicle
        assert isinstance(vehicle['service_count'], int)

    def test_fleet_vehicle_has_days_since_service(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle_stats(client, mfr_token, owner_email=owner['email'])

        r = client.get('/api/vehicle/fleet', headers=auth(mfr_token))
        vehicle = r.get_json()['vehicles'][0]
        assert 'days_since_service' in vehicle

    def test_fleet_vehicle_has_last_service_date(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle_stats(client, mfr_token, owner_email=owner['email'])

        r = client.get('/api/vehicle/fleet', headers=auth(mfr_token))
        vehicle = r.get_json()['vehicles'][0]
        assert 'last_service_date' in vehicle

    def test_fleet_service_count_increments_after_service(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle_stats(client, mfr_token, owner_email=owner['email'])
        sc_token = _activate_sc_stats(client, mfr_token, sc_user)

        client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Oil Change',
            'service_date': TODAY_STATS, 'mileage': 5000,
        })

        r = client.get('/api/vehicle/fleet', headers=auth(mfr_token))
        vehicle = r.get_json()['vehicles'][0]
        assert vehicle['service_count'] >= 1


# ---------------------------------------------------------------------------
# PDF export endpoint
# ---------------------------------------------------------------------------

class TestPdfExport:
    def test_export_returns_pdf_for_registered_vehicle(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle_stats(client, mfr_token, owner_email=owner['email'])

        r = client.get(f'/api/vehicle/export/{VIN}')
        assert r.status_code == 200
        assert r.content_type == 'application/pdf'

    def test_export_content_disposition_header(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle_stats(client, mfr_token, owner_email=owner['email'])

        r = client.get(f'/api/vehicle/export/{VIN}')
        assert r.status_code == 200
        assert 'attachment' in r.headers.get('Content-Disposition', '')

    def test_export_returns_404_for_unknown_vin(self, client):
        r = client.get('/api/vehicle/export/UNKNOWNVIN000000X')
        assert r.status_code in (400, 404)

    def test_export_returns_400_for_invalid_vin(self, client):
        r = client.get('/api/vehicle/export/BAD')
        assert r.status_code == 400

    def test_export_is_public_no_auth_needed(self, client):
        """PDF export is a public endpoint — no auth token required."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _register_vehicle_stats(client, mfr_token)
        r = client.get(f'/api/vehicle/export/{VIN}')
        # Pending vehicle (no owner) should still work
        assert r.status_code == 200

    def test_export_pdf_has_non_zero_content(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle_stats(client, mfr_token, owner_email=owner['email'])

        r = client.get(f'/api/vehicle/export/{VIN}')
        assert r.status_code == 200
        assert len(r.data) > 1000  # A PDF should be at least ~1KB


# ---------------------------------------------------------------------------
# Public verify — enriched service records
# ---------------------------------------------------------------------------

class TestPublicVerifyEnrichment:
    def _setup_with_service(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle_stats(client, mfr_token, owner_email=owner['email'])
        sc_token = _activate_sc_stats(client, mfr_token, sc_user)
        client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Brake Service',
            'service_date': TODAY_STATS, 'mileage': 12000,
        })
        return mfr_token

    def test_public_verify_returns_200(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle_stats(client, mfr_token, owner_email=owner['email'])
        r = client.get(f'/api/vehicle/public/{VIN}')
        assert r.status_code == 200

    def test_public_verify_has_service_records_key(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle_stats(client, mfr_token, owner_email=owner['email'])
        r = client.get(f'/api/vehicle/public/{VIN}')
        assert 'service_records' in r.get_json()

    def test_public_verify_service_records_have_record_index(self, client):
        """service_records returned by public verify must include record_index."""
        from blockchain.adapters.service_log import service_log as sl
        sl.get_finalized_services.return_value = [{
            'metadata_hash': '0x' + 'ab' * 32,
            'verified': True,
            'disputed': False,
            'service_center': '0x' + '01' * 20,
        }]
        try:
            mfr_token, _ = register_and_login(client, 'MANUFACTURER')
            _, owner = register_and_login(client, 'OWNER')
            _register_vehicle_stats(client, mfr_token, owner_email=owner['email'])
            r = client.get(f'/api/vehicle/public/{VIN}')
            data = r.get_json()
            if data.get('service_records'):
                assert 'record_index' in data['service_records'][0]
        finally:
            sl.get_finalized_services.return_value = []

    def test_public_verify_no_auth_required(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _register_vehicle_stats(client, mfr_token)
        r = client.get(f'/api/vehicle/public/{VIN}')
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Manufacturer dashboard — sc_pending field
# ---------------------------------------------------------------------------

class TestDashboardSCPending:
    def test_dashboard_stats_includes_sc_pending(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.get('/api/vehicle/dashboard-stats', headers=auth(mfr_token))
        assert r.status_code == 200
        assert 'sc_pending' in r.get_json()

    def test_sc_pending_is_zero_with_no_service_centers(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.get('/api/vehicle/dashboard-stats', headers=auth(mfr_token))
        assert r.get_json()['sc_pending'] == 0

    def test_sc_pending_increments_when_sc_registers(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        register_and_login(client, 'SERVICE_CENTER')  # brand=Honda (same as mfr default)
        r = client.get('/api/vehicle/dashboard-stats', headers=auth(mfr_token))
        assert r.get_json()['sc_pending'] >= 1

    def test_sc_pending_decreases_after_activation(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        before = client.get('/api/vehicle/dashboard-stats',
                            headers=auth(mfr_token)).get_json()['sc_pending']
        client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate',
                    headers=auth(mfr_token))
        after = client.get('/api/vehicle/dashboard-stats',
                           headers=auth(mfr_token)).get_json()['sc_pending']
        assert after < before
