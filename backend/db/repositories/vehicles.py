from db.models import db, VehicleVINMapping


def find_by_vin(vin: str) -> VehicleVINMapping | None:
    return VehicleVINMapping.query.filter_by(vin=vin).first()


def find_by_vin_hash(vin_hash: str) -> VehicleVINMapping | None:
    return VehicleVINMapping.query.filter_by(vin_hash=vin_hash).first()


def create(vin: str, vin_hash: str, owner_address: str,
           make: str = None, model: str = None, year: int = None) -> VehicleVINMapping:
    mapping = VehicleVINMapping(vin=vin, vin_hash=vin_hash, owner_address=owner_address,
                                make=make, model=model, year=year)
    db.session.add(mapping)
    db.session.commit()
    return mapping


def update_owner(vin: str, new_owner_address: str) -> VehicleVINMapping | None:
    mapping = find_by_vin(vin)
    if mapping:
        mapping.owner_address = new_owner_address
        db.session.commit()
    return mapping
