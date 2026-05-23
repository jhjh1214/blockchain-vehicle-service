"""
End-to-end integration tests — require a running Ganache node and deployed contracts.

Run with:  pytest -m e2e
Skip with: pytest -m "not e2e"  (default — these do NOT run in CI)
"""
import time
import uuid
import pytest
import requests

BASE = 'http://localhost:5000/api'
E2E_PASSWORD = 'E2eTest1!'


def uid(prefix=''):
    return f'{prefix}{uuid.uuid4().hex[:6]}'


def headers(token):
    return {'Authorization': f'Bearer {token}'}


def check(r, label):
    assert r.ok, f'{label} failed ({r.status_code}): {r.text}'
    return r.json()


@pytest.mark.e2e
def test_full_workflow():
    """
    Complete workflow:
      1  Register Manufacturer, Service Center, Owner
      2  Manufacturer registers vehicle (with owner — active immediately)
      3  Get vehicle details
      4  Service Center submits service record
      5  Owner views pending services
      6  Owner verifies service → on-chain finalization
      7  View service history (should have 1 record)
      8  Owner submits warranty claim
      9  Manufacturer approves warranty claim
      10 Owner views their claims
    """
    mfr_email = f'mfr-{uid()}@e2e.test'
    sc_email = f'sc-{uid()}@e2e.test'
    owner_email = f'owner-{uid()}@e2e.test'
    vin = f'1HGBH41JXM{uid("N")}'[:17].upper()

    # 1 — Register users
    mfr = check(requests.post(f'{BASE}/auth/register', json={
        'email': mfr_email, 'password': E2E_PASSWORD,
        'role': 'MANUFACTURER', 'name': 'E2E Manufacturer',
    }), 'Register manufacturer')
    mfr_token = mfr['access_token']

    sc = check(requests.post(f'{BASE}/auth/register', json={
        'email': sc_email, 'password': E2E_PASSWORD,
        'role': 'SERVICE_CENTER', 'name': 'E2E Service Center',
    }), 'Register service center')
    sc_token = sc['access_token']

    owner = check(requests.post(f'{BASE}/auth/register', json={
        'email': owner_email, 'password': E2E_PASSWORD,
        'role': 'OWNER', 'name': 'E2E Owner',
    }), 'Register owner')
    owner_token = owner['access_token']

    # 2 — Register vehicle (with owner, active immediately)
    reg = check(requests.post(f'{BASE}/vehicle/register', headers=headers(mfr_token), json={
        'vin': vin, 'owner_email': owner_email,
        'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024,
    }), 'Register vehicle')
    assert reg['vin'] == vin
    assert reg['registration_status'] == 'active'
    assert 'tx_hash' in reg['transaction']

    # 3 — Get vehicle details
    v = check(requests.get(f'{BASE}/vehicle/{vin}', headers=headers(owner_token)), 'Get vehicle')
    assert v['make'] == 'Honda'
    assert v['warranty']['is_valid'] is True
    assert v['registration_status'] == 'active'

    # 4 — Submit service record
    svc = check(requests.post(f'{BASE}/service/submit', headers=headers(sc_token), json={
        'vin': vin,
        'service_type': 'Oil Change',
        'service_date': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'mileage': 15000,
        'technician_name': 'Bob Mechanic',
        'parts_replaced': 'Oil filter',
        'service_notes': 'Regular service',
    }), 'Submit service')
    assert svc['metadata_hash'].startswith('0x')

    # 5 — Check pending services
    pending = check(requests.get(f'{BASE}/service/pending/{vin}', headers=headers(owner_token)),
                    'Get pending')
    assert pending['count'] == 1
    assert pending['pending_services'][0]['metadata']['service_type'] == 'Oil Change'

    # 6 — Owner verifies service (writes to chain)
    verify = check(requests.post(f'{BASE}/service/verify', headers=headers(owner_token), json={
        'vin': vin, 'record_index': 0,
    }), 'Verify service')
    assert 'tx_hash' in verify['transaction']

    # 7 — Service history should have 1 finalized record
    hist = check(requests.get(f'{BASE}/service/history/{vin}', headers=headers(owner_token)),
                 'Service history')
    assert hist['count'] == 1

    # 8 — Owner submits warranty claim
    claim = check(requests.post(f'{BASE}/warranty/submit-claim', headers=headers(owner_token), json={
        'vin': vin, 'issue_description': 'Strange engine noise', 'photos': [],
    }), 'Submit warranty claim')
    assert claim['claim_hash'].startswith('0x')

    # 9 — Manufacturer approves claim
    approve = check(requests.post(f'{BASE}/warranty/approve-claim', headers=headers(mfr_token), json={
        'vin': vin, 'claim_index': 0,
    }), 'Approve claim')
    assert 'tx_hash' in approve['transaction']

    # 10 — Owner views their claims
    my_claims = check(requests.get(f'{BASE}/warranty/owner/claims', headers=headers(owner_token)),
                      'Owner claims')
    assert my_claims['count'] >= 1
    approved = [c for c in my_claims['claims'] if c.get('status') == 'approved']
    assert len(approved) == 1


