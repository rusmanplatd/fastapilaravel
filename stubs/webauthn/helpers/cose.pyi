from __future__ import annotations

from typing import Dict, Any
from enum import IntEnum


class COSEAlgorithmIdentifier(IntEnum):
    """COSE Algorithm Identifier constants."""
    ES256 = -7
    ES384 = -35
    ES512 = -36
    RS1 = -65535
    RS256 = -257
    RS384 = -258
    RS512 = -259
    PS256 = -37
    PS384 = -38
    PS512 = -39
    EdDSA = -8


def decode_credential_public_key(credential_public_key: bytes) -> Dict[str, Any]: ...


def encode_credential_public_key(public_key_dict: Dict[str, Any]) -> bytes: ...