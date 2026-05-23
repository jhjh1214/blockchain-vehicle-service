from web3 import Web3
import json
import hashlib


def vin_to_bytes32(vin: str) -> bytes:
    """keccak256 of VIN string, returns bytes32."""
    return Web3.keccak(text=vin)


def vin_to_hex(vin: str) -> str:
    """keccak256 of VIN string as 0x-prefixed hex."""
    return '0x' + bytes(vin_to_bytes32(vin)).hex()


def compute_metadata_hash(metadata: dict) -> str:
    """SHA256 of deterministically sorted JSON, returns 0x-prefixed hex."""
    metadata_str = json.dumps(metadata, sort_keys=True)
    return '0x' + hashlib.sha256(metadata_str.encode()).hexdigest()


def compute_string_hash(s: str) -> str:
    """SHA256 of a plain string, returns 0x-prefixed hex."""
    return '0x' + hashlib.sha256(s.encode()).hexdigest()