@pytest.mark.e2e
def test_pending_claim_workflow():
    """
    Pre-registration and claim workflow:
      1  Register Manufacturer and Owner
      2  Manufacturer pre-registers vehicle (no owner → pending)
      3  Verify vehicle appears in fleet as pending
      4  Owner claims vehicle
      5  Verify vehicle is now active in fleet and owner's my-vehicles
    """
    mfr_email = f'mfr-{uid()}@e2e.test'
    owner_email = f'owner-{uid()}@e2e.test'
    vin = f'3HGBH41JXM{uid("P")}'[:17].upper()

    mfr_token = check(requests.post(f'{BASE}/auth/register', json={
        'email': mfr_email, 'password': E2E_PASSWORD,
        'role': 'MANUFACTURER', 'name': 'E2E MFR',
    }), 'reg mfr')['access_token']

    owner_token = check(requests.post(f'{BASE}/auth/register', json={
        'email': owner_email, 'password': E2E_PASSWORD,
        'role': 'OWNER', 'name': 'E2E Owner',
    }), 'reg owner')['access_token']

    # Pre-register — no owner_email
    reg = check(requests.post(f'{BASE}/vehicle/register', headers=headers(mfr_token), json={
        'vin': vin, 'warranty_years': 3, 'make': 'Toyota', 'model': 'Corolla', 'year': 2023,
    }), 'pre-register')
    assert reg['registration_status'] == 'pending'
    assert reg['owner'] is None

    fleet = check(requests.get(f'{BASE}/vehicle/fleet', headers=headers(mfr_token)), 'fleet')
    pending_vins = [v['vin'] for v in fleet['vehicles'] if v['registration_status'] == 'pending']
    assert vin in pending_vins

    # Owner claims the vehicle
    claim = check(requests.post(f'{BASE}/vehicle/claim', headers=headers(owner_token), json={
        'vin': vin,
    }), 'claim vehicle')
    assert claim['vin'] == vin

    # Verify active in fleet
    fleet2 = check(requests.get(f'{BASE}/vehicle/fleet', headers=headers(mfr_token)), 'fleet after claim')
    match = next(v for v in fleet2['vehicles'] if v['vin'] == vin)
    assert match['registration_status'] == 'active'

    # Verify in owner's my-vehicles
    my_v = check(requests.get(f'{BASE}/vehicle/my-vehicles', headers=headers(owner_token)),
                 'my-vehicles')
    assert any(v['vin'] == vin for v in my_v['vehicles'])


@pytest.mark.e2e
def test_dispute_workflow():
    """
    Dispute resolution workflow:
      1  Register all parties
      2  Manufacturer registers vehicle
      3  Service Center submits service
      4  Owner disputes service
      5  Manufacturer resolves dispute (approve)
      6  Service now finalized
    """
    mfr_email = f'mfr-{uid()}@e2e.test'
    sc_email = f'sc-{uid()}@e2e.test'
    owner_email = f'owner-{uid()}@e2e.test'
    vin = f'2HGBH41JXM{uid("D")}'[:17].upper()

    mfr_token = check(requests.post(f'{BASE}/auth/register', json={
        'email': mfr_email, 'password': E2E_PASSWORD, 'role': 'MANUFACTURER', 'name': 'MFR',
    }), 'reg mfr')['access_token']

    sc_token = check(requests.post(f'{BASE}/auth/register', json={
        'email': sc_email, 'password': E2E_PASSWORD, 'role': 'SERVICE_CENTER', 'name': 'SC',
    }), 'reg sc')['access_token']

    owner_token = check(requests.post(f'{BASE}/auth/register', json={
        'email': owner_email, 'password': E2E_PASSWORD, 'role': 'OWNER', 'name': 'Owner',
    }), 'reg owner')['access_token']

    check(requests.post(f'{BASE}/vehicle/register', headers=headers(mfr_token), json={
        'vin': vin, 'owner_email': owner_email,
        'warranty_years': 2, 'make': 'Toyota', 'model': 'Corolla', 'year': 2023,
    }), 'register vehicle')

    check(requests.post(f'{BASE}/service/submit', headers=headers(sc_token), json={
        'vin': vin, 'service_type': 'Brake Pad Replacement',
        'service_date': time.strftime('%Y-%m-%dT%H:%M:%S'), 'mileage': 30000,
    }), 'submit service')

    check(requests.post(f'{BASE}/service/dispute', headers=headers(owner_token), json={
        'vin': vin, 'record_index': 0, 'reason': 'Wrong brake pads used',
    }), 'dispute service')

    pending = check(requests.get(f'{BASE}/service/pending/{vin}', headers=headers(owner_token)),
                    'get pending')
    assert pending['pending_services'][0]['disputed'] is True

    check(requests.post(f'{BASE}/service/resolve-dispute', headers=headers(mfr_token), json={
        'vin': vin, 'record_index': 0, 'decision': 1,
        'resolution_notes': 'Inspection confirmed correct parts',
    }), 'resolve dispute')

    hist = check(requests.get(f'{BASE}/service/history/{vin}', headers=headers(owner_token)),
                 'history after resolve')
    assert hist['count'] == 1
