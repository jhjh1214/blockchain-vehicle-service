"""Tests for new features: dashboard fleet_health_score, ETH balance, PDF export,
warranty claim status persistence, and service resolution persistence."""
import time
import pytest
from unittest.mock import MagicMock, patch
from conftest import register_and_login, auth, STRONG_PASSWORD

VIN   = '1HGCM82633A004352'
TODAY = time.strftime('%Y-%m-%dT%H:%M:%S')


def _register_vehicle(client, mfr_token, owner_email=None, vin=VIN):
    payload = {'vin': vin, 'warranty_years': 3, 'make': 'Honda', 'model': 'Civic', 'year': 2024}
    if owner_email:
        payload['owner_email'] = owner_email
    return client.post('/api/vehicle/register', headers=auth(mfr_token), json=payload)


def _activate_sc(client, mfr_token, sc_user):
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
        _register_vehicle(client, mfr_token, owner_email=owner['email'])

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
        _register_vehicle(client, mfr_token, owner_email=owner['email'])

        r = client.get('/api/vehicle/fleet', headers=auth(mfr_token))
        assert r.status_code == 200
        vehicle = r.get_json()['vehicles'][0]
        assert 'service_count' in vehicle
        assert isinstance(vehicle['service_count'], int)

    def test_fleet_vehicle_has_days_since_service(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])

        r = client.get('/api/vehicle/fleet', headers=auth(mfr_token))
        vehicle = r.get_json()['vehicles'][0]
        assert 'days_since_service' in vehicle

    def test_fleet_vehicle_has_last_service_date(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])

        r = client.get('/api/vehicle/fleet', headers=auth(mfr_token))
        vehicle = r.get_json()['vehicles'][0]
        assert 'last_service_date' in vehicle

    def test_fleet_service_count_increments_after_service(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        sc_token = _activate_sc(client, mfr_token, sc_user)

        client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Oil Change',
            'service_date': TODAY, 'mileage': 5000,
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
        _register_vehicle(client, mfr_token, owner_email=owner['email'])

        r = client.get(f'/api/vehicle/export/{VIN}')
        assert r.status_code == 200
        assert r.content_type == 'application/pdf'

    def test_export_content_disposition_header(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])

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
        _register_vehicle(client, mfr_token)
        r = client.get(f'/api/vehicle/export/{VIN}')
        # Pending vehicle (no owner) should still work
        assert r.status_code == 200

    def test_export_pdf_has_non_zero_content(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])

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
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        sc_token = _activate_sc(client, mfr_token, sc_user)
        client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Brake Service',
            'service_date': TODAY, 'mileage': 12000,
        })
        return mfr_token

    def test_public_verify_returns_200(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        r = client.get(f'/api/vehicle/public/{VIN}')
        assert r.status_code == 200

    def test_public_verify_has_service_records_key(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
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
            _register_vehicle(client, mfr_token, owner_email=owner['email'])
            r = client.get(f'/api/vehicle/public/{VIN}')
            data = r.get_json()
            if data.get('service_records'):
                assert 'record_index' in data['service_records'][0]
        finally:
            sl.get_finalized_services.return_value = []

    def test_public_verify_no_auth_required(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _register_vehicle(client, mfr_token)
        r = client.get(f'/api/vehicle/public/{VIN}')
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Warranty claim status persistence
# ---------------------------------------------------------------------------

class TestWarrantyClaimStatusPersistence:
    def _setup_claim(self, client):
        """Submit a claim and configure wt.get_claims to return the actual claim hash."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])

        r = client.post('/api/warranty/submit-claim', headers=auth(owner_token), json={
            'vin': VIN, 'issue_description': 'Gearbox grinding noise',
        })
        actual_hash = r.get_json()['claim_hash']

        # Point get_claims mock at the real hash so update_status can find the DB record
        from blockchain.adapters.warranty_tracker import warranty_tracker as wt
        wt.get_claims.return_value = [{'claim_details_hash': actual_hash, 'timestamp': 0}]

        return mfr_token, actual_hash

    def test_approve_claim_persists_approved_status(self, client, app):
        mfr_token, _ = self._setup_claim(client)

        client.post('/api/warranty/approve-claim', headers=auth(mfr_token), json={
            'vin': VIN, 'claim_index': 0,
        })

        with app.app_context():
            from db.models import WarrantyClaimMetadata
            record = WarrantyClaimMetadata.query.filter_by(vin=VIN).first()
            assert record is not None
            assert record.status == 'approved'

    def test_deny_claim_persists_denied_status(self, client, app):
        mfr_token, _ = self._setup_claim(client)

        client.post('/api/warranty/deny-claim', headers=auth(mfr_token), json={
            'vin': VIN, 'claim_index': 0, 'reason': 'Outside warranty scope',
        })

        with app.app_context():
            from db.models import WarrantyClaimMetadata
            record = WarrantyClaimMetadata.query.filter_by(vin=VIN).first()
            assert record is not None
            assert record.status == 'denied'

    def test_deny_claim_persists_reason_as_notes(self, client, app):
        mfr_token, _ = self._setup_claim(client)

        client.post('/api/warranty/deny-claim', headers=auth(mfr_token), json={
            'vin': VIN, 'claim_index': 0, 'reason': 'Vehicle was modified by owner',
        })

        with app.app_context():
            from db.models import WarrantyClaimMetadata
            record = WarrantyClaimMetadata.query.filter_by(vin=VIN).first()
            assert record.approved_notes == 'Vehicle was modified by owner'

    def test_new_claim_has_pending_status_by_default(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])

        client.post('/api/warranty/submit-claim', headers=auth(owner_token), json={
            'vin': VIN, 'issue_description': 'Strange rattle from dashboard',
        })

        with app.app_context():
            from db.models import WarrantyClaimMetadata
            record = WarrantyClaimMetadata.query.filter_by(vin=VIN).first()
            assert record is not None
            assert record.status == 'pending'

    def test_approve_sets_approved_at_timestamp(self, client, app):
        mfr_token, _ = self._setup_claim(client)

        client.post('/api/warranty/approve-claim', headers=auth(mfr_token), json={
            'vin': VIN, 'claim_index': 0,
        })

        with app.app_context():
            from db.models import WarrantyClaimMetadata
            record = WarrantyClaimMetadata.query.filter_by(vin=VIN).first()
            assert record.approved_at is not None

    def teardown_method(self, method):
        from blockchain.adapters.warranty_tracker import warranty_tracker as wt
        wt.get_claims.return_value = []


# ---------------------------------------------------------------------------
# Service dispute resolution persistence
# ---------------------------------------------------------------------------

class TestServiceResolutionPersistence:
    def _setup_dispute(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        sc_token = _activate_sc(client, mfr_token, sc_user)

        client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Engine Service',
            'service_date': TODAY, 'mileage': 30000,
        })

        with app.app_context():
            from db.models import ServiceMetadata
            record = ServiceMetadata.query.filter_by(vin=VIN).first()
            assert record is not None
            meta_hash = record.metadata_hash

        from blockchain.adapters.service_log import service_log as sl
        sl.get_pending_services.return_value = [{
            'metadata_hash': meta_hash,
            'verified': False,
            'disputed': True,
            'service_center': '0x' + '02' * 20,
        }]

        return mfr_token, meta_hash

    def test_resolve_dispute_persists_decision(self, client, app):
        mfr_token, meta_hash = self._setup_dispute(client, app)

        client.post('/api/service/resolve-dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'record_index': 0, 'decision': 1,
            'resolution_notes': 'Claim verified and approved',
        })

        with app.app_context():
            from db.models import ServiceMetadata
            record = ServiceMetadata.query.filter_by(vin=VIN).first()
            assert record.resolution_decision == 'approved'

    def test_resolve_dispute_persists_notes(self, client, app):
        mfr_token, meta_hash = self._setup_dispute(client, app)

        client.post('/api/service/resolve-dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'record_index': 0, 'decision': 2,
            'resolution_notes': 'No evidence of defect found',
        })

        with app.app_context():
            from db.models import ServiceMetadata
            record = ServiceMetadata.query.filter_by(vin=VIN).first()
            assert record.resolution_notes == 'No evidence of defect found'

    def test_resolve_dispute_sets_resolved_at(self, client, app):
        mfr_token, meta_hash = self._setup_dispute(client, app)

        client.post('/api/service/resolve-dispute', headers=auth(mfr_token), json={
            'vin': VIN, 'record_index': 0, 'decision': 1,
            'resolution_notes': 'Resolved',
        })

        with app.app_context():
            from db.models import ServiceMetadata
            record = ServiceMetadata.query.filter_by(vin=VIN).first()
            assert record.resolved_at is not None

    def test_service_metadata_resolution_fields_in_to_dict(self, client, app):
        """ServiceMetadata.to_dict() must include resolution fields."""
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        _, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        sc_token = _activate_sc(client, mfr_token, sc_user)
        client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Tyre Rotation',
            'service_date': TODAY, 'mileage': 8000,
        })

        with app.app_context():
            from db.models import ServiceMetadata
            record = ServiceMetadata.query.filter_by(vin=VIN).first()
            d = record.to_dict()
            assert 'resolution_decision' in d
            assert 'resolution_notes' in d
            assert 'resolved_at' in d

    def teardown_method(self, method):
        from blockchain.adapters.service_log import service_log as sl
        sl.get_pending_services.return_value = []


# ---------------------------------------------------------------------------
# WarrantyClaimMetadata model — new fields
# ---------------------------------------------------------------------------

class TestWarrantyClaimMetadataModel:
    def test_warranty_claim_to_dict_includes_status(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        client.post('/api/warranty/submit-claim', headers=auth(owner_token), json={
            'vin': VIN, 'issue_description': 'Oil leak',
        })

        with app.app_context():
            from db.models import WarrantyClaimMetadata
            record = WarrantyClaimMetadata.query.filter_by(vin=VIN).first()
            d = record.to_dict()
            assert 'status' in d
            assert 'approved_at' in d
            assert 'approved_notes' in d

    def test_warranty_claim_default_status_is_pending(self, client, app):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        client.post('/api/warranty/submit-claim', headers=auth(owner_token), json={
            'vin': VIN, 'issue_description': 'Coolant leak',
        })

        with app.app_context():
            from db.models import WarrantyClaimMetadata
            record = WarrantyClaimMetadata.query.filter_by(vin=VIN).first()
            assert record.status == 'pending'
            assert record.approved_at is None


# ---------------------------------------------------------------------------
# Vehicle detail — service stats (last_service_date, days_since_service, etc.)
# ---------------------------------------------------------------------------

class TestVehicleDetailServiceStats:
    def test_vehicle_detail_includes_service_stat_keys(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        r = client.get(f'/api/vehicle/{VIN}', headers=auth(owner_token))
        assert r.status_code == 200
        data = r.get_json()
        assert 'last_service_date' in data
        assert 'days_since_service' in data
        assert 'last_service_mileage' in data

    def test_service_stats_null_when_no_service_exists(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        r = client.get(f'/api/vehicle/{VIN}', headers=auth(owner_token))
        data = r.get_json()
        assert data['last_service_date'] is None
        assert data['days_since_service'] is None
        assert data['last_service_mileage'] is None

    def test_service_stats_populated_after_service_submitted(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _, sc_user = register_and_login(client, 'SERVICE_CENTER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        sc_token = _activate_sc(client, mfr_token, sc_user)

        client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Oil Change',
            'service_date': TODAY, 'mileage': 8000,
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
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        sc_token = _activate_sc(client, mfr_token, sc_user)

        client.post('/api/service/submit', headers=auth(sc_token), json={
            'vin': VIN, 'service_type': 'Brake Check',
            'service_date': TODAY, 'mileage': 12000,
        })

        r = client.get(f'/api/vehicle/{VIN}', headers=auth(owner_token))
        days = r.get_json()['days_since_service']
        assert days >= 0

    def test_service_count_in_vehicle_detail(self, client):
        mfr_token, _ = register_and_login(client, 'MANUFACTURER')
        owner_token, owner = register_and_login(client, 'OWNER')
        _register_vehicle(client, mfr_token, owner_email=owner['email'])
        r = client.get(f'/api/vehicle/{VIN}', headers=auth(owner_token))
        assert 'service_count' in r.get_json()


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
