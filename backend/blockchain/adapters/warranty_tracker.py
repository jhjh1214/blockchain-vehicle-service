from web3 import Web3
from blockchain.client import web3_client
from blockchain.utils import vin_to_bytes32
from config import Config


class WarrantyTrackerAdapter:
    def __init__(self):
        self.contract = web3_client.load_contract('WarrantyTracker.json', Config.WARRANTY_TRACKER_ADDRESS)

    def is_warranty_valid(self, vin: str) -> dict:
        result = self.contract.functions.isWarrantyValid(vin_to_bytes32(vin)).call()
        return {'valid': result[0], 'reason': result[1]}

    def void_warranty(self, vin: str, from_address: str) -> dict:
        """Manufacturer approves a void request — enforces on-chain so no new claims can be filed."""
        tx = self.contract.functions.voidWarranty(
            vin_to_bytes32(vin)
        ).build_transaction({'from': Web3.to_checksum_address(from_address)})
        return web3_client.sign_and_send(tx, from_address)

    def submit_claim(self, vin: str, claim_details_hash: str, from_address: str) -> dict:
        tx = self.contract.functions.submitClaim(
            vin_to_bytes32(vin),
            Web3.to_bytes(hexstr=claim_details_hash)
        ).build_transaction({'from': Web3.to_checksum_address(from_address)})
        return web3_client.sign_and_send(tx, from_address)

    def approve_claim(self, vin: str, claim_index: int, from_address: str) -> dict:
        tx = self.contract.functions.approveClaim(
            vin_to_bytes32(vin),
            claim_index
        ).build_transaction({'from': Web3.to_checksum_address(from_address)})
        return web3_client.sign_and_send(tx, from_address)

    def deny_claim(self, vin: str, claim_index: int, reason_hash: str, from_address: str) -> dict:
        tx = self.contract.functions.denyClaim(
            vin_to_bytes32(vin),
            claim_index,
            Web3.to_bytes(hexstr=reason_hash)
        ).build_transaction({'from': Web3.to_checksum_address(from_address)})
        return web3_client.sign_and_send(tx, from_address)

    def get_claims(self, vin: str) -> list:
        claims = self.contract.functions.getClaims(vin_to_bytes32(vin)).call()
        return [self._format_claim(c) for c in claims]

    @staticmethod
    def _format_claim(claim) -> dict:
        empty = b'\x00' * 32
        status_map = {0: 'pending', 1: 'approved', 2: 'denied'}
        return {
            'vin': '0x' + claim[0].hex(),
            'claim_details_hash': '0x' + claim[1].hex(),
            'timestamp': claim[2],
            'claimant': claim[3],
            'status': status_map.get(claim[4], 'pending'),
            'resolution_notes_hash': '0x' + claim[5].hex() if claim[5] != empty else None
        }


warranty_tracker = WarrantyTrackerAdapter()
