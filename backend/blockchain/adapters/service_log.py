from web3 import Web3
from blockchain.client import web3_client
from blockchain.utils import vin_to_bytes32
from config import Config


class ServiceLogAdapter:
    def __init__(self):
        self.contract = web3_client.load_contract('ServiceLog.json', Config.SERVICE_LOG_ADDRESS)

    def submit_service(self, vin: str, metadata_hash: str, from_address: str) -> dict:
        tx = self.contract.functions.submitService(
            vin_to_bytes32(vin),
            Web3.to_bytes(hexstr=metadata_hash)
        ).build_transaction({'from': Web3.to_checksum_address(from_address)})
        return web3_client.sign_and_send(tx, from_address)

    def verify_service(self, vin: str, record_index: int, from_address: str) -> dict:
        tx = self.contract.functions.verifyService(
            vin_to_bytes32(vin),
            record_index
        ).build_transaction({'from': Web3.to_checksum_address(from_address)})
        return web3_client.sign_and_send(tx, from_address)

    def dispute_service(self, vin: str, record_index: int, reason: str, from_address: str) -> dict:
        tx = self.contract.functions.disputeService(
            vin_to_bytes32(vin),
            record_index,
            reason
        ).build_transaction({'from': Web3.to_checksum_address(from_address)})
        return web3_client.sign_and_send(tx, from_address)

    def resolve_dispute(self, vin: str, record_index: int, decision: int,
                        resolution_notes_hash: str, from_address: str) -> dict:
        tx = self.contract.functions.resolveDispute(
            vin_to_bytes32(vin),
            record_index,
            decision,
            Web3.to_bytes(hexstr=resolution_notes_hash)
        ).build_transaction({'from': Web3.to_checksum_address(from_address)})
        return web3_client.sign_and_send(tx, from_address)

    def get_pending_services(self, vin: str) -> list:
        records = self.contract.functions.getPendingServices(vin_to_bytes32(vin)).call()
        return [self._format_record(r) for r in records]

    def get_finalized_services(self, vin: str) -> list:
        records = self.contract.functions.getFinalizedServices(vin_to_bytes32(vin)).call()
        return [self._format_record(r) for r in records]

    @staticmethod
    def _format_record(record) -> dict:
        # ServiceRecord: vin[0], metadataHash[1], timestamp[2],
        #                serviceCenter[3], verified[4], disputed[5], disputeReason[6]
        return {
            'vin': '0x' + record[0].hex(),
            'metadata_hash': '0x' + record[1].hex(),
            'timestamp': record[2],
            'service_center': record[3],
            'verified': record[4],
            'disputed': record[5],
            'dispute_reason': record[6]
        }


service_log = ServiceLogAdapter()
