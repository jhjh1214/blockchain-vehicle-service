import logging
import time
from datetime import datetime
from blockchain.adapters.warranty_tracker import warranty_tracker
from blockchain.adapters.vehicle_registry import vehicle_registry
from blockchain.utils import compute_metadata_hash, compute_string_hash
from db.models import db
from db.repositories import warranties as warranty_repo, vehicles as vehicle_repo

logger = logging.getLogger(__name__)


def check_warranty(vin: str) -> dict:
    result = warranty_tracker.is_warranty_valid(vin)
    vehicle = vehicle_registry.get_vehicle(vin)
    days_remaining = (vehicle['warranty_expiry'] - int(time.time())) // (24 * 60 * 60)
    return {
        'vin': vin,
        'valid': result['valid'],
        'reason': result['reason'],
        'warranty_expiry': vehicle['warranty_expiry'],
        'days_remaining': max(0, days_remaining)
    }


def submit_claim(vin: str, issue_description: str, photos: list, from_address: str) -> dict:
    mapping = vehicle_repo.find_by_vin(vin)
    if not mapping or mapping.owner_address.lower() != from_address.lower():
        raise ValueError('You do not own this vehicle')

    if mapping.warranty_expiry and mapping.warranty_expiry < int(time.time()):
        raise ValueError('Warranty has expired')

    claim_details = {
        'issue_description': issue_description,
        'photos': photos or [],
        'submitted_date': datetime.now().isoformat()
    }
    claim_hash = compute_metadata_hash(claim_details)

    # Blockchain first — DB is the read cache, not the source of truth
    result = warranty_tracker.submit_claim(vin, claim_hash, from_address)

    try:
        warranty_repo.create(
            vin=vin,
            claim_hash=claim_hash,
            issue_description=issue_description,
            photos=photos or []
        )
    except Exception as exc:
        db.session.rollback()
        logger.error('DB sync failed after on-chain warranty claim for VIN %s: %s', vin, exc)
        raise RuntimeError(
            'Warranty claim was submitted on-chain but the database record could not be saved. '
            'Contact support and quote VIN: ' + vin
        ) from exc

    return {
        'message': 'Warranty claim submitted successfully',
        'vin': vin,
        'claim_hash': claim_hash,
        'status': 'pending',
        'transaction': result
    }


def get_claims(vin: str) -> list:
    claims = warranty_tracker.get_claims(vin)
    for claim in claims:
        metadata = warranty_repo.find_by_claim_hash(claim['claim_details_hash'])
        if metadata:
            claim['metadata'] = {
                'issue_description': metadata.issue_description,
                'photos': metadata.photos or [],
                'status': metadata.status,
                'approved_at': metadata.approved_at.isoformat() if metadata.approved_at else None,
                'approved_notes': metadata.approved_notes,
            }
    return claims


def get_owner_claims(owner_address: str) -> list:
    vin_hashes = vehicle_registry.get_owned_vehicles(owner_address)
    all_claims = []
    for vin_hash in vin_hashes:
        mapping = vehicle_repo.find_by_vin_hash(vin_hash)
        if not mapping:
            continue
        claims = warranty_tracker.get_claims(mapping.vin)
        for idx, claim in enumerate(claims):
            metadata = warranty_repo.find_by_claim_hash(claim['claim_details_hash'])
            issue_description = ''
            db_status = 'pending'
            if metadata:
                issue_description = metadata.issue_description or ''
                db_status = metadata.status or 'pending'
            all_claims.append({
                'vin': mapping.vin,
                'claim_index': idx,
                'issue_description': issue_description,
                'status': db_status,
                'denial_reason': None,
                'submitted_at': claim.get('timestamp', 0),
                'make': mapping.make,
                'model': mapping.model,
                'year': mapping.year,
            })
    return all_claims


def get_mfr_claims(mfr_address: str) -> list:
    """All warranty claims across every VIN this manufacturer registered.

    Mirrors get_owner_claims' shape but keyed by registering manufacturer instead
    of owner, and nests metadata like get_claims() so the existing per-VIN claims
    UI can render aggregate rows without any template changes.
    """
    mappings = vehicle_repo.find_by_registered_by(mfr_address)
    all_claims = []
    for mapping in mappings:
        claims = warranty_tracker.get_claims(mapping.vin)
        for idx, claim in enumerate(claims):
            metadata = warranty_repo.find_by_claim_hash(claim['claim_details_hash'])
            issue_description = ''
            photos = []
            db_status = 'pending'
            if metadata:
                issue_description = metadata.issue_description or ''
                photos = metadata.photos or []
                db_status = metadata.status or 'pending'
            all_claims.append({
                'vin': mapping.vin,
                'claim_index': idx,
                'claim_details_hash': claim.get('claim_details_hash', ''),
                'timestamp': claim.get('timestamp', 0),
                'claimant': claim.get('claimant', ''),
                'status': db_status,
                'resolution_notes_hash': claim.get('resolution_notes_hash'),
                'metadata': {'issue_description': issue_description, 'photos': photos},
                'make': mapping.make,
                'model': mapping.model,
                'year': mapping.year,
            })
    all_claims.sort(key=lambda c: (c['status'] != 'pending', -(c.get('timestamp') or 0)))
    return all_claims


def approve_claim(vin: str, claim_index: int, from_address: str, notes: str = '') -> dict:
    mapping = vehicle_repo.find_by_vin(vin)
    if mapping and mapping.warranty_expiry and mapping.warranty_expiry < int(time.time()):
        raise ValueError('Cannot approve: the warranty for this vehicle has since expired')
    result = warranty_tracker.approve_claim(vin, claim_index, from_address)
    # Persist status to DB: look up the claim by index
    claims = warranty_tracker.get_claims(vin)
    if claim_index < len(claims):
        claim_hash = claims[claim_index].get('claim_details_hash', '')
        if claim_hash:
            warranty_repo.update_status(claim_hash, 'approved', notes or None)
    return {
        'message': 'Warranty claim approved',
        'vin': vin,
        'claim_index': claim_index,
        'transaction': result
    }


def deny_claim(vin: str, claim_index: int, reason: str, from_address: str) -> dict:
    reason_hash = compute_string_hash(reason or '')
    result = warranty_tracker.deny_claim(vin, claim_index, reason_hash, from_address)
    # Persist status to DB: look up the claim by index
    claims = warranty_tracker.get_claims(vin)
    if claim_index < len(claims):
        claim_hash = claims[claim_index].get('claim_details_hash', '')
        if claim_hash:
            warranty_repo.update_status(claim_hash, 'denied', reason or None)
    return {
        'message': 'Warranty claim denied',
        'vin': vin,
        'claim_index': claim_index,
        'reason': reason,
        'transaction': result
    }
