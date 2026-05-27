import json
from datetime import datetime
from blockchain.adapters.service_log import service_log
from blockchain.adapters.vehicle_registry import vehicle_registry
from blockchain.utils import compute_metadata_hash, compute_string_hash
from db.repositories import services as service_repo, vehicles as vehicle_repo
from db.models import User as _User


def submit_service(vin: str, service_type: str, service_date: str, mileage: int,
                   parts_replaced: str, technician_name: str, service_notes: str,
                   ecu_modules: list, photos: list, from_address: str) -> dict:
    metadata = {
        'service_type': service_type,
        'service_date': service_date,
        'mileage': mileage,
        'parts_replaced': parts_replaced or '',
        'technician_name': technician_name or '',
        'service_notes': service_notes or '',
        'ecu_modules': ecu_modules or [],
        'photos': photos or []
    }
    metadata_hash = compute_metadata_hash(metadata)

    service_repo.create(
        vin=vin,
        metadata_hash=metadata_hash,
        service_type=service_type,
        service_date=datetime.fromisoformat(service_date.replace('Z', '+00:00')),
        mileage=mileage,
        parts_replaced=parts_replaced,
        technician_name=technician_name,
        service_notes=service_notes,
        photos=photos or [],
        service_center_address=from_address
    )

    result = service_log.submit_service(vin, metadata_hash, from_address)

    return {
        'message': 'Service submitted successfully',
        'vin': vin,
        'metadata_hash': metadata_hash,
        'status': 'pending',
        'transaction': result
    }


def verify_service(vin: str, record_index: int, from_address: str) -> dict:
    result = service_log.verify_service(vin, record_index, from_address)
    return {
        'message': 'Service verified successfully',
        'vin': vin,
        'record_index': record_index,
        'transaction': result
    }


def dispute_service(vin: str, record_index: int, reason: str, from_address: str) -> dict:
    result = service_log.dispute_service(vin, record_index, reason, from_address)
    return {
        'message': 'Service disputed successfully',
        'vin': vin,
        'record_index': record_index,
        'reason': reason,
        'transaction': result
    }


def resolve_dispute(vin: str, record_index: int, decision: int,
                    resolution_notes: str, from_address: str) -> dict:
    resolution_hash = compute_string_hash(resolution_notes or '')
    result = service_log.resolve_dispute(vin, record_index, decision, resolution_hash, from_address)
    return {
        'message': 'Dispute resolved successfully',
        'vin': vin,
        'record_index': record_index,
        'decision': {1: 'approved', 2: 'rejected', 3: 'modify'}.get(decision, 'rejected'),
        'transaction': result
    }


def _enrich_records(records: list) -> list:
    for record in records:
        metadata = service_repo.find_by_metadata_hash(record['metadata_hash'])
        if metadata:
            record['metadata'] = {
                'service_type': metadata.service_type,
                'service_date': metadata.service_date.isoformat() if metadata.service_date else None,
                'mileage': metadata.mileage,
                'parts_replaced': metadata.parts_replaced,
                'technician_name': metadata.technician_name,
                'service_notes': metadata.service_notes,
                'photos': metadata.photos or [],
                'rebuttal_notes': metadata.rebuttal_notes,
                'rebuttal_submitted_at': metadata.rebuttal_submitted_at.isoformat() if metadata.rebuttal_submitted_at else None,
            }
    return records


def get_pending_services(vin: str) -> list:
    return _enrich_records(service_log.get_pending_services(vin))


def get_sc_pending_services(sc_address: str) -> list:
    """All pending records across all VINs that were submitted by this service centre."""
    from db.models import ServiceMetadata
    sc_vins = (
        ServiceMetadata.query
        .filter_by(service_center_address=sc_address)
        .with_entities(ServiceMetadata.vin)
        .distinct()
        .all()
    )
    all_pending = []
    for (vin,) in sc_vins:
        mapping = vehicle_repo.find_by_vin(vin)
        raw_records = service_log.get_pending_services(vin)
        for idx, record in enumerate(raw_records):
            if record.get('service_center', '').lower() != sc_address.lower():
                continue
            metadata = service_repo.find_by_metadata_hash(record['metadata_hash'])
            if metadata:
                record['metadata'] = {
                    'service_type': metadata.service_type,
                    'service_date': metadata.service_date.isoformat() if metadata.service_date else None,
                    'mileage': metadata.mileage,
                    'technician_name': metadata.technician_name,
                    'parts_replaced': metadata.parts_replaced,
                    'service_notes': metadata.service_notes,
                    'photos': metadata.photos or []
                }
            flat = _flatten_owner_record(record, idx, mapping) if mapping else {}
            if not flat:
                flat = {
                    'vin': vin,
                    'record_index': idx,
                    'metadata_hash': record.get('metadata_hash', ''),
                    'status': 'disputed' if record.get('disputed') else 'pending',
                    'dispute_reason': record.get('dispute_reason'),
                    **record.get('metadata', {}),
                }
            all_pending.append(flat)
    return all_pending


