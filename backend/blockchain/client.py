from web3 import Web3
try:
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
except ImportError:
    from web3.middleware import geth_poa_middleware
import json
import os
import threading
from config import Config
from blockchain.keystore import keystore


class Web3Client:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(Config.GANACHE_URL, request_kwargs={'timeout': 30}))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        # Per-address locks prevent nonce collisions when requests arrive concurrently
        self._nonce_locks: dict[str, threading.Lock] = {}
        self._locks_meta = threading.Lock()

    def _nonce_lock(self, address: str) -> threading.Lock:
        addr = address.lower()
        with self._locks_meta:
            if addr not in self._nonce_locks:
                self._nonce_locks[addr] = threading.Lock()
            return self._nonce_locks[addr]

    def load_contract(self, abi_filename: str, address: str):
        abi_path = os.path.join(Config.ABI_DIR, abi_filename)
        with open(abi_path) as f:
            abi = json.load(f)['abi']
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(address),
            abi=abi
        )

    def sign_and_send(self, transaction: dict, from_address: str) -> dict:
        private_key = keystore.get_key(from_address)
        if not private_key:
            raise ValueError(f"No private key found for address {from_address}")

        # Strip EIP-1559 fee fields; always use legacy gasPrice
        transaction.pop('maxFeePerGas', None)
        transaction.pop('maxPriorityFeePerGas', None)
        transaction.pop('type', None)
        transaction['from'] = from_address
        transaction['chainId'] = Config.CHAIN_ID
        transaction['gasPrice'] = self.w3.eth.gas_price

        # Estimate gas with 20 % buffer; fall back to 3 M if estimation fails
        if 'gas' not in transaction:
            try:
                transaction['gas'] = int(self.w3.eth.estimate_gas(transaction) * 1.2)
            except Exception:
                transaction['gas'] = 3_000_000

        # Hold the per-address lock only while acquiring the nonce and broadcasting.
        # Waiting for the receipt happens outside the lock so other addresses can proceed.
        with self._nonce_lock(from_address):
            transaction['nonce'] = self.w3.eth.get_transaction_count(from_address, 'pending')
            signed = self.w3.eth.account.sign_transaction(transaction, private_key)
            raw = signed.rawTransaction if hasattr(signed, 'rawTransaction') else signed.raw_transaction
            tx_hash = self.w3.eth.send_raw_transaction(raw)

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt.get('status') == 0:
            raise RuntimeError(f"Transaction reverted on-chain: {tx_hash.hex()}")

        return {
            'tx_hash': tx_hash.hex(),
            'block_number': receipt['blockNumber'],
            'gas_used': receipt['gasUsed'],
            'status': receipt['status'],
        }

    def transfer_eth(self, from_address: str, to_address: str, amount_wei: int):
        private_key = keystore.get_key(from_address)
        if not private_key:
            raise ValueError(f"No private key found for address {from_address}")
        tx = {
            'to': to_address,
            'value': amount_wei,
            'gas': 21000,
            'gasPrice': self.w3.eth.gas_price,
            'chainId': Config.CHAIN_ID,
        }
        with self._nonce_lock(from_address):
            tx['nonce'] = self.w3.eth.get_transaction_count(from_address, 'pending')
            signed = self.w3.eth.account.sign_transaction(tx, private_key)
            raw = signed.rawTransaction if hasattr(signed, 'rawTransaction') else signed.raw_transaction
            tx_hash = self.w3.eth.send_raw_transaction(raw)
        self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

    def grant_role(self, contract, role_hash: bytes, account: str, from_address: str):
        tx = contract.functions.grantRole(
            role_hash, Web3.to_checksum_address(account)
        ).build_transaction({'from': Web3.to_checksum_address(from_address)})
        self.sign_and_send(tx, from_address)


web3_client = Web3Client()
