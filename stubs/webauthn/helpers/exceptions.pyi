from __future__ import annotations


class WebAuthnError(Exception):
    """Base WebAuthn exception."""
    pass


class InvalidRegistrationResponse(WebAuthnError):
    """Invalid registration response."""
    pass


class InvalidAuthenticationResponse(WebAuthnError):
    """Invalid authentication response.""" 
    pass


class InvalidJSONStructure(WebAuthnError):
    """Invalid JSON structure."""
    pass