from web3 import Web3
from blockchain.client import web3_client
from blockchain.utils import vin_to_bytes32
from config import Config


class VehicleRegistryAdapter:
    def __init__(self):
        self.contract = web3_client.load_contract('VehicleRegistry.json', Config.VEHICLE_REGISTRY_ADDRESS)

    def register_vehicle(self, vin: str, owner_address: str, warranty_expiry: int, from_address: str) -> dict:
        tx = self.contract.functions.registerVehicle(
            vin_to_bytes32(vin),
            Web3.to_checksum_address(owner_address),
            warranty_expiry
        ).build_transaction({'from': Web3.to_checksum_address(from_address)})
        return web3_client.sign_and_send(tx, from_address)

    def transfer_ownership(self, vin: str, new_owner_address: str, from_address: str) -> dict:
        tx = self.contract.functions.transferOwnership(
            vin_to_bytes32(vin),
            Web3.to_checksum_address(new_owner_address)
        ).build_transaction({'from': Web3.to_checksum_address(from_address)})
        return web3_client.sign_and_send(tx, from_address)

    def get_vehicle(self, vin: str) -> dict:
        result = self.contract.functions.getVehicle(vin_to_bytes32(vin)).call()
        return {
            'owner': result[0],
            'warranty_start': result[1],
            'warranty_expiry': result[2],
            'service_hashes': result[3],
            'exists': result[4]
        }

    def get_owned_vehicles(self, owner_address: str) -> list:
        """Returns list of VIN hashes as 0x-prefixed hex strings."""
        vins = self.contract.functions.getOwnedVehicles(
            Web3.to_checksum_address(owner_address)
        ).call()
        return ['0x' + v.hex() for v in vins]


vehicle_registry = VehicleRegistryAdapter()
