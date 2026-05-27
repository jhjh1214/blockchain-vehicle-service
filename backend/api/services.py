from datetime import datetime
from flask import Blueprint, request, jsonify
from api.middleware import token_required, role_required
from api.utils import sanitize, validate_vin, validate_mileage, paginate
from core import service_log_service

service_bp = Blueprint('service', __name__)


@service_bp.route('/submit', methods=['POST'])
@role_required('SERVICE_CENTER')
def submit_service():
    # Support both JSON (no photos) and multipart/form-data (with photo files)
    ct = request.content_type or ''
    if 'multipart/form-data' in ct:
        import json as _json
        data = request.form.to_dict()
        try:
            data['mileage'] = int(data.get('mileage', 0))
        except (ValueError, TypeError):
            data['mileage'] = 0
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

    service_type = sanitize(data.get('service_type', ''), 100)
    service_date = sanitize(data.get('service_date', ''), 20)
    if not service_type or not service_date:
        return jsonify({'error': 'Missing required fields: service_type, service_date'}), 400

    sc_brand = request.user.get('brand', '')
    if sc_brand:
        from db.repositories import vehicles as vehicle_repo
        mapping = vehicle_repo.find_by_vin(vin)
        if mapping and mapping.make and mapping.make.lower() != sc_brand.lower():
            return jsonify({'error': f"Brand mismatch: your service centre is authorised for '{sc_brand}' vehicles only"}), 403

    try:
        result = service_log_service.submit_service(
            vin=vin,
            service_type=service_type,
            service_date=service_date,
            mileage=mileage,
            parts_replaced=sanitize(data.get('parts_replaced', ''), 500),
            technician_name=sanitize(data.get('technician_name', ''), 100),
            service_notes=sanitize(data.get('service_notes', ''), 1000),
            ecu_modules=data.get('ecu_modules', []),
            photos=data.get('photos', []),
            from_address=request.user['blockchain_address']
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/verify', methods=['POST'])
@token_required
def verify_service():
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    record_index = data.get('record_index')
    if record_index is None:
        return jsonify({'error': 'record_index required'}), 400
    try:
        result = service_log_service.verify_service(vin, record_index, request.user['blockchain_address'])
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/dispute', methods=['POST'])
@token_required
def dispute_service():
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    record_index = data.get('record_index')
    reason = sanitize(data.get('reason', ''), 500)
    if record_index is None or not reason:
        return jsonify({'error': 'record_index and reason required'}), 400
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

    sm.rebuttal_notes = rebuttal
    sm.rebuttal_submitted_at = datetime.utcnow()
    _db.session.commit()

    return jsonify({'message': 'Rebuttal submitted successfully', 'vin': vin}), 200


@service_bp.route('/resolve-dispute', methods=['POST'])
@role_required('MANUFACTURER')
def resolve_dispute():
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    record_index = data.get('record_index')
    decision     = data.get('decision')
    if record_index is None or decision is None:
        return jsonify({'error': 'record_index and decision required'}), 400
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
        return jsonify({'error': str(e)}), 500


@service_bp.route('/owner/verify', methods=['POST'])
@role_required('OWNER')
def owner_verify_service():
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    record_index = data.get('record_index')
    if record_index is None:
        return jsonify({'error': 'record_index required'}), 400
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
    record_index = data.get('record_index')
    reason = sanitize(data.get('reason', ''), 500)
    if record_index is None or not reason:
        return jsonify({'error': 'record_index and reason required'}), 400
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
