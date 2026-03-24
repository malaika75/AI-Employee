# Advanced Security System - Encryption & Secrets Management

## Overview
The Platinum Tier security system implements advanced encryption and secrets management to protect sensitive information such as API keys, database credentials, and other confidential data. This system uses industry-standard cryptographic practices to ensure sensitive information is never stored in plain text.

## Encryption Method

### Fernet Symmetric Encryption
The secrets management system uses Fernet encryption from the `cryptography` library, which provides:

- **Symmetric encryption**: The same key encrypts and decrypts data
- **Authenticated encryption**: Ensures data integrity and authenticity
- **URL-safe base64 encoding**: For safe storage in text files

### How It Works
1. **Key Generation**: A 256-bit AES key is generated and stored securely
2. **Encryption Process**:
   - Secrets are serialized to JSON format
   - The JSON string is encrypted using Fernet
   - The encrypted data is base64-encoded for file storage
3. **Decryption Process**:
   - Base64-encoded data is decoded
   - The encrypted data is decrypted using the stored key
   - The JSON string is parsed back to a dictionary

### Key Storage
- The encryption key is stored in `vault/Secrets.key`
- File permissions are restricted to owner-read/write only (0o600)
- The key file is ignored by Git to prevent accidental commits

## Secrets Management Architecture

### SecretsManager Class
The `secrets_manager.py` file contains the `SecretsManager` class which provides:

- `encrypt_data(data)`: Encrypts a dictionary of secrets
- `decrypt_data(encrypted_data)`: Decrypts an encrypted string back to secrets
- `save_secrets(secrets)`: Saves encrypted secrets to the vault
- `load_secrets()`: Loads and decrypts secrets from the vault
- `get_secret(key, default)`: Retrieves a specific secret value
- `set_secret(key, value)`: Sets a specific secret value

### Storage Location
- Encrypted secrets are stored in `vault/Secrets.json`
- The file contains a JSON object with:
  - `encrypted`: Boolean indicating encryption status
  - `version`: Schema version
  - `data`: The base64-encoded encrypted secrets

## Supported Secrets

The system supports various types of secrets:

### Odoo Integration Secrets
- `odoo_url`: URL to the Odoo instance (e.g., https://your-odoo-instance.com)
- `odoo_port`: Port number for Odoo (default: 8069)
- `odoo_db_name`: Database name
- `odoo_api_key`: API key or username for authentication
- `odoo_password`: Password for authentication

### Social Media Secrets
- `twitter_api_key`: Twitter API key
- `twitter_api_secret`: Twitter API secret
- `twitter_access_token`: Twitter access token
- `twitter_access_token_secret`: Twitter access token secret
- `facebook_api_key`: Facebook API key
- `facebook_page_id`: Facebook page ID for posting
- `instagram_api_key`: Instagram API key
- `linkedin_api_key`: LinkedIn API key

## Integration with MCP Systems

### Odoo MCP Integration
The `odoo_mcp.py` system now loads connection details from encrypted secrets:
- The `--vault-path` command-line argument is deprecated
- All credentials are retrieved via `SecretsManager`
- Configuration is backward-compatible with the new system

### Social MCP Integration
The `social_mcp.py` system includes:
- A `get_social_credentials(platform)` method to retrieve encrypted platform credentials
- Secure storage of browser sessions (separate from API credentials)
- Support for future API-based posting methods

## Why Secrets Never Sync to Git

### Security by Design
The security system prevents sensitive data from being committed to Git through several mechanisms:

1. **Git Ignore Rules**:
   - The `vault/Secrets.json` file is automatically ignored by Git
   - The `vault/Secrets.key` encryption key file is also ignored
   - All sensitive vault files are protected by `.gitignore`

2. **File Permissions**:
   - The secrets key file has restrictive permissions (0o600)
   - Only the file owner can read or write the key

3. **Encrypted Storage**:
   - Even if accidentally committed, the secrets are encrypted
   - The encryption key is separately stored and also ignored

### File Locations
```
vault/
├── Secrets.json          # Encrypted secrets (ignored by Git)
├── Secrets.key           # Encryption key (ignored by Git)
├── Need_Action/
├── Pending_Approval/
├── Approved/
├── Rejected/
├── Done/
├── Drafts/
└── Logs/
```

## Security Best Practices

### Key Rotation
- Regularly rotate encryption keys for enhanced security
- Use the `migrate_unencrypted_file()` method to transition old files
- Maintain multiple key versions during rotation periods

### Access Control
- The system implements role-based access control via the dashboard
- Only users with appropriate permissions can modify secrets
- Comprehensive audit logging tracks all secrets access

### Error Handling
- Failed decryption attempts are logged to the audit system
- Invalid secrets configurations prevent system startup
- Graceful fallbacks when secrets are missing

## Testing the Security System

### Test Flow
1. **Save Encrypted Secrets**: Use the SecretsManager to store secrets
2. **MCP Systems Load Secrets**: Verify both MCP systems load encrypted secrets correctly
3. **Verify Functionality**: Confirm systems work with encrypted credentials

### Example Usage
```python
from secrets_manager import SecretsManager

# Create manager instance
secrets_manager = SecretsManager()

# Save secrets
secrets_manager.save_secrets({
    'odoo_url': 'https://your-odoo-instance.com',
    'odoo_api_key': 'your_api_key_here',
    'odoo_password': 'your_password_here'
})

# Load secrets
secrets = secrets_manager.load_secrets()
odoo_url = secrets.get('odoo_url')
```

## Recovery Procedures

### Lost Encryption Key
If the encryption key is lost:
1. Generate a new `Secrets.json` with required credentials
2. Create a new `Secrets.key` file
3. Repopulate all secrets through the management API

### Migration from Unencrypted Data
Use the `migrate_unencrypted_file()` method to securely migrate existing configuration files to encrypted format.

## Future Enhancements

- Hardware Security Module (HSM) integration for key management
- Automatic key rotation policies
- Integration with cloud key management services
- Enhanced access logging and anomaly detection