import threading
from flask import Blueprint, request, jsonify
from web3 import Web3
from api.middleware import role_required, token_required
from api.utils import sanitize, paginate
from db.repositories import users as user_repo
from db.models import ServiceMetadata, EthFundRequest, AuthorizedSCLicense
from db.models import db as _db
from datetime import datetime
from blockchain.client import web3_client
from config import Config


def _fetch_eth_balance(addr: str, timeout: float = 2.0):
    """Fetch ETH balance with timeout. Returns float or None."""
    holder = [None]
    def _task():
        try:
            bal = web3_client.w3.eth.get_balance(Web3.to_checksum_address(addr))
            holder[0] = float(Web3.from_wei(bal, 'ether'))
        except Exception:
            pass
    t = threading.Thread(target=_task, daemon=True)
    t.start()
    t.join(timeout=timeout)
    return holder[0]

sc_bp = Blueprint('sc_management', __name__)

_MAX_FUND_ETH = 10.0  # safety cap per transaction


def _brand_mismatch(sc, mfr_brand: str) -> bool:
    """Return True if SC brand doesn't match manufacturer brand (case-insensitive)."""
    if not mfr_brand:
        return False
    sc_brand = sc.brand or ''
    return sc_brand.lower() != mfr_brand.lower()


@sc_bp.route('/service-centers', methods=['GET'])
@role_required('MANUFACTURER')
def list_service_centers():
    mfr_brand = request.user.get('brand', '')
    city   = request.args.get('city', '').strip()
    state  = request.args.get('state', '').strip()
    status = request.args.get('status', '').strip()
    search = request.args.get('search', '').strip()

    scs = user_repo.find_service_centers(city=city, state=state,
                                          status=status, search=search,
                                          brand=mfr_brand)

    result = [sc.to_dict() for sc in scs]
    paginated = paginate(result, request.args)
    return jsonify(paginated), 200


@sc_bp.route('/service-centers/<int:sc_id>', methods=['GET'])
@role_required('MANUFACTURER')
def get_service_center(sc_id):
    sc = user_repo.find_by_id(sc_id)
    if not sc or sc.role != 'SERVICE_CENTER':
        return jsonify({'error': 'Service center not found'}), 404
    if _brand_mismatch(sc, request.user.get('brand', '')):
        return jsonify({'error': 'Service center belongs to a different brand'}), 403

    d = sc.to_dict()
    d['eth_balance'] = _fetch_eth_balance(sc.blockchain_address)
    return jsonify(d), 200


@sc_bp.route('/service-centers/<int:sc_id>/activate', methods=['POST'])
@role_required('MANUFACTURER')
def activate_service_center(sc_id):
    sc = user_repo.find_by_id(sc_id)
    if not sc or sc.role != 'SERVICE_CENTER':
        return jsonify({'error': 'Service center not found'}), 404
    if _brand_mismatch(sc, request.user.get('brand', '')):
        return jsonify({'error': 'Service center belongs to a different brand'}), 403
    user_repo.update_status(sc_id, 'active')
    from api.vehicles import invalidate_stats_cache; invalidate_stats_cache()
    return jsonify({'message': f'{sc.name or sc.email} activated', 'sc': sc.to_dict()}), 200


@sc_bp.route('/service-centers/<int:sc_id>/suspend', methods=['POST'])
@role_required('MANUFACTURER')
def suspend_service_center(sc_id):
    sc = user_repo.find_by_id(sc_id)
    if not sc or sc.role != 'SERVICE_CENTER':
        return jsonify({'error': 'Service center not found'}), 404
    if _brand_mismatch(sc, request.user.get('brand', '')):
        return jsonify({'error': 'Service center belongs to a different brand'}), 403
    user_repo.update_status(sc_id, 'suspended')
    user_repo.revoke_all_refresh_tokens(sc_id)

    # Revoke on-chain SERVICE_CENTER_ROLE so a suspended SC cannot bypass Flask
    # by calling the smart contract directly with their private key.
    try:
        from web3 import Web3 as _Web3
        from blockchain.adapters.service_log import service_log as _sl
        from config import Config as _Cfg
        _SC_ROLE = _Web3.keccak(text="SERVICE_CENTER_ROLE")
        revoke_tx = _sl.contract.functions.revokeRole(
            _SC_ROLE, _Web3.to_checksum_address(sc.blockchain_address)
        ).build_transaction({'from': _Web3.to_checksum_address(_Cfg.DEPLOYER_ADDRESS)})
        web3_client.sign_and_send(revoke_tx, _Cfg.DEPLOYER_ADDRESS)
    except Exception as _exc:
        import logging
        logging.getLogger(__name__).warning(
            'Could not revoke on-chain SERVICE_CENTER_ROLE for %s: %s', sc.email, _exc
        )

    from api.vehicles import invalidate_stats_cache; invalidate_stats_cache()
    return jsonify({'message': f'{sc.name or sc.email} suspended', 'sc': sc.to_dict()}), 200


