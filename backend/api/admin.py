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

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/reset-db', methods=['POST'])
def reset_db():
    """Wipe all DB tables (drop+recreate) and keep only the deployer key in the keystore."""
    secret = request.headers.get('X-Admin-Secret', '')
    if not Config.ADMIN_SECRET or secret != Config.ADMIN_SECRET:
        return jsonify({'error': 'Unauthorized'}), 401
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
        else:
            vehicle_repo.create(
                vin=vin, vin_hash=vin_hash,
                owner_address=new_owner.blockchain_address,
                make=make, model=model,
                year=int(year) if year else None,
                registered_by=request.user['blockchain_address'],
            )
    except Exception as e:
        return jsonify({'error': f'DB sync failed: {str(e)}'}), 500

    return jsonify({
        'message': f'Ownership of {vin} transferred to {new_owner.email}',
        'vin': vin,
        'new_owner': new_owner.email,
    }), 200
