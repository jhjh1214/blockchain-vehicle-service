import time
from datetime import datetime
from blockchain.adapters.warranty_tracker import warranty_tracker
from blockchain.adapters.vehicle_registry import vehicle_registry
from blockchain.utils import compute_metadata_hash, compute_string_hash
from db.repositories import warranties as warranty_repo, vehicles as vehicle_repo


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

    warranty_repo.create(
        vin=vin,
        claim_hash=claim_hash,
        issue_description=issue_description,
        photos=photos or []
    )

    result = warranty_tracker.submit_claim(vin, claim_hash, from_address)

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
                'photos': metadata.photos or []
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
            if metadata:
                issue_description = metadata.issue_description or ''
            all_claims.append({
                'vin': mapping.vin,
                'claim_index': idx,
                'issue_description': issue_description,
                'status': claim.get('status', 'pending'),
                'denial_reason': None,
                'submitted_at': claim.get('timestamp', 0),
                'make': mapping.make,
                'model': mapping.model,
                'year': mapping.year,
            })
    return all_claims


def approve_claim(vin: str, claim_index: int, from_address: str) -> dict:
    result = warranty_tracker.approve_claim(vin, claim_index, from_address)
    return {
        'message': 'Warranty claim approved',
        'vin': vin,
        'claim_index': claim_index,
        'transaction': result
    }


def deny_claim(vin: str, claim_index: int, reason: str, from_address: str) -> dict:
    reason_hash = compute_string_hash(reason or '')
    result = warranty_tracker.deny_claim(vin, claim_index, reason_hash, from_address)
    return {
        'message': 'Warranty claim denied',
        'vin': vin,
        'claim_index': claim_index,
        'reason': reason,
        'transaction': result
    }
