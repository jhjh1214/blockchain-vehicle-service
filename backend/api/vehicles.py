from flask import Blueprint, request, jsonify
from api.middleware import token_required, role_required
from api.utils import sanitize, validate_vin, paginate
from core import vehicle_service

vehicle_bp = Blueprint('vehicle', __name__)


@vehicle_bp.route('/register', methods=['POST'])
@role_required('MANUFACTURER')
def register_vehicle():
    data = request.get_json() or {}
    try:
        vin         = validate_vin(data.get('vin', ''))
        owner_email = sanitize(data.get('owner_email', ''), 255).lower()
        make        = sanitize(data.get('make', ''), 50)
        model       = sanitize(data.get('model', ''), 50)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    if not owner_email:
        return jsonify({'error': 'owner_email required'}), 400

    try:
        year = int(data.get('year', 0)) if data.get('year') else None
    except (TypeError, ValueError):
        return jsonify({'error': 'year must be an integer'}), 400

    try:
        result = vehicle_service.register_vehicle(
            vin=vin,
            owner_email=owner_email,
            warranty_years=int(data.get('warranty_years', 3)),
            make=make,
            model=model,
            year=year,
            from_address=request.user['blockchain_address']
        )
        return jsonify(result), 200
    except (ValueError, LookupError) as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@vehicle_bp.route('/my-vehicles', methods=['GET'])
@token_required
def get_my_vehicles():
    try:
        vehicles = vehicle_service.get_my_vehicles(request.user['blockchain_address'])
        result = paginate(vehicles, request.args)
        return jsonify({**result, 'vehicles': result.pop('items')}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@vehicle_bp.route('/transfer', methods=['POST'])
@token_required
def transfer_vehicle():
    data = request.get_json() or {}
    try:
        vin = validate_vin(data.get('vin', ''))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    new_owner_email = sanitize(data.get('new_owner_email', ''), 255).lower()
    if not new_owner_email:
        return jsonify({'error': 'new_owner_email required'}), 400
    try:
        result = vehicle_service.transfer_vehicle(
            vin=vin,
            new_owner_email=new_owner_email,
            from_address=request.user['blockchain_address']
        )
        return jsonify(result), 200
    except LookupError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@vehicle_bp.route('/<vin>', methods=['GET'])
@token_required
def get_vehicle(vin):
    try:
        vin = validate_vin(vin)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    try:
        result = vehicle_service.get_vehicle(vin)
        return jsonify(result), 200
    except LookupError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@vehicle_bp.route('/owner/vehicles', methods=['GET'])
@role_required('OWNER')
def get_owner_vehicles():
    try:
        vehicles = vehicle_service.get_my_vehicles(request.user['blockchain_address'])
        result = paginate(vehicles, request.args)
        return jsonify({**result, 'vehicles': result.pop('items')}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
