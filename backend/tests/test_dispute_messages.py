"""Tests for in-app dispute messaging endpoints:
  GET  /api/service/dispute-messages/<vin>/<record_index>
  POST /api/service/dispute-messages
"""
import time
import pytest
from conftest import register_and_login, auth, STRONG_PASSWORD

VIN   = '1HGCM82633A004352'
TODAY = time.strftime('%Y-%m-%dT%H:%M:%S')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_vehicle(client, mfr_token, owner_email):
    return client.post('/api/vehicle/register', headers=auth(mfr_token), json={
        'vin': VIN, 'warranty_years': 3,
        'make': 'Honda', 'model': 'Civic', 'year': 2024,
        'owner_email': owner_email,
    })


def _activate_sc(client, mfr_token, sc_user):
    client.post(f'/api/sc/service-centers/{sc_user["id"]}/activate', headers=auth(mfr_token))
    fresh = client.post('/api/auth/login',
                        json={'email': sc_user['email'], 'password': STRONG_PASSWORD})
    return fresh.get_json()['access_token']


def _setup_full(client):
    """Return (mfr_token, owner_token, sc_token, mfr_user, owner_user, sc_user)."""
    mfr_token,   mfr_user   = register_and_login(client, 'MANUFACTURER')
    owner_token, owner_user = register_and_login(client, 'OWNER')
    _,           sc_user    = register_and_login(client, 'SERVICE_CENTER')
    _register_vehicle(client, mfr_token, owner_user['email'])
    sc_token = _activate_sc(client, mfr_token, sc_user)
    # Submit a service record so the SC has a row in ServiceMetadata for VIN
    client.post('/api/service/submit', headers=auth(sc_token), json={
        'vin': VIN, 'service_type': 'Oil Change',
        'service_date': TODAY, 'mileage': 5000,
    })
    return mfr_token, owner_token, sc_token, mfr_user, owner_user, sc_user


# ---------------------------------------------------------------------------
# GET dispute-messages
# ---------------------------------------------------------------------------

