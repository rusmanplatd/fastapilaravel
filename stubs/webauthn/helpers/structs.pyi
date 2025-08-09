from __future__ import annotations

from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass


class COSEAlgorithmIdentifier(Enum):
    ES256 = -7
    RS256 = -257


class UserVerificationRequirement(Enum):
    REQUIRED = "required"
    PREFERRED = "preferred" 
    DISCOURAGED = "discouraged"


class AuthenticatorAttachment(Enum):
    PLATFORM = "platform"
    CROSS_PLATFORM = "cross-platform"


class AuthenticatorTransport(Enum):
    USB = "usb"
    NFC = "nfc"
    BLE = "ble"
    INTERNAL = "internal"


class AttestationConveyancePreference(Enum):
    NONE = "none"
    INDIRECT = "indirect"
    DIRECT = "direct"
    ENTERPRISE = "enterprise"


@dataclass
class RelyingParty:
    name: str
    id: str


@dataclass
class User:
    id: bytes
    name: str
    display_name: str


@dataclass
class AuthenticatorSelectionCriteria:
    authenticator_attachment: Optional[AuthenticatorAttachment] = None
    require_resident_key: bool = False
    user_verification: UserVerificationRequirement = UserVerificationRequirement.PREFERRED


@dataclass
class PublicKeyCredentialCreationOptions:
    rp: RelyingParty
    user: User
    challenge: bytes
    supported_pub_key_algs: List[COSEAlgorithmIdentifier]
    timeout: Optional[int] = None
    exclude_credentials: Optional[List[Dict[str, Any]]] = None
    authenticator_selection: Optional[AuthenticatorSelectionCriteria] = None
    attestation: Optional[AttestationConveyancePreference] = None


@dataclass
class PublicKeyCredentialRequestOptions:
    challenge: bytes
    timeout: Optional[int] = None
    rp_id: Optional[str] = None
    allow_credentials: Optional[List[Dict[str, Any]]] = None
    user_verification: UserVerificationRequirement = UserVerificationRequirement.PREFERRED


@dataclass
class VerifiedRegistration:
    credential_id: bytes
    credential_public_key: bytes
    sign_count: int
    aaguid: bytes
    credential_type: str
    credential_backed_up: bool
    credential_device_type: str


@dataclass  
class VerifiedAuthentication:
    credential_id: bytes
    new_sign_count: int
    credential_backed_up: bool
    credential_device_type: str


@dataclass
class RegistrationCredential:
    credential_id: bytes
    credential_public_key: bytes
    sign_count: int = 0


@dataclass  
class AuthenticationCredential:
    credential_id: bytes
    signature: bytes
    authenticator_data: bytes
    client_data_json: bytes


class ResidentKeyRequirement(Enum):
    DISCOURAGED = "discouraged"
    PREFERRED = "preferred"
    REQUIRED = "required"