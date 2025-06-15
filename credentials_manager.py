from __future__ import annotations
import json
from pathlib import Path
from cryptography.fernet import Fernet

CREDENTIALS_FILE = Path('azure_credentials.enc')
KEY_FILE = Path('credentials.key')

def load_credentials() -> tuple[str, str, str]:
    """Decrypt and return Azure OpenAI credentials.

    Returns a tuple of (api_key, api_version, azure_endpoint).
    Raises FileNotFoundError if the encrypted file or key is missing.
    """
    if not CREDENTIALS_FILE.exists() or not KEY_FILE.exists():
        raise FileNotFoundError(
            'Encrypted credentials not found. Run generate_credentials.py to create them.'
        )
    key = KEY_FILE.read_bytes()
    fernet = Fernet(key)
    data = json.loads(fernet.decrypt(CREDENTIALS_FILE.read_bytes()).decode('utf-8'))
    return data['api_key'], data['api_version'], data['azure_endpoint']