class TestGetDisputeMessages:
    def test_owner_can_get_empty_thread(self, client):
        _, owner_token, _, _, _, _ = _setup_full(client)
        r = client.get(f'/api/service/dispute-messages/{VIN}/0',
                       headers=auth(owner_token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'messages' in data
        assert data['messages'] == []

    def test_manufacturer_can_get_thread(self, client):
        mfr_token, _, _, _, _, _ = _setup_full(client)
        r = client.get(f'/api/service/dispute-messages/{VIN}/0',
                       headers=auth(mfr_token))
        assert r.status_code == 200
        assert 'messages' in r.get_json()

    def test_sc_can_get_thread(self, client):
        _, _, sc_token, _, _, _ = _setup_full(client)
        r = client.get(f'/api/service/dispute-messages/{VIN}/0',
                       headers=auth(sc_token))
        assert r.status_code == 200

    def test_unauthenticated_returns_401(self, client):
        _setup_full(client)
        r = client.get(f'/api/service/dispute-messages/{VIN}/0')
        assert r.status_code == 401

    def test_unrelated_owner_cannot_access(self, client):
        _setup_full(client)
        other_token, _ = register_and_login(client, 'OWNER')
        r = client.get(f'/api/service/dispute-messages/{VIN}/0',
                       headers=auth(other_token))
        assert r.status_code == 403

    def test_invalid_vin_returns_400(self, client):
        _, owner_token, _, _, _, _ = _setup_full(client)
        r = client.get('/api/service/dispute-messages/BADVIN/0',
                       headers=auth(owner_token))
        assert r.status_code == 400

    def test_messages_ordered_by_created_at(self, client):
        _, owner_token, _, _, _, _ = _setup_full(client)
        for msg in ('First message', 'Second message', 'Third message'):
            client.post('/api/service/dispute-messages',
                        headers=auth(owner_token),
                        json={'vin': VIN, 'record_index': 0, 'message': msg})
        r = client.get(f'/api/service/dispute-messages/{VIN}/0',
                       headers=auth(owner_token))
        messages = r.get_json()['messages']
        assert len(messages) == 3
        assert messages[0]['message'] == 'First message'
        assert messages[2]['message'] == 'Third message'


# ---------------------------------------------------------------------------
# POST dispute-messages
# ---------------------------------------------------------------------------

class TestPostDisputeMessage:
    def test_owner_can_post_message(self, client):
        _, owner_token, _, _, _, _ = _setup_full(client)
        r = client.post('/api/service/dispute-messages',
                        headers=auth(owner_token),
                        json={'vin': VIN, 'record_index': 0, 'message': 'I dispute this.'})
        assert r.status_code == 201
        data = r.get_json()
        assert data['message'] == 'I dispute this.'
        assert data['sender_role'] == 'OWNER'

    def test_sc_can_post_message(self, client):
        _, _, sc_token, _, _, _ = _setup_full(client)
        r = client.post('/api/service/dispute-messages',
                        headers=auth(sc_token),
                        json={'vin': VIN, 'record_index': 0, 'message': 'Rebuttal from SC.'})
        assert r.status_code == 201
        assert r.get_json()['sender_role'] == 'SERVICE_CENTER'

    def test_manufacturer_can_post_message(self, client):
        mfr_token, _, _, _, _, _ = _setup_full(client)
        r = client.post('/api/service/dispute-messages',
                        headers=auth(mfr_token),
                        json={'vin': VIN, 'record_index': 0, 'message': 'Resolution: claim valid.'})
        assert r.status_code == 201
        assert r.get_json()['sender_role'] == 'MANUFACTURER'

    def test_unauthenticated_returns_401(self, client):
        _setup_full(client)
        r = client.post('/api/service/dispute-messages',
                        json={'vin': VIN, 'record_index': 0, 'message': 'No auth.'})
        assert r.status_code == 401

    def test_unrelated_owner_cannot_post(self, client):
        _setup_full(client)
        other_token, _ = register_and_login(client, 'OWNER')
        r = client.post('/api/service/dispute-messages',
                        headers=auth(other_token),
                        json={'vin': VIN, 'record_index': 0, 'message': 'Intruder.'})
        assert r.status_code == 403

    def test_empty_message_returns_400(self, client):
        _, owner_token, _, _, _, _ = _setup_full(client)
        r = client.post('/api/service/dispute-messages',
                        headers=auth(owner_token),
                        json={'vin': VIN, 'record_index': 0, 'message': ''})
        assert r.status_code == 400

    def test_missing_message_returns_400(self, client):
        _, owner_token, _, _, _, _ = _setup_full(client)
        r = client.post('/api/service/dispute-messages',
                        headers=auth(owner_token),
                        json={'vin': VIN, 'record_index': 0})
        assert r.status_code == 400

    def test_missing_vin_returns_400(self, client):
        _, owner_token, _, _, _, _ = _setup_full(client)
        r = client.post('/api/service/dispute-messages',
                        headers=auth(owner_token),
                        json={'record_index': 0, 'message': 'No VIN.'})
        assert r.status_code == 400

    def test_invalid_vin_returns_400(self, client):
        _, owner_token, _, _, _, _ = _setup_full(client)
        r = client.post('/api/service/dispute-messages',
                        headers=auth(owner_token),
                        json={'vin': 'BAD', 'record_index': 0, 'message': 'Bad VIN.'})
        assert r.status_code == 400

    def test_negative_record_index_returns_400(self, client):
        _, owner_token, _, _, _, _ = _setup_full(client)
        r = client.post('/api/service/dispute-messages',
                        headers=auth(owner_token),
                        json={'vin': VIN, 'record_index': -1, 'message': 'Neg index.'})
        assert r.status_code == 400

    def test_posted_message_appears_in_get(self, client):
        _, owner_token, _, _, _, _ = _setup_full(client)
        client.post('/api/service/dispute-messages',
                    headers=auth(owner_token),
                    json={'vin': VIN, 'record_index': 0, 'message': 'Hello thread!'})
        r = client.get(f'/api/service/dispute-messages/{VIN}/0',
                       headers=auth(owner_token))
        messages = r.get_json()['messages']
        assert len(messages) == 1
        assert messages[0]['message'] == 'Hello thread!'

    def test_response_includes_all_expected_fields(self, client):
        _, owner_token, _, _, _, _ = _setup_full(client)
        r = client.post('/api/service/dispute-messages',
                        headers=auth(owner_token),
                        json={'vin': VIN, 'record_index': 0, 'message': 'Check fields.'})
        data = r.get_json()
        for field in ('id', 'vin', 'record_index', 'sender_id', 'sender_name',
                      'sender_role', 'message', 'created_at'):
            assert field in data, f'Missing field: {field}'

    def test_message_persisted_to_db(self, client, app):
        _, owner_token, _, _, _, _ = _setup_full(client)
        client.post('/api/service/dispute-messages',
                    headers=auth(owner_token),
                    json={'vin': VIN, 'record_index': 0, 'message': 'DB persist test.'})
        with app.app_context():
            from db.models import DisputeMessage
            msg = DisputeMessage.query.filter_by(vin=VIN, record_index=0).first()
            assert msg is not None
            assert msg.message == 'DB persist test.'
            assert msg.sender_role == 'OWNER'

    def test_multiple_messages_from_different_roles(self, client):
        mfr_token, owner_token, sc_token, _, _, _ = _setup_full(client)
        client.post('/api/service/dispute-messages', headers=auth(owner_token),
                    json={'vin': VIN, 'record_index': 0, 'message': 'Owner says X.'})
        client.post('/api/service/dispute-messages', headers=auth(sc_token),
                    json={'vin': VIN, 'record_index': 0, 'message': 'SC replies Y.'})
        client.post('/api/service/dispute-messages', headers=auth(mfr_token),
                    json={'vin': VIN, 'record_index': 0, 'message': 'MFR resolves Z.'})
        r = client.get(f'/api/service/dispute-messages/{VIN}/0',
                       headers=auth(owner_token))
        messages = r.get_json()['messages']
        assert len(messages) == 3
        roles = [m['sender_role'] for m in messages]
        assert 'OWNER' in roles
        assert 'SERVICE_CENTER' in roles
        assert 'MANUFACTURER' in roles
