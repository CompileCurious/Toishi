import os
import json
import uuid
import base64
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


_DEFAULTS = {
    "ftp_host": "192.168.7.1",
    "ftp_port": 2121,
    "ftp_user": "onikiri",
    "ftp_password": "onikiri",
    "data_dir": os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Toishi"),
    "auto_connect": True,
    "theme": "dark",
}

_MASKED = "••••••••"


def _derive_key() -> bytes:
    node = uuid.getnode()
    node_bytes = node.to_bytes(8, "big")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"toishi-salt-v1",
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(node_bytes))


def _fernet() -> Fernet:
    return Fernet(_derive_key())


def _settings_path(data_dir: str) -> Path:
    return Path(data_dir) / "settings.json"


def load_settings() -> dict:
    data_dir = _DEFAULTS["data_dir"]
    path = _settings_path(data_dir)
    if not path.exists():
        return dict(_DEFAULTS)
    try:
        raw = path.read_bytes()
        decrypted = _fernet().decrypt(raw)
        stored = json.loads(decrypted)
        result = dict(_DEFAULTS)
        result.update(stored)
        return result
    except Exception:
        return dict(_DEFAULTS)


def save_settings(new_settings: dict):
    current = load_settings()
    for key in _DEFAULTS:
        if key in new_settings:
            if key == "ftp_password" and new_settings[key] == _MASKED:
                continue
            current[key] = new_settings[key]
    data_dir = current.get("data_dir", _DEFAULTS["data_dir"])
    os.makedirs(data_dir, exist_ok=True)
    path = _settings_path(data_dir)
    encrypted = _fernet().encrypt(json.dumps(current).encode())
    path.write_bytes(encrypted)


def get_public_settings() -> dict:
    s = load_settings()
    s["ftp_password"] = _MASKED
    return s
