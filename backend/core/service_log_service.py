import logging
import time as _time
from datetime import datetime
from blockchain.adapters.service_log import service_log
from blockchain.adapters.vehicle_registry import vehicle_registry
from blockchain.utils import compute_metadata_hash, compute_string_hash
from db.models import db
from db.repositories import services as service_repo, vehicles as vehicle_repo
from db.models import User as _User, ServiceMetadata

logger = logging.getLogger(__name__)


def submit_service(vin: str, service_type: str, service_date: str, mileage: int,
                   parts_replaced: str, technician_name: str, service_notes: str,
                   ecu_modules: list, photos: list, from_address: str,
                   sc_brand: str = '') -> dict:
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

    # Blockchain first — DB is the read cache, not the source of truth
    result = service_log.submit_service(vin, metadata_hash, from_address)

    # Retry the PostgreSQL write up to 3 times — on-chain write already succeeded so we
    # must persist the metadata or the record becomes unreadable from the API.
    last_exc = None
    for attempt in range(3):
        try:
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
                service_center_address=from_address,
                sc_brand=sc_brand or None,
            )
            last_exc = None
            break
        except Exception as exc:
            db.session.rollback()
            last_exc = exc
            logger.warning('DB sync attempt %d/3 failed for VIN %s: %s', attempt + 1, vin, exc)
            if attempt < 2:
                _time.sleep(0.15 * (attempt + 1))  # 0.15 s, 0.30 s

    if last_exc is not None:
        logger.error('DB sync permanently failed for VIN %s after 3 attempts: %s', vin, last_exc)
        raise RuntimeError(
            'Service was recorded on the blockchain but metadata could not be saved to the database. '
            'The on-chain record is safe. Contact support and quote VIN: ' + vin
        ) from last_exc

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
    decision_label = {1: 'approved', 2: 'rejected', 3: 'modify'}.get(decision, 'rejected')

    # Persist resolution to DB via metadata_hash from chain record
    try:
        pending = service_log.get_pending_services(vin)
        if record_index < len(pending):
            meta_hash = pending[record_index].get('metadata_hash', '')
            if meta_hash:
                service_repo.update_resolution(meta_hash, decision_label, resolution_notes or '')
    except Exception as exc:
        logger.warning('Could not persist resolution for VIN %s index %d: %s', vin, record_index, exc)

    return {
        'message': 'Dispute resolved successfully',
        'vin': vin,
        'record_index': record_index,
        'decision': decision_label,
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
                'resolution_decision': metadata.resolution_decision,
                'resolution_notes': metadata.resolution_notes,
                'resolved_at': metadata.resolved_at.isoformat() if metadata.resolved_at else None,
                'escalated': metadata.escalated,
                'escalated_at': metadata.escalated_at.isoformat() if metadata.escalated_at else None,
            }
            record['integrity_status'] = metadata.integrity_status
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
    raw_collected = []
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
                    'photos': metadata.photos or [],
                    'rebuttal_notes': metadata.rebuttal_notes,
                    'rebuttal_submitted_at': metadata.rebuttal_submitted_at.isoformat() if metadata.rebuttal_submitted_at else None,
                    'escalated': metadata.escalated,
                    'escalated_at': metadata.escalated_at.isoformat() if metadata.escalated_at else None,
                }
            raw_collected.append((record, idx, mapping))

    if not raw_collected:
        return []
    sc_user_cache = _load_sc_user_cache([r for r, _, _ in raw_collected])
    result = []
    for record, idx, mapping in raw_collected:
        if mapping:
            result.append(_flatten_owner_record(record, idx, mapping, sc_user_cache))
        else:
            result.append({
                'vin': None,
                'record_index': idx,
                'metadata_hash': record.get('metadata_hash', ''),
                'status': 'disputed' if record.get('disputed') else 'pending',
                'dispute_reason': record.get('dispute_reason'),
                **record.get('metadata', {}),
            })
    return result


def get_finalized_services(vin: str) -> list:
    try:
        return _enrich_records(service_log.get_finalized_services(vin))
    except Exception as exc:
        logger.warning('Blockchain unavailable for get_finalized_services(%s): %s — falling back to DB', vin, exc)
        return _finalized_from_db(vin)


