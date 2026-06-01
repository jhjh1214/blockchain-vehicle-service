"""
Demo seed script — creates a realistic dataset for presentations and testing.

Usage (from the backend/ directory):
    python scripts/seed_demo.py

What it creates:
  - 1 Manufacturer  (Toyota Malaysia)
  - 1 Authorized SSM license pre-registered by that manufacturer
  - 1 Authorized SC (Toyota Ampang SC)
  - 1 Independent workshop (QuickFix Auto)
  - 2 Vehicle owners
  - 3 Toyota vehicles (registered to owners, one pending claim)
  - Service records in various states (pending, verified, disputed)
  - 1 active recall

All passwords: Demo@1234
"""

import os
import sys

# Allow running from backend/ or project root
_here = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.dirname(_here)
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from app import create_app

app = create_app()

with app.app_context():
    from db.models import db, User, VehicleVINMapping, AuthorizedSCLicense, VehicleRecall
    from core import auth_service, vehicle_service, service_log_service
    from blockchain.utils import compute_metadata_hash

    DEMO_PASSWORD = 'Demo@1234'
    BRAND = 'Toyota'

    print('=== VehicleChain Demo Seed ===\n')

    # ── Helper ────────────────────────────────────────────────────────────────
    def _exists(email: str) -> bool:
        return User.query.filter_by(email=email).first() is not None

    def _reg(email, role, name, **kwargs):
        if _exists(email):
            print(f'  SKIP  {email} (already exists)')
            user = User.query.filter_by(email=email).first()
            return user, None, None
        user, at, rt = auth_service.register_user(
            email=email, password=DEMO_PASSWORD, role=role, name=name,
            consent_given=True, **kwargs
        )
        print(f'  CREATE {role:20s} {email}')
        return user, at, rt

    # ── Manufacturer ─────────────────────────────────────────────────────────
    print('[1] Manufacturer')
    mfr, _, _ = _reg(
        'toyota.demo@vehiclechain.my',
        'MANUFACTURER',
        'Toyota Motor Malaysia',
        brand=BRAND,
        ssm_number='MY-TYT-001',
        city='Kuala Lumpur',
        state='Kuala Lumpur',
    )

    # Pre-register an SSM license for authorized SCs
    print('\n[2] Pre-registering SSM license')
    ssm_num = 'SC-AMP-2024'
    existing_lic = AuthorizedSCLicense.query.filter_by(ssm_number=ssm_num).first()
    if not existing_lic:
        lic = AuthorizedSCLicense(
            ssm_number=ssm_num,
            sc_name='Toyota Ampang Authorised SC',
            brand=BRAND,
            registered_by_user_id=mfr.id,
        )
        db.session.add(lic)
        db.session.commit()
        print(f'  CREATE license {ssm_num}')
    else:
        print(f'  SKIP  license {ssm_num} (already exists)')

    # ── Authorized SC ─────────────────────────────────────────────────────────
    print('\n[3] Authorized Service Centre')
    sc_auth, _, _ = _reg(
        'sc.ampang@vehiclechain.my',
        'SERVICE_CENTER',
        'Toyota Ampang SC',
        brand=BRAND,
        ssm_number=ssm_num,
        city='Ampang',
        state='Selangor',
    )
    if sc_auth.status == 'pending':
        from db.repositories import users as user_repo
        user_repo.update_status(sc_auth.id, 'active')
        print(f'  ACTIVATE {sc_auth.email}')

    # ── Independent Workshop ───────────────────────────────────────────────────
    print('\n[4] Independent Workshop')
    sc_indep, _, _ = _reg(
        'quickfix@vehiclechain.my',
        'SERVICE_CENTER',
        'QuickFix Auto',
        is_independent=True,
        city='Petaling Jaya',
        state='Selangor',
    )

    # ── Owners ────────────────────────────────────────────────────────────────
    print('\n[5] Vehicle Owners')
    owner1, _, _ = _reg('alice@demo.my', 'OWNER', 'Alice Tan', city='Kuala Lumpur', state='Kuala Lumpur')
    owner2, _, _ = _reg('bob@demo.my',   'OWNER', 'Bob Lim',   city='Petaling Jaya', state='Selangor')

    # ── Vehicles ──────────────────────────────────────────────────────────────
    print('\n[6] Vehicles')
    from config import Config

    def _register_vehicle(vin, owner_email, make, model, year, warranty_years=3):
        existing = VehicleVINMapping.query.filter_by(vin=vin).first()
        if existing:
            print(f'  SKIP  {vin} (already exists)')
            return existing
        result = vehicle_service.register_vehicle(
            vin=vin,
            owner_email=owner_email,
            warranty_years=warranty_years,
            make=make,
            model=model,
            year=year,
            from_address=Config.DEPLOYER_ADDRESS,
            registered_by=mfr.blockchain_address,
            intended_owner_email=owner_email,
        )
        print(f'  CREATE {vin}  {year} {make} {model}  → {owner_email}')
        return VehicleVINMapping.query.filter_by(vin=vin).first()

    v1 = _register_vehicle('JMF4CA20901234567', owner1.email, BRAND, 'Vios', 2022)
    v2 = _register_vehicle('JMF4CA21001234568', owner1.email, BRAND, 'Camry', 2023, warranty_years=5)
    v3 = _register_vehicle('JMF4CA20801234569', owner2.email, BRAND, 'Hilux', 2021)

    # ── Service Records ───────────────────────────────────────────────────────
    print('\n[7] Service Records')
    from db.models import ServiceMetadata

    def _service_exists(vin, sc_addr):
        return ServiceMetadata.query.filter_by(
            vin=vin, service_center_address=sc_addr
        ).first() is not None

    if v1 and not _service_exists(v1.vin, sc_auth.blockchain_address):
        try:
            service_log_service.submit_service(
                vin=v1.vin,
                service_type='Oil Change & Filter',
                service_date='2024-03-15T10:00:00',
                mileage=15000,
                parts_replaced='Engine oil, oil filter',
                technician_name='Ahmad Razif',
                service_notes='Full synthetic 5W-30. Next service at 30,000 km.',
                ecu_modules=[],
                photos=[],
                from_address=sc_auth.blockchain_address,
                sc_brand=BRAND,
            )
            print(f'  CREATE service on {v1.vin} (pending, by authorized SC)')
        except Exception as e:
            print(f'  WARN  service on {v1.vin}: {e}')

    if v2 and not _service_exists(v2.vin, sc_auth.blockchain_address):
        try:
            service_log_service.submit_service(
                vin=v2.vin,
                service_type='Full Service',
                service_date='2024-06-01T09:30:00',
                mileage=20000,
                parts_replaced='Air filter, cabin filter, spark plugs, engine oil',
                technician_name='Mohd Hafiz',
                service_notes='30,000 km major service completed.',
                ecu_modules=['ECM', 'TCM'],
                photos=[],
                from_address=sc_auth.blockchain_address,
                sc_brand=BRAND,
            )
            print(f'  CREATE service on {v2.vin} (pending, by authorized SC)')
        except Exception as e:
            print(f'  WARN  service on {v2.vin}: {e}')

    if v3 and not _service_exists(v3.vin, sc_indep.blockchain_address):
        try:
            service_log_service.submit_service(
                vin=v3.vin,
                service_type='Brake Inspection',
                service_date='2024-07-20T14:00:00',
                mileage=55000,
                parts_replaced='Front brake pads',
                technician_name='James Wong',
                service_notes='Rear pads at 40% — recommend replacement at next visit.',
                ecu_modules=[],
                photos=[],
                from_address=sc_indep.blockchain_address,
                sc_brand='',
            )
            print(f'  CREATE service on {v3.vin} (pending, by independent workshop)')
        except Exception as e:
            print(f'  WARN  service on {v3.vin}: {e}')

    # ── Recall ────────────────────────────────────────────────────────────────
    print('\n[8] Recall')
    existing_recall = VehicleRecall.query.filter_by(brand=BRAND, title='Airbag Inflator Safety Recall').first()
    if not existing_recall:
        recall = VehicleRecall(
            brand=BRAND,
            issued_by_user_id=mfr.id,
            title='Airbag Inflator Safety Recall',
            description=(
                'Certain vehicles may have a defective airbag inflator that can rupture '
                'in the event of a crash, potentially causing injury. '
                'Owners are urged to visit an authorised service centre for a free replacement.'
            ),
        )
        db.session.add(recall)
        db.session.commit()
        print(f'  CREATE recall: {recall.title}')
    else:
        print(f'  SKIP  recall (already exists)')

    # ── Summary ───────────────────────────────────────────────────────────────
    print('\n=== Seed complete ===')
    print(f'\nAll accounts use password: {DEMO_PASSWORD}')
    print('\nAccounts created:')
    print(f'  Manufacturer  : toyota.demo@vehiclechain.my')
    print(f'  Auth SC        : sc.ampang@vehiclechain.my')
    print(f'  Independent SC : quickfix@vehiclechain.my')
    print(f'  Owner 1        : alice@demo.my  (2 vehicles)')
    print(f'  Owner 2        : bob@demo.my    (1 vehicle)')
    print('\nNote: Owners must log in via the Flutter mobile app to claim their vehicles.')
    print('      Service records are in PENDING state — owners can verify or dispute them.')
