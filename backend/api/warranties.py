from flask import Blueprint, request, jsonify
from api.middleware import token_required, role_required
from api.utils import sanitize, validate_vin, paginate
from core import warranty_service

warranty_bp = Blueprint('warranty', __name__)


@warranty_bp.route('/check-eligibility/<vin>', methods=['GET'])
@token_required
def check_warranty_eligibility(vin):
    """Check warranty eligibility before allowing a claim submission.
    Returns validity, reason, days remaining, and whether service history is maintained."""
    try:
        vin = validate_vin(vin)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    try:
        result = warranty_service.check_warranty(vin)
        from blockchain.adapters.service_log import service_log as sl
        finalized = sl.get_finalized_services(vin) or []
        service_count = len(finalized)
        eligible = result['valid'] and service_count >= 0
        return jsonify({
            **result,
            'service_record_count': service_count,
            'service_history_maintained': service_count > 0,
            'eligible_to_claim': eligible,
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@warranty_bp.route('/check/<vin>', methods=['GET'])
@token_required
def check_warranty(vin):
    try:
        vin = validate_vin(vin)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    try:
        result = warranty_service.check_warranty(vin)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@warranty_bp.route('/submit-claim', methods=['POST'])
@role_required('OWNER')
def submit_claim():
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    issue_description = sanitize(data.get('issue_description', ''), 1000)
    if not issue_description:
        return jsonify({'error': 'issue_description required'}), 400
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
        vin = validate_vin(vin)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    try:
        claims = warranty_service.get_claims(vin)
        result = paginate(claims, request.args)
        return jsonify({**result, 'vin': vin, 'claims': result.pop('items')}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@warranty_bp.route('/approve-claim', methods=['POST'])
@role_required('MANUFACTURER')
def approve_claim():
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    claim_index = data.get('claim_index')
    if claim_index is None:
        return jsonify({'error': 'claim_index required'}), 400

    from db.repositories import vehicles as vehicle_repo
    mapping = vehicle_repo.find_by_vin(vin)
    if mapping and mapping.registered_by and mapping.registered_by != request.user['blockchain_address']:
        return jsonify({'error': 'You can only manage warranty claims for vehicles your brand registered'}), 403

    try:
        result = warranty_service.approve_claim(vin, claim_index, request.user['blockchain_address'])
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@warranty_bp.route('/deny-claim', methods=['POST'])
@role_required('MANUFACTURER')
def deny_claim():
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    claim_index = data.get('claim_index')
    if claim_index is None:
        return jsonify({'error': 'claim_index required'}), 400

    from db.repositories import vehicles as vehicle_repo
    mapping = vehicle_repo.find_by_vin(vin)
    if mapping and mapping.registered_by and mapping.registered_by != request.user['blockchain_address']:
        return jsonify({'error': 'You can only manage warranty claims for vehicles your brand registered'}), 403

    try:
        result = warranty_service.deny_claim(
            vin=vin,
            claim_index=claim_index,
            reason=sanitize(data.get('reason', ''), 500),
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
        result = paginate(claims, request.args)
        return jsonify({**result, 'claims': result.pop('items')}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
