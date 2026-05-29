import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from api.middleware import token_required, role_required
from api.utils import sanitize, validate_vin, validate_mileage, paginate
from core import service_log_service

logger = logging.getLogger(__name__)
service_bp = Blueprint('service', __name__)


@service_bp.route('/submit', methods=['POST'])
@role_required('SERVICE_CENTER')
def submit_service():
    from db.models import User as _UserModel
    _sc_user = _UserModel.query.filter_by(blockchain_address=request.user['blockchain_address']).first()
    if _sc_user and _sc_user.status != 'active':
        return jsonify({'error': 'Your service centre account is suspended and cannot submit records'}), 403

    # Support both JSON (no photos) and multipart/form-data (with photo files)
    ct = request.content_type or ''
    if 'multipart/form-data' in ct:
        import json as _json
        data = request.form.to_dict()
        try:
            data['ecu_modules'] = _json.loads(data.get('ecu_modules', '[]'))
        except Exception:
            data['ecu_modules'] = []
        # Save uploaded photo files
        from core.upload_service import save_file as _save_file
        photo_filenames = []
        for f in request.files.getlist('photos'):
            if f and f.filename:
                try:
                    res = _save_file(f, request.user['user_id'])
                    photo_filenames.append(res['filename'])
                except Exception:
                    pass
        data['photos'] = photo_filenames
    else:
        data = request.get_json() or {}

    try:
        vin     = validate_vin(data.get('vin', ''))
        mileage = validate_mileage(data.get('mileage'))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    ecu_modules = data.get('ecu_modules', [])
    if not isinstance(ecu_modules, list):
        return jsonify({'error': 'ecu_modules must be a list'}), 400
    if len(ecu_modules) > 20:
        return jsonify({'error': 'ecu_modules cannot contain more than 20 entries'}), 400
    ecu_modules = [str(m)[:100] for m in ecu_modules]

    service_type = sanitize(data.get('service_type', ''), 100)
    service_date = sanitize(data.get('service_date', ''), 35)
    if not service_type or not service_date:
        return jsonify({'error': 'Missing required fields: service_type, service_date'}), 400

    from datetime import date as _date
    try:
        svc_dt = datetime.fromisoformat(service_date.replace('Z', '+00:00'))
        if svc_dt.date() > _date.today():
            return jsonify({'error': 'service_date cannot be in the future'}), 400
        if svc_dt.year < 2000:
            return jsonify({'error': 'service_date must be on or after year 2000'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid service_date format. Use ISO 8601 (e.g. 2024-01-15T10:00:00)'}), 400

    from db.repositories import vehicles as vehicle_repo
    mapping = vehicle_repo.find_by_vin(vin)
    if mapping and mapping.registration_status == 'pending':
        return jsonify({'error': 'Cannot submit a service record for a vehicle with no registered owner'}), 400

    sc_brand = request.user.get('brand', '')
    if sc_brand:
        if mapping and mapping.make and mapping.make.lower() != sc_brand.lower():
            return jsonify({'error': f"Brand mismatch: your service centre is authorised for '{sc_brand}' vehicles only"}), 403

    from db.models import ServiceMetadata, db as _db
    max_mileage = _db.session.query(_db.func.max(ServiceMetadata.mileage)).filter(
        ServiceMetadata.vin == vin
    ).scalar()
    if max_mileage is not None and mileage < max_mileage:
        return jsonify({'error': f'Mileage cannot decrease: last recorded mileage is {max_mileage} km'}), 400

    try:
        result = service_log_service.submit_service(
            vin=vin,
            service_type=service_type,
            service_date=service_date,
            mileage=mileage,
            parts_replaced=sanitize(data.get('parts_replaced', ''), 500),
            technician_name=sanitize(data.get('technician_name', ''), 100),
            service_notes=sanitize(data.get('service_notes', ''), 1000),
            ecu_modules=ecu_modules,
            photos=data.get('photos', []),
            from_address=request.user['blockchain_address']
        )
        # Notify owner about the new pending service record
        from db.repositories import users as user_repo
        from core.notifications import notify_new_pending_service
        owner_mapping = vehicle_repo.find_by_vin(vin)
        if owner_mapping and owner_mapping.owner_address:
            owner = user_repo.find_by_blockchain_address(owner_mapping.owner_address)
            if owner:
                notify_new_pending_service(owner.id, vin, service_type)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/verify', methods=['POST'])
@role_required('OWNER')
def verify_service():
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    try:
        record_index = int(data.get('record_index'))
        if record_index < 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({'error': 'record_index must be a non-negative integer'}), 400
    from db.repositories import vehicles as vehicle_repo
    mapping = vehicle_repo.find_by_vin(vin)
    if not mapping or mapping.owner_address.lower() != request.user['blockchain_address'].lower():
        return jsonify({'error': 'You do not own this vehicle'}), 403
    try:
        result = service_log_service.verify_service(vin, record_index, request.user['blockchain_address'])
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/dispute', methods=['POST'])
@role_required('OWNER')
def dispute_service():
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    try:
        record_index = int(data.get('record_index'))
        if record_index < 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({'error': 'record_index must be a non-negative integer'}), 400
    reason = sanitize(data.get('reason', ''), 500)
    if not reason:
        return jsonify({'error': 'reason required'}), 400
    from db.repositories import vehicles as vehicle_repo
    mapping = vehicle_repo.find_by_vin(vin)
    if not mapping or mapping.owner_address.lower() != request.user['blockchain_address'].lower():
        return jsonify({'error': 'You do not own this vehicle'}), 403
    try:
        result = service_log_service.dispute_service(vin, record_index, reason, request.user['blockchain_address'])
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/dispute-response', methods=['POST'])
@role_required('SERVICE_CENTER')
def submit_dispute_response():
    """Service centre submits a rebuttal to an owner's dispute before manufacturer resolves."""
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    metadata_hash = sanitize(data.get('metadata_hash', ''), 66)
    rebuttal = sanitize(data.get('rebuttal_notes', ''), 1000)
    if not metadata_hash or not rebuttal:
        return jsonify({'error': 'metadata_hash and rebuttal_notes required'}), 400

    from db.models import db as _db, ServiceMetadata
    sm = ServiceMetadata.query.filter_by(
        metadata_hash=metadata_hash,
        service_center_address=request.user['blockchain_address']
    ).first()
    if not sm:
        return jsonify({'error': 'Service record not found or not owned by your service centre'}), 404
    if not sm.disputed:
        return jsonify({'error': 'Record is not disputed'}), 400

    try:
        sm.rebuttal_notes = rebuttal
        sm.rebuttal_submitted_at = datetime.utcnow()
        _db.session.commit()
    except Exception:
        _db.session.rollback()
        logger.exception('Failed to save rebuttal')
        return jsonify({'error': 'Failed to save rebuttal. Please try again.'}), 500

    return jsonify({'message': 'Rebuttal submitted successfully', 'vin': vin}), 200


@service_bp.route('/escalate-dispute', methods=['POST'])
@role_required('SERVICE_CENTER')
def escalate_dispute():
    """Service centre formally escalates a disputed record to manufacturer priority review."""
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    metadata_hash = sanitize(data.get('metadata_hash', ''), 66)
    if not metadata_hash:
        return jsonify({'error': 'metadata_hash required'}), 400

    from db.models import ServiceMetadata
    sm = ServiceMetadata.query.filter_by(
        metadata_hash=metadata_hash,
        service_center_address=request.user['blockchain_address']
    ).first()
    if not sm:
        return jsonify({'error': 'Service record not found or not owned by your service centre'}), 404
    if not sm.disputed:
        return jsonify({'error': 'Only disputed records can be escalated'}), 400
    if sm.escalated:
        return jsonify({'message': 'Record already escalated', 'vin': vin}), 200

    from db.repositories import services as service_repo
    try:
        service_repo.set_escalated(metadata_hash)
    except Exception:
        logger.exception('Failed to escalate dispute')
        return jsonify({'error': 'Failed to escalate dispute. Please try again.'}), 500

    return jsonify({
        'message': 'Dispute escalated successfully',
        'vin': vin,
        'metadata_hash': metadata_hash,
    }), 200


@service_bp.route('/resolve-dispute', methods=['POST'])
@role_required('MANUFACTURER')
def resolve_dispute():
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    try:
        record_index = int(data.get('record_index'))
        if record_index < 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({'error': 'record_index must be a non-negative integer'}), 400
    decision = data.get('decision')
    if decision is None:
        return jsonify({'error': 'decision required'}), 400
    try:
        decision_int = int(decision)
    except (TypeError, ValueError):
        return jsonify({'error': 'decision must be 1 (approve), 2 (reject), or 3 (modify)'}), 400
    if decision_int not in (1, 2, 3):
        return jsonify({'error': 'decision must be 1 (approve), 2 (reject), or 3 (modify)'}), 400

    from db.repositories import vehicles as vehicle_repo
    mapping = vehicle_repo.find_by_vin(vin)
    if mapping and mapping.registered_by and mapping.registered_by != request.user['blockchain_address']:
        return jsonify({'error': 'You can only resolve disputes for vehicles your brand registered'}), 403

    try:
        result = service_log_service.resolve_dispute(
            vin=vin,
            record_index=record_index,
            decision=decision_int,
            resolution_notes=sanitize(data.get('resolution_notes', ''), 500),
            from_address=request.user['blockchain_address']
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/pending/<vin>', methods=['GET'])
@token_required
def get_pending_services(vin):
    try:
        vin = validate_vin(vin)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    from db.repositories import vehicles as vehicle_repo
    mapping = vehicle_repo.find_by_vin(vin)
    role = request.user.get('role')
    if role == 'OWNER':
        if not mapping or mapping.owner_address.lower() != request.user['blockchain_address'].lower():
            return jsonify({'error': 'You do not own this vehicle'}), 403
    elif role in ('MANUFACTURER', 'SERVICE_CENTER'):
        user_brand = request.user.get('brand', '')
        if user_brand and mapping and mapping.make and mapping.make.lower() != user_brand.lower():
            return jsonify({'error': 'Vehicle belongs to a different brand'}), 403
    else:
        return jsonify({'error': 'Insufficient permissions'}), 403

    try:
        records = service_log_service.get_pending_services(vin)
        result  = paginate(records, request.args)
        return jsonify({**result, 'vin': vin, 'pending_services': result.pop('items')}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/history/<vin>', methods=['GET'])
@token_required
def get_service_history(vin):
    try:
        vin = validate_vin(vin)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    try:
        records = service_log_service.get_finalized_services(vin)
        result  = paginate(records, request.args)
        return jsonify({**result, 'vin': vin, 'service_history': result.pop('items')}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/owner/pending', methods=['GET'])
@role_required('OWNER')
def get_owner_pending_services():
    try:
        records = service_log_service.get_owner_pending_services(request.user['blockchain_address'])
        result  = paginate(records, request.args)
        return jsonify({**result, 'pending_services': result.pop('items')}), 200
    except Exception as e:
        logger.exception('Error in get_owner_pending_services')
        return jsonify({'error': str(e)}), 500


@service_bp.route('/owner/verify', methods=['POST'])
@role_required('OWNER')
def owner_verify_service():
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    try:
        record_index = int(data.get('record_index'))
        if record_index < 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({'error': 'record_index must be a non-negative integer'}), 400
    from db.repositories import vehicles as vehicle_repo
    mapping = vehicle_repo.find_by_vin(vin)
    if not mapping or mapping.owner_address.lower() != request.user['blockchain_address'].lower():
        return jsonify({'error': 'You do not own this vehicle'}), 403
    try:
        result = service_log_service.verify_service(vin, record_index, request.user['blockchain_address'])
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/owner/dispute', methods=['POST'])
@role_required('OWNER')
def owner_dispute_service():
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    try:
        record_index = int(data.get('record_index'))
        if record_index < 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({'error': 'record_index must be a non-negative integer'}), 400
    reason = sanitize(data.get('reason', ''), 500)
    if not reason:
        return jsonify({'error': 'reason required'}), 400
    from db.repositories import vehicles as vehicle_repo
    mapping = vehicle_repo.find_by_vin(vin)
    if not mapping or mapping.owner_address.lower() != request.user['blockchain_address'].lower():
        return jsonify({'error': 'You do not own this vehicle'}), 403
    try:
        # Fetch pending record to get metadata_hash before disputing
        from blockchain.adapters.service_log import service_log as _sl
        pending = _sl.get_pending_services(vin)
        metadata_hash_for_record = None
        if pending and record_index < len(pending):
            metadata_hash_for_record = pending[record_index].get('metadata_hash')

        result = service_log_service.dispute_service(vin, record_index, reason, request.user['blockchain_address'])

        # Mark the corresponding ServiceMetadata row as disputed for dispute-rate tracking
        if metadata_hash_for_record:
            from db.models import db as _db, ServiceMetadata
            sm = ServiceMetadata.query.filter_by(metadata_hash=metadata_hash_for_record).first()
            if sm:
                sm.disputed = True
                _db.session.commit()

        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/center/pending', methods=['GET'])
@role_required('SERVICE_CENTER')
def get_sc_pending_records():
    """All pending service records submitted by this service center across all VINs."""
    try:
        records = service_log_service.get_sc_pending_services(request.user['blockchain_address'])
        result = paginate(records, request.args)
        return jsonify({**result, 'pending_services': result.pop('items')}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/owner/history', methods=['GET'])
@role_required('OWNER')
def get_owner_service_history():
    try:
        records = service_log_service.get_owner_finalized_services(request.user['blockchain_address'])
        result  = paginate(records, request.args)
        return jsonify({**result, 'service_history': result.pop('items')}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/dispute-messages/<vin>/<int:record_index>', methods=['GET'])
@token_required
def get_dispute_messages(vin, record_index):
    try:
        vin = validate_vin(vin)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    from db.models import DisputeMessage
    from db.repositories import vehicles as vehicle_repo

    mapping = vehicle_repo.find_by_vin(vin)
    role = request.user.get('role')
    addr = request.user['blockchain_address'].lower()
    if role == 'OWNER':
        if not mapping or mapping.owner_address.lower() != addr:
            return jsonify({'error': 'Access denied'}), 403
    elif role == 'SERVICE_CENTER':
        from db.models import ServiceMetadata
        if not ServiceMetadata.query.filter_by(vin=vin).filter(
                ServiceMetadata.service_center_address.ilike(addr)).first():
            return jsonify({'error': 'Access denied'}), 403
    elif role != 'MANUFACTURER':
        return jsonify({'error': 'Access denied'}), 403

    messages = (DisputeMessage.query
                .filter_by(vin=vin, record_index=record_index)
                .order_by(DisputeMessage.created_at.asc())
                .all())
    return jsonify({'messages': [m.to_dict() for m in messages]}), 200


@service_bp.route('/dispute-messages', methods=['POST'])
@token_required
def post_dispute_message():
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    try:
        record_index = int(data.get('record_index'))
        if record_index < 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({'error': 'record_index must be a non-negative integer'}), 400

    message = sanitize(data.get('message', ''), 1000).strip()
    if not message:
        return jsonify({'error': 'message required'}), 400

    from db.models import DisputeMessage, ServiceMetadata, db as _db
    from db.repositories import vehicles as vehicle_repo, users as user_repo

    role = request.user.get('role')
    addr = request.user['blockchain_address'].lower()
    mapping = vehicle_repo.find_by_vin(vin)

    if role == 'OWNER':
        if not mapping or mapping.owner_address.lower() != addr:
            return jsonify({'error': 'Access denied'}), 403
    elif role == 'SERVICE_CENTER':
        if not ServiceMetadata.query.filter_by(vin=vin).filter(
                ServiceMetadata.service_center_address.ilike(addr)).first():
            return jsonify({'error': 'Access denied'}), 403
    elif role != 'MANUFACTURER':
        return jsonify({'error': 'Access denied'}), 403

    user = user_repo.find_by_blockchain_address(request.user['blockchain_address'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    msg = DisputeMessage(
        vin=vin,
        record_index=record_index,
        sender_id=user.id,
        sender_role=role,
        message=message,
    )
    _db.session.add(msg)
    _db.session.commit()
    return jsonify(msg.to_dict()), 201