@sc_bp.route('/service-centers/<int:sc_id>/fund', methods=['POST'])
@role_required('MANUFACTURER')
def fund_service_center(sc_id):
    sc = user_repo.find_by_id(sc_id)
    if not sc or sc.role != 'SERVICE_CENTER':
        return jsonify({'error': 'Service center not found'}), 404
    if _brand_mismatch(sc, request.user.get('brand', '')):
        return jsonify({'error': 'Service center belongs to a different brand'}), 403

    data = request.get_json() or {}
    try:
        amount_eth = float(data.get('amount_eth', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'amount_eth must be a number'}), 400

    if amount_eth <= 0:
        return jsonify({'error': 'amount_eth must be positive'}), 400
    if amount_eth > _MAX_FUND_ETH:
        return jsonify({'error': f'Maximum {_MAX_FUND_ETH} ETH per transaction'}), 400

    deployer = Config.DEPLOYER_ADDRESS
    if not deployer:
        return jsonify({'error': 'Deployer address not configured'}), 500

    try:
        amount_wei = Web3.to_wei(amount_eth, 'ether')
        web3_client.transfer_eth(deployer, sc.blockchain_address, amount_wei)
        new_balance = float(Web3.from_wei(
            web3_client.w3.eth.get_balance(Web3.to_checksum_address(sc.blockchain_address)),
            'ether'
        ))
        # Auto-fulfill any pending ETH request from this SC
        pending_req = EthFundRequest.query.filter_by(sc_user_id=sc.id, status='pending').first()
        if pending_req:
            pending_req.status = 'fulfilled'
            pending_req.fulfilled_at = datetime.utcnow()
            _db.session.commit()
        return jsonify({
            'message': f'Sent {amount_eth} ETH to {sc.name or sc.email}',
            'new_balance': new_balance,
        }), 200
    except Exception as e:
        return jsonify({'error': f'Transaction failed: {str(e)}'}), 500


@sc_bp.route('/my-stats', methods=['GET'])
@role_required('SERVICE_CENTER')
def get_sc_stats():
    """Stats for the logged-in service center."""
    addr = request.user.get('blockchain_address', '')
    services_submitted = ServiceMetadata.query.filter_by(
        service_center_address=addr
    ).count() if addr else 0

    disputed_count = ServiceMetadata.query.filter_by(
        service_center_address=addr, disputed=True
    ).count() if addr else 0

    dispute_rate = round(disputed_count / services_submitted * 100, 1) if services_submitted else 0.0
    flagged = dispute_rate > 10.0

    eth_balance = _fetch_eth_balance(addr) if addr else None

    return jsonify({
        'services_submitted': services_submitted,
        'disputed_count':     disputed_count,
        'dispute_rate':       dispute_rate,
        'flagged':            flagged,
        'eth_balance':        eth_balance,
    }), 200


@sc_bp.route('/fund-all', methods=['POST'])
@role_required('MANUFACTURER')
def fund_all_service_centers():
    """Send a fixed amount of ETH to every active service center."""
    data = request.get_json() or {}
    try:
        amount_eth = float(data.get('amount_eth', 0.1))
    except (TypeError, ValueError):
        return jsonify({'error': 'amount_eth must be a number'}), 400

    if amount_eth <= 0 or amount_eth > 1.0:
        return jsonify({'error': 'amount_eth must be between 0 and 1 ETH for bulk funding'}), 400

    deployer = Config.DEPLOYER_ADDRESS
    if not deployer:
        return jsonify({'error': 'Deployer address not configured'}), 500

    mfr_brand = request.user.get('brand', '')
    scs = user_repo.find_service_centers(status='active', brand=mfr_brand)
    results = []
    for sc in scs:
        try:
            amount_wei = Web3.to_wei(amount_eth, 'ether')
            web3_client.transfer_eth(deployer, sc.blockchain_address, amount_wei)
            results.append({'id': sc.id, 'name': sc.name or sc.email, 'status': 'funded'})
        except Exception as e:
            results.append({'id': sc.id, 'name': sc.name or sc.email, 'status': 'failed', 'error': str(e)})

    funded = sum(1 for r in results if r['status'] == 'funded')
    return jsonify({
        'message': f'Funded {funded}/{len(results)} service centers with {amount_eth} ETH each',
        'results': results,
    }), 200


