from __future__ import annotations

from typing import Dict, Any


def decode_credential_public_key(credential_public_key: bytes) -> Dict[str, Any]: ...


def encode_credential_public_key(public_key_dict: Dict[str, Any]) -> bytes: ...