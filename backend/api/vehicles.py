from flask import Blueprint, request, jsonify
from api.middleware import token_required, role_required
from core import vehicle_service

vehicle_bp = Blueprint('vehicle', __name__)


@vehicle_bp.route('/register', methods=['POST'])
@role_required('MANUFACTURER')
def register_vehicle():
    data = request.get_json() or {}
    vin = data.get('vin')
    owner_email = data.get('owner_email')
    if not vin or not owner_email:
        return jsonify({'error': 'VIN and owner_email required'}), 400
    try:
        result = vehicle_service.register_vehicle(
            vin=vin,
            owner_email=owner_email,
            warranty_years=data.get('warranty_years', 3),
            make=data.get('make', ''),
            model=data.get('model', ''),
            year=data.get('year'),
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
        return jsonify({'vehicles': vehicles, 'count': len(vehicles)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@vehicle_bp.route('/transfer', methods=['POST'])
@token_required
def transfer_vehicle():
    data = request.get_json() or {}
    vin = data.get('vin')
    new_owner_email = data.get('new_owner_email')
    if not vin or not new_owner_email:
        return jsonify({'error': 'VIN and new_owner_email required'}), 400
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
        result = vehicle_service.get_vehicle(vin)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except LookupError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@vehicle_bp.route('/owner/vehicles', methods=['GET'])
@role_required('OWNER')
def get_owner_vehicles():
    try:
        vehicles = vehicle_service.get_my_vehicles(request.user['blockchain_address'])
        return jsonify({'vehicles': vehicles, 'count': len(vehicles)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