# ─── ETH Fund Request endpoints ──────────────────────────────────────────────

@sc_bp.route('/eth-request', methods=['POST'])
@role_required('SERVICE_CENTER')
def create_eth_request():
    sc_user_id = request.user['user_id']
    brand = request.user.get('brand', '')
    if not brand:
        return jsonify({'error': 'No brand associated with your account'}), 400

    existing = EthFundRequest.query.filter_by(sc_user_id=sc_user_id, status='pending').first()
    if existing:
        return jsonify({'message': 'Request already pending', 'request': existing.to_dict()}), 200

    data = request.get_json() or {}
    notes = (data.get('notes') or '').strip()[:500]

    req = EthFundRequest(sc_user_id=sc_user_id, brand=brand, notes=notes or None)
    _db.session.add(req)
    _db.session.commit()
    return jsonify({'message': 'ETH request sent to manufacturer', 'request': req.to_dict()}), 201


@sc_bp.route('/manufacturer/eth-requests', methods=['GET'])
@role_required('MANUFACTURER')
def list_eth_requests():
    brand = request.user.get('brand', '')
    reqs = EthFundRequest.query.filter_by(brand=brand, status='pending').order_by(
        EthFundRequest.created_at.desc()
    ).all()
    return jsonify({'requests': [r.to_dict() for r in reqs], 'count': len(reqs)}), 200


@sc_bp.route('/manufacturer/eth-requests/count', methods=['GET'])
@role_required('MANUFACTURER')
def eth_requests_count():
    brand = request.user.get('brand', '')
    count = EthFundRequest.query.filter_by(brand=brand, status='pending').count()
    return jsonify({'count': count}), 200


@sc_bp.route('/manufacturer/eth-requests/<int:req_id>/dismiss', methods=['POST'])
@role_required('MANUFACTURER')
def dismiss_eth_request(req_id):
    brand = request.user.get('brand', '')
    req = EthFundRequest.query.filter_by(id=req_id, brand=brand).first()
    if not req:
        return jsonify({'error': 'Request not found'}), 404
    req.status = 'dismissed'
    _db.session.commit()
    return jsonify({'message': 'Request dismissed'}), 200


# ─── Authorized SC License management ────────────────────────────────────────

@sc_bp.route('/authorized-licenses', methods=['GET'])
@role_required('MANUFACTURER')
def list_authorized_licenses():
    mfr_id = request.user['user_id']
    entries = AuthorizedSCLicense.query.filter_by(manufacturer_user_id=mfr_id).order_by(
        AuthorizedSCLicense.created_at.desc()
    ).all()
    return jsonify({'licenses': [e.to_dict() for e in entries]}), 200


@sc_bp.route('/authorized-licenses', methods=['POST'])
@role_required('MANUFACTURER')
def add_authorized_license():
    data = request.get_json() or {}
    ssm_number = sanitize(data.get('ssm_number', ''), 50).upper().strip()
    sc_name = sanitize(data.get('sc_name', ''), 255).strip() or None
    brand = request.user.get('brand', '')

    if not ssm_number:
        return jsonify({'error': 'ssm_number is required'}), 400
    if not brand:
        return jsonify({'error': 'Your manufacturer account has no brand configured'}), 400

    existing = AuthorizedSCLicense.query.filter_by(ssm_number=ssm_number).first()
    if existing:
        return jsonify({'error': 'This SSM number is already registered'}), 409

    entry = AuthorizedSCLicense(
        manufacturer_user_id=request.user['user_id'],
        ssm_number=ssm_number,
        sc_name=sc_name,
        brand=brand,
    )
    _db.session.add(entry)
    _db.session.commit()
    return jsonify({'message': 'SSM license registered', 'license': entry.to_dict()}), 201


@sc_bp.route('/authorized-licenses/<int:license_id>', methods=['DELETE'])
@role_required('MANUFACTURER')
def delete_authorized_license(license_id):
    mfr_id = request.user['user_id']
    entry = AuthorizedSCLicense.query.filter_by(id=license_id, manufacturer_user_id=mfr_id).first()
    if not entry:
        return jsonify({'error': 'License not found'}), 404
    if entry.used:
        return jsonify({'error': 'Cannot delete a license that has already been used to register an account'}), 400
    _db.session.delete(entry)
    _db.session.commit()
    return jsonify({'message': 'License removed'}), 200
