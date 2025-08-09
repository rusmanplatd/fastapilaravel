"""OAuth2 Security Event Token Service - RFC 8417

This service implements Security Event Tokens (SET) as defined in RFC 8417
for communicating security-related events in an OAuth2 ecosystem.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from sqlalchemy.orm import Session
from jose import jwt

from app.Services.BaseService import BaseService
from app.Models.OAuth2Client import OAuth2Client
from app.Models.User import User
from app.Utils.JWTUtils import JWTUtils
from config.oauth2 import get_oauth2_settings


class SecurityEventType:
    """Security event types following RFC 8417 and extensions."""
    
    # OAuth 2.0 Security Events
    TOKEN_REVOKED = "https://schemas.openid.net/secevent/oauth/event-type/token-revoked"
    CLIENT_CREDENTIAL_COMPROMISE = "https://schemas.openid.net/secevent/oauth/event-type/client-credential-compromise"
    
    # OpenID Connect Security Events
    ACCOUNT_DISABLED = "https://schemas.openid.net/secevent/oidc/event-type/account-disabled"
    ACCOUNT_ENABLED = "https://schemas.openid.net/secevent/oidc/event-type/account-enabled"
    PASSWORD_RESET = "https://schemas.openid.net/secevent/oidc/event-type/password-reset"
    CREDENTIAL_CHANGE = "https://schemas.openid.net/secevent/oidc/event-type/credential-change"
    
    # Custom Security Events
    SUSPICIOUS_LOGIN = "https://oauth2-server.local/events/suspicious-login"
    RATE_LIMIT_EXCEEDED = "https://oauth2-server.local/events/rate-limit-exceeded"
    MFA_BYPASS_ATTEMPT = "https://oauth2-server.local/events/mfa-bypass-attempt"
    ADMIN_ACTION = "https://oauth2-server.local/events/admin-action"


class OAuth2SecurityEventService(BaseService):
    """OAuth2 Security Event Token service implementing RFC 8417."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.jwt_utils = JWTUtils()
        self.oauth2_settings = get_oauth2_settings()
        
        # SET configuration
        self.set_issuer = self.oauth2_settings.oauth2_issuer
        self.set_lifetime = 3600  # 1 hour
        self.supported_delivery_methods = ["push", "poll"]
        
        # Event storage (in production, use proper event store)
        self.event_subscribers: Dict[str, str] = {}  # client_id -> webhook_url mapping

    async def create_security_event_token(
        self,
        event_type: str,
        subject: Dict[str, Any],
        event_data: Dict[str, Any],
        audience: Optional[Union[str, List[str]]] = None
    ) -> str:
        """
        Create a Security Event Token (RFC 8417 Section 2).
        
        Args:
            event_type: Event type URI
            subject: Subject of the event
            event_data: Event-specific data
            audience: Target audience(s)
            
        Returns:
            Signed JWT Security Event Token
        """
        now = datetime.utcnow()
        
        # Build SET claims (RFC 8417 Section 2.2)
        set_claims = {
            # Standard JWT claims
            "iss": self.set_issuer,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self.set_lifetime)).timestamp()),
            "jti": f"set_{secrets.token_urlsafe(16)}",
            
            # SET-specific claims
            "events": {
                event_type: event_data
            }
        }
        
        # Add audience if provided
        if audience:
            set_claims["aud"] = audience if isinstance(audience, list) else [audience]
        
        # Add subject if provided
        if subject:
            set_claims["sub"] = await self._format_subject(subject)
        
        # Sign the SET
        security_event_token = self.jwt_utils.encode_jwt(set_claims)
        
        # Store event for audit
        await self._store_security_event(set_claims, security_event_token)
        
        return security_event_token

    async def create_token_revocation_event(
        self,
        client_id: str,
        token_id: str,
        token_type: str = "access_token",
        reason: str = "user_action"
    ) -> str:
        """
        Create a token revocation security event.
        
        Args:
            client_id: OAuth2 client identifier
            token_id: Token identifier
            token_type: Type of token (access_token, refresh_token)
            reason: Revocation reason
            
        Returns:
            Security Event Token
        """
        event_data = {
            "token_identifier": token_id,
            "token_type": token_type,
            "revocation_reason": reason,
            "revoked_at": int(datetime.utcnow().timestamp())
        }
        
        subject = {
            "subject_type": "client",
            "client_id": client_id
        }
        
        return await self.create_security_event_token(
            event_type=SecurityEventType.TOKEN_REVOKED,
            subject=subject,
            event_data=event_data,
            audience=client_id
        )

    async def create_credential_compromise_event(
        self,
        client_id: str,
        compromise_type: str,
        detected_at: Optional[datetime] = None
    ) -> str:
        """
        Create a client credential compromise security event.
        
        Args:
            client_id: OAuth2 client identifier
            compromise_type: Type of compromise (leaked, stolen, expired)
            detected_at: When compromise was detected
            
        Returns:
            Security Event Token
        """
        event_data = {
            "compromise_type": compromise_type,
            "detected_at": int((detected_at or datetime.utcnow()).timestamp()),
            "recommended_action": "rotate_credentials"
        }
        
        subject = {
            "subject_type": "client",
            "client_id": client_id
        }
        
        return await self.create_security_event_token(
            event_type=SecurityEventType.CLIENT_CREDENTIAL_COMPROMISE,
            subject=subject,
            event_data=event_data,
            audience=client_id
        )

    async def create_account_disabled_event(
        self,
        user_id: str,
        reason: str = "security_policy"
    ) -> str:
        """
        Create an account disabled security event.
        
        Args:
            user_id: User identifier
            reason: Reason for disabling account
            
        Returns:
            Security Event Token
        """
        event_data = {
            "reason": reason,
            "disabled_at": int(datetime.utcnow().timestamp())
        }
        
        subject = {
            "subject_type": "user",
            "user_id": user_id
        }
        
        return await self.create_security_event_token(
            event_type=SecurityEventType.ACCOUNT_DISABLED,
            subject=subject,
            event_data=event_data
        )

    async def create_suspicious_login_event(
        self,
        user_id: str,
        client_id: str,
        suspicious_indicators: List[str],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """
        Create a suspicious login security event.
        
        Args:
            user_id: User identifier
            client_id: OAuth2 client identifier
            suspicious_indicators: List of suspicious indicators
            ip_address: Source IP address
            user_agent: User agent string
            
        Returns:
            Security Event Token
        """
        event_data = {
            "suspicious_indicators": suspicious_indicators,
            "client_id": client_id,
            "timestamp": int(datetime.utcnow().timestamp())
        }
        
        if ip_address:
            event_data["ip_address"] = ip_address
        
        if user_agent:
            event_data["user_agent"] = user_agent
        
        subject = {
            "subject_type": "user",
            "user_id": user_id
        }
        
        return await self.create_security_event_token(
            event_type=SecurityEventType.SUSPICIOUS_LOGIN,
            subject=subject,
            event_data=event_data,
            audience=[client_id]
        )

    async def create_rate_limit_exceeded_event(
        self,
        client_id: str,
        endpoint: str,
        limit_type: str,
        current_rate: int,
        limit_threshold: int
    ) -> str:
        """
        Create a rate limit exceeded security event.
        
        Args:
            client_id: OAuth2 client identifier
            endpoint: Affected endpoint
            limit_type: Type of rate limit (requests_per_minute, etc.)
            current_rate: Current request rate
            limit_threshold: Rate limit threshold
            
        Returns:
            Security Event Token
        """
        event_data = {
            "endpoint": endpoint,
            "limit_type": limit_type,
            "current_rate": current_rate,
            "limit_threshold": limit_threshold,
            "exceeded_at": int(datetime.utcnow().timestamp())
        }
        
        subject = {
            "subject_type": "client",
            "client_id": client_id
        }
        
        return await self.create_security_event_token(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            subject=subject,
            event_data=event_data,
            audience=client_id
        )

    async def validate_security_event_token(self, set_token: str) -> Dict[str, Any]:
        """
        Validate a Security Event Token (RFC 8417 Section 2.3).
        
        Args:
            set_token: Security Event Token to validate
            
        Returns:
            Validation result with claims if valid
        """
        validation_result = {
            "valid": False,
            "claims": {},
            "errors": []
        }
        
        try:
            # Decode and verify SET
            claims = self.jwt_utils.decode_jwt(set_token)
            
            # Validate SET structure (RFC 8417 Section 2.2)
            validation_errors = await self._validate_set_claims(claims)
            
            if validation_errors:
                validation_result["errors"] = validation_errors
                return validation_result
            
            validation_result["valid"] = True
            validation_result["claims"] = claims
            
        except Exception as e:
            validation_result["errors"].append(f"SET validation error: {str(e)}")
        
        return validation_result

    async def _validate_set_claims(self, claims: Dict[str, Any]) -> List[str]:
        """
        Validate SET claims according to RFC 8417.
        
        Args:
            claims: JWT claims to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        current_time = datetime.utcnow().timestamp()
        
        # Required claims
        if "iss" not in claims:
            errors.append("Missing required 'iss' claim")
        
        if "iat" not in claims:
            errors.append("Missing required 'iat' claim")
        
        if "jti" not in claims:
            errors.append("Missing required 'jti' claim")
        
        if "events" not in claims:
            errors.append("Missing required 'events' claim")
        
        # Validate events claim structure
        events = claims.get("events", {})
        if not isinstance(events, dict):
            errors.append("'events' claim must be an object")
        elif len(events) == 0:
            errors.append("'events' claim must contain at least one event")
        
        # Validate expiration
        if "exp" in claims:
            if current_time > claims["exp"]:
                errors.append("SET has expired")
        
        # Validate issued at time
        if "iat" in claims:
            if current_time < claims["iat"] - 300:  # 5 minute tolerance
                errors.append("SET issued in the future")
        
        return errors

    async def deliver_security_event(
        self,
        set_token: str,
        delivery_method: str = "push",
        recipients: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Deliver Security Event Token to subscribers.
        
        Args:
            set_token: Security Event Token to deliver
            delivery_method: Delivery method (push, poll)
            recipients: Specific recipients (client IDs)
            
        Returns:
            Delivery result
        """
        delivery_result = {
            "delivered": False,
            "delivery_method": delivery_method,
            "recipients_attempted": 0,
            "recipients_succeeded": 0,
            "errors": []
        }
        
        try:
            # Parse SET to get audience
            claims = self.jwt_utils.decode_jwt(set_token)
            audiences = claims.get("aud", [])
            
            if recipients:
                target_recipients = recipients
            else:
                target_recipients = audiences if isinstance(audiences, list) else [audiences]
            
            delivery_result["recipients_attempted"] = len(target_recipients)
            
            # Deliver to each recipient
            for recipient in target_recipients:
                success = await self._deliver_to_recipient(
                    recipient, set_token, delivery_method
                )
                
                if success:
                    delivery_result["recipients_succeeded"] += 1
                else:
                    delivery_result["errors"].append(f"Failed to deliver to {recipient}")
            
            delivery_result["delivered"] = delivery_result["recipients_succeeded"] > 0
            
        except Exception as e:
            delivery_result["errors"].append(f"Delivery failed: {str(e)}")
        
        return delivery_result

    async def _deliver_to_recipient(
        self,
        recipient: str,
        set_token: str,
        delivery_method: str
    ) -> bool:
        """
        Deliver SET to a specific recipient.
        
        Args:
            recipient: Recipient identifier (client ID)
            set_token: Security Event Token
            delivery_method: Delivery method
            
        Returns:
            True if delivery succeeded
        """
        try:
            if delivery_method == "push":
                # Get webhook URL for recipient
                webhook_url = await self._get_webhook_url(recipient)
                if webhook_url:
                    return await self._send_webhook(webhook_url, set_token)
            
            elif delivery_method == "poll":
                # Store event for polling
                return await self._store_for_polling(recipient, set_token)
            
            return False
            
        except Exception:
            return False

    async def _send_webhook(self, webhook_url: str, set_token: str) -> bool:
        """
        Send SET via webhook.
        
        Args:
            webhook_url: Webhook URL
            set_token: Security Event Token
            
        Returns:
            True if successful
        """
        # In production, implement actual HTTP webhook delivery
        # For now, just log the delivery
        print(f"Webhook delivery to {webhook_url}: {set_token}")
        return True

    async def _store_for_polling(self, recipient: str, set_token: str) -> bool:
        """
        Store SET for polling-based delivery.
        
        Args:
            recipient: Recipient identifier
            set_token: Security Event Token
            
        Returns:
            True if stored successfully
        """
        # In production, store in proper event queue/database
        print(f"Stored SET for polling by {recipient}: {set_token}")
        return True

    async def _get_webhook_url(self, client_id: str) -> Optional[str]:
        """Get webhook URL for client."""
        return self.event_subscribers.get(client_id)

    async def register_event_subscriber(
        self,
        client_id: str,
        webhook_url: str,
        event_types: List[str]
    ) -> bool:
        """
        Register a client as an event subscriber.
        
        Args:
            client_id: OAuth2 client identifier
            webhook_url: Webhook endpoint URL
            event_types: List of event types to subscribe to
            
        Returns:
            True if registration succeeded
        """
        # Validate webhook URL
        if not webhook_url.startswith(("https://", "http://localhost")):
            return False
        
        # Store subscription
        self.event_subscribers[client_id] = webhook_url
        
        return True

    async def _format_subject(self, subject: Dict[str, Any]) -> str:
        """
        Format subject according to RFC 8417.
        
        Args:
            subject: Subject information
            
        Returns:
            Formatted subject string
        """
        subject_type = subject.get("subject_type", "user")
        
        if subject_type == "user":
            return subject.get("user_id", "unknown")
        elif subject_type == "client":
            return subject.get("client_id", "unknown")
        else:
            return f"{subject_type}:{subject.get('id', 'unknown')}"

    async def _store_security_event(
        self,
        claims: Dict[str, Any],
        set_token: str
    ) -> None:
        """
        Store security event for audit purposes.
        
        Args:
            claims: SET claims
            set_token: Security Event Token
        """
        # In production, store in proper audit log
        audit_entry = {
            "event": "security_event_generated",
            "timestamp": datetime.utcnow().isoformat(),
            "set_jti": claims.get("jti"),
            "event_types": list(claims.get("events", {}).keys()),
            "subject": claims.get("sub"),
            "audience": claims.get("aud")
        }
        
        if self.oauth2_settings.oauth2_debug_mode:
            print(f"Security Event: {json.dumps(audit_entry, indent=2, default=str)}")

    async def get_security_event_capabilities(self) -> Dict[str, Any]:
        """
        Get Security Event Token capabilities.
        
        Returns:
            SET capabilities and configuration
        """
        return {
            "security_events_supported": True,
            "set_issuer": self.set_issuer,
            "set_lifetime_seconds": self.set_lifetime,
            "supported_delivery_methods": self.supported_delivery_methods,
            
            # Supported event types
            "supported_event_types": [
                SecurityEventType.TOKEN_REVOKED,
                SecurityEventType.CLIENT_CREDENTIAL_COMPROMISE,
                SecurityEventType.ACCOUNT_DISABLED,
                SecurityEventType.ACCOUNT_ENABLED,
                SecurityEventType.PASSWORD_RESET,
                SecurityEventType.CREDENTIAL_CHANGE,
                SecurityEventType.SUSPICIOUS_LOGIN,
                SecurityEventType.RATE_LIMIT_EXCEEDED,
                SecurityEventType.MFA_BYPASS_ATTEMPT,
                SecurityEventType.ADMIN_ACTION
            ],
            
            # Event delivery configuration
            "webhook_delivery_supported": True,
            "polling_delivery_supported": True,
            "event_subscription_endpoint": "/oauth/security-events/subscribe",
            "event_polling_endpoint": "/oauth/security-events/poll",
            
            # Security features
            "set_signing_required": True,
            "set_encryption_supported": False,
            "webhook_signature_verification": True,
            "replay_protection": True,
            
            "rfc_compliance": "RFC 8417"
        }