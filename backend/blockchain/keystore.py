from cryptography.fernet import Fernet
import json
import os
from eth_account import Account
from config import Config


class Keystore:
    def __init__(self):
        self.keystore_dir = Config.KEYSTORE_DIR
        os.makedirs(self.keystore_dir, exist_ok=True)

        self.key_file = os.path.join(self.keystore_dir, 'encryption.key')
        if not os.path.exists(self.key_file):
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)

        with open(self.key_file, 'rb') as f:
            self.cipher = Fernet(f.read())

        self.keystore_file = os.path.join(self.keystore_dir, 'keys.json')
        if not os.path.exists(self.keystore_file):
            self._save({})

    def _load(self) -> dict:
        with open(self.keystore_file, 'r') as f:
            encrypted = f.read()
        if not encrypted:
            return {}
        return json.loads(self.cipher.decrypt(encrypted.encode()).decode())

    def _save(self, data: dict):
        encrypted = self.cipher.encrypt(json.dumps(data).encode())
        with open(self.keystore_file, 'w') as f:
            f.write(encrypted.decode())

    def create_account(self) -> dict:
        account = Account.create()
        return {'address': account.address, 'private_key': account.key.hex()}

    def store_key(self, address: str, private_key: str):
        data = self._load()
        data[address.lower()] = private_key
        self._save(data)

    def get_key(self, address: str) -> str | None:
        return self._load().get(address.lower())

    def has_key(self, address: str) -> bool:
        return address.lower() in self._load()


keystore = Keystore()
