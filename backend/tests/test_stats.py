"""Tests for stats and fleet endpoints."""
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

    def test_non_manufacturer_forbidden(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.get('/api/vehicle/stats', headers=auth(sc_token))
        assert r.status_code == 403

    def test_stats_unauthenticated(self, client):
        r = client.get('/api/vehicle/stats')
        assert r.status_code == 401


class TestFleet:
    def test_manufacturer_gets_fleet(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        r = client.get('/api/vehicle/fleet', headers=auth(mfr_token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'vehicles' in data
        assert 'pagination' in data

    def test_fleet_after_register(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        client.post('/api/vehicle/register', headers=auth(mfr_token), json={
            'vin': VIN, 'owner_email': owner['email'],
            'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
        })
        r = client.get('/api/vehicle/fleet', headers=auth(mfr_token))
        assert r.status_code == 200
        assert len(r.get_json()['vehicles']) >= 1

    def test_non_manufacturer_forbidden(self, client):
        sc_token, _ = register_and_login(client, 'SERVICE_CENTER')
        r = client.get('/api/vehicle/fleet', headers=auth(sc_token))
        assert r.status_code == 403


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

    def test_verify_unregistered_vehicle(self, client):
        r = client.get('/api/vehicle/public/UNKNOWNVIN000000X')
        assert r.status_code in (400, 404)
