from flask import Blueprint, request, jsonify
from api.middleware import token_required, role_required
from core import service_log_service

service_bp = Blueprint('service', __name__)


@service_bp.route('/submit', methods=['POST'])
@role_required('SERVICE_CENTER')
def submit_service():
    data = request.get_json() or {}
    vin = data.get('vin')
    service_type = data.get('service_type')
    service_date = data.get('service_date')
    mileage = data.get('mileage')
    if not all([vin, service_type, service_date, mileage is not None]):
        return jsonify({'error': 'Missing required fields: vin, service_type, service_date, mileage'}), 400
    try:
        result = service_log_service.submit_service(
            vin=vin,
            service_type=service_type,
            service_date=service_date,
            mileage=mileage,
            parts_replaced=data.get('parts_replaced', ''),
            technician_name=data.get('technician_name', ''),
            service_notes=data.get('service_notes', ''),
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
    vin = data.get('vin')
    record_index = data.get('record_index')
    if vin is None or record_index is None:
        return jsonify({'error': 'VIN and record_index required'}), 400
    try:
        result = service_log_service.verify_service(vin, record_index, request.user['blockchain_address'])
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/dispute', methods=['POST'])
@token_required
def dispute_service():
    data = request.get_json() or {}
    vin = data.get('vin')
    record_index = data.get('record_index')
    reason = data.get('reason')
    if not all([vin, record_index is not None, reason]):
        return jsonify({'error': 'VIN, record_index, and reason required'}), 400
    try:
        result = service_log_service.dispute_service(vin, record_index, reason, request.user['blockchain_address'])
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/resolve-dispute', methods=['POST'])
@role_required('MANUFACTURER')
def resolve_dispute():
    data = request.get_json() or {}
    vin = data.get('vin')
    record_index = data.get('record_index')
    decision = data.get('decision')
    if not all([vin, record_index is not None, decision is not None]):
        return jsonify({'error': 'VIN, record_index, and decision required'}), 400
    try:
        decision_int = int(decision)
    except (TypeError, ValueError):
        return jsonify({'error': 'decision must be an integer: 1=approve, 2=reject'}), 400
    if decision_int not in (1, 2):
        return jsonify({'error': 'decision must be 1 (approve) or 2 (reject)'}), 400
    try:
        result = service_log_service.resolve_dispute(
            vin=vin,
            record_index=record_index,
            decision=decision_int,
            resolution_notes=data.get('resolution_notes', ''),
            from_address=request.user['blockchain_address']
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/pending/<vin>', methods=['GET'])
@token_required
def get_pending_services(vin):
    try:
        records = service_log_service.get_pending_services(vin)
        return jsonify({'vin': vin, 'pending_services': records, 'count': len(records)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/history/<vin>', methods=['GET'])
@token_required
def get_service_history(vin):
    try:
        records = service_log_service.get_finalized_services(vin)
        return jsonify({'vin': vin, 'service_history': records, 'count': len(records)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/owner/pending', methods=['GET'])
@role_required('OWNER')
def get_owner_pending_services():
    try:
        records = service_log_service.get_owner_pending_services(request.user['blockchain_address'])
        return jsonify({'pending_services': records, 'count': len(records)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/owner/verify', methods=['POST'])
@role_required('OWNER')
def owner_verify_service():
    data = request.get_json() or {}
    vin = data.get('vin')
    record_index = data.get('record_index')
    if vin is None or record_index is None:
        return jsonify({'error': 'VIN and record_index required'}), 400
    try:
        result = service_log_service.verify_service(vin, record_index, request.user['blockchain_address'])
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@service_bp.route('/owner/dispute', methods=['POST'])
@role_required('OWNER')
def owner_dispute_service():
    data = request.get_json() or {}
    vin = data.get('vin')
    record_index = data.get('record_index')
    reason = data.get('reason')
    if not all([vin, record_index is not None, reason]):
        return jsonify({'error': 'VIN, record_index, and reason required'}), 400
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
        return jsonify({'service_history': records, 'count': len(records)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
