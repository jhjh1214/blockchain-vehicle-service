"""Unit tests for blockchain utility functions — no mocking needed."""
import hashlib
import json
import pytest
from blockchain.utils import (
    vin_to_bytes32,
    vin_to_hex,
    compute_metadata_hash,
    compute_string_hash,
)

SAMPLE_VIN = '1HGCM82633A004352'


class TestVinHashing:
    def test_vin_to_bytes32_returns_bytes(self):
        result = vin_to_bytes32(SAMPLE_VIN)
        assert isinstance(result, bytes)
        assert len(result) == 32

    def test_vin_to_hex_format(self):
        result = vin_to_hex(SAMPLE_VIN)
        assert result.startswith('0x')
        assert len(result) == 66  # 0x + 64 hex chars

    def test_vin_to_hex_deterministic(self):
        assert vin_to_hex(SAMPLE_VIN) == vin_to_hex(SAMPLE_VIN)

    def test_different_vins_produce_different_hashes(self):
        assert vin_to_hex(SAMPLE_VIN) != vin_to_hex('2HGCM82633A004352')

    def test_vin_to_hex_matches_bytes32_hex(self):
        b32 = vin_to_bytes32(SAMPLE_VIN)
        assert vin_to_hex(SAMPLE_VIN) == '0x' + b32.hex()


class TestMetadataHash:
    def test_returns_hex_string(self):
        result = compute_metadata_hash({'key': 'value'})
        assert result.startswith('0x')
        assert len(result) == 66

    def test_deterministic(self):
        metadata = {'service_type': 'Oil Change', 'mileage': 15000}
        assert compute_metadata_hash(metadata) == compute_metadata_hash(metadata)

    def test_order_independent(self):
        """sort_keys=True must make hash independent of dict insertion order."""
        a = compute_metadata_hash({'b': 2, 'a': 1})
        b = compute_metadata_hash({'a': 1, 'b': 2})
        assert a == b

    def test_different_data_different_hash(self):
        assert compute_metadata_hash({'mileage': 1}) != compute_metadata_hash({'mileage': 2})

    def test_matches_manual_sha256(self):
        metadata = {'service_type': 'Brake Check', 'mileage': 5000}
        expected = '0x' + hashlib.sha256(
            json.dumps(metadata, sort_keys=True).encode()
        ).hexdigest()
        assert compute_metadata_hash(metadata) == expected


class TestStringHash:
    def test_returns_hex_string(self):
        result = compute_string_hash('hello world')
        assert result.startswith('0x')
        assert len(result) == 66

    def test_deterministic(self):
        assert compute_string_hash('test') == compute_string_hash('test')

    def test_different_strings_different_hashes(self):
        assert compute_string_hash('approve') != compute_string_hash('reject')

    def test_matches_manual_sha256(self):
        s = 'resolution notes'
        expected = '0x' + hashlib.sha256(s.encode()).hexdigest()
        assert compute_string_hash(s) == expected

    def test_empty_string(self):
        result = compute_string_hash('')
        assert result.startswith('0x')
        assert len(result) == 66
