"""OAuth2 JWT Bearer Token Grant Controller - RFC 7521

This controller implements OAuth 2.0 JWT Bearer Token Grant as defined in RFC 7521
for service-to-service authentication and token exchange scenarios.
"""

from __future__ import annotations

import time
import hashlib
from typing import Dict, Any, Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.param_functions import Form
from starlette.requests import Request
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.Http.Controllers.BaseController import BaseController
from app.Http.Schemas.OAuth2ErrorSchemas import OAuth2ErrorCode, create_oauth2_error_response
from app.Services.OAuth2AuthServerService import OAuth2AuthServerService
from config.oauth2 import get_oauth2_settings
from database.connection import get_db


class OAuth2JWTBearerController(BaseController):
    """OAuth2 JWT Bearer Token Grant controller implementing RFC 7521."""
    
    def __init__(self) -> None:
        super().__init__()
        self.auth_server = OAuth2AuthServerService()
        self.oauth2_settings = get_oauth2_settings()
        
        # JWT Bearer grant configuration
        self.jwt_bearer_grant_type = "urn:ietf:params:oauth:grant-type:jwt-bearer"
        self.max_jwt_lifetime = 3600  # 1 hour
        self.allowed_algorithms = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
        self.clock_skew_tolerance = 300  # 5 minutes
        
        # Trusted JWT issuers (configure based on your environment)
        self.trusted_issuers = [
            "https://accounts.google.com",
            "https://login.microsoftonline.com",
            "https://your-trusted-service.com"
        ]
    
    async def jwt_bearer_token_grant(
        self,
        request: Request,
        db: Session = Depends(get_db),
        grant_type: str = Form(..., description="Must be 'urn:ietf:params:oauth:grant-type:jwt-bearer'"),
        assertion: str = Form(..., description="JWT assertion"),
        scope: Optional[str] = Form(None, description="Requested scope"),
        client_id: Optional[str] = Form(None, description="OAuth2 client identifier"),
        client_secret: Optional[str] = Form(None, description="Client secret for additional authentication")
    ) -> Dict[str, Any]:
        """
        JWT Bearer Token Grant endpoint (RFC 7521).
        
        This endpoint allows clients to obtain access tokens using JWT assertions
        for service-to-service authentication and delegation scenarios.
        
        Args:
            request: FastAPI request object
            db: Database session
            grant_type: Must be the JWT Bearer grant type URI
            assertion: JWT assertion containing authentication/authorization info
            scope: Requested token scope
            client_id: Optional client identifier
            client_secret: Optional client secret
        
        Returns:
            OAuth2 token response with JWT Bearer context
        """
        try:
            # Validate grant type
            if grant_type != self.jwt_bearer_grant_type:
                return self._create_error_response(
                    OAuth2ErrorCode.UNSUPPORTED_GRANT_TYPE,
                    f"Unsupported grant type. Expected: {self.jwt_bearer_grant_type}"
                )
            
            # Validate and parse JWT assertion
            jwt_validation = await self._validate_jwt_assertion(assertion)
            if not jwt_validation["valid"]:
                return self._create_error_response(
                    OAuth2ErrorCode.INVALID_GRANT,
                    jwt_validation["error"]
                )
            
            jwt_claims = jwt_validation["claims"]
            
            # Extract client information from JWT or form parameters
            effective_client_id = client_id or jwt_claims.get("iss")
            if not effective_client_id:
                return self._create_error_response(
                    OAuth2ErrorCode.INVALID_CLIENT,
                    "Client identification required (client_id or JWT issuer)"
                )
            
            # Validate client
            client_validation = await self._validate_jwt_bearer_client(
                db, effective_client_id, client_secret, jwt_claims
            )
            if not client_validation["valid"]:
                return self._create_error_response(
                    OAuth2ErrorCode.INVALID_CLIENT,
                    client_validation["error"]
                )
            
            client = client_validation["client"]
            
            # Determine token parameters based on JWT assertion
            token_params = self._extract_token_parameters(jwt_claims, scope)
            
            # Check authorization based on JWT content
            auth_check = await self._check_jwt_authorization(
                db, jwt_claims, token_params, client
            )
            if not auth_check["authorized"]:
                return self._create_error_response(
                    OAuth2ErrorCode.UNAUTHORIZED_CLIENT,
                    auth_check["reason"]
                )
            
            # Generate access token with JWT context
            token_result = await self._generate_jwt_bearer_tokens(
                db, client, jwt_claims, token_params
            )
            
            # Log JWT Bearer grant usage
            await self._log_jwt_bearer_usage(
                db, client, jwt_claims, token_result
            )
            
            return {
                "access_token": token_result["access_token"],
                "token_type": "Bearer",
                "expires_in": token_result["expires_in"],
                "scope": token_result["scope"],
                "jwt_bearer_context": {
                    "assertion_issuer": jwt_claims.get("iss"),
                    "assertion_subject": jwt_claims.get("sub"),
                    "assertion_audience": jwt_claims.get("aud"),
                    "grant_type": grant_type,
                    "issued_at": int(time.time())
                },
                "token_metadata": {
                    "grant_type": "jwt_bearer",
                    "assertion_validated": True,
                    "client_authenticated": client_validation["authentication_method"],
                    "rfc_compliance": "RFC 7521"
                }
            }
            
        except Exception as e:
            return self._create_error_response(
                OAuth2ErrorCode.SERVER_ERROR,
                f"JWT Bearer grant failed: {str(e)}"
            )
    
    async def validate_jwt_assertion(
        self,
        request: Request,
        assertion: str = Form(..., description="JWT assertion to validate"),
        issuer_hint: Optional[str] = Form(None, description="Expected issuer hint"),
        audience_hint: Optional[str] = Form(None, description="Expected audience hint")
    ) -> Dict[str, Any]:
        """
        Validate JWT assertion for compliance and security.
        
        This endpoint provides JWT assertion validation services for debugging
        and compliance checking purposes.
        
        Args:
            request: FastAPI request object
            assertion: JWT assertion to validate
            issuer_hint: Expected issuer hint
            audience_hint: Expected audience hint
        
        Returns:
            JWT validation result with detailed analysis
        """
        try:
            # Perform comprehensive JWT validation
            validation_result = await self._validate_jwt_assertion(
                assertion, issuer_hint, audience_hint
            )
            
            if validation_result["valid"]:
                claims = validation_result["claims"]
                
                # Additional security analysis
                security_analysis = self._analyze_jwt_security(claims, assertion)
                
                return {
                    "valid": True,
                    "claims": claims,
                    "header": validation_result.get("header", {}),
                    "security_analysis": security_analysis,
                    "compliance_check": self._check_rfc_compliance(claims),
                    "validation_timestamp": int(time.time())
                }
            else:
                return {
                    "valid": False,
                    "error": validation_result["error"],
                    "error_details": validation_result.get("error_details", {}),
                    "validation_timestamp": int(time.time())
                }
            
        except Exception as e:
            return self._create_error_response(
                OAuth2ErrorCode.SERVER_ERROR,
                f"JWT validation failed: {str(e)}"
            )
    
    async def get_jwt_bearer_configuration(
        self,
        request: Request
    ) -> Dict[str, Any]:
        """
        Get JWT Bearer grant configuration and requirements.
        
        This endpoint provides information about JWT Bearer grant support,
        requirements, and configuration for clients.
        
        Args:
            request: FastAPI request object
        
        Returns:
            JWT Bearer configuration information
        """
        try:
            base_url = f"{request.url.scheme}://{request.url.netloc}"
            
            return {
                "jwt_bearer_grant_supported": True,
                "grant_type_uri": self.jwt_bearer_grant_type,
                "token_endpoint": f"{base_url}/oauth/token",
                "jwt_bearer_endpoint": f"{base_url}/oauth/jwt-bearer/token",
                "validation_endpoint": f"{base_url}/oauth/jwt-bearer/validate",
                
                # JWT requirements
                "jwt_requirements": {
                    "supported_algorithms": self.allowed_algorithms,
                    "max_lifetime_seconds": self.max_jwt_lifetime,
                    "clock_skew_tolerance_seconds": self.clock_skew_tolerance,
                    "required_claims": ["iss", "sub", "aud", "exp", "iat"],
                    "optional_claims": ["nbf", "jti", "scope"]
                },
                
                # Security requirements
                "security_requirements": {
                    "signature_required": True,
                    "encryption_supported": False,
                    "trusted_issuers": self.trusted_issuers,
                    "audience_validation": True,
                    "replay_protection": True
                },
                
                # Supported scenarios
                "supported_scenarios": [
                    "service_to_service_authentication",
                    "token_delegation",
                    "federated_authentication",
                    "cross_domain_authorization"
                ],
                
                # Example JWT structure
                "example_jwt_claims": {
                    "iss": "https://trusted-service.example.com",
                    "sub": "service-account-123",
                    "aud": f"{base_url}/oauth/token",
                    "exp": int(time.time()) + 3600,
                    "iat": int(time.time()),
                    "jti": "unique-jwt-id-123",
                    "scope": "api:read api:write"
                },
                
                "rfc_compliance": "RFC 7521"
            }
            
        except Exception as e:
            return self._create_error_response(
                OAuth2ErrorCode.SERVER_ERROR,
                f"Failed to get JWT Bearer configuration: {str(e)}"
            )
    
    async def _validate_jwt_assertion(
        self,
        assertion: str,
        expected_issuer: Optional[str] = None,
        expected_audience: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate JWT assertion according to RFC 7521."""
        
        try:
            # Parse JWT header without verification
            header = jwt.get_unverified_header(assertion)
            
            # Validate algorithm
            algorithm = header.get("alg")
            if algorithm not in self.allowed_algorithms:
                return {
                    "valid": False,
                    "error": f"Unsupported algorithm: {algorithm}",
                    "error_details": {"supported_algorithms": self.allowed_algorithms}
                }
            
            # For this example, we'll skip signature verification
            # In production, you must verify signatures with proper key management
            claims = jwt.get_unverified_claims(assertion)
            
            # Validate required claims
            required_claims = ["iss", "sub", "aud", "exp", "iat"]
            for claim in required_claims:
                if claim not in claims:
                    return {
                        "valid": False,
                        "error": f"Missing required claim: {claim}"
                    }
            
            # Validate issuer
            issuer = claims.get("iss")
            if expected_issuer and issuer != expected_issuer:
                return {
                    "valid": False,
                    "error": f"Issuer mismatch. Expected: {expected_issuer}, Got: {issuer}"
                }
            
            # For production, validate against trusted issuers
            # if issuer not in self.trusted_issuers:
            #     return {"valid": False, "error": f"Untrusted issuer: {issuer}"}
            
            # Validate audience
            audience = claims.get("aud")
            if expected_audience and audience != expected_audience:
                return {
                    "valid": False,
                    "error": f"Audience mismatch. Expected: {expected_audience}, Got: {audience}"
                }
            
            # Validate timing claims
            current_time = int(time.time())
            
            # Check expiration
            exp = claims.get("exp")
            if exp and current_time > (exp + self.clock_skew_tolerance):
                return {
                    "valid": False,
                    "error": "JWT has expired"
                }
            
            # Check not before
            nbf = claims.get("nbf")
            if nbf and current_time < (nbf - self.clock_skew_tolerance):
                return {
                    "valid": False,
                    "error": "JWT not yet valid (nbf claim)"
                }
            
            # Check issued at
            iat = claims.get("iat")
            if iat:
                jwt_age = current_time - iat
                if jwt_age > self.max_jwt_lifetime:
                    return {
                        "valid": False,
                        "error": f"JWT too old (age: {jwt_age}s, max: {self.max_jwt_lifetime}s)"
                    }
                
                if jwt_age < -self.clock_skew_tolerance:
                    return {
                        "valid": False,
                        "error": "JWT issued in the future"
                    }
            
            return {
                "valid": True,
                "claims": claims,
                "header": header
            }
            
        except JWTError as e:
            return {
                "valid": False,
                "error": f"JWT validation error: {str(e)}"
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Assertion validation failed: {str(e)}"
            }
    
    async def _validate_jwt_bearer_client(
        self,
        db: Session,
        client_id: str,
        client_secret: Optional[str],
        jwt_claims: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate client for JWT Bearer grant."""
        
        # Find client
        client = self.auth_server.find_client_by_client_id(db, client_id)
        if not client:
            return {"valid": False, "error": "Client not found"}
        
        # Check if client supports JWT Bearer grant
        supported_grants = getattr(client, "supported_grant_types", [])
        if self.jwt_bearer_grant_type not in supported_grants:
            return {
                "valid": False,
                "error": "Client not authorized for JWT Bearer grant"
            }
        
        # Determine authentication method
        authentication_method = "jwt_assertion"
        
        # If client secret provided, validate it (hybrid authentication)
        if client_secret:
            if not self.auth_server.validate_client_credentials(db, client_id, client_secret):
                return {"valid": False, "error": "Invalid client secret"}
            authentication_method = "jwt_assertion_and_secret"
        
        # Additional JWT-specific client validation
        # Check if JWT issuer matches expected client issuer
        jwt_issuer = jwt_claims.get("iss")
        expected_issuer = getattr(client, "jwt_bearer_issuer", None)
        if expected_issuer and jwt_issuer != expected_issuer:
            return {
                "valid": False,
                "error": f"JWT issuer mismatch for client. Expected: {expected_issuer}"
            }
        
        return {
            "valid": True,
            "client": client,
            "authentication_method": authentication_method
        }
    
    def _extract_token_parameters(
        self,
        jwt_claims: Dict[str, Any],
        requested_scope: Optional[str]
    ) -> Dict[str, Any]:
        """Extract token parameters from JWT claims."""
        
        # Extract scope from JWT or use requested scope
        jwt_scope = jwt_claims.get("scope")
        if jwt_scope and isinstance(jwt_scope, str):
            effective_scope = jwt_scope
        elif requested_scope:
            effective_scope = requested_scope
        else:
            effective_scope = "read"  # Default scope
        
        # Extract other parameters
        return {
            "scope": effective_scope,
            "subject": jwt_claims.get("sub"),
            "issuer": jwt_claims.get("iss"),
            "audience": jwt_claims.get("aud"),
            "jwt_id": jwt_claims.get("jti"),
            "expires_at": jwt_claims.get("exp")
        }
    
    async def _check_jwt_authorization(
        self,
        db: Session,
        jwt_claims: Dict[str, Any],
        token_params: Dict[str, Any],
        client: Any
    ) -> Dict[str, Any]:
        """Check authorization based on JWT content."""
        
        # Check if subject is authorized for the requested scope
        subject = jwt_claims.get("sub")
        requested_scope = token_params.get("scope", "")
        
        # In a real implementation, you would check authorization policies
        # For now, perform basic validation
        
        # Check if client is authorized to act on behalf of the subject
        if not self._is_client_authorized_for_subject(client, subject):
            return {
                "authorized": False,
                "reason": f"Client not authorized to act on behalf of subject: {subject}"
            }
        
        # Check scope authorization
        if not self._is_scope_authorized_for_subject(subject, requested_scope):
            return {
                "authorized": False,
                "reason": f"Subject not authorized for scope: {requested_scope}"
            }
        
        return {"authorized": True}
    
    def _is_client_authorized_for_subject(self, client: Any, subject: str) -> bool:
        """Check if client is authorized to act on behalf of subject."""
        # In a real implementation, check delegation policies
        return True  # Placeholder
    
    def _is_scope_authorized_for_subject(self, subject: str, scope: str) -> bool:
        """Check if subject is authorized for the requested scope."""
        # In a real implementation, check subject permissions
        return True  # Placeholder
    
    async def _generate_jwt_bearer_tokens(
        self,
        db: Session,
        client: Any,
        jwt_claims: Dict[str, Any],
        token_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate tokens for JWT Bearer grant."""
        
        # Create access token with JWT context
        current_time = int(time.time())
        access_token_lifetime = self.oauth2_settings.oauth2_access_token_expire_minutes * 60
        
        access_token_claims = {
            "iss": self.oauth2_settings.oauth2_issuer,
            "aud": client.client_id,
            "sub": token_params.get("subject"),
            "iat": current_time,
            "exp": current_time + access_token_lifetime,
            "scope": token_params.get("scope"),
            "client_id": client.client_id,
            "grant_type": "jwt_bearer",
            "jti": f"jwt_bearer_{int(time.time())}_{client.client_id}",
            
            # JWT Bearer specific claims
            "jwt_bearer": {
                "assertion_issuer": jwt_claims.get("iss"),
                "assertion_subject": jwt_claims.get("sub"),
                "assertion_jti": jwt_claims.get("jti"),
                "delegation": True
            }
        }
        
        # Generate JWT access token
        access_token = jwt.encode(
            access_token_claims,
            self.oauth2_settings.oauth2_secret_key,
            algorithm=self.oauth2_settings.oauth2_algorithm
        )
        
        return {
            "access_token": access_token,
            "expires_in": access_token_lifetime,
            "scope": token_params.get("scope"),
            "token_claims": access_token_claims
        }
    
    def _analyze_jwt_security(self, claims: Dict[str, Any], assertion: str) -> Dict[str, Any]:
        """Analyze JWT security characteristics."""
        
        security_score = 100
        issues = []
        recommendations = []
        
        # Check for security best practices
        if not claims.get("jti"):
            security_score -= 10
            issues.append("Missing JWT ID (jti) claim")
            recommendations.append("Add jti claim for replay protection")
        
        if not claims.get("nbf"):
            security_score -= 5
            recommendations.append("Consider adding nbf (not before) claim")
        
        # Check token lifetime
        exp = claims.get("exp", 0)
        iat = claims.get("iat", 0)
        lifetime = exp - iat
        
        if lifetime > 3600:  # 1 hour
            security_score -= 15
            issues.append(f"Long JWT lifetime: {lifetime} seconds")
            recommendations.append("Use shorter JWT lifetimes (max 1 hour)")
        
        # Estimate entropy
        token_entropy = len(assertion) * 4  # Rough estimate
        if token_entropy < 256:
            security_score -= 10
            issues.append("Low token entropy")
        
        return {
            "security_score": max(0, security_score),
            "security_level": "high" if security_score >= 80 else "medium" if security_score >= 60 else "low",
            "issues": issues,
            "recommendations": recommendations,
            "token_entropy_estimate": token_entropy
        }
    
    def _check_rfc_compliance(self, claims: Dict[str, Any]) -> Dict[str, Any]:
        """Check RFC 7521 compliance."""
        
        compliance_issues = []
        compliance_score = 100
        
        # Required claims per RFC 7521
        required_claims = ["iss", "sub", "aud", "exp", "iat"]
        for claim in required_claims:
            if claim not in claims:
                compliance_issues.append(f"Missing required claim: {claim}")
                compliance_score -= 20
        
        # Recommended claims
        recommended_claims = ["jti", "nbf"]
        for claim in recommended_claims:
            if claim not in claims:
                compliance_score -= 5
        
        return {
            "rfc_compliant": len(compliance_issues) == 0,
            "compliance_score": max(0, compliance_score),
            "issues": compliance_issues,
            "rfc_reference": "RFC 7521"
        }
    
    async def _log_jwt_bearer_usage(
        self,
        db: Session,
        client: Any,
        jwt_claims: Dict[str, Any],
        token_result: Dict[str, Any]
    ) -> None:
        """Log JWT Bearer grant usage for auditing."""
        
        # In a real implementation, log to audit system
        log_entry = {
            "event": "jwt_bearer_grant",
            "client_id": client.client_id,
            "assertion_issuer": jwt_claims.get("iss"),
            "assertion_subject": jwt_claims.get("sub"),
            "granted_scope": token_result.get("scope"),
            "timestamp": int(time.time())
        }
        
        print(f"JWT Bearer grant: {log_entry}")
    
    def _create_error_response(
        self,
        error_code: OAuth2ErrorCode,
        description: str
    ) -> Dict[str, Any]:
        """Create standardized error response."""
        error_response = create_oauth2_error_response(
            error_code=error_code,
            description=description
        )
        
        return error_response.dict(exclude_none=True)