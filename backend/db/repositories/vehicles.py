from db.models import db, VehicleVINMapping


def find_by_vin(vin: str) -> VehicleVINMapping | None:
    return VehicleVINMapping.query.filter_by(vin=vin).first()


def find_by_vin_hash(vin_hash: str) -> VehicleVINMapping | None:
    return VehicleVINMapping.query.filter_by(vin_hash=vin_hash).first()


def find_by_owner(owner_address: str, status: str = None) -> list:
    q = VehicleVINMapping.query.filter_by(owner_address=owner_address)
    if status:
        q = q.filter_by(registration_status=status)
    return q.all()


def create(vin: str, vin_hash: str, owner_address: str,
           make: str = None, model: str = None, year: int = None,
           warranty_expiry: int = None, registered_by: str = None,
           registration_status: str = 'active',
           intended_owner_email: str = None) -> VehicleVINMapping:
    mapping = VehicleVINMapping(vin=vin, vin_hash=vin_hash, owner_address=owner_address,
                                registered_by=registered_by,
                                registration_status=registration_status,
                                intended_owner_email=intended_owner_email,
                                make=make, model=model, year=year,
                                warranty_expiry=warranty_expiry)
    db.session.add(mapping)
    db.session.commit()
    return mapping


def update_owner(vin: str, new_owner_address: str) -> VehicleVINMapping | None:
    mapping = find_by_vin(vin)
    if mapping:
        mapping.owner_address = new_owner_address
        db.session.commit()
    return mapping


def update_registration_status(vin: str, status: str) -> VehicleVINMapping | None:
    mapping = find_by_vin(vin)
    if mapping:
        mapping.registration_status = status
        db.session.commit()
    return mapping