def _finalized_from_db(vin: str) -> list:
    """Return service records from PostgreSQL when blockchain is unreachable.
    Status is set to 'cached' to indicate the verification state is unknown."""
    records = ServiceMetadata.query.filter_by(vin=vin).order_by(ServiceMetadata.service_date).all()
    result = []
    for i, m in enumerate(records):
        sc_user = _User.query.filter(
            _User.blockchain_address.ilike(m.service_center_address)
        ).first() if m.service_center_address else None
        mapping = vehicle_repo.find_by_vin(vin)
        result.append({
            'vin': vin,
            'record_index': i,
            'service_type': m.service_type or '',
            'service_date': m.service_date.isoformat() if m.service_date else '',
            'mileage': m.mileage,
            'parts_replaced': m.parts_replaced,
            'technician_name': m.technician_name,
            'service_notes': m.service_notes,
            'photos': m.photos or [],
            'status': 'cached',  # blockchain verification unavailable
            'dispute_reason': None,
            'submitted_by': m.service_center_address or '',
            'service_center_name': sc_user.name if sc_user else m.service_center_address,
            'service_center_id': sc_user.id if sc_user else None,
            'sc_brand': m.sc_brand,
            'make': mapping.make if mapping else '',
            'model': mapping.model if mapping else '',
            'year': mapping.year if mapping else None,
            'metadata_hash': m.metadata_hash,
            'rebuttal_notes': m.rebuttal_notes,
            'rebuttal_submitted_at': m.rebuttal_submitted_at.isoformat() if m.rebuttal_submitted_at else None,
            '_blockchain_unavailable': True,
        })
    return result


def _load_sc_user_cache(raw_records: list) -> dict:
    """Batch-load service center users to avoid per-record DB queries."""
    addresses = {r.get('service_center', '').lower() for r in raw_records if r.get('service_center')}
    if not addresses:
        return {}
    users = _User.query.filter(_User.blockchain_address.in_(list(addresses))).all()
    return {u.blockchain_address.lower(): u for u in users}


def _flatten_owner_record(record, index: int, mapping, sc_user_cache=None) -> dict:
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
    if sc_user_cache is not None:
        sc_user = sc_user_cache.get(sc_address.lower()) if sc_address else None
    else:
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
        'service_center_id': sc_user.id if sc_user else None,
        'sc_brand': sc_user.brand if sc_user else None,
        'make': mapping.make,
        'model': mapping.model,
        'year': mapping.year,
        'metadata_hash': record.get('metadata_hash', ''),
        'rebuttal_notes': meta.get('rebuttal_notes'),
        'rebuttal_submitted_at': meta.get('rebuttal_submitted_at'),
        'integrity_status': record.get('integrity_status'),
    }


def get_owner_finalized_services(owner_address: str, filters: dict = None) -> list:
    try:
        vin_hashes = vehicle_registry.get_owned_vehicles(owner_address)
    except Exception as exc:
        logger.warning('Blockchain unavailable for get_owner_finalized_services: %s — falling back to DB', exc)
        # Fall back to all VINs owned by this address from DB
        mappings = vehicle_repo.find_by_owner(owner_address)
        result = []
        for m in mappings:
            result.extend(_finalized_from_db(m.vin))
        return result

    collected = []
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
                    'photos': metadata.photos or [],
                    'rebuttal_notes': metadata.rebuttal_notes,
                    'rebuttal_submitted_at': metadata.rebuttal_submitted_at.isoformat() if metadata.rebuttal_submitted_at else None,
                    'escalated': metadata.escalated,
                    'escalated_at': metadata.escalated_at.isoformat() if metadata.escalated_at else None,
                }
                record['integrity_status'] = metadata.integrity_status
            collected.append((record, idx, mapping))

    if not collected:
        return []
    sc_user_cache = _load_sc_user_cache([r for r, _, _ in collected])
    results = [_flatten_owner_record(r, idx, m, sc_user_cache) for r, idx, m in collected]
    if filters:
        results = _apply_filters(results, filters)
    return results


def _apply_filters(records: list, filters: dict) -> list:
    status     = (filters.get('status') or '').strip().lower()
    svc_type   = (filters.get('service_type') or '').strip().lower()
    date_from  = filters.get('date_from')
    date_to    = filters.get('date_to')

    def _keep(r):
        if status and r.get('status', '').lower() != status:
            return False
        if svc_type and svc_type not in (r.get('service_type') or '').lower():
            return False
        svc_date_str = r.get('service_date') or ''
        if svc_date_str and (date_from or date_to):
            try:
                svc_date = datetime.fromisoformat(svc_date_str[:10])
                if date_from and svc_date < datetime.fromisoformat(date_from):
                    return False
                if date_to and svc_date > datetime.fromisoformat(date_to):
                    return False
            except (ValueError, TypeError):
                pass
        return True

    return [r for r in records if _keep(r)]


def get_owner_pending_services(owner_address: str) -> list:
    vin_hashes = vehicle_registry.get_owned_vehicles(owner_address)
    collected = []
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
                    'photos': metadata.photos or [],
                    'rebuttal_notes': metadata.rebuttal_notes,
                    'rebuttal_submitted_at': metadata.rebuttal_submitted_at.isoformat() if metadata.rebuttal_submitted_at else None,
                    'escalated': metadata.escalated,
                    'escalated_at': metadata.escalated_at.isoformat() if metadata.escalated_at else None,
                }
                record['integrity_status'] = metadata.integrity_status
            collected.append((record, idx, mapping))

    if not collected:
        return []
    sc_user_cache = _load_sc_user_cache([r for r, _, _ in collected])
    return [_flatten_owner_record(r, idx, m, sc_user_cache) for r, idx, m in collected]
