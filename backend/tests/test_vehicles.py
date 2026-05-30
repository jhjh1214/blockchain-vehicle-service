"""Tests for /api/vehicle endpoints."""
import time
import pytest
from conftest import register_and_login, auth, STRONG_PASSWORD

VIN = '1HGCM82633A004352'
VIN2 = '2HGCM82633A004352'

HONDA_PAYLOAD = {'make': 'Honda', 'model': 'Civic', 'year': 2024, 'warranty_years': 3}
TOYOTA_PAYLOAD = {'make': 'Toyota', 'model': 'Camry', 'year': 2024, 'warranty_years': 3}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_with_owner(client, mfr_token, owner_email, vin=VIN):
    return client.post('/api/vehicle/register', headers=auth(mfr_token), json={
        'vin': vin, 'owner_email': owner_email,
        'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
    })


def _register_pending(client, mfr_token, vin=VIN):
    """Pre-register without owner (status=pending)."""
    return client.post('/api/vehicle/register', headers=auth(mfr_token), json={
        'vin': vin,
        'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
    })


# ---------------------------------------------------------------------------
# RegisterVehicle — with owner
# ---------------------------------------------------------------------------

class TestRegisterVehicleWithOwner:
    def test_manufacturer_can_register_with_owner(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')

        r = _register_with_owner(client, mfr_token, owner['email'])
        assert r.status_code == 200
        data = r.get_json()
        assert data['vin'] == VIN
        assert data['registration_status'] == 'active'
        assert data['owner'] == owner['email']
        assert 'transaction' in data

    def test_non_manufacturer_cannot_register(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        _, owner = register_and_login(client, 'OWNER')
        r = _register_with_owner(client, sc_token, owner['email'])
        assert r.status_code == 403

    def test_register_requires_auth(self, client):
        r = client.post('/api/vehicle/register', json={
            'vin': VIN, 'owner_email': 'x@x.com',
            'warranty_years': 1, 'make': 'Honda', 'model': 'Civic', 'year': 2022,
        })
        assert r.status_code == 401

    def test_register_unknown_owner_returns_error(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = _register_with_owner(client, mfr_token, 'nobody@nowhere.com')
        assert r.status_code == 400

    def test_invalid_vin_returns_400(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': 'TOOSHORT',
            'warranty_years': 1, 'make': 'Honda', 'model': 'Civic', 'year': 2020,
        })
        assert r.status_code in (400, 500)

    def test_invalid_vin_chars_rejected(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        # VIN with forbidden char 'I'
        r = client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': 'IIIIIIIIIIIIIIIIII',
            'warranty_years': 1, 'make': 'Honda', 'model': 'Civic', 'year': 2020,
        })
        assert r.status_code in (400, 500)


# ---------------------------------------------------------------------------
# Brand enforcement
# ---------------------------------------------------------------------------

class TestBrandEnforcement:
    def test_manufacturer_cannot_register_wrong_brand(self, client):
        """Honda manufacturer cannot register a Toyota vehicle."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        r = client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'Toyota', 'model': 'Camry', 'year': 2024,
        })
        assert r.status_code == 403
        assert 'brand' in r.get_json()['error'].lower()

    def test_manufacturer_can_register_own_brand(self, client):
        """Honda manufacturer can register a Honda vehicle (case-insensitive)."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        r = client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'honda', 'model': 'Civic', 'year': 2024,
        })
        assert r.status_code == 200

    def test_manufacturer_fleet_isolated_from_other_brand(self, client):
        """Manufacturer A can only see their own vehicles."""
        mfr_a, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        mfr_b, _ = register_and_login(client, 'MANUFACTURER', brand='Toyota')

        # A registers a Honda vehicle
        client.post('/api/vehicle/register', headers=auth(mfr_a), json={
            'vin': VIN, **HONDA_PAYLOAD,
        })
        # B registers a Toyota vehicle
        client.post('/api/vehicle/register', headers=auth(mfr_b), json={
            'vin': VIN2, **TOYOTA_PAYLOAD,
        })

        fleet_a = client.get('/api/vehicle/fleet', headers=auth(mfr_a)).get_json()['vehicles']
        fleet_b = client.get('/api/vehicle/fleet', headers=auth(mfr_b)).get_json()['vehicles']

        assert any(v['vin'] == VIN for v in fleet_a)
        assert not any(v['vin'] == VIN2 for v in fleet_a)
        assert any(v['vin'] == VIN2 for v in fleet_b)
        assert not any(v['vin'] == VIN for v in fleet_b)


