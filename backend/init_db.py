"""
Database initialisation + demo seed.

Usage:
    python init_db.py          # reset schema only (no seed data)
    python init_db.py --seed   # reset schema AND load demo data

Demo accounts (all password: Demo@1234):
    Manufacturer  : toyota.demo@vehiclechain.my
    Authorized SC : sc.ampang@vehiclechain.my
    Independent SC: quickfix@vehiclechain.my
    Owner 1       : alice@demo.my  (2 vehicles)
    Owner 2       : bob@demo.my    (1 vehicle)

Owners must use the Flutter mobile app to claim their vehicles.
Service records are created in PENDING state.
"""

import sys

from app import create_app
from db.models import db

app = create_app()

with app.app_context():
    db.drop_all()
    print('Dropped all tables')

    db.create_all()
    print('Created all tables')

    from sqlalchemy import inspect as _inspect
    tables = _inspect(db.engine).get_table_names()
    print('\nDatabase initialised successfully!')
    print('Tables created:')
    for t in tables:
        print(f'  - {t}')

    # ── Optional demo seed ────────────────────────────────────────────────────
    if '--seed' not in sys.argv:
        print('\nTip: run with --seed to load demo data.')
        sys.exit(0)

    print('\n=== Loading demo data ===\n')

    from db.models import AuthorizedSCLicense, VehicleRecall
    from db.repositories import users as user_repo
    from core import auth_service, vehicle_service, service_log_service
    from config import Config

    DEMO_PASSWORD = 'Demo@1234'
    BRAND = 'Toyota'

    def _reg(email, role, name, **kwargs):
        user, at, rt = auth_service.register_user(
            email=email, password=DEMO_PASSWORD, role=role, name=name,
            consent_given=True, **kwargs
        )
        # Mark demo accounts as verified so they can log in immediately
        user.email_verified = True
        db.session.commit()
        print(f'  CREATE {role:25s} {email}')
        return user

    # Manufacturer
    print('[1] Manufacturer')
    mfr = _reg(
        'toyota.demo@vehiclechain.my', 'MANUFACTURER', 'Toyota Motor Malaysia',
        brand=BRAND, ssm_number='MY-TYT-001',
        city='Kuala Lumpur', state='Kuala Lumpur',
    )

    # Pre-register an SSM license
    print('\n[2] SSM license')
    ssm_num = 'SC-AMP-2024'
    lic = AuthorizedSCLicense(
        ssm_number=ssm_num, sc_name='Toyota Ampang Authorised SC',
        brand=BRAND, registered_by_user_id=mfr.id,
    )
    db.session.add(lic)
    db.session.commit()
    print(f'  CREATE license {ssm_num}')

    # Authorized SC
    print('\n[3] Authorized Service Centre')
    sc_auth = _reg(
        'sc.ampang@vehiclechain.my', 'SERVICE_CENTER', 'Toyota Ampang SC',
        brand=BRAND, ssm_number=ssm_num,
        city='Ampang', state='Selangor',
    )
    user_repo.update_status(sc_auth.id, 'active')
    print(f'  ACTIVATE {sc_auth.email}')

    # Independent Workshop
    print('\n[4] Independent Workshop')
    sc_indep = _reg(
        'quickfix@vehiclechain.my', 'SERVICE_CENTER', 'QuickFix Auto',
        is_independent=True, city='Petaling Jaya', state='Selangor',
    )

    # Owners
    print('\n[5] Vehicle Owners')
    owner1 = _reg('alice@demo.my', 'OWNER', 'Alice Tan', city='Kuala Lumpur', state='Kuala Lumpur')
    owner2 = _reg('bob@demo.my',   'OWNER', 'Bob Lim',   city='Petaling Jaya', state='Selangor')

    # Vehicles
    print('\n[6] Vehicles')

    def _reg_vehicle(vin, owner_email, model, year, warranty_years=3):
        result = vehicle_service.register_vehicle(
            vin=vin, owner_email=owner_email,
            warranty_years=warranty_years,
            make=BRAND, model=model, year=year,
            from_address=Config.DEPLOYER_ADDRESS,
            registered_by=mfr.blockchain_address,
            intended_owner_email=owner_email,
        )
        print(f'  CREATE {vin}  {year} {BRAND} {model}  → {owner_email}')

    _reg_vehicle('JMF4CA20901234567', owner1.email, 'Vios',  2022)
    _reg_vehicle('JMF4CA21001234568', owner1.email, 'Camry', 2023, warranty_years=5)
    _reg_vehicle('JMF4CA20801234569', owner2.email, 'Hilux', 2021)

    # Service records
    print('\n[7] Service Records')

    def _svc(vin, sc, svc_type, date, mileage, parts, tech, notes, brand=''):
        try:
            service_log_service.submit_service(
                vin=vin, service_type=svc_type, service_date=date,
                mileage=mileage, parts_replaced=parts,
                technician_name=tech, service_notes=notes,
                ecu_modules=[], photos=[],
                from_address=sc.blockchain_address,
                sc_brand=brand,
            )
            print(f'  CREATE service on {vin} ({svc_type})')
        except Exception as e:
            print(f'  WARN  {vin}: {e}')

    _svc('JMF4CA20901234567', sc_auth,  'Oil Change & Filter', '2024-03-15T10:00:00',
         15000, 'Engine oil, oil filter', 'Ahmad Razif',
         'Full synthetic 5W-30. Next service at 30,000 km.', brand=BRAND)

    _svc('JMF4CA21001234568', sc_auth,  'Full Service', '2024-06-01T09:30:00',
         20000, 'Air filter, cabin filter, spark plugs, engine oil', 'Mohd Hafiz',
         '30,000 km major service completed.', brand=BRAND)

    _svc('JMF4CA20801234569', sc_indep, 'Brake Inspection', '2024-07-20T14:00:00',
         55000, 'Front brake pads', 'James Wong',
         'Rear pads at 40% — recommend replacement at next visit.')

    # Recall
    print('\n[8] Recall')
    recall = VehicleRecall(
        brand=BRAND,
        issued_by_user_id=mfr.id,
        title='Airbag Inflator Safety Recall',
        description=(
            'Certain vehicles may have a defective airbag inflator that can rupture '
            'in a crash, potentially causing injury. '
            'Visit an authorised service centre for a free replacement.'
        ),
    )
    db.session.add(recall)
    db.session.commit()
    print(f'  CREATE recall: {recall.title}')

    print('\n=== Demo data loaded ===')
    print(f'\nAll demo accounts use password: {DEMO_PASSWORD}')
    print('\n  toyota.demo@vehiclechain.my  (Manufacturer)')
    print('  sc.ampang@vehiclechain.my    (Authorized SC — active)')
    print('  quickfix@vehiclechain.my     (Independent Workshop)')
    print('  alice@demo.my                (Owner — 2 vehicles)')
    print('  bob@demo.my                  (Owner — 1 vehicle)')
