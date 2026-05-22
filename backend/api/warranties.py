from flask import Blueprint, request, jsonify
from api.middleware import token_required, role_required
from core import warranty_service

warranty_bp = Blueprint('warranty', __name__)


@warranty_bp.route('/check/<vin>', methods=['GET'])
@token_required
def check_warranty(vin):
    try:
        result = warranty_service.check_warranty(vin)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@warranty_bp.route('/submit-claim', methods=['POST'])
@role_required('OWNER')
def submit_claim():
    data = request.get_json() or {}
    vin = data.get('vin')
    issue_description = data.get('issue_description')
    if not all([vin, issue_description]):
        return jsonify({'error': 'VIN and issue_description required'}), 400
    try:
        result = warranty_service.submit_claim(
            vin=vin,
            issue_description=issue_description,
            photos=data.get('photos', []),
            from_address=request.user['blockchain_address']
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@warranty_bp.route('/claims/<vin>', methods=['GET'])
@token_required
def get_claims(vin):
    try:
        claims = warranty_service.get_claims(vin)
        return jsonify({'vin': vin, 'claims': claims, 'count': len(claims)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@warranty_bp.route('/approve-claim', methods=['POST'])
@role_required('MANUFACTURER')
def approve_claim():
    data = request.get_json() or {}
    vin = data.get('vin')
    claim_index = data.get('claim_index')
    if vin is None or claim_index is None:
        return jsonify({'error': 'VIN and claim_index required'}), 400
    try:
        result = warranty_service.approve_claim(vin, claim_index, request.user['blockchain_address'])
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@warranty_bp.route('/deny-claim', methods=['POST'])
@role_required('MANUFACTURER')
def deny_claim():
    data = request.get_json() or {}
    vin = data.get('vin')
    claim_index = data.get('claim_index')
    if vin is None or claim_index is None:
        return jsonify({'error': 'VIN and claim_index required'}), 400
    try:
        result = warranty_service.deny_claim(
            vin=vin,
            claim_index=claim_index,
            reason=data.get('reason', ''),
            from_address=request.user['blockchain_address']
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@warranty_bp.route('/owner/claims', methods=['GET'])
@role_required('OWNER')
def get_owner_claims():
    try:
        claims = warranty_service.get_owner_claims(request.user['blockchain_address'])
        return jsonify({'claims': claims, 'count': len(claims)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
