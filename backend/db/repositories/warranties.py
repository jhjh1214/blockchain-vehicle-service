from datetime import datetime
from db.models import db, WarrantyClaimMetadata


def find_by_claim_hash(claim_hash: str) -> WarrantyClaimMetadata | None:
    return WarrantyClaimMetadata.query.filter_by(claim_hash=claim_hash).first()


def find_by_vin(vin: str) -> list:
    return WarrantyClaimMetadata.query.filter_by(vin=vin).all()


def create(vin: str, claim_hash: str, issue_description: str,
           photos) -> WarrantyClaimMetadata:
    record = WarrantyClaimMetadata(
        vin=vin,
        claim_hash=claim_hash,
        issue_description=issue_description,
        photos=photos
    )
    db.session.add(record)
    db.session.commit()
    return record


def update_status(claim_hash: str, status: str, notes: str = None) -> WarrantyClaimMetadata | None:
    record = find_by_claim_hash(claim_hash)
    if not record:
        return None
    record.status = status
    if notes is not None:
        record.approved_notes = notes
    record.approved_at = datetime.utcnow()
    db.session.commit()
    return record
