import threading
from flask import Blueprint, request, jsonify
from web3 import Web3
from api.middleware import role_required, token_required
from api.utils import sanitize, paginate
from db.repositories import users as user_repo
from db.models import ServiceMetadata
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
