import json
from datetime import datetime
from blockchain.adapters.service_log import service_log
from blockchain.adapters.vehicle_registry import vehicle_registry
from blockchain.utils import compute_metadata_hash, compute_string_hash
from db.repositories import services as service_repo, vehicles as vehicle_repo


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
        photos=photos or []
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
        'decision': 'approved' if decision == 1 else 'rejected',
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
                'photos': metadata.photos or []
            }
    return records


def get_pending_services(vin: str) -> list:
    return _enrich_records(service_log.get_pending_services(vin))


def get_finalized_services(vin: str) -> list:
    return _enrich_records(service_log.get_finalized_services(vin))


def get_owner_finalized_services(owner_address: str) -> list:
    vin_hashes = vehicle_registry.get_owned_vehicles(owner_address)
    all_finalized = []
    for vin_hash in vin_hashes:
        mapping = vehicle_repo.find_by_vin_hash(vin_hash)
        if not mapping:
            continue
        records = service_log.get_finalized_services(mapping.vin)
        for record in records:
            metadata = service_repo.find_by_metadata_hash(record['metadata_hash'])
            record['vin'] = mapping.vin
            record['make'] = mapping.make
            record['model'] = mapping.model
            record['year'] = mapping.year
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
            all_finalized.append(record)
    return all_finalized


def get_owner_pending_services(owner_address: str) -> list:
    vin_hashes = vehicle_registry.get_owned_vehicles(owner_address)
    all_pending = []
    for vin_hash in vin_hashes:
        mapping = vehicle_repo.find_by_vin_hash(vin_hash)
        if not mapping:
            continue
        records = service_log.get_pending_services(mapping.vin)
        for record in records:
            metadata = service_repo.find_by_metadata_hash(record['metadata_hash'])
            record['vin'] = mapping.vin
            record['make'] = mapping.make
            record['model'] = mapping.model
            record['year'] = mapping.year
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
            all_pending.append(record)
    return all_pending
