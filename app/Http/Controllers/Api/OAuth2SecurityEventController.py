"""OAuth2 Security Event Token Controller - RFC 8417

This controller handles Security Event Token (SET) operations as defined in RFC 8417
for communicating security-related events in an OAuth2 ecosystem.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from fastapi import Request, Query, Body
try:
    from fastapi import Form
except ImportError:
    from fastapi.params import Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Services.OAuth2SecurityEventService import OAuth2SecurityEventService, SecurityEventType


class OAuth2SecurityEventController(BaseController):
    """Controller for OAuth2 Security Event Tokens (RFC 8417)."""

    def __init__(self) -> None:
        super().__init__()

    async def create_security_event(
        self,
        request: Request,
        db: Session,
        event_type: str = Form(...),
        subject: Dict[str, Any] = Body(...),
        event_data: Dict[str, Any] = Body(...),
        audience: Optional[List[str]] = Form(None)
    ) -> JSONResponse:
        """
        Create a Security Event Token.
        
        Args:
            request: FastAPI request object
            db: Database session
            event_type: Security event type URI
            subject: Subject of the event
            event_data: Event-specific data
            audience: Target audience(s)
            
        Returns:
            Security Event Token response
        """
        try:
            security_event_service = OAuth2SecurityEventService(db)
            
            set_token = await security_event_service.create_security_event_token(
                event_type=event_type,
                subject=subject,
                event_data=event_data,
                audience=audience
            )
            
            return JSONResponse(
                status_code=201,
                content={
                    "security_event_token": set_token,
                    "event_type": event_type,
                    "created_at": set_token  # In real implementation, extract timestamp
                }
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "set_creation_failed",
                    "error_description": str(e)
                }
            )

    async def validate_security_event(
        self,
        request: Request,
        db: Session,
        set_token: str = Form(...)
    ) -> JSONResponse:
        """
        Validate a Security Event Token.
        
        Args:
            request: FastAPI request object
            db: Database session
            set_token: Security Event Token to validate
            
        Returns:
            Validation result
        """
        try:
            security_event_service = OAuth2SecurityEventService(db)
            
            validation_result = await security_event_service.validate_security_event_token(
                set_token
            )
            
            return JSONResponse(
                status_code=200,
                content={
                    "validation_result": validation_result,
                    "rfc_compliance": "RFC 8417"
                }
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "validation_failed",
                    "error_description": str(e)
                }
            )

    async def deliver_security_event(
        self,
        request: Request,
        db: Session,
        set_token: str = Form(...),
        delivery_method: str = Form("push"),
        recipients: Optional[List[str]] = Form(None)
    ) -> JSONResponse:
        """
        Deliver a Security Event Token to subscribers.
        
        Args:
            request: FastAPI request object
            db: Database session
            set_token: Security Event Token to deliver
            delivery_method: Delivery method (push, poll)
            recipients: Specific recipients
            
        Returns:
            Delivery result
        """
        try:
            security_event_service = OAuth2SecurityEventService(db)
            
            delivery_result = await security_event_service.deliver_security_event(
                set_token=set_token,
                delivery_method=delivery_method,
                recipients=recipients
            )
            
            return JSONResponse(
                status_code=200,
                content=delivery_result
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "delivery_failed",
                    "error_description": str(e)
                }
            )

    async def subscribe_to_events(
        self,
        request: Request,
        db: Session,
        client_id: str = Form(...),
        webhook_url: str = Form(...),
        event_types: List[str] = Form(...)
    ) -> JSONResponse:
        """
        Subscribe a client to security events.
        
        Args:
            request: FastAPI request object
            db: Database session
            client_id: OAuth2 client identifier
            webhook_url: Webhook endpoint URL
            event_types: List of event types to subscribe to
            
        Returns:
            Subscription result
        """
        try:
            security_event_service = OAuth2SecurityEventService(db)
            
            success = await security_event_service.register_event_subscriber(
                client_id=client_id,
                webhook_url=webhook_url,
                event_types=event_types
            )
            
            if success:
                return JSONResponse(
                    status_code=201,
                    content={
                        "message": "Successfully subscribed to security events",
                        "client_id": client_id,
                        "webhook_url": webhook_url,
                        "event_types": event_types
                    }
                )
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "subscription_failed",
                        "error_description": "Failed to register event subscriber"
                    }
                )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "subscription_error",
                    "error_description": str(e)
                }
            )

    async def get_security_event_capabilities(
        self,
        request: Request,
        db: Session
    ) -> JSONResponse:
        """
        Get Security Event Token capabilities.
        
        Args:
            request: FastAPI request object
            db: Database session
            
        Returns:
            SET capabilities and configuration
        """
        try:
            security_event_service = OAuth2SecurityEventService(db)
            capabilities = await security_event_service.get_security_event_capabilities()
            
            # Add endpoint URLs
            base_url = f"{request.url.scheme}://{request.url.netloc}"
            capabilities.update({
                "set_creation_endpoint": f"{base_url}/oauth/security-events/create",
                "set_validation_endpoint": f"{base_url}/oauth/security-events/validate",
                "set_delivery_endpoint": f"{base_url}/oauth/security-events/deliver",
                "subscription_endpoint": f"{base_url}/oauth/security-events/subscribe"
            })
            
            return JSONResponse(
                status_code=200,
                content=capabilities
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "capabilities_error",
                    "error_description": str(e)
                }
            )

    async def create_token_revocation_event(
        self,
        request: Request,
        db: Session,
        client_id: str = Form(...),
        token_id: str = Form(...),
        token_type: str = Form("access_token"),
        reason: str = Form("user_action")
    ) -> JSONResponse:
        """
        Create a token revocation security event.
        
        Args:
            request: FastAPI request object
            db: Database session
            client_id: OAuth2 client identifier
            token_id: Token identifier
            token_type: Type of token
            reason: Revocation reason
            
        Returns:
            Security Event Token for token revocation
        """
        try:
            security_event_service = OAuth2SecurityEventService(db)
            
            set_token = await security_event_service.create_token_revocation_event(
                client_id=client_id,
                token_id=token_id,
                token_type=token_type,
                reason=reason
            )
            
            return JSONResponse(
                status_code=201,
                content={
                    "security_event_token": set_token,
                    "event_type": SecurityEventType.TOKEN_REVOKED,
                    "client_id": client_id,
                    "token_id": token_id,
                    "reason": reason
                }
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "event_creation_failed",
                    "error_description": str(e)
                }
            )

    async def create_credential_compromise_event(
        self,
        request: Request,
        db: Session,
        client_id: str = Form(...),
        compromise_type: str = Form(...),
        detected_at: Optional[str] = Form(None)
    ) -> JSONResponse:
        """
        Create a credential compromise security event.
        
        Args:
            request: FastAPI request object
            db: Database session
            client_id: OAuth2 client identifier
            compromise_type: Type of compromise
            detected_at: When compromise was detected (ISO format)
            
        Returns:
            Security Event Token for credential compromise
        """
        try:
            from datetime import datetime
            
            security_event_service = OAuth2SecurityEventService(db)
            
            detected_datetime = None
            if detected_at:
                detected_datetime = datetime.fromisoformat(detected_at.replace('Z', '+00:00'))
            
            set_token = await security_event_service.create_credential_compromise_event(
                client_id=client_id,
                compromise_type=compromise_type,
                detected_at=detected_datetime
            )
            
            return JSONResponse(
                status_code=201,
                content={
                    "security_event_token": set_token,
                    "event_type": SecurityEventType.CLIENT_CREDENTIAL_COMPROMISE,
                    "client_id": client_id,
                    "compromise_type": compromise_type
                }
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "event_creation_failed",
                    "error_description": str(e)
                }
            )

    async def create_suspicious_login_event(
        self,
        request: Request,
        db: Session,
        user_id: str = Form(...),
        client_id: str = Form(...),
        suspicious_indicators: List[str] = Form(...),
        ip_address: Optional[str] = Form(None),
        user_agent: Optional[str] = Form(None)
    ) -> JSONResponse:
        """
        Create a suspicious login security event.
        
        Args:
            request: FastAPI request object
            db: Database session
            user_id: User identifier
            client_id: OAuth2 client identifier
            suspicious_indicators: List of suspicious indicators
            ip_address: Source IP address
            user_agent: User agent string
            
        Returns:
            Security Event Token for suspicious login
        """
        try:
            security_event_service = OAuth2SecurityEventService(db)
            
            set_token = await security_event_service.create_suspicious_login_event(
                user_id=user_id,
                client_id=client_id,
                suspicious_indicators=suspicious_indicators,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return JSONResponse(
                status_code=201,
                content={
                    "security_event_token": set_token,
                    "event_type": SecurityEventType.SUSPICIOUS_LOGIN,
                    "user_id": user_id,
                    "client_id": client_id,
                    "indicators": suspicious_indicators
                }
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "event_creation_failed",
                    "error_description": str(e)
                }
            )

    async def get_supported_event_types(
        self,
        request: Request,
        db: Session
    ) -> JSONResponse:
        """
        Get supported security event types.
        
        Args:
            request: FastAPI request object
            db: Database session
            
        Returns:
            List of supported event types
        """
        try:
            event_types = [
                {
                    "type": SecurityEventType.TOKEN_REVOKED,
                    "description": "OAuth2 token revocation event",
                    "category": "oauth2"
                },
                {
                    "type": SecurityEventType.CLIENT_CREDENTIAL_COMPROMISE,
                    "description": "Client credential compromise event",
                    "category": "security"
                },
                {
                    "type": SecurityEventType.ACCOUNT_DISABLED,
                    "description": "User account disabled event",
                    "category": "account"
                },
                {
                    "type": SecurityEventType.ACCOUNT_ENABLED,
                    "description": "User account enabled event",
                    "category": "account"
                },
                {
                    "type": SecurityEventType.PASSWORD_RESET,
                    "description": "Password reset event",
                    "category": "account"
                },
                {
                    "type": SecurityEventType.CREDENTIAL_CHANGE,
                    "description": "Credential change event",
                    "category": "account"
                },
                {
                    "type": SecurityEventType.SUSPICIOUS_LOGIN,
                    "description": "Suspicious login attempt event",
                    "category": "security"
                },
                {
                    "type": SecurityEventType.RATE_LIMIT_EXCEEDED,
                    "description": "Rate limit exceeded event",
                    "category": "abuse"
                },
                {
                    "type": SecurityEventType.MFA_BYPASS_ATTEMPT,
                    "description": "MFA bypass attempt event",
                    "category": "security"
                },
                {
                    "type": SecurityEventType.ADMIN_ACTION,
                    "description": "Administrative action event",
                    "category": "admin"
                }
            ]
            
            return JSONResponse(
                status_code=200,
                content={
                    "supported_event_types": event_types,
                    "total_count": len(event_types),
                    "rfc_compliance": "RFC 8417"
                }
            )
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "event_types_error",
                    "error_description": str(e)
                }
            )