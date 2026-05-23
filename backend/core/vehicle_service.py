import time
from blockchain.adapters.vehicle_registry import vehicle_registry
from blockchain.utils import vin_to_hex
from db.repositories import vehicles as vehicle_repo, users as user_repo


def register_vehicle(vin: str, owner_email: str, warranty_years: int,
                     make: str, model: str, year: int,
                     from_address: str, registered_by: str = None) -> dict:
    if len(vin) != 17:
        raise ValueError('VIN must be 17 characters')

    owner = user_repo.find_by_email(owner_email)
    if not owner:
        raise LookupError('Owner not found. User must register first.')

    warranty_expiry = int(time.time()) + (warranty_years * 365 * 24 * 60 * 60)
    vin_hash = vin_to_hex(vin)

    result = vehicle_registry.register_vehicle(vin, owner.blockchain_address, warranty_expiry, from_address)
    vehicle_repo.create(vin=vin, vin_hash=vin_hash, owner_address=owner.blockchain_address,
                        make=make, model=model, year=year, warranty_expiry=warranty_expiry,
                        registered_by=registered_by or from_address)

    return {
        'message': 'Vehicle registered successfully',
        'vin': vin,
        'vin_hash': vin_hash,
        'owner': owner.email,
        'warranty_expiry': warranty_expiry,
        'transaction': result
    }


def get_vehicle(vin: str) -> dict:
    if len(vin) != 17:
        raise ValueError('Invalid VIN format')

    vehicle = vehicle_registry.get_vehicle(vin)
    if not vehicle['exists']:
        raise LookupError('Vehicle not found')

    mapping = vehicle_repo.find_by_vin(vin)
    owner = user_repo.find_by_blockchain_address(vehicle['owner'])

    return {
        'vin': vin,
        'make': mapping.make if mapping else 'Unknown',
        'model': mapping.model if mapping else 'Unknown',
        'year': mapping.year if mapping else None,
        'owner': {
            'address': vehicle['owner'],
            'name': owner.name if owner else 'Unknown',
            'email': owner.email if owner else None
        },
        'warranty': {
            'start': vehicle['warranty_start'],
            'expiry': vehicle['warranty_expiry'],
            'is_valid': vehicle['warranty_expiry'] > int(time.time())
        },
        'service_count': len(vehicle['service_hashes']),
        'service_hashes': ['0x' + h.hex() if isinstance(h, bytes) else h
                           for h in vehicle['service_hashes']]
    }


def get_my_vehicles(owner_address: str) -> list:
    mappings = vehicle_repo.find_by_owner(owner_address)
    now = int(time.time())
    return [{
        'vin': m.vin,
        'make': m.make,
        'model': m.model,
        'year': m.year,
        'warranty_expiry': m.warranty_expiry,
        'is_valid': m.warranty_expiry > now if m.warranty_expiry else None,
        'service_count': 0,
    } for m in mappings]


def transfer_vehicle(vin: str, new_owner_email: str, from_address: str) -> dict:
    new_owner = user_repo.find_by_email(new_owner_email)
    if not new_owner:
        raise LookupError('New owner not found')

    result = vehicle_registry.transfer_ownership(vin, new_owner.blockchain_address, from_address)
    vehicle_repo.update_owner(vin, new_owner.blockchain_address)

    return {
        'message': 'Vehicle transferred successfully',
        'vin': vin,
        'new_owner': new_owner.email,
        'transaction': result
    }
