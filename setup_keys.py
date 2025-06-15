#!/usr/bin/env python3
"""Genera un archivo .env.secure cifrado y una clave .key."""
from pathlib import Path
from cryptography.fernet import Fernet


def main():
    env_path = Path(".env")
    if not env_path.exists():
        print("Archivo .env no encontrado")
        return

    key = Fernet.generate_key()
    with open(".key", "wb") as kf:
        kf.write(key)

    cipher = Fernet(key)
    encrypted = cipher.encrypt(env_path.read_bytes())
    with open(".env.secure", "wb") as ef:
        ef.write(encrypted)

    print("Credenciales cifradas en .env.secure")
    print("Clave guardada en .key (no versionar)")


if __name__ == "__main__":
    main()
