from __future__ import annotations

import hashlib
import time
from typing import Callable, Optional, Dict, Any, List, Tuple, Awaitable, TypeVar, Union
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.Models import User, MFASession, MFASessionStatus
from app.Services import MFAService
from app.Services.MFAPolicyService import MFAPolicyService, MFARequirementLevel
from app.Services.MFAAuditService import MFAAuditService
from app.Services.MFARateLimitService import MFARateLimitService
from database.migrations.create_mfa_audit_log_table import MFAAuditEvent
from config.database import get_db


class AdvancedMFAMiddleware:
    """Advanced MFA middleware with policy enforcement and security features"""
    
    def __init__(self) -> None:
        # Security configuration
        self.device_fingerprint_enabled = True
        self.geo_blocking_enabled = False  # Requires GeoIP database
        self.behavioral_analysis_enabled = True
        self.adaptive_auth_enabled = True
        
        # Trusted networks (bypass MFA)
        self.trusted_networks = [
            "192.168.0.0/16",  # Private networks
            "10.0.0.0/8",
            "172.16.0.0/12"
        ]
        
        # Critical endpoints that always require MFA
        self.critical_endpoints = [
            "/api/v1/auth/change-password",
            "/api/v1/users/{user_id}/delete",
            "/api/v1/roles/assign",
            "/api/v1/permissions/grant",
            "/api/v1/admin/",
            "/api/v1/billing/",
            "/api/v1/system/"
        ]
        
        # Endpoints that never require MFA
        self.mfa_exempt_endpoints = [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/mfa/",
            "/docs",
            "/openapi.json",
            "/favicon.ico",
            "/.well-known/",
            "/health",
            "/status"
        ]
    
    async def __call__(
        self, 
        request: Request, 
        call_next: Callable[[Request], Awaitable[Response]], 
        user: Optional[User] = None
    ) -> Union[Response, JSONResponse]:
        """Advanced MFA middleware with comprehensive security checks"""
        try:
            # Skip if no user (let auth middleware handle)
            if not user:
                return await call_next(request)
            
            # Check if endpoint is exempt from MFA
            if hasattr(request, 'url'):
                path = str(request.url.path)
            elif hasattr(request, '__dict__') and hasattr(request, 'scope'):
                path = getattr(request.scope, 'path', '/')
            else:
                path = '/'
            if self._is_mfa_exempt(path):
                return await call_next(request)
            
            # Get database session
            db: Session = next(get_db())
            
            try:
                # Initialize services
                mfa_service = MFAService(db)
                policy_service = MFAPolicyService(db)
                audit_service = MFAAuditService(db)
                rate_limit_service = MFARateLimitService(db)
                
                # Gather request context
                context = self._gather_request_context(request, user)
                
                # Check if user is from trusted network
                if self._is_trusted_network(context.get("ip_address")):
                    context["trusted_network"] = True
                
                # Evaluate MFA requirement based on policy
                requirement_level, reason, policy_evaluation = policy_service.evaluate_mfa_requirement(
                    user, context
                )
                
                # Always require MFA for critical endpoints
                if self._is_critical_endpoint(path):
                    requirement_level = MFARequirementLevel.ENFORCED
                    reason += "; Critical endpoint accessed"
                
                # Skip MFA if not required and not enforced
                if requirement_level == MFARequirementLevel.NONE:
                    return await call_next(request)
                
                # Check for existing valid MFA session
                mfa_session_token = self._extract_mfa_session_token(request)
                
                if mfa_session_token:
                    # Verify MFA session
                    session_valid, session_info = self._verify_mfa_session(
                        mfa_session_token, user, mfa_service, context
                    )
                    
                    if session_valid:
                        # Log successful MFA check
                        audit_service.log_event(
                            MFAAuditEvent.VERIFICATION_SUCCESS,
                            user=user,
                            ip_address=context.get("ip_address"),
                            user_agent=context.get("user_agent"),
                            details={
                                "session_info": session_info,
                                "endpoint": path,
                                "requirement_level": requirement_level.value
                            }
                        )
                        
                        # Add MFA context to request
                        request.state.mfa_verified = True  # type: ignore[attr-defined]
                        request.state.mfa_method = session_info.get("method_used") if session_info else None  # type: ignore[attr-defined]
                        
                        return await call_next(request)
                
                # MFA required but not provided or invalid
                available_methods = mfa_service.get_available_mfa_methods(user)
                
                # Create MFA challenge session if user has MFA methods
                challenge_response = None
                if available_methods:
                    success, message, session_token = mfa_service.create_mfa_session(
                        user, 
                        context.get("ip_address"), 
                        context.get("user_agent")
                    )
                    
                    if success:
                        challenge_response = {
                            "session_token": session_token,
                            "available_methods": available_methods,
                            "expires_in": 600  # 10 minutes
                        }
                
                # Log MFA challenge
                audit_service.log_event(
                    MFAAuditEvent.MFA_REQUIRED,
                    user=user,
                    ip_address=context.get("ip_address"),
                    user_agent=context.get("user_agent"),
                    details={
                        "requirement_level": requirement_level.value,
                        "reason": reason,
                        "endpoint": path,
                        "available_methods": available_methods,
                        "policy_evaluation": policy_evaluation
                    }
                )
                
                # Return MFA challenge response
                return self._create_mfa_challenge_response(
                    requirement_level, reason, available_methods, challenge_response
                )
                
            finally:
                db.close()
                
        except Exception as e:
            # Log error and fail securely
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "message": "MFA middleware error",
                    "error": str(e)
                }
            )
    
    def _gather_request_context(self, request: Request, user: User) -> Dict[str, Any]:
        """Gather comprehensive request context for risk assessment"""
        # Get endpoint path
        if hasattr(request, 'url'):
            endpoint = str(request.url.path)
        elif hasattr(request, '__dict__') and hasattr(request, 'scope'):
            endpoint = getattr(request.scope, 'path', '/')
        else:
            endpoint = '/'
            
        # Get method
        if hasattr(request, 'method'):
            method = request.method
        elif hasattr(request, '__dict__') and hasattr(request, 'scope'):
            method = getattr(request.scope, 'method', 'GET')
        else:
            method = 'GET'
            
        context = {
            "endpoint": endpoint,
            "method": method,
            "timestamp": time.time(),
            "user_id": user.id
        }
        
        # Client information
        context["ip_address"] = self._get_client_ip(request)
        context["user_agent"] = request.headers.get("user-agent", "") if hasattr(request, 'headers') else ""
        context["referer"] = request.headers.get("referer", "")  # type: ignore[attr-defined]
        
        # Device fingerprinting
        if self.device_fingerprint_enabled:
            context["device_fingerprint"] = self._generate_device_fingerprint(request)
        
        # Behavioral analysis
        if self.behavioral_analysis_enabled:
            context.update(self._analyze_user_behavior(user, context))
        
        # Risk factors
        context["risk_factors"] = self._identify_risk_factors(request, user, context)
        
        return context
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address with proxy support"""
        # Check for forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")  # type: ignore[attr-defined]
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()  # type: ignore[no-any-return]
        
        real_ip = request.headers.get("x-real-ip")  # type: ignore[attr-defined]
        if real_ip:
            return real_ip  # type: ignore[no-any-return]
        
        # Fallback to direct connection IP
        if request.client:  # type: ignore[attr-defined]
            return request.client.host  # type: ignore[attr-defined,no-any-return]
        
        return "unknown"
    
    def _generate_device_fingerprint(self, request: Request) -> str:
        """Generate device fingerprint from request headers"""
        fingerprint_data = [
            request.headers.get("user-agent", ""),  # type: ignore[attr-defined]
            request.headers.get("accept-language", ""),  # type: ignore[attr-defined]
            request.headers.get("accept-encoding", ""),  # type: ignore[attr-defined]
            request.headers.get("sec-ch-ua", ""),  # type: ignore[attr-defined]
            request.headers.get("sec-ch-ua-platform", ""),  # type: ignore[attr-defined]
            str(sorted(request.headers.items()))  # type: ignore[attr-defined]
        ]
        
        fingerprint_string = "|".join(fingerprint_data)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]
    
    def _analyze_user_behavior(self, user: User, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user behavior patterns"""
        behavior = {
            "new_device": False,
            "new_location": False,
            "unusual_time": False,
            "unusual_endpoint": False
        }
        
        try:
            # Simple heuristics (can be enhanced with ML)
            current_hour = time.localtime().tm_hour
            
            # Unusual time (outside business hours)
            if current_hour < 6 or current_hour > 22:
                behavior["unusual_time"] = True
            
            # Check if device fingerprint is new (simplified)
            if context.get("device_fingerprint"):
                # This would typically query historical data
                behavior["new_device"] = True  # Placeholder
            
            # Check if IP/location is new (simplified)
            if context.get("ip_address"):
                # This would typically use GeoIP and historical data
                behavior["new_location"] = False  # Placeholder
            
        except Exception:
            pass  # Fail silently for behavioral analysis
        
        return behavior
    
    def _identify_risk_factors(self, request: Request, user: User, context: Dict[str, Any]) -> List[str]:
        """Identify risk factors from context"""
        risk_factors = []
        
        # High-privilege user
        if user.has_any_role(["admin", "administrator", "super_admin"]):
            risk_factors.append("high_privilege_user")
        
        # New device/location
        if context.get("new_device", False):
            risk_factors.append("new_device")
        
        if context.get("new_location", False):
            risk_factors.append("new_location")
        
        # Unusual timing
        if context.get("unusual_time", False):
            risk_factors.append("unusual_time")
        
        # Critical endpoint
        if self._is_critical_endpoint(context["endpoint"]):
            risk_factors.append("critical_endpoint")
        
        # Admin operations
        if "/admin/" in context["endpoint"] or "/manage/" in context["endpoint"]:
            risk_factors.append("admin_operation")
        
        # Data modification operations
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:  # type: ignore[attr-defined]
            risk_factors.append("data_modification")
        
        return risk_factors
    
    def _is_mfa_exempt(self, path: str) -> bool:
        """Check if endpoint is exempt from MFA"""
        return any(
            path.startswith(exempt_path.rstrip("*")) 
            for exempt_path in self.mfa_exempt_endpoints
        )
    
    def _is_critical_endpoint(self, path: str) -> bool:
        """Check if endpoint is critical and always requires MFA"""
        return any(
            path.startswith(critical_path.rstrip("*").replace("{user_id}", "").replace("//", "/"))
            for critical_path in self.critical_endpoints
        )
    
    def _is_trusted_network(self, ip_address: Optional[str]) -> bool:
        """Check if IP is from trusted network"""
        if not ip_address:
            return False
        
        try:
            import ipaddress
            ip = ipaddress.ip_address(ip_address)
            
            for network_str in self.trusted_networks:
                network = ipaddress.ip_network(network_str, strict=False)
                if ip in network:
                    return True
                    
        except Exception:
            pass
        
        return False
    
    def _extract_mfa_session_token(self, request: Request) -> Optional[str]:
        """Extract MFA session token from request"""
        # Check header
        token = request.headers.get("x-mfa-session-token")  # type: ignore[attr-defined]
        if token:
            return token  # type: ignore[no-any-return]
        
        # Check query parameter (less secure, for compatibility)
        token = request.query_params.get("mfa_session_token")  # type: ignore[attr-defined]
        if token:
            return token  # type: ignore[no-any-return]
        
        return None
    
    def _verify_mfa_session(
        self,
        session_token: str,
        user: User,
        mfa_service: MFAService,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Verify MFA session with additional security checks"""
        try:
            mfa_session = mfa_service.get_mfa_session(session_token)
            
            if not mfa_session:
                return False, None
            
            # Basic validation
            if (mfa_session.user_id != user.id or 
                mfa_session.status != MFASessionStatus.VERIFIED):
                return False, None
            
            # Additional security checks
            session_info = {
                "session_id": mfa_session.id,
                "method_used": mfa_session.method_used,
                "verified_at": mfa_session.verified_at,
                "expires_at": mfa_session.expires_at
            }
            
            # IP address validation (if available)
            if (mfa_session.ip_address and 
                context.get("ip_address") and
                mfa_session.ip_address != context.get("ip_address")):
                
                # Allow IP changes within same network/region (basic check)
                ip_address = context.get("ip_address")
                if ip_address and not self._is_similar_ip(mfa_session.ip_address, ip_address):
                    return False, {"error": "IP address mismatch"}
            
            # User agent validation (basic check)
            user_agent = context.get("user_agent")
            if (mfa_session.user_agent and 
                user_agent and
                not self._is_similar_user_agent(mfa_session.user_agent, user_agent)):
                # Log suspicious activity but don't block (user agents can vary)
                session_info["user_agent_mismatch"] = "True"
            
            return True, session_info
            
        except Exception as e:
            return False, {"error": str(e)}
    
    def _is_similar_ip(self, ip1: str, ip2: str) -> bool:
        """Check if two IPs are similar (same subnet)"""
        try:
            import ipaddress
            addr1 = ipaddress.ip_address(ip1)
            addr2 = ipaddress.ip_address(ip2)
            
            # Check if in same /24 subnet for IPv4
            if isinstance(addr1, ipaddress.IPv4Address) and isinstance(addr2, ipaddress.IPv4Address):
                network1 = ipaddress.ip_network(f"{addr1}/24", strict=False)
                return addr2 in network1
            
            return ip1 == ip2
            
        except Exception:
            return ip1 == ip2
    
    def _is_similar_user_agent(self, ua1: str, ua2: str) -> bool:
        """Check if two user agents are similar"""
        # Simple similarity check (can be enhanced)
        if not ua1 or not ua2:
            return True
        
        # Extract browser and version info
        def extract_browser_info(ua: str) -> str:
            # Simple extraction of browser name
            for browser in ["Chrome", "Firefox", "Safari", "Edge", "Opera"]:
                if browser in ua:
                    return browser
            return "unknown"
        
        return extract_browser_info(ua1) == extract_browser_info(ua2)
    
    def _create_mfa_challenge_response(
        self,
        requirement_level: MFARequirementLevel,
        reason: str,
        available_methods: List[str],
        challenge_info: Optional[Dict[str, Any]]
    ) -> JSONResponse:
        """Create MFA challenge response"""
        status_code = status.HTTP_403_FORBIDDEN
        
        # Use 401 for optional MFA, 403 for enforced
        if requirement_level in [MFARequirementLevel.REQUIRED, MFARequirementLevel.ENFORCED]:
            status_code = status.HTTP_401_UNAUTHORIZED
        
        response_data = {
            "success": False,
            "message": "Multi-Factor Authentication required",
            "requires_mfa": True,
            "requirement_level": requirement_level.value,
            "reason": reason,
            "available_methods": available_methods
        }
        
        if challenge_info:
            response_data.update(challenge_info)
        
        # Add helpful instructions
        if available_methods:
            instructions = []
            if "totp" in available_methods:
                instructions.append("Use your authenticator app")
            if "webauthn" in available_methods:
                instructions.append("Use your security key or biometric")
            if "sms" in available_methods:
                instructions.append("Use SMS verification")
            
            response_data["instructions"] = instructions
        else:
            response_data["setup_required"] = True
            response_data["message"] = "MFA setup required before accessing this resource"
        
        return JSONResponse(
            status_code=status_code,
            content=response_data,
            headers={
                "WWW-Authenticate": "MFA",
                "X-MFA-Methods": ",".join(available_methods) if available_methods else "setup-required"
            }
        )


class MFAContextManager:
    """Helper class to manage MFA context in requests"""
    
    @staticmethod
    def add_mfa_context(request: Request, **context: Any) -> None:
        """Add MFA context to request state"""
        if not hasattr(request.state, "mfa_context"):  # type: ignore[attr-defined]
            request.state.mfa_context = {}  # type: ignore[attr-defined]
        
        request.state.mfa_context.update(context)  # type: ignore[attr-defined]
    
    @staticmethod
    def get_mfa_context(request: Request) -> Dict[str, Any]:
        """Get MFA context from request state"""
        return getattr(request.state, "mfa_context", {})  # type: ignore[attr-defined]
    
    @staticmethod
    def is_mfa_verified(request: Request) -> bool:
        """Check if MFA is verified for this request"""
        return getattr(request.state, "mfa_verified", False)  # type: ignore[attr-defined]
    
    @staticmethod
    def get_mfa_method(request: Request) -> Optional[str]:
        """Get MFA method used for this request"""
        return getattr(request.state, "mfa_method", None)  # type: ignore[attr-defined]


# Utility functions for route decorators
def require_mfa(requirement_level: MFARequirementLevel = MFARequirementLevel.REQUIRED) -> Callable[[Any], Any]:
    """Decorator to require MFA for specific routes"""
    def decorator(func: Any) -> Any:
        func._mfa_required = True
        func._mfa_requirement_level = requirement_level
        return func
    return decorator


def mfa_exempt() -> Callable[[Any], Any]:
    """Decorator to exempt routes from MFA"""
    def decorator(func: Any) -> Any:
        func._mfa_exempt = True
        return func
    return decorator