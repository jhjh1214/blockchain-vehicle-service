from db.models import db, WarrantyClaimMetadata


def find_by_claim_hash(claim_hash: str) -> WarrantyClaimMetadata | None:
    return WarrantyClaimMetadata.query.filter_by(claim_hash=claim_hash).first()


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