def get_finalized_services(vin: str) -> list:
    return _enrich_records(service_log.get_finalized_services(vin))


def _flatten_owner_record(record, index: int, mapping) -> dict:
    """Produce a flat dict matching what the Flutter ServiceRecord.fromJson expects."""
    meta = record.get('metadata', {})
    verified = record.get('verified', False)
    disputed = record.get('disputed', False)
    if disputed:
        status = 'disputed'
    elif verified:
        status = 'verified'
    else:
        status = 'pending'
    sc_address = record.get('service_center', '')
    sc_user = _User.query.filter_by(blockchain_address=sc_address.lower()).first() if sc_address else None
    return {
        'vin': mapping.vin,
        'record_index': index,
        'service_type': meta.get('service_type', ''),
        'service_date': meta.get('service_date', ''),
        'mileage': meta.get('mileage'),
        'parts_replaced': meta.get('parts_replaced'),
        'technician_name': meta.get('technician_name'),
        'service_notes': meta.get('service_notes'),
        'photos': meta.get('photos', []),
        'status': status,
        'dispute_reason': record.get('dispute_reason'),
        'submitted_by': sc_address,
        'service_center_name': sc_user.name if sc_user else sc_address,
        'make': mapping.make,
        'model': mapping.model,
        'year': mapping.year,
        'metadata_hash': record.get('metadata_hash', ''),
        'rebuttal_notes': meta.get('rebuttal_notes'),
        'rebuttal_submitted_at': meta.get('rebuttal_submitted_at'),
    }


def get_owner_finalized_services(owner_address: str) -> list:
    vin_hashes = vehicle_registry.get_owned_vehicles(owner_address)
    all_finalized = []
    for vin_hash in vin_hashes:
        mapping = vehicle_repo.find_by_vin_hash(vin_hash)
        if not mapping:
            continue
        raw_records = service_log.get_finalized_services(mapping.vin)
        for idx, record in enumerate(raw_records):
            metadata = service_repo.find_by_metadata_hash(record['metadata_hash'])
            if metadata:
                record['metadata'] = {
                    'service_type': metadata.service_type,
                    'service_date': metadata.service_date.isoformat() if metadata.service_date else None,
                    'mileage': metadata.mileage,
                    'technician_name': metadata.technician_name,
                    'parts_replaced': metadata.parts_replaced,
                    'service_notes': metadata.service_notes,
                    'photos': metadata.photos or []
                }
            all_finalized.append(_flatten_owner_record(record, idx, mapping))
    return all_finalized


def get_owner_pending_services(owner_address: str) -> list:
    vin_hashes = vehicle_registry.get_owned_vehicles(owner_address)
    all_pending = []
    for vin_hash in vin_hashes:
        mapping = vehicle_repo.find_by_vin_hash(vin_hash)
        if not mapping:
            continue
        raw_records = service_log.get_pending_services(mapping.vin)
        for idx, record in enumerate(raw_records):
            metadata = service_repo.find_by_metadata_hash(record['metadata_hash'])
            if metadata:
                record['metadata'] = {
                    'service_type': metadata.service_type,
                    'service_date': metadata.service_date.isoformat() if metadata.service_date else None,
                    'mileage': metadata.mileage,
                    'technician_name': metadata.technician_name,
                    'parts_replaced': metadata.parts_replaced,
                    'service_notes': metadata.service_notes,
                    'photos': metadata.photos or []
                }
            all_pending.append(_flatten_owner_record(record, idx, mapping))
    return all_pending
