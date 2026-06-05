import logging
from datetime import datetime, date as _date
from flask import Blueprint, request, jsonify
from api.middleware import token_required, role_required
from api.utils import sanitize, validate_vin, validate_mileage, paginate
from core import service_log_service
from core.audit import log_event
from config import Config
from extensions import limiter

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

    # Validate photos — must be a list of strings (uploaded filenames), max 20
    photos_raw = data.get('photos', [])
    if not isinstance(photos_raw, list):
        return jsonify({'error': 'photos must be a list'}), 400
    if len(photos_raw) > 20:
        return jsonify({'error': 'photos cannot contain more than 20 entries'}), 400
    photos_clean = [str(p)[:255] for p in photos_raw if isinstance(p, str) and p.strip()]

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

    sc_brand = request.user.get('brand', '') or ''
    if sc_brand:
        if mapping and mapping.make and mapping.make.lower() != sc_brand.lower():
            return jsonify({'error': f"Brand mismatch: your service centre is authorised for '{sc_brand}' vehicles only"}), 403

    from db.models import ServiceMetadata, db as _db
    max_mileage = _db.session.query(_db.func.max(ServiceMetadata.mileage)).filter(
        ServiceMetadata.vin == vin
    ).scalar()
    if max_mileage is not None and mileage < max_mileage:
        return jsonify({'error': f'Mileage cannot decrease: last recorded mileage is {max_mileage} km'}), 400

    # Daily submission limit — prevents SC accounts from spamming the blockchain
    from db.models import ServiceMetadata as _SM
    sc_addr = request.user['blockchain_address']
    today_start = datetime.combine(_date.today(), datetime.min.time())
    today_count = _SM.query.filter(
        _SM.service_center_address.ilike(sc_addr),
        _SM.created_at >= today_start,
    ).count()
    daily_limit = Config.SC_DAILY_SUBMISSION_LIMIT if sc_brand else Config.INDEP_SC_DAILY_LIMIT
    if today_count >= daily_limit:
        return jsonify({'error': f'Daily submission limit of {daily_limit} records reached. Try again tomorrow.'}), 429

    # Detect suspicious mileage gap — configurable threshold
    mileage_gap_warning = None
    if max_mileage is not None and (mileage - max_mileage) > Config.MILEAGE_GAP_THRESHOLD:
        mileage_gap_warning = {
            'gap': mileage - max_mileage,
            'last_authorized_mileage': max_mileage,
        }

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
            photos=photos_clean,
            from_address=request.user['blockchain_address'],
            sc_brand=sc_brand,
        )
        # Notify owner about the new pending service record
        from db.repositories import users as user_repo
        from core.notifications import notify_new_pending_service
        owner_mapping = vehicle_repo.find_by_vin(vin)
        if owner_mapping and owner_mapping.owner_address:
            owner = user_repo.find_by_blockchain_address(owner_mapping.owner_address)
            if owner:
                notify_new_pending_service(owner.id, vin, service_type)
        if mileage_gap_warning:
            result['mileage_gap_warning'] = mileage_gap_warning
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
    metadata_hash = sanitize(data.get('metadata_hash', ''), 66)
    if not metadata_hash:
        return jsonify({'error': 'metadata_hash required'}), 400
    from db.repositories import vehicles as vehicle_repo
    mapping = vehicle_repo.find_by_vin(vin)
    if not mapping or mapping.owner_address.lower() != request.user['blockchain_address'].lower():
        return jsonify({'error': 'You do not own this vehicle'}), 403
    try:
        result = service_log_service.verify_service(vin, metadata_hash, request.user['blockchain_address'])
        log_event('service_verified', user_id=request.user.get('user_id'),
                  detail={'vin': vin, 'metadata_hash': metadata_hash})
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
    metadata_hash = sanitize(data.get('metadata_hash', ''), 66)
    if not metadata_hash:
        return jsonify({'error': 'metadata_hash required'}), 400
    reason = sanitize(data.get('reason', ''), 500)
    if not reason:
        return jsonify({'error': 'reason required'}), 400
    from db.repositories import vehicles as vehicle_repo
    mapping = vehicle_repo.find_by_vin(vin)
    if not mapping or mapping.owner_address.lower() != request.user['blockchain_address'].lower():
        return jsonify({'error': 'You do not own this vehicle'}), 403
    try:
        result = service_log_service.dispute_service(vin, metadata_hash, reason, request.user['blockchain_address'])
        log_event('service_disputed', user_id=request.user.get('user_id'),
                  detail={'vin': vin, 'metadata_hash': metadata_hash, 'reason': reason[:100]})
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
    metadata_hash = sanitize(data.get('metadata_hash', ''), 66)
    if not metadata_hash:
        return jsonify({'error': 'metadata_hash required'}), 400
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
            metadata_hash=metadata_hash,
            decision=decision_int,
            resolution_notes=sanitize(data.get('resolution_notes', ''), 500),
            from_address=request.user['blockchain_address']
        )
        log_event('dispute_resolved', user_id=request.user.get('user_id'),
                  detail={'vin': vin, 'metadata_hash': metadata_hash, 'decision': decision_int})
        # Notify owner via FCM
        from db.repositories import vehicles as vehicle_repo, users as user_repo
        from core.notifications import notify_dispute_resolved
        from core.email import send_email
        _mapping = vehicle_repo.find_by_vin(vin)
        if _mapping and _mapping.owner_address:
            _owner = user_repo.find_by_blockchain_address(_mapping.owner_address)
            if _owner:
                notify_dispute_resolved(_owner.id, vin, decision_int)
        # Email the service centre that submitted the disputed record
        from db.models import ServiceMetadata
        _sm = ServiceMetadata.query.filter_by(vin=vin, disputed=True).order_by(
            ServiceMetadata.id.desc()
        ).first()
        if _sm and _sm.service_center_address:
            _sc = user_repo.find_by_blockchain_address(_sm.service_center_address)
            if _sc:
                decision_labels = {1: 'accepted', 2: 'rejected', 3: 'modified'}
                _label = decision_labels.get(decision_int, 'resolved')
                send_email(
                    _sc.email,
                    f'Dispute Resolution — {vin}',
                    (
                        f'The disputed service record you submitted for vehicle {vin} '
                        f'has been {_label} by the manufacturer.\n\n'
                        f'Log in to VehicleChain to review the resolution details.'
                    ),
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

    role = request.user.get('role')
    caller_address = request.user.get('blockchain_address', '')

    # Owners may only view history for vehicles they own
    if role == 'OWNER':
        from db.repositories import vehicles as vehicle_repo
        mapping = vehicle_repo.find_by_vin(vin)
        if not mapping or mapping.owner_address != caller_address:
            return jsonify({'error': 'You can only view service history for your own vehicles'}), 403

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
    metadata_hash = sanitize(data.get('metadata_hash', ''), 66)
    if not metadata_hash:
        return jsonify({'error': 'metadata_hash required'}), 400
    from db.repositories import vehicles as vehicle_repo
    mapping = vehicle_repo.find_by_vin(vin)
    if not mapping or mapping.owner_address.lower() != request.user['blockchain_address'].lower():
        return jsonify({'error': 'You do not own this vehicle'}), 403
    try:
        result = service_log_service.verify_service(vin, metadata_hash, request.user['blockchain_address'])
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
    metadata_hash = sanitize(data.get('metadata_hash', ''), 66)
    if not metadata_hash:
        return jsonify({'error': 'metadata_hash required'}), 400
    reason = sanitize(data.get('reason', ''), 500)
    if not reason:
        return jsonify({'error': 'reason required'}), 400
    from db.repositories import vehicles as vehicle_repo
    mapping = vehicle_repo.find_by_vin(vin)
    if not mapping or mapping.owner_address.lower() != request.user['blockchain_address'].lower():
        return jsonify({'error': 'You do not own this vehicle'}), 403
    try:
        result = service_log_service.dispute_service(vin, metadata_hash, reason, request.user['blockchain_address'])

        # Mark the corresponding ServiceMetadata row as disputed for dispute-rate tracking
        from db.models import db as _db, ServiceMetadata
        sm = ServiceMetadata.query.filter_by(metadata_hash=metadata_hash).first()
        if sm:
            sm.disputed = True
            _db.session.commit()

        # Email all manufacturers about the new dispute
        from db.repositories import users as _user_repo
        from core.email import send_email as _send_email
        for _mfr in _user_repo.find_all_by_role('MANUFACTURER'):
            _send_email(
                _mfr.email,
                f'Service Dispute Filed — {vin}',
                (
                    f'An owner has disputed a service record for vehicle {vin}.\n\n'
                    f'Reason: {reason}\n\n'
                    f'Log in to VehicleChain to review the dispute and take action.'
                ),
            )

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
    filters = {
        'status':       request.args.get('status'),
        'service_type': request.args.get('service_type'),
        'date_from':    request.args.get('date_from'),
        'date_to':      request.args.get('date_to'),
    }
    try:
        records = service_log_service.get_owner_finalized_services(
            request.user['blockchain_address'], filters=filters
        )
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
@limiter.limit('30 per minute')
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


# ─── Warranty Void Requests ───────────────────────────────────────────────────

@service_bp.route('/void-request', methods=['POST'])
@role_required('SERVICE_CENTER')
def create_void_request():
    data = request.get_json() or {}
    from api.utils import validate_vin
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    reason = (data.get('reason') or '').strip()[:1000]
    if not reason:
        return jsonify({'error': 'reason is required'}), 400

    mileage_submitted = data.get('mileage_submitted')
    last_authorized_mileage = data.get('last_authorized_mileage')

    from db.models import WarrantyVoidRequest, db as _db
    from db.repositories import vehicles as vehicle_repo, users as user_repo

    existing = WarrantyVoidRequest.query.filter_by(vin=vin, status='pending').first()
    if existing:
        return jsonify({'message': 'A pending void request already exists for this VIN', 'request': existing.to_dict()}), 200

    req = WarrantyVoidRequest(
        vin=vin,
        sc_user_id=request.user['user_id'],
        reason=reason,
        mileage_submitted=mileage_submitted,
        last_authorized_mileage=last_authorized_mileage,
    )
    _db.session.add(req)
    _db.session.commit()

    # Notify manufacturer via notification system (find manufacturer for this vehicle's brand)
    try:
        mapping = vehicle_repo.find_by_vin(vin)
        if mapping and mapping.registered_by:
            mfr = user_repo.find_by_blockchain_address(mapping.registered_by)
            if mfr:
                from core.email import send_email
                send_email(
                    to=mfr.email,
                    subject=f'[Warranty Void Request] VIN {vin}',
                    text=f'A service centre has submitted a warranty void request for VIN {vin}.\n\n'
                         f'Reason: {reason}\n\n'
                         f'Please review this in your dashboard.',
                )
        # Also notify the vehicle owner
        if mapping and mapping.owner_address:
            owner = user_repo.find_by_blockchain_address(mapping.owner_address)
            if owner:
                from core.notifications import send_to_user
                send_to_user(
                    owner.id,
                    title='Warranty Void Request',
                    body=f'A service centre has requested to void the warranty on your vehicle {vin}. Tap to review and dispute.',
                    data={'type': 'warranty_void', 'vin': vin, 'request_id': str(req.id)},
                )
    except Exception:
        pass

    return jsonify({'message': 'Void request submitted', 'request': req.to_dict()}), 201


@service_bp.route('/void-requests/manufacturer', methods=['GET'])
@role_required('MANUFACTURER')
def list_void_requests_manufacturer():
    from db.models import WarrantyVoidRequest
    from db.repositories import vehicles as vehicle_repo, users as user_repo

    mfr_brand = request.user.get('brand', '')
    # Get all VINs for vehicles registered by this manufacturer
    reqs = WarrantyVoidRequest.query.order_by(WarrantyVoidRequest.created_at.desc()).all()

    # Filter to only vehicles registered by this manufacturer (same brand)
    result = []
    for r in reqs:
        mapping = vehicle_repo.find_by_vin(r.vin)
        if mapping and mapping.registered_by:
            mfr = user_repo.find_by_blockchain_address(mapping.registered_by)
            if mfr and (not mfr_brand or mfr.brand == mfr_brand) and mfr.id == request.user['user_id']:
                result.append(r.to_dict())

    return jsonify({'requests': result}), 200


@service_bp.route('/void-requests/owner', methods=['GET'])
@role_required('OWNER')
def list_void_requests_owner():
    from db.models import WarrantyVoidRequest
    from db.repositories import vehicles as vehicle_repo

    owner_addr = request.user.get('blockchain_address', '')
    vehicles = vehicle_repo.find_by_owner(owner_addr)
    vins = {v.vin for v in vehicles}
    reqs = WarrantyVoidRequest.query.filter(
        WarrantyVoidRequest.vin.in_(vins)
    ).order_by(WarrantyVoidRequest.created_at.desc()).all()
    return jsonify({'requests': [r.to_dict() for r in reqs]}), 200


@service_bp.route('/void-requests/<int:req_id>/resolve', methods=['POST'])
@role_required('MANUFACTURER')
def resolve_void_request(req_id):
    data = request.get_json() or {}
    decision = data.get('decision')  # 'approved' | 'denied'
    notes = (data.get('notes') or '').strip()[:500]
    if decision not in ('approved', 'denied'):
        return jsonify({'error': "decision must be 'approved' or 'denied'"}), 400

    from db.models import WarrantyVoidRequest, db as _db
    from db.repositories import vehicles as vehicle_repo, users as user_repo

    req = WarrantyVoidRequest.query.get(req_id)
    if not req:
        return jsonify({'error': 'Request not found'}), 404
    if req.status not in ('pending', 'disputed'):
        return jsonify({'error': 'Request already resolved'}), 400

    req.status = decision
    req.manufacturer_notes = notes or None
    req.resolved_at = datetime.utcnow()
    _db.session.commit()

    # If approved — enforce warranty void on-chain so no new claims can be filed
    if decision == 'approved':
        try:
            from blockchain.adapters.warranty_tracker import warranty_tracker
            warranty_tracker.void_warranty(req.vin, request.user['blockchain_address'])
        except Exception as _exc:
            import logging
            logging.getLogger(__name__).warning(
                'Could not void warranty on-chain for VIN %s: %s', req.vin, _exc
            )

    # Notify owner
    try:
        mapping = vehicle_repo.find_by_vin(req.vin)
        if mapping and mapping.owner_address:
            owner = user_repo.find_by_blockchain_address(mapping.owner_address)
            if owner:
                from core.notifications import send_to_user
                label = 'approved — warranty voided' if decision == 'approved' else 'denied — warranty remains valid'
                send_to_user(
                    owner.id,
                    title='Warranty Void Decision',
                    body=f'The warranty void request for {req.vin} has been {label}.',
                    data={'type': 'warranty_void_resolved', 'vin': req.vin, 'decision': decision},
                )
    except Exception:
        pass

    return jsonify({'message': f'Void request {decision}', 'request': req.to_dict()}), 200


@service_bp.route('/void-requests/<int:req_id>/dispute', methods=['POST'])
@role_required('OWNER')
def dispute_void_request(req_id):
    data = request.get_json() or {}
    dispute_reason = (data.get('reason') or '').strip()[:1000]
    if not dispute_reason:
        return jsonify({'error': 'reason is required'}), 400

    from db.models import WarrantyVoidRequest, db as _db
    from db.repositories import vehicles as vehicle_repo

    req = WarrantyVoidRequest.query.get(req_id)
    if not req:
        return jsonify({'error': 'Request not found'}), 404

    owner_addr = request.user.get('blockchain_address', '')
    mapping = vehicle_repo.find_by_vin(req.vin)
    if not mapping or mapping.owner_address.lower() != owner_addr.lower():
        return jsonify({'error': 'You do not own this vehicle'}), 403

    if req.status not in ('pending',):
        return jsonify({'error': 'Can only dispute a pending request'}), 400

    req.status = 'disputed'
    req.owner_dispute_reason = dispute_reason
    _db.session.commit()
    return jsonify({'message': 'Dispute submitted', 'request': req.to_dict()}), 200


# ─── Abuse Reporting ──────────────────────────────────────────────────────────

@service_bp.route('/report', methods=['POST'])
@role_required('OWNER', 'MANUFACTURER', 'SERVICE_CENTER')
def report_abuse():
    data = request.get_json() or {}
    reported_id = data.get('reported_user_id')
    reason = sanitize(data.get('reason', ''), 1000).strip()
    category = data.get('category', 'other')
    vin = data.get('vin', '') or None

    if not reported_id or not reason:
        return jsonify({'error': 'reported_user_id and reason are required'}), 400
    if category not in ('spam', 'fake_service', 'harassment', 'other'):
        category = 'other'

    # Non-owner reporters must supply a VIN as evidence (prevents groundless mass reporting)
    reporter_role = request.user['role']
    if reporter_role in ('MANUFACTURER', 'SERVICE_CENTER') and not vin:
        return jsonify({'error': 'VIN is required for manufacturer and service centre reports'}), 400

    from db.models import AbuseReport, db as _db
    from db.repositories import users as user_repo
    from datetime import timedelta

    target = user_repo.find_by_id(reported_id)
    if not target:
        return jsonify({'error': 'User not found'}), 404

    reporter_id = request.user['user_id']

    # Rate-limit: one report per reporter per target per 24 hours
    cutoff = datetime.utcnow() - timedelta(hours=24)
    existing = AbuseReport.query.filter(
        AbuseReport.reporter_user_id == reporter_id,
        AbuseReport.reported_user_id == reported_id,
        AbuseReport.created_at >= cutoff,
    ).first()
    if existing:
        return jsonify({'error': 'You have already submitted a report for this user in the last 24 hours'}), 429

    report = AbuseReport(
        reported_user_id=reported_id,
        reporter_user_id=reporter_id,
        reporter_role=reporter_role,
        reason=reason,
        category=category,
        vin=vin,
    )
    _db.session.add(report)
    _db.session.commit()

    # Auto-suspend independent SCs — but only if at least one report comes from an owner
    # (prevents manufacturers coordinating to eliminate independent competition)
    if target.role == 'SERVICE_CENTER' and not target.brand:
        all_reports = AbuseReport.query.filter_by(reported_user_id=reported_id).all()
        report_count = len(all_reports)
        has_owner_report = any(r.reporter_role == 'OWNER' for r in all_reports)
        if (report_count >= Config.ABUSE_AUTO_SUSPEND_THRESHOLD
                and has_owner_report
                and target.status != 'suspended'):
            target.status = 'suspended'
            _db.session.commit()
            # Notify admin by email
            try:
                from core.email import send_email
                send_email(
                    to=Config.ADMIN_CONTACT_EMAIL,
                    subject=f'[Auto-Suspend] Independent Workshop {target.email}',
                    text=(
                        f'Independent workshop account {target.name or target.email} '
                        f'(ID {target.id}) has been automatically suspended after '
                        f'{report_count} abuse reports.\n\n'
                        f'Latest report reason: {reason}\n\n'
                        f'Please review at your earliest convenience. '
                        f'The workshop can dispute this suspension by contacting support.'
                    ),
                )
            except Exception:
                pass

    return jsonify({'message': 'Report submitted. Our team will review it.'}), 201
