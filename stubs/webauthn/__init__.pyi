from __future__ import annotations

from typing import Any, Dict, List, Optional
from .helpers.structs import (
    PublicKeyCredentialCreationOptions,
    PublicKeyCredentialRequestOptions, 
    VerifiedRegistration,
    VerifiedAuthentication
)


def generate_registration_options(
    rp_id: str,
    rp_name: str, 
    user_id: bytes,
    user_name: str,
    user_display_name: str,
    exclude_credentials: Optional[List[Dict[str, Any]]] = None,
    **kwargs: Any
) -> PublicKeyCredentialCreationOptions: ...


def verify_registration_response(
    credential: Dict[str, Any],
    expected_challenge: str,
    expected_origin: str,
    expected_rp_id: str,
    **kwargs: Any
) -> VerifiedRegistration: ...


def generate_authentication_options(
    rp_id: str,
    allow_credentials: Optional[List[Dict[str, Any]]] = None,
    **kwargs: Any
) -> PublicKeyCredentialRequestOptions: ...


def verify_authentication_response(
    credential: Dict[str, Any],
    expected_challenge: str,
    expected_origin: str,
    expected_rp_id: str,
    credential_public_key: bytes,
    credential_current_sign_count: int,
    **kwargs: Any
) -> VerifiedAuthentication: ...