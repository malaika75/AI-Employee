"""
Platinum Tier Secrets Manager
Securely encrypts and decrypts sensitive information using Fernet symmetric encryption
"""
import os
import json
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecretsManager:
    def __init__(self, vault_path=None):
        """
        Initialize the SecretsManager
        :param vault_path: Path to the vault directory (default: ./vault)
        """
        self.vault_path = Path(vault_path) if vault_path else Path("vault")
        self.secrets_file = self.vault_path / "Secrets.json"
        self.key_file = self.vault_path / "Secrets.key"

        # Create vault directory if it doesn't exist
        self.vault_path.mkdir(exist_ok=True)

        # Generate or load encryption key
        self.key = self._get_or_create_key()
        self.cipher_suite = Fernet(self.key)

    def _get_or_create_key(self):
        """
        Get existing encryption key or create a new one
        """
        if self.key_file.exists():
            with open(self.key_file, 'rb') as key_file:
                return key_file.read()
        else:
            # Generate a new key and save it
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as key_file:
                key_file.write(key)
            # Set restrictive permissions on the key file
            os.chmod(self.key_file, 0o600)  # Read/write for owner only
            return key

    def _derive_key_from_password(self, password: str) -> bytes:
        """
        Derive a key from a password using PBKDF2
        This is useful if we want to require a master password
        """
        salt = b'static_salt_for_demo_purposes'  # In production, use a random salt stored securely
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def encrypt_data(self, data: dict) -> str:
        """
        Encrypt a dictionary of secrets
        :param data: Dictionary containing secrets to encrypt
        :return: Encrypted JSON string
        """
        json_data = json.dumps(data)
        encrypted_data = self.cipher_suite.encrypt(json_data.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')

    def decrypt_data(self, encrypted_data: str) -> dict:
        """
        Decrypt an encrypted JSON string
        :param encrypted_data: Encrypted JSON string
        :return: Decrypted dictionary of secrets
        """
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
        decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
        return json.loads(decrypted_data.decode('utf-8'))

    def save_secrets(self, secrets: dict):
        """
        Save encrypted secrets to the secrets file
        :param secrets: Dictionary containing secrets to save
        """
        encrypted_secrets = self.encrypt_data(secrets)
        encrypted_data = {
            "encrypted": True,
            "version": "1.0",
            "data": encrypted_secrets
        }

        with open(self.secrets_file, 'w') as f:
            json.dump(encrypted_data, f, indent=2)

    def load_secrets(self) -> dict:
        """
        Load and decrypt secrets from the secrets file
        :return: Dictionary containing decrypted secrets, or empty dict if file doesn't exist
        """
        if not self.secrets_file.exists():
            return {}

        with open(self.secrets_file, 'r') as f:
            encrypted_data = json.load(f)

        if not encrypted_data.get("encrypted", False):
            raise ValueError("Secrets file is not properly encrypted")

        return self.decrypt_data(encrypted_data["data"])

    def get_secret(self, key: str, default=None):
        """
        Get a specific secret value
        :param key: The key of the secret to retrieve
        :param default: Default value if key doesn't exist
        :return: The secret value or default
        """
        secrets = self.load_secrets()
        return secrets.get(key, default)

    def set_secret(self, key: str, value):
        """
        Set a specific secret value
        :param key: The key of the secret to set
        :param value: The value to set
        """
        secrets = self.load_secrets()
        secrets[key] = value
        self.save_secrets(secrets)

    def delete_secret(self, key: str):
        """
        Delete a specific secret
        :param key: The key of the secret to delete
        """
        secrets = self.load_secrets()
        if key in secrets:
            del secrets[key]
            self.save_secrets(secrets)

    def list_secrets(self) -> list:
        """
        List all secret keys (without revealing values)
        :return: List of secret keys
        """
        secrets = self.load_secrets()
        return list(secrets.keys())

    def migrate_unencrypted_file(self, unencrypted_file_path: str):
        """
        Helper method to migrate an unencrypted secrets file to encrypted format
        :param unencrypted_file_path: Path to the unencrypted file
        """
        unencrypted_path = Path(unencrypted_file_path)
        if unencrypted_path.exists():
            with open(unencrypted_path, 'r') as f:
                secrets = json.load(f)
            self.save_secrets(secrets)
            print(f"Migrated {unencrypted_file_path} to encrypted format")
            # Optionally, back up and remove the unencrypted file
            backup_path = unencrypted_path.with_suffix('.json.backup')
            unencrypted_path.rename(backup_path)
            print(f"Backed up original file to {backup_path}")


# Example usage and testing
if __name__ == "__main__":
    # Create an instance of the secrets manager
    secrets_manager = SecretsManager()

    # Example: Save some secrets
    example_secrets = {
        "odoo_url": "https://your-odoo-instance.com",
        "odoo_api_key": "your_odoo_api_key_here",
        "odoo_db_name": "your_database_name",
        "social_api_token": "your_social_api_token",
        "email_password": "your_email_password",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587
    }

    # Save the example secrets
    secrets_manager.save_secrets(example_secrets)
    print("Example secrets saved successfully!")

    # Load and verify the secrets
    loaded_secrets = secrets_manager.load_secrets()
    print("Loaded secrets keys:", list(loaded_secrets.keys()))

    # Test getting a specific secret
    odoo_url = secrets_manager.get_secret("odoo_url")
    print(f"Odoo URL: {odoo_url}")