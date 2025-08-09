"""OAuth2 DPoP Controller - RFC 9449

This controller handles OAuth2 DPoP (Demonstrating Proof-of-Possession) endpoints
according to RFC 9449 for enhanced token security.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from fastapi import Request, Header, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Services.OAuth2DPoPService import OAuth2DPoPService
from app.Services.OAuth2AuthServerService import OAuth2AuthServerService
from database.connection import get_db


class OAuth2DPoPController(BaseController):
    """OAuth2 DPoP controller implementing RFC 9449."""
    
    def __init__(self) -> None:
        super().__init__()
        self.dpop_service = OAuth2DPoPService()
        self.auth_server = OAuth2AuthServerService()
    
    async def validate_dpop_request(
        self,
        request: Request,
        db: Session = Depends(get_db),
        authorization: Optional[str] = Header(None),
        dpop: Optional[str] = Header(None, alias="DPoP")
    ) -> Dict[str, Any]:
        """
        Validate a DPoP-protected resource request.
        
        Args:
            request: FastAPI request object
            db: Database session
            authorization: Authorization header with DPoP token
            dpop: DPoP proof header
        
        Returns:
            Validation result
        """
        try:
            # Check for required headers
            if not authorization or not dpop:
                return {
                    "valid": False,
                    "error": "invalid_request",
                    "error_description": "Missing Authorization or DPoP header"
                }
            
            # Extract access token from Authorization header
            if not authorization.startswith("DPoP "):
                return {
                    "valid": False,
                    "error": "invalid_token",
                    "error_description": "Invalid Authorization header format for DPoP"
                }
            
            access_token = authorization[5:]  # Remove "DPoP " prefix
            
            # Get request details
            http_method = request.method
            http_uri = str(request.url).split("?")[0]  # Remove query parameters
            
            # Verify DPoP-bound token
            is_valid, token_obj, error = self.dpop_service.verify_dpop_bound_token(
                db=db,
                access_token=access_token,
                dpop_proof=dpop,
                http_method=http_method,
                http_uri=http_uri
            )
            
            if not is_valid:
                return {
                    "valid": False,
                    "error": "invalid_token",
                    "error_description": error or "Invalid DPoP-bound token"
                }
            
            return {
                "valid": True,
                "token": {
                    "id": token_obj.id.str,
                    "scope": token_obj.scope,
                    "client_id": token_obj.client_id.str,
                    "user_id": token_obj.user_id.str,
                    "expires_at": token_obj.expires_at.isoformat(),
                    "token_type": "DPoP"
                },
                "dpop_jkt": token_obj.dpop_jkt
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": "server_error",
                "error_description": f"DPoP validation failed: {str(e)}"
            }
    
    async def generate_dpop_demo(
        self,
        request: Request,
        http_method: str = "POST",
        http_uri: Optional[str] = None,
        algorithm: str = "RS256"
    ) -> Dict[str, Any]:
        """
        Generate a DPoP proof demonstration.
        
        Args:
            request: FastAPI request object
            http_method: HTTP method for the proof
            http_uri: HTTP URI for the proof
            algorithm: Signing algorithm
        
        Returns:
            DPoP proof demonstration
        """
        try:
            # Use current request URI if not specified
            if not http_uri:
                http_uri = str(request.url).split("?")[0]
            
            # Generate key pair
            key_pair = self.dpop_service.create_dpop_key_pair(algorithm)
            
            # Generate DPoP proof
            dpop_proof = self.dpop_service.generate_dpop_proof(
                key_pair=key_pair,
                http_method=http_method,
                http_uri=http_uri
            )
            
            # Get JWK for client use
            public_jwk = key_pair.get_jwk()
            
            return {
                "dpop_proof": dpop_proof,
                "jwk": public_jwk,
                "algorithm": algorithm,
                "http_method": http_method,
                "http_uri": http_uri,
                "instructions": {
                    "usage": "Include this proof in the 'DPoP' header when making requests",
                    "authorization_header": "Use 'DPoP <access_token>' format",
                    "key_binding": "The access token will be bound to this key pair"
                },
                "example_request": {
                    "headers": {
                        "Authorization": "DPoP <your_access_token>",
                        "DPoP": dpop_proof,
                        "Content-Type": "application/json"
                    }
                }
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate DPoP demonstration: {str(e)}"
            )
    
    async def dpop_token_introspection(
        self,
        request: Request,
        db: Session = Depends(get_db),
        authorization: Optional[str] = Header(None),
        dpop: Optional[str] = Header(None, alias="DPoP")
    ) -> Dict[str, Any]:
        """
        Introspect a DPoP-bound access token.
        
        Args:
            request: FastAPI request object
            db: Database session
            authorization: Authorization header
            dpop: DPoP proof header
        
        Returns:
            Token introspection result
        """
        try:
            # Validate DPoP request first
            validation_result = await self.validate_dpop_request(
                request=request,
                db=db,
                authorization=authorization,
                dpop=dpop
            )
            
            if not validation_result["valid"]:
                return {
                    "active": False,
                    "error": validation_result["error"],
                    "error_description": validation_result["error_description"]
                }
            
            token_info = validation_result["token"]
            
            return {
                "active": True,
                "token_type": "DPoP",
                "scope": token_info["scope"],
                "client_id": token_info["client_id"],
                "user_id": token_info["user_id"],
                "exp": token_info["expires_at"],
                "dpop_jkt": validation_result["dpop_jkt"],
                "cnf": {
                    "jkt": validation_result["dpop_jkt"]
                }
            }
            
        except Exception as e:
            return {
                "active": False,
                "error": "server_error",
                "error_description": f"DPoP introspection failed: {str(e)}"
            }
    
    async def dpop_capabilities(self) -> Dict[str, Any]:
        """
        Get DPoP capabilities and configuration.
        
        Returns:
            DPoP capabilities
        """
        return {
            "dpop_supported": True,
            "dpop_signing_alg_values_supported": self.dpop_service.supported_algorithms,
            "dpop_version": "RFC 9449",
            "features": {
                "token_binding": True,
                "replay_protection": True,
                "key_confirmation": True,
                "http_method_binding": True,
                "uri_binding": True
            },
            "security": {
                "max_proof_age_seconds": self.dpop_service.max_proof_age,
                "access_token_hash_required": True,
                "nonce_supported": True
            },
            "supported_token_types": ["access_token"],
            "supported_endpoints": [
                "token",
                "introspect",
                "userinfo",
                "resource"
            ]
        }
    
    async def dpop_nonce(self) -> Dict[str, Any]:
        """
        Get a DPoP nonce for replay protection.
        
        Returns:
            DPoP nonce response
        """
        try:
            nonce = self.dpop_service.get_dpop_nonce()
            
            return {
                "dpop_nonce": nonce,
                "expires_in": self.dpop_service.max_proof_age,
                "usage": "Include this nonce in the 'nonce' claim of your DPoP proof"
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate DPoP nonce: {str(e)}"
            )
    
    async def dpop_key_rotation_demo(
        self,
        old_algorithm: str = "RS256",
        new_algorithm: str = "ES256"
    ) -> Dict[str, Any]:
        """
        Demonstrate DPoP key rotation process.
        
        Args:
            old_algorithm: Current key algorithm
            new_algorithm: New key algorithm
        
        Returns:
            Key rotation demonstration
        """
        try:
            # Generate old and new key pairs
            old_key_pair = self.dpop_service.create_dpop_key_pair(old_algorithm)
            new_key_pair = self.dpop_service.create_dpop_key_pair(new_algorithm)
            
            # Calculate thumbprints
            old_jkt = self.dpop_service._calculate_jwk_thumbprint(old_key_pair.get_jwk())
            new_jkt = self.dpop_service._calculate_jwk_thumbprint(new_key_pair.get_jwk())
            
            return {
                "key_rotation_demo": True,
                "old_key": {
                    "algorithm": old_algorithm,
                    "jkt": old_jkt,
                    "jwk": old_key_pair.get_jwk()
                },
                "new_key": {
                    "algorithm": new_algorithm,
                    "jkt": new_jkt,
                    "jwk": new_key_pair.get_jwk()
                },
                "rotation_process": [
                    "1. Generate new key pair",
                    "2. Start using new key for DPoP proofs",
                    "3. Update token binding to new JKT",
                    "4. Securely destroy old private key"
                ],
                "security_notes": [
                    "Always rotate keys regularly",
                    "Never reuse key pairs across different purposes",
                    "Store private keys securely",
                    "Monitor for key compromise"
                ]
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate key rotation demo: {str(e)}"
            )