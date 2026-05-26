from flask import Blueprint, request, jsonify
from api.middleware import token_required, role_required
from api.utils import sanitize, validate_vin, validate_mileage, paginate
from core import service_log_service

service_bp = Blueprint('service', __name__)


@service_bp.route('/submit', methods=['POST'])
@role_required('SERVICE_CENTER')
def submit_service():
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
        return jsonify({'error': 'decision must be 1 (approve) or 2 (reject)'}), 400
    if decision_int not in (1, 2):
        return jsonify({'error': 'decision must be 1 (approve) or 2 (reject)'}), 400

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
        result = service_log_service.dispute_service(vin, record_index, reason, request.user['blockchain_address'])
        return jsonify(result), 200
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
