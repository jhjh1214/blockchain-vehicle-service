"""Tests for /api/vehicle endpoints."""
import pytest
from conftest import register_and_login, auth

VIN = '1HGCM82633A004352'


class TestRegisterVehicle:
    def test_manufacturer_can_register(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')

        r = client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN,
            'owner_email': owner['email'],
            'warranty_years': 3,
            'make': 'Honda',
            'model': 'Civic',
            'year': 2024,
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data['vin'] == VIN
        assert 'transaction' in data

    def test_non_manufacturer_cannot_register(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        _, owner = register_and_login(client, 'OWNER')

        r = client.post('/api/vehicle/register', headers=auth(sc_token), json={
            'vin': VIN,
            'owner_email': owner['email'],
            'warranty_years': 2,
            'make': 'Toyota',
            'model': 'Corolla',
            'year': 2023,
        })
        assert r.status_code == 403

    def test_register_requires_auth(self, client):
        r = client.post('/api/vehicle/register', json={
            'vin': VIN, 'owner_email': 'x@x.com',
            'warranty_years': 1, 'make': 'BMW', 'model': 'X5', 'year': 2022,
        })
        assert r.status_code == 401

    def test_register_unknown_owner_returns_error(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN,
            'owner_email': 'nobody@nowhere.com',
            'warranty_years': 3,
            'make': 'Ford',
            'model': 'Focus',
            'year': 2021,
        })
        assert r.status_code == 400

    def test_invalid_vin_length(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        r = client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': 'TOOSHORT',
            'owner_email': owner['email'],
            'warranty_years': 1,
            'make': 'X', 'model': 'Y', 'year': 2020,
        })
        assert r.status_code in (400, 500)


class TestGetVehicle:
    def test_get_vehicle_authenticated(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')

        client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'owner_email': owner['email'],
            'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })

        r = client.get(f'/api/vehicle/{VIN}', headers=auth(owner_token))
        assert r.status_code == 200
        data = r.get_json()
        assert data['vin'] == VIN
        assert 'warranty' in data
        assert 'service_hashes' in data

    def test_get_vehicle_unauthenticated(self, client):
        r = client.get(f'/api/vehicle/{VIN}')
        assert r.status_code == 401


class TestMyVehicles:
    def test_my_vehicles_returns_list(self, client):
        token, _ = register_and_login(client, 'OWNER')
        r = client.get('/api/vehicle/my-vehicles', headers=auth(token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'vehicles' in data or isinstance(data, list)

    def test_my_vehicles_requires_auth(self, client):
        r = client.get('/api/vehicle/my-vehicles')
        assert r.status_code == 401
