"""Tests for /api/vehicle endpoints."""
import pytest
from conftest import register_and_login, auth

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
