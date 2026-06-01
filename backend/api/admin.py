from flask import Blueprint, jsonify, request
from web3 import Web3

from api.middleware import role_required
from api.utils import validate_vin
from blockchain.adapters.vehicle_registry import vehicle_registry
from blockchain.client import web3_client
from blockchain.keystore import keystore
from blockchain.utils import vin_to_bytes32, vin_to_hex
from config import Config  # needed for DEPLOYER_ADDRESS / DEPLOYER_PRIVATE_KEY
from db.models import db
from db.repositories import vehicles as vehicle_repo, users as user_repo
from extensions import limiter

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/reset-db', methods=['POST'])
@limiter.limit('5 per minute')
def reset_db():
    """Wipe all DB tables (drop+recreate) and keep only the deployer key in the keystore.

    Callers must supply both X-Admin-Secret and a time-based HMAC signature to
    prevent simple secret replay attacks:
      X-Admin-Timestamp : Unix seconds (string), must be within ±30 s of server time
      X-Admin-Signature : hex( HMAC-SHA256( ADMIN_SECRET, timestamp ) )
    """
    import hashlib, hmac, time as _time

    secret = request.headers.get('X-Admin-Secret', '')
    if not Config.ADMIN_SECRET or secret != Config.ADMIN_SECRET:
        return jsonify({'error': 'Unauthorized'}), 401

    timestamp_str = request.headers.get('X-Admin-Timestamp', '')
    signature     = request.headers.get('X-Admin-Signature', '')
    try:
        ts = int(timestamp_str)
    except (TypeError, ValueError):
        return jsonify({'error': 'X-Admin-Timestamp header required (Unix seconds)'}), 401

    if abs(_time.time() - ts) > 30:
        return jsonify({'error': 'Request timestamp expired or too far in the future'}), 401

    expected = hmac.new(
        Config.ADMIN_SECRET.encode(),
        timestamp_str.encode(),
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return jsonify({'error': 'Invalid request signature'}), 401

    try:
        db.drop_all()
        db.create_all()
    except Exception as e:
        return jsonify({'error': f'DB reset failed: {str(e)}'}), 500

    # Keep only the deployer key in the keystore
    deployer_lower = (Config.DEPLOYER_ADDRESS or '').lower()
    all_keys = keystore._load()
    fresh = {k: v for k, v in all_keys.items() if k == deployer_lower}
    keystore._save(fresh)
    if Config.DEPLOYER_ADDRESS and Config.DEPLOYER_PRIVATE_KEY:
        keystore.store_key(Config.DEPLOYER_ADDRESS, Config.DEPLOYER_PRIVATE_KEY)

    return jsonify({'message': 'Database wiped and keystore pruned'}), 200


@admin_bp.route('/fix-ownership', methods=['POST'])
@role_required('MANUFACTURER')
def fix_ownership():
    """Force-transfer a vehicle's on-chain owner to a new user.

    Uses the deployer's DEFAULT_ADMIN_ROLE to temporarily grant itself
    OWNER_ROLE, call transferOwnership, then revoke OWNER_ROLE again.
    Also upserts the vehicle into the local DB.
    """
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    new_owner_email = data.get('new_owner_email', '').strip().lower()
    make  = data.get('make', '')
    model = data.get('model', '')
    year  = data.get('year')

    warranty_years_raw = data.get('warranty_years')
    warranty_expiry_new = None
    if warranty_years_raw is not None:
        try:
            warranty_years = int(warranty_years_raw)
        except (TypeError, ValueError):
            return jsonify({'error': 'warranty_years must be an integer'}), 400
        if not (1 <= warranty_years <= 20):
            return jsonify({'error': 'warranty_years must be between 1 and 20'}), 400
        import time as _time
        warranty_expiry_new = int(_time.time()) + warranty_years * 365 * 24 * 3600

    new_owner = user_repo.find_by_email(new_owner_email)
    if not new_owner:
        return jsonify({'error': f'User {new_owner_email} not found'}), 404
    if new_owner.role != 'OWNER':
        return jsonify({'error': 'Target user must have the OWNER role'}), 400

    mfr_brand = request.user.get('brand', '')
    if mfr_brand and make and make.lower() != mfr_brand.lower():
        return jsonify({'error': f"Brand mismatch: your account is authorised for '{mfr_brand}' vehicles only"}), 403
    existing_mapping = vehicle_repo.find_by_vin(vin)
    if existing_mapping and mfr_brand:
        if existing_mapping.make and existing_mapping.make.lower() != mfr_brand.lower():
            return jsonify({'error': 'Vehicle belongs to a different brand'}), 403
        if existing_mapping.registered_by and existing_mapping.registered_by != request.user['blockchain_address']:
            return jsonify({'error': 'You can only fix ownership of vehicles your brand registered'}), 403

    deployer = Config.DEPLOYER_ADDRESS
    if not deployer:
        return jsonify({'error': 'Deployer address not configured'}), 500

    try:
        OWNER_ROLE = vehicle_registry.contract.functions.OWNER_ROLE().call()

        # 1. Grant OWNER_ROLE to deployer so it can call transferOwnership
        web3_client.grant_role(vehicle_registry.contract, OWNER_ROLE, deployer, deployer)

        # 2. Transfer on-chain ownership to new owner
        tx = vehicle_registry.contract.functions.transferOwnership(
            vin_to_bytes32(vin),
            Web3.to_checksum_address(new_owner.blockchain_address)
        ).build_transaction({'from': Web3.to_checksum_address(deployer)})
        web3_client.sign_and_send(tx, deployer)

        # 3. Revoke OWNER_ROLE from deployer (clean up)
        revoke_tx = vehicle_registry.contract.functions.revokeRole(
            OWNER_ROLE, Web3.to_checksum_address(deployer)
        ).build_transaction({'from': Web3.to_checksum_address(deployer)})
        web3_client.sign_and_send(revoke_tx, deployer)

    except Exception as e:
        return jsonify({'error': f'Blockchain transfer failed: {str(e)}'}), 500

    # 4. Upsert vehicle in local DB
    try:
        vin_hash = vin_to_hex(vin)
        mapping = vehicle_repo.find_by_vin(vin)
        if mapping:
            vehicle_repo.update_owner(vin, new_owner.blockchain_address)
            if mapping.registration_status != 'active':
                vehicle_repo.update_registration_status(vin, 'active')
        else:
            vehicle_repo.create(
                vin=vin, vin_hash=vin_hash,
                owner_address=new_owner.blockchain_address,
                make=make, model=model,
                year=int(year) if year else None,
                warranty_expiry=warranty_expiry_new,
                registered_by=request.user['blockchain_address'],
            )
    except Exception as e:
        return jsonify({'error': f'DB sync failed: {str(e)}'}), 500

    return jsonify({
        'message': f'Ownership of {vin} transferred to {new_owner.email}',
        'vin': vin,
        'new_owner': new_owner.email,
    }), 200


# ─── Blockchain–DB Reconciliation ────────────────────────────────────────────

@admin_bp.route('/reconcile', methods=['GET'])
@limiter.limit('5 per minute')
def reconcile():
    """
    Verify that every ServiceMetadata row's stored hash matches a re-computation
    from its own fields. Optionally also checks the on-chain record exists.

    Query params:
      ?vin=<VIN>     — restrict to one vehicle (recommended for large datasets)
      ?on_chain=1    — also verify the hash appears on-chain (slower)

    Returns a list of mismatches. An empty list means all records are consistent.
    """
    import hashlib, hmac as _hmac, json as _json, time as _t

    secret = request.headers.get('X-Admin-Secret', '')
    if not Config.ADMIN_SECRET or secret != Config.ADMIN_SECRET:
        return jsonify({'error': 'Unauthorized'}), 401
    ts_str = request.headers.get('X-Admin-Timestamp', '')
    sig    = request.headers.get('X-Admin-Signature', '')
    try:
        if abs(_t.time() - float(ts_str)) > 30:
            return jsonify({'error': 'Timestamp expired'}), 401
    except (TypeError, ValueError):
        return jsonify({'error': 'X-Admin-Timestamp required'}), 401
    expected = _hmac.new(Config.ADMIN_SECRET.encode(), ts_str.encode(), hashlib.sha256).hexdigest()
    if not _hmac.compare_digest(expected, sig):
        return jsonify({'error': 'Invalid signature'}), 401

    from db.models import ServiceMetadata as _SM

    vin_filter = request.args.get('vin', '').strip().upper()
    check_chain = request.args.get('on_chain', '') == '1'

    query = _SM.query
    if vin_filter:
        query = query.filter_by(vin=vin_filter)

    mismatches = []
    checked = 0

    for row in query.all():
        checked += 1
        # Reconstruct the metadata dict exactly as submit_service() built it
        recomputed_meta = {
            'service_type':    row.service_type or '',
            'service_date':    row.service_date.isoformat() if row.service_date else '',
            'mileage':         row.mileage,
            'parts_replaced':  row.parts_replaced or '',
            'technician_name': row.technician_name or '',
            'service_notes':   row.service_notes or '',
            'ecu_modules':     [],   # not persisted in ServiceMetadata; always empty at rest
            'photos':          row.photos or [],
        }
        recomputed_hash = '0x' + hashlib.sha256(
            _json.dumps(recomputed_meta, sort_keys=True).encode()
        ).hexdigest()

        db_hash = row.metadata_hash or ''
        hash_ok = recomputed_hash == db_hash

        chain_ok = None
        if check_chain and hash_ok:
            try:
                from blockchain.adapters.service_log import service_log as _sl
                pending   = _sl.get_pending_services(row.vin)
                finalized = _sl.get_finalized_services(row.vin)
                all_hashes = [r.get('metadata_hash') for r in pending + finalized]
                chain_ok = db_hash in all_hashes
            except Exception:
                chain_ok = None  # blockchain unreachable — skip chain check

        if not hash_ok or chain_ok is False:
            mismatches.append({
                'id':             row.id,
                'vin':            row.vin,
                'metadata_hash':  db_hash,
                'recomputed':     recomputed_hash,
                'hash_match':     hash_ok,
                'chain_match':    chain_ok,
                'service_date':   row.service_date.isoformat() if row.service_date else None,
                'service_type':   row.service_type,
            })

    return jsonify({
        'checked':    checked,
        'mismatches': len(mismatches),
        'results':    mismatches,
    }), 200


