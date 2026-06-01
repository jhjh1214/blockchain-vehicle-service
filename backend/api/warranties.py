from flask import Blueprint, request, jsonify
from api.middleware import token_required, role_required
from api.utils import sanitize, validate_vin, paginate
from core import warranty_service
from core.audit import log_event
from extensions import limiter

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
@limiter.limit('5 per hour')
def submit_claim():
    ct = request.content_type or ''
    if 'multipart/form-data' in ct:
        data = request.form.to_dict()
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
        # Email all manufacturers about the new warranty claim
        from db.repositories import users as _user_repo
        from core.email import send_email as _send_email
        for _mfr in _user_repo.find_all_by_role('MANUFACTURER'):
            _send_email(
                _mfr.email,
                f'New Warranty Claim — {vin}',
                (
                    f'A warranty claim has been submitted for vehicle {vin}.\n\n'
                    f'Log in to VehicleChain to review and process the claim.'
                ),
            )
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@warranty_bp.route('/claims/<vin>', methods=['GET'])
@role_required('MANUFACTURER')
def get_claims(vin):
    try:
        vin = validate_vin(vin)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    try:
        from db.repositories import vehicles as vehicle_repo
        mapping = vehicle_repo.find_by_vin(vin)
        if mapping and mapping.registered_by and mapping.registered_by != request.user['blockchain_address']:
            return jsonify({'error': 'You can only view warranty claims for vehicles your brand registered'}), 403
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
    try:
        claim_index = int(data.get('claim_index'))
        if claim_index < 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({'error': 'claim_index must be a non-negative integer'}), 400

    from db.repositories import vehicles as vehicle_repo
    mapping = vehicle_repo.find_by_vin(vin)
    if mapping and mapping.registered_by and mapping.registered_by != request.user['blockchain_address']:
        return jsonify({'error': 'You can only manage warranty claims for vehicles your brand registered'}), 403

    try:
        result = warranty_service.approve_claim(vin, claim_index, request.user['blockchain_address'])
        log_event('warranty_claim_approved', user_id=request.user.get('user_id'),
                  detail={'vin': vin, 'claim_index': claim_index})
        _notify_warranty(vin, 'approved')
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
    try:
        claim_index = int(data.get('claim_index'))
        if claim_index < 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({'error': 'claim_index must be a non-negative integer'}), 400

    reason = sanitize(data.get('reason', ''), 500)
    if not reason:
        return jsonify({'error': 'reason required for claim denial'}), 400

    from db.repositories import vehicles as vehicle_repo
    mapping = vehicle_repo.find_by_vin(vin)
    if mapping and mapping.registered_by and mapping.registered_by != request.user['blockchain_address']:
        return jsonify({'error': 'You can only manage warranty claims for vehicles your brand registered'}), 403

    try:
        result = warranty_service.deny_claim(
            vin=vin,
            claim_index=claim_index,
            reason=reason,
            from_address=request.user['blockchain_address']
        )
        log_event('warranty_claim_denied', user_id=request.user.get('user_id'),
                  detail={'vin': vin, 'claim_index': claim_index})
        _notify_warranty(vin, 'denied')
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _notify_warranty(vin: str, status: str) -> None:
    try:
        from db.repositories import vehicles as vehicle_repo, users as user_repo
        from core.notifications import notify_warranty_claim_update
        mapping = vehicle_repo.find_by_vin(vin)
        if mapping and mapping.owner_address:
            owner = user_repo.find_by_blockchain_address(mapping.owner_address)
            if owner:
                notify_warranty_claim_update(owner.id, vin, status)
    except Exception:
        pass


@warranty_bp.route('/owner/claims', methods=['GET'])
@role_required('OWNER')
def get_owner_claims():
    try:
        claims = warranty_service.get_owner_claims(request.user['blockchain_address'])
        result = paginate(claims, request.args)
        return jsonify({**result, 'claims': result.pop('items')}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