# ---------------------------------------------------------------------------
# RegisterVehicle — pre-register (pending, no owner)
# ---------------------------------------------------------------------------

class TestPreRegisterVehicle:
    def test_manufacturer_can_register_without_owner(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = _register_pending(client, mfr_token)
        assert r.status_code == 200
        data = r.get_json()
        assert data['vin'] == VIN
        assert data['registration_status'] == 'pending'
        assert data['owner'] is None
        assert 'transaction' in data

    def test_pending_vehicle_appears_in_fleet(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _register_pending(client, mfr_token)

        r = client.get('/api/vehicle/fleet', headers=auth(mfr_token))
        assert r.status_code == 200
        vehicles = r.get_json()['vehicles']
        assert any(v['vin'] == VIN and v['registration_status'] == 'pending' for v in vehicles)

    def test_pending_vehicle_not_in_owner_my_vehicles(self, client):
        mfr_token, mfr = register_and_login(client, 'MANUFACTURER')
        _register_pending(client, mfr_token)

        # The manufacturer's own address is placeholder owner — they're not an OWNER role user
        owner_token, _ = register_and_login(client, 'OWNER')
        r = client.get('/api/vehicle/my-vehicles', headers=auth(owner_token))
        assert r.status_code == 200
        vins = [v['vin'] for v in r.get_json()['vehicles']]
        assert VIN not in vins


# ---------------------------------------------------------------------------
# Claim vehicle
# ---------------------------------------------------------------------------

class TestClaimVehicle:
    def test_owner_can_claim_pending_vehicle(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, _ = register_and_login(client, 'OWNER')

        _register_pending(client, mfr_token)

        r = client.post('/api/vehicle/claim', headers=auth(owner_token), json={'vin': VIN})
        assert r.status_code == 200
        data = r.get_json()
        assert data['vin'] == VIN
        assert 'transaction' in data

    def test_claim_makes_vehicle_active(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, _ = register_and_login(client, 'OWNER')
        _register_pending(client, mfr_token)

        client.post('/api/vehicle/claim', headers=auth(owner_token), json={'vin': VIN})

        r = client.get('/api/vehicle/fleet', headers=auth(mfr_token))
        vehicles = r.get_json()['vehicles']
        match = next((v for v in vehicles if v['vin'] == VIN), None)
        assert match is not None
        assert match['registration_status'] == 'active'

    def test_claim_already_active_returns_409(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        owner2_token, _ = register_and_login(client, 'OWNER')

        _register_with_owner(client, mfr_token, owner['email'])

        r = client.post('/api/vehicle/claim', headers=auth(owner2_token), json={'vin': VIN})
        assert r.status_code == 409

    def test_claim_nonexistent_vin_returns_404(self, client):
        owner_token, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/vehicle/claim', headers=auth(owner_token), json={'vin': VIN})
        assert r.status_code == 404

    def test_non_owner_cannot_claim(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _register_pending(client, mfr_token)

        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.post('/api/vehicle/claim', headers=auth(sc_token), json={'vin': VIN})
        assert r.status_code == 403

    def test_claim_requires_auth(self, client):
        r = client.post('/api/vehicle/claim', json={'vin': VIN})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# GetVehicle
# ---------------------------------------------------------------------------

class TestGetVehicle:
    def test_get_vehicle_authenticated(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_with_owner(client, mfr_token, owner['email'])

        r = client.get(f'/api/vehicle/{VIN}', headers=auth(owner_token))
        assert r.status_code == 200
        data = r.get_json()
        assert data['vin'] == VIN
        assert 'warranty' in data
        assert 'registration_status' in data

    def test_get_vehicle_unauthenticated(self, client):
        r = client.get(f'/api/vehicle/{VIN}')
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# MyVehicles
# ---------------------------------------------------------------------------

class TestMyVehicles:
    def test_my_vehicles_returns_list(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.get('/api/vehicle/my-vehicles', headers=auth(token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'vehicles' in data

    def test_my_vehicles_requires_auth(self, client):
        r = client.get('/api/vehicle/my-vehicles')
        assert r.status_code == 401

    def test_my_vehicles_shows_active_after_claim(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, _ = register_and_login(client, 'OWNER')
        _register_pending(client, mfr_token)
        client.post('/api/vehicle/claim', headers=auth(owner_token), json={'vin': VIN})

        r = client.get('/api/vehicle/my-vehicles', headers=auth(owner_token))
        assert r.status_code == 200
        vins = [v['vin'] for v in r.get_json()['vehicles']]
        assert VIN in vins

    def test_my_vehicles_has_service_count_field(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, _ = register_and_login(client, 'OWNER')
        _register_pending(client, mfr_token)
        client.post('/api/vehicle/claim', headers=auth(owner_token), json={'vin': VIN})

        r = client.get('/api/vehicle/my-vehicles', headers=auth(owner_token))
        assert r.status_code == 200
        vehicles = r.get_json()['vehicles']
        assert len(vehicles) == 1
        assert 'service_count' in vehicles[0]
        assert isinstance(vehicles[0]['service_count'], int)


# ---------------------------------------------------------------------------
# TransferVehicle
# ---------------------------------------------------------------------------

class TestTransferVehicle:
    def test_owner_can_transfer_vehicle(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _, new_owner = register_and_login(client, 'OWNER')
        _register_with_owner(client, mfr_token, owner['email'])

        r = client.post('/api/vehicle/transfer', headers=auth(owner_token), json={
            'vin': VIN, 'new_owner_email': new_owner['email'],
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data['vin'] == VIN
        assert data['new_owner'] == new_owner['email']
        assert 'transaction' in data

    def test_transfer_to_unknown_user_returns_404(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_with_owner(client, mfr_token, owner['email'])

        r = client.post('/api/vehicle/transfer', headers=auth(owner_token), json={
            'vin': VIN, 'new_owner_email': 'nobody@nowhere.com',
        })
        assert r.status_code == 404

    def test_transfer_requires_auth(self, client):
        r = client.post('/api/vehicle/transfer', json={
            'vin': VIN, 'new_owner_email': 'any@any.com',
        })
        assert r.status_code == 401

    def test_transfer_missing_new_owner_email(self, client):
        owner_token, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/vehicle/transfer', headers=auth(owner_token), json={'vin': VIN})
        assert r.status_code == 400

    def test_non_owner_cannot_transfer(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.post('/api/vehicle/transfer', headers=auth(sc_token), json={
            'vin': VIN, 'new_owner_email': 'any@any.com',
        })
        assert r.status_code == 403

    def test_manufacturer_cannot_transfer(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/vehicle/transfer', headers=auth(mfr_token), json={
            'vin': VIN, 'new_owner_email': 'any@any.com',
        })
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Dashboard stats brand isolation
# ---------------------------------------------------------------------------

class TestDashboardStatsBrandIsolation:
    def test_sc_counts_scoped_to_manufacturer_brand(self, client):
        """Stats endpoint counts only SCs belonging to the requesting manufacturer's brand."""
        honda_mfr, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        register_and_login(client, 'SERVICE_CENTER', brand='Honda')
        register_and_login(client, 'SERVICE_CENTER', brand='Toyota')

        r = client.get('/api/vehicle/stats', headers=auth(honda_mfr))
        assert r.status_code == 200
        data = r.get_json()
        # Honda mfr should see 1 Honda SC, not the Toyota SC
        assert data['sc_total'] == 1
        assert data['sc_pending'] == 1

    def test_dashboard_stats_sc_counts_scoped_to_brand(self, client):
        honda_mfr, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        register_and_login(client, 'SERVICE_CENTER', brand='Honda')
        register_and_login(client, 'SERVICE_CENTER', brand='Toyota')

        r = client.get('/api/vehicle/dashboard-stats', headers=auth(honda_mfr))
        assert r.status_code == 200
        data = r.get_json()
        assert data['sc_total'] == 1
        assert data['sc_pending'] == 1

    def test_activity_feed_shows_only_own_registrations(self, client):
        """Activity feed only includes vehicles registered by the requesting manufacturer."""
        honda_mfr, _ = register_and_login(client, 'MANUFACTURER', brand='Honda')
        toyota_mfr, _ = register_and_login(client, 'MANUFACTURER', brand='Toyota')

        # Honda registers VIN; Toyota registers VIN2
        client.post('/api/vehicle/register', headers=auth(honda_mfr), json={
            'vin': VIN, **HONDA_PAYLOAD,
        })
        client.post('/api/vehicle/register', headers=auth(toyota_mfr), json={
            'vin': VIN2, **TOYOTA_PAYLOAD,
        })

        honda_feed = client.get('/api/vehicle/activity-feed', headers=auth(honda_mfr)).get_json()['feed']
        toyota_feed = client.get('/api/vehicle/activity-feed', headers=auth(toyota_mfr)).get_json()['feed']

        honda_vins = [e['vin'] for e in honda_feed if e['type'] == 'registration']
        toyota_vins = [e['vin'] for e in toyota_feed if e['type'] == 'registration']

        assert VIN in honda_vins
        assert VIN2 not in honda_vins
        assert VIN2 in toyota_vins
        assert VIN not in toyota_vins


# ---------------------------------------------------------------------------
# Transfer recipient must be OWNER role
# ---------------------------------------------------------------------------

class TestTransferRoleEnforcement:
    def test_cannot_transfer_to_manufacturer(self, client):
        mfr_token, mfr = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_with_owner(client, mfr_token, owner['email'])

        # Try to transfer to the manufacturer's email
        r = client.post('/api/vehicle/transfer', headers=auth(owner_token), json={
            'vin': VIN, 'new_owner_email': mfr['email'],
        })
        assert r.status_code == 400
        assert 'owner' in r.get_json()['error'].lower()

    def test_cannot_transfer_to_service_center(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _, sc = register_and_login(client, 'SERVICE_CENTER')
        _register_with_owner(client, mfr_token, owner['email'])

        r = client.post('/api/vehicle/transfer', headers=auth(owner_token), json={
            'vin': VIN, 'new_owner_email': sc['email'],
        })
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Warranty claim ownership enforcement
# ---------------------------------------------------------------------------

class TestWarrantyClaimOwnership:
    def test_owner_can_claim_own_vehicle_warranty(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_with_owner(client, mfr_token, owner['email'])

        r = client.post('/api/warranty/submit-claim', headers=auth(owner_token), json={
            'vin': VIN, 'issue_description': 'Engine makes noise',
        })
        assert r.status_code == 200

    def test_owner_cannot_claim_warranty_for_unowned_vehicle(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, other_owner = register_and_login(client, 'OWNER')
        intruder_token, _ = register_and_login(client, 'OWNER')
        _register_with_owner(client, mfr_token, other_owner['email'])

        r = client.post('/api/warranty/submit-claim', headers=auth(intruder_token), json={
            'vin': VIN, 'issue_description': 'Fake claim on someone else\'s car',
        })
        assert r.status_code == 400
        assert 'own' in r.get_json()['error'].lower()


# ---------------------------------------------------------------------------
# Intended owner reservation for pending vehicles
# ---------------------------------------------------------------------------

class TestIntendedOwner:
    def test_intended_owner_can_claim(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')

        # Pre-register with intended_owner_email
        client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
            'intended_owner_email': owner['email'],
        })

        r = client.post('/api/vehicle/claim', headers=auth(owner_token), json={'vin': VIN})
        assert r.status_code == 200

    def test_wrong_owner_cannot_claim_reserved_vehicle(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, intended_owner = register_and_login(client, 'OWNER')
        intruder_token, _ = register_and_login(client, 'OWNER')

        client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
            'intended_owner_email': intended_owner['email'],
        })

        r = client.post('/api/vehicle/claim', headers=auth(intruder_token), json={'vin': VIN})
        assert r.status_code == 409
        assert 'reserved' in r.get_json()['error'].lower()

    def test_unreserved_pending_vehicle_claimable_by_any_owner(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, _ = register_and_login(client, 'OWNER')

        client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })

        r = client.post('/api/vehicle/claim', headers=auth(owner_token), json={'vin': VIN})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Vehicle detail owner email privacy
# ---------------------------------------------------------------------------

class TestVehicleDetailPrivacy:
    def test_owner_sees_own_email_in_vehicle_detail(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_with_owner(client, mfr_token, owner['email'])

        r = client.get(f'/api/vehicle/{VIN}', headers=auth(owner_token))
        assert r.status_code == 200
        assert r.get_json()['owner']['email'] == owner['email']

    def test_sc_does_not_see_owner_email(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        _register_with_owner(client, mfr_token, owner['email'])

        r = client.get(f'/api/vehicle/{VIN}', headers=auth(sc_token))
        assert r.status_code == 200
        assert 'email' not in r.get_json()['owner']

    def test_manufacturer_does_not_see_owner_email(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_with_owner(client, mfr_token, owner['email'])

        r = client.get(f'/api/vehicle/{VIN}', headers=auth(mfr_token))
        assert r.status_code == 200
        assert 'email' not in r.get_json()['owner']


# ---------------------------------------------------------------------------
# /my-vehicles role enforcement
# ---------------------------------------------------------------------------

class TestMyVehiclesRoleEnforcement:
    def test_manufacturer_cannot_use_my_vehicles(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.get('/api/vehicle/my-vehicles', headers=auth(mfr_token))
        assert r.status_code == 403

    def test_sc_cannot_use_my_vehicles(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.get('/api/vehicle/my-vehicles', headers=auth(sc_token))
        assert r.status_code == 403


# ===========================================================================
# Vehicle detail service stats (from test_new_features.py)
# ===========================================================================

TODAY_VEHICLE = time.strftime('%Y-%m-%dT%H:%M:%S')


def _activate_sc_vehicle(client, mfr_token, sc_user):
    client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(mfr_token))
    fresh = client.post('/api/auth/login',
                        json={'email': sc_user['email'], 'password': STRONG_PASSWORD})
    return fresh.get_json()['access_token']


class TestVehicleDetailServiceStats:
    def test_vehicle_detail_includes_service_stat_keys(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_with_owner(client, mfr_token, owner['email'])
        r = client.get(f'/api/vehicle/{VIN}', headers=auth(owner_token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'last_service_date' in data
        assert 'days_since_service' in data
        assert 'last_service_mileage' in data

    def test_service_stats_null_when_no_service_exists(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_with_owner(client, mfr_token, owner['email'])
        r = client.get(f'/api/vehicle/{VIN}', headers=auth(owner_token))
        data = r.get_json()
        assert data['last_service_date'] is None
        assert data['days_since_service'] is None
        assert data['last_service_mileage'] is None

    def test_service_stats_populated_after_service_submitted(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_with_owner(client, mfr_token, owner['email'])
        sc_token = _activate_sc_vehicle(client, mfr_token, sc_user)

        client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Oil Change',
            'service_date': TODAY_VEHICLE, 'mileage': 8000,
        })

        r = client.get(f'/api/vehicle/{VIN}', headers=auth(owner_token))
        data = r.get_json()
        assert data['last_service_date'] is not None
        assert data['days_since_service'] is not None
        assert data['last_service_mileage'] == 8000

    def test_days_since_service_is_non_negative(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_with_owner(client, mfr_token, owner['email'])
        sc_token = _activate_sc_vehicle(client, mfr_token, sc_user)

        client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Brake Check',
            'service_date': TODAY_VEHICLE, 'mileage': 12000,
        })

        r = client.get(f'/api/vehicle/{VIN}', headers=auth(owner_token))
        days = r.get_json()['days_since_service']
        assert days >= 0

    def test_service_count_in_vehicle_detail(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_with_owner(client, mfr_token, owner['email'])
        r = client.get(f'/api/vehicle/{VIN}', headers=auth(owner_token))
        assert 'service_count' in r.get_json()
