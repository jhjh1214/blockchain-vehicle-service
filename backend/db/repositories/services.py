from datetime import datetime
from db.models import db, ServiceMetadata


def find_by_metadata_hash(metadata_hash: str) -> ServiceMetadata | None:
    return ServiceMetadata.query.filter_by(metadata_hash=metadata_hash).first()


def create(vin: str, metadata_hash: str, service_type: str, service_date: datetime,
           mileage: int, parts_replaced: str, technician_name: str,
           service_notes: str, photos) -> ServiceMetadata:
    record = ServiceMetadata(
        vin=vin,
        metadata_hash=metadata_hash,
        service_type=service_type,
        service_date=service_date,
        mileage=mileage,
        parts_replaced=parts_replaced,
        technician_name=technician_name,
        service_notes=service_notes,
        photos=photos
    )
    db.session.add(record)
    db.session.commit()
    return record
