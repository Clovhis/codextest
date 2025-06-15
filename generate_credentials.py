from __future__ import annotations
import json
from pathlib import Path
from cryptography.fernet import Fernet

CREDENTIALS_FILE = Path('azure_credentials.enc')
KEY_FILE = Path('credentials.key')

def main() -> None:
    api_key = input('Azure API key: ').strip()
    api_version = input('Azure API version: ').strip()
    azure_endpoint = input('Azure endpoint: ').strip()

    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    fernet = Fernet(key)
    data = json.dumps({'api_key': api_key, 'api_version': api_version, 'azure_endpoint': azure_endpoint}).encode('utf-8')
    CREDENTIALS_FILE.write_bytes(fernet.encrypt(data))
    print(f'Encrypted credentials saved to {CREDENTIALS_FILE}')

if __name__ == '__main__':
    main()
