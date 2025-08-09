from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple, Set
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from fastapi import Request
import json
import secrets
import hashlib
import time

from app.Services.BaseService import BaseService
from app.Models import User, OAuth2Client, OAuth2AccessToken
from config.oauth2 import get_oauth2_settings


class OAuth2SessionManagementService(BaseService):
    """
    OAuth2 Session Management and Single Sign-Out Service
    
    This service provides session management capabilities for OAuth2 including:
    - Session creation and tracking across multiple clients
    - Single Sign-Out (SLO) coordination
    - Session state synchronization
    - Cross-domain session management
    - Session security monitoring
    - Back-channel logout coordination
    - Front-channel logout support
    """

    def __init__(self, db: Session):
        super().__init__(db)
        self.oauth2_settings = get_oauth2_settings()
        self.session_cache = {}  # In production, use Redis
        
        # Session configuration
        self.session_timeout = 3600 * 8  # 8 hours default
        self.max_concurrent_sessions = 10
        self.session_cleanup_interval = 300  # 5 minutes
        
        # Single Sign-Out configuration
        self.slo_timeout = 30  # 30 seconds for SLO coordination
        self.max_logout_endpoints = 20
        self.logout_retry_attempts = 3
        
        # Session tracking
        self.active_sessions = {}
        self.logout_coordination = {}

    async def create_session(
        self,
        user: User,
        client: OAuth2Client,
        request: Request,
        scope: Optional[str] = None,
        session_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Create a new OAuth2 session.
        
        Args:
            user: Authenticated user
            client: OAuth2 client
            request: HTTP request
            scope: Granted scopes
            session_metadata: Additional session data
            
        Returns:
            Tuple of (session_id, session_info)
        """
        session_id = secrets.token_urlsafe(32)
        current_time = datetime.utcnow()
        
        # Extract session context
        context = await self._extract_session_context(request, user, client)
        
        # Create session record
        session_info = {
            "session_id": session_id,
            "user_id": user.id,
            "client_id": client.client_id,
            "created_at": current_time,
            "last_activity": current_time,
            "expires_at": current_time + timedelta(seconds=self.session_timeout),
            "scope": scope or "",
            "status": "active",
            "context": context,
            "metadata": session_metadata or {},
            "tokens": [],
            "logout_urls": []
        }
        
        # Check concurrent session limits
        await self._enforce_session_limits(user.id, session_info)
        
        # Store session
        session_key = f"oauth_session:{session_id}"
        self.session_cache[session_key] = session_info
        
        # Track active sessions by user
        user_sessions_key = f"user_sessions:{user.id}"
        if user_sessions_key not in self.session_cache:
            self.session_cache[user_sessions_key] = set()
        self.session_cache[user_sessions_key].add(session_id)
        
        # Log session creation
        await self._log_session_event("session_created", session_info)
        
        return session_id, session_info

    async def get_session(
        self,
        session_id: str,
        update_activity: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve session information.
        
        Args:
            session_id: Session identifier
            update_activity: Whether to update last activity time
            
        Returns:
            Session information or None if not found/expired
        """
        session_key = f"oauth_session:{session_id}"
        session_info = self.session_cache.get(session_key)
        
        if not session_info:
            return None
        
        # Check expiration
        if session_info["expires_at"] < datetime.utcnow():
            await self._cleanup_expired_session(session_id, session_info)
            return None
        
        # Update last activity
        if update_activity:
            session_info["last_activity"] = datetime.utcnow()
            self.session_cache[session_key] = session_info
        
        return session_info

    async def associate_token_with_session(
        self,
        session_id: str,
        token_info: Dict[str, Any]
    ) -> bool:
        """
        Associate an access token with a session.
        
        Args:
            session_id: Session identifier
            token_info: Token information
            
        Returns:
            Success status
        """
        session_info = await self.get_session(session_id)
        if not session_info:
            return False
        
        # Add token to session
        token_record = {
            "token_id": token_info.get("access_token_id"),
            "token_hash": hashlib.sha256(
                token_info.get("access_token", "").encode()
            ).hexdigest()[:16],
            "created_at": datetime.utcnow(),
            "scope": token_info.get("scope"),
            "expires_at": token_info.get("expires_at")
        }
        
        session_info["tokens"].append(token_record)
        
        # Update session
        session_key = f"oauth_session:{session_id}"
        self.session_cache[session_key] = session_info
        
        return True

    async def register_logout_endpoint(
        self,
        session_id: str,
        logout_url: str,
        client_id: str,
        method: str = "GET"
    ) -> bool:
        """
        Register a logout endpoint for single sign-out.
        
        Args:
            session_id: Session identifier
            logout_url: Client's logout endpoint
            client_id: Client identifier
            method: HTTP method for logout
            
        Returns:
            Success status
        """
        session_info = await self.get_session(session_id)
        if not session_info:
            return False
        
        # Add logout URL
        logout_record = {
            "client_id": client_id,
            "url": logout_url,
            "method": method,
            "registered_at": datetime.utcnow(),
            "status": "registered"
        }
        
        session_info["logout_urls"].append(logout_record)
        
        # Limit number of logout endpoints
        if len(session_info["logout_urls"]) > self.max_logout_endpoints:
            session_info["logout_urls"] = session_info["logout_urls"][-self.max_logout_endpoints:]
        
        # Update session
        session_key = f"oauth_session:{session_id}"
        self.session_cache[session_key] = session_info
        
        return True

    async def initiate_single_sign_out(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[int] = None,
        logout_hint: Optional[str] = None,
        post_logout_redirect_uri: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Initiate single sign-out process.
        
        Args:
            session_id: Specific session to logout
            user_id: User ID to logout all sessions
            logout_hint: Hint about which user to logout
            post_logout_redirect_uri: Where to redirect after logout
            
        Returns:
            Tuple of (logout_request_id, logout_status)
        """
        logout_request_id = secrets.token_urlsafe(16)
        current_time = datetime.utcnow()
        
        # Determine sessions to logout
        target_sessions = []
        
        if session_id:
            session_info = await self.get_session(session_id)
            if session_info:
                target_sessions.append(session_info)
        elif user_id:
            target_sessions = await self._get_user_sessions(user_id)
        elif logout_hint:
            # Try to find sessions by hint (email, username, etc.)
            target_sessions = await self._find_sessions_by_hint(logout_hint)
        
        if not target_sessions:
            return logout_request_id, {
                "status": "no_sessions",
                "message": "No active sessions found",
                "logout_request_id": logout_request_id
            }
        
        # Create logout coordination record
        logout_coordination = {
            "logout_request_id": logout_request_id,
            "initiated_at": current_time,
            "status": "in_progress",
            "sessions": [s["session_id"] for s in target_sessions],
            "logout_endpoints": [],
            "completed_endpoints": [],
            "failed_endpoints": [],
            "post_logout_redirect_uri": post_logout_redirect_uri,
            "timeout_at": current_time + timedelta(seconds=self.slo_timeout)
        }
        
        # Collect all logout endpoints
        for session in target_sessions:
            for logout_url_info in session.get("logout_urls", []):
                logout_coordination["logout_endpoints"].append({
                    "session_id": session["session_id"],
                    "client_id": logout_url_info["client_id"],
                    "url": logout_url_info["url"],
                    "method": logout_url_info["method"],
                    "status": "pending"
                })
        
        # Store coordination record
        coordination_key = f"logout_coordination:{logout_request_id}"
        self.logout_coordination[coordination_key] = logout_coordination
        
        # Start logout process
        await self._execute_logout_coordination(logout_request_id)
        
        return logout_request_id, {
            "status": "initiated",
            "logout_request_id": logout_request_id,
            "sessions_count": len(target_sessions),
            "endpoints_count": len(logout_coordination["logout_endpoints"]),
            "estimated_completion": current_time + timedelta(seconds=self.slo_timeout)
        }

    async def _execute_logout_coordination(self, logout_request_id: str) -> None:
        """Execute the logout coordination process."""
        coordination_key = f"logout_coordination:{logout_request_id}"
        coordination = self.logout_coordination.get(coordination_key)
        
        if not coordination:
            return
        
        try:
            # Invalidate local sessions first
            for session_id in coordination["sessions"]:
                await self._invalidate_session(session_id)
            
            # Notify logout endpoints
            await self._notify_logout_endpoints(coordination)
            
            # Update coordination status
            coordination["status"] = "completed"
            coordination["completed_at"] = datetime.utcnow()
            
        except Exception as e:
            coordination["status"] = "failed"
            coordination["error"] = str(e)
            coordination["completed_at"] = datetime.utcnow()
        
        finally:
            self.logout_coordination[coordination_key] = coordination

    async def _notify_logout_endpoints(self, coordination: Dict[str, Any]) -> None:
        """Notify client logout endpoints."""
        import httpx
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for endpoint in coordination["logout_endpoints"]:
                try:
                    # Prepare logout request
                    logout_params = {
                        "logout_token": await self._create_logout_token(
                            endpoint["session_id"],
                            endpoint["client_id"]
                        ),
                        "session_id": endpoint["session_id"]
                    }
                    
                    # Send logout notification
                    if endpoint["method"].upper() == "POST":
                        response = await client.post(
                            endpoint["url"],
                            data=logout_params
                        )
                    else:
                        response = await client.get(
                            endpoint["url"],
                            params=logout_params
                        )
                    
                    if response.status_code == 200:
                        endpoint["status"] = "completed"
                        coordination["completed_endpoints"].append(endpoint)
                    else:
                        endpoint["status"] = "failed"
                        endpoint["error"] = f"HTTP {response.status_code}"
                        coordination["failed_endpoints"].append(endpoint)
                        
                except Exception as e:
                    endpoint["status"] = "failed"
                    endpoint["error"] = str(e)
                    coordination["failed_endpoints"].append(endpoint)

    async def _create_logout_token(
        self,
        session_id: str,
        client_id: str
    ) -> str:
        """Create a logout token for back-channel logout."""
        import jwt
        
        current_time = datetime.utcnow()
        
        # Create logout token payload
        payload = {
            "iss": self.oauth2_settings.oauth2_openid_connect_issuer,
            "aud": client_id,
            "iat": int(current_time.timestamp()),
            "exp": int((current_time + timedelta(minutes=5)).timestamp()),
            "jti": secrets.token_urlsafe(16),
            "events": {
                "http://schemas.openid.net/secevent/oauth/event-type/token-revoked": {},
                "http://schemas.openid.net/secevent/oauth/event-type/session-logout": {
                    "session_id": session_id
                }
            },
            "session_id": session_id
        }
        
        # Sign the logout token
        signing_key = self.oauth2_settings.oauth2_secret_key
        logout_token = jwt.encode(payload, signing_key, algorithm="HS256")
        
        return logout_token

    async def _invalidate_session(self, session_id: str) -> None:
        """Invalidate a session and associated tokens."""
        session_key = f"oauth_session:{session_id}"
        session_info = self.session_cache.get(session_key)
        
        if not session_info:
            return
        
        # Mark session as terminated
        session_info["status"] = "terminated"
        session_info["terminated_at"] = datetime.utcnow()
        
        # Revoke associated tokens
        for token_record in session_info.get("tokens", []):
            if token_record.get("token_id"):
                # In production, mark token as revoked in database
                pass
        
        # Remove from user sessions
        user_sessions_key = f"user_sessions:{session_info['user_id']}"
        if user_sessions_key in self.session_cache:
            self.session_cache[user_sessions_key].discard(session_id)
        
        # Log session termination
        await self._log_session_event("session_terminated", session_info)
        
        # Remove session record
        del self.session_cache[session_key]

    async def get_logout_status(self, logout_request_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a logout request."""
        coordination_key = f"logout_coordination:{logout_request_id}"
        coordination = self.logout_coordination.get(coordination_key)
        
        if not coordination:
            return None
        
        return {
            "logout_request_id": logout_request_id,
            "status": coordination["status"],
            "initiated_at": coordination["initiated_at"],
            "completed_at": coordination.get("completed_at"),
            "sessions_count": len(coordination["sessions"]),
            "endpoints": {
                "total": len(coordination["logout_endpoints"]),
                "completed": len(coordination["completed_endpoints"]),
                "failed": len(coordination["failed_endpoints"]),
                "pending": len(coordination["logout_endpoints"]) - 
                          len(coordination["completed_endpoints"]) - 
                          len(coordination["failed_endpoints"])
            },
            "post_logout_redirect_uri": coordination.get("post_logout_redirect_uri"),
            "error": coordination.get("error")
        }

    async def _get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all active sessions for a user."""
        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = self.session_cache.get(user_sessions_key, set())
        
        sessions = []
        for session_id in session_ids.copy():  # Copy to avoid modification during iteration
            session_info = await self.get_session(session_id)
            if session_info:
                sessions.append(session_info)
            else:
                # Clean up stale session ID
                session_ids.discard(session_id)
        
        return sessions

    async def _find_sessions_by_hint(self, hint: str) -> List[Dict[str, Any]]:
        """Find sessions by logout hint."""
        # In production, this would query the database
        # For now, search through cached sessions
        sessions = []
        
        for key, session_info in self.session_cache.items():
            if not key.startswith("oauth_session:"):
                continue
            
            if isinstance(session_info, dict):
                user_id = session_info.get("user_id")
                if user_id:
                    # In production, fetch user and check email/username
                    user = self.db.query(User).filter(User.id == user_id).first()
                    if user and (
                        getattr(user, "email", "") == hint or
                        getattr(user, "username", "") == hint
                    ):
                        sessions.append(session_info)
        
        return sessions

    async def _extract_session_context(
        self,
        request: Request,
        user: User,
        client: OAuth2Client
    ) -> Dict[str, Any]:
        """Extract session context from request."""
        return {
            "ip_address": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", ""),
            "client_name": getattr(client, "client_name", client.client_id),
            "authentication_method": "oauth2",
            "created_from_endpoint": request.url.path,
            "security_level": "standard"
        }

    async def _enforce_session_limits(
        self,
        user_id: int,
        new_session_info: Dict[str, Any]
    ) -> None:
        """Enforce concurrent session limits."""
        user_sessions = await self._get_user_sessions(user_id)
        
        if len(user_sessions) >= self.max_concurrent_sessions:
            # Remove oldest sessions
            user_sessions.sort(key=lambda x: x["created_at"])
            sessions_to_remove = user_sessions[:-(self.max_concurrent_sessions-1)]
            
            for session in sessions_to_remove:
                await self._invalidate_session(session["session_id"])

    async def _cleanup_expired_session(
        self,
        session_id: str,
        session_info: Dict[str, Any]
    ) -> None:
        """Clean up an expired session."""
        await self._log_session_event("session_expired", session_info)
        await self._invalidate_session(session_id)

    async def _log_session_event(
        self,
        event_type: str,
        session_info: Dict[str, Any]
    ) -> None:
        """Log session management events."""
        log_entry = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_info.get("session_id"),
            "user_id": session_info.get("user_id"),
            "client_id": session_info.get("client_id"),
            "context": session_info.get("context", {})
        }
        
        # In production, send to proper logging system
        if self.oauth2_settings.oauth2_debug_mode:
            print(f"Session Event: {json.dumps(log_entry, indent=2)}")

    async def cleanup_expired_sessions(self) -> Dict[str, int]:
        """Clean up expired sessions and coordination records."""
        current_time = datetime.utcnow()
        cleanup_stats = {
            "sessions_cleaned": 0,
            "coordination_cleaned": 0
        }
        
        # Clean expired sessions
        expired_sessions = []
        for key, session_info in self.session_cache.items():
            if key.startswith("oauth_session:") and isinstance(session_info, dict):
                if session_info.get("expires_at", datetime.max) < current_time:
                    expired_sessions.append(key)
        
        for session_key in expired_sessions:
            session_id = session_key.replace("oauth_session:", "")
            await self._cleanup_expired_session(session_id, self.session_cache[session_key])
            cleanup_stats["sessions_cleaned"] += 1
        
        # Clean expired logout coordination
        expired_coordinations = []
        for key, coordination in self.logout_coordination.items():
            if coordination.get("timeout_at", datetime.max) < current_time:
                expired_coordinations.append(key)
        
        for coord_key in expired_coordinations:
            del self.logout_coordination[coord_key]
            cleanup_stats["coordination_cleaned"] += 1
        
        return cleanup_stats

    async def get_session_capabilities(self) -> Dict[str, Any]:
        """Get session management capabilities."""
        return {
            "session_management_supported": True,
            "single_sign_out_supported": True,
            "back_channel_logout_supported": True,
            "front_channel_logout_supported": True,
            "session_timeout_seconds": self.session_timeout,
            "max_concurrent_sessions": self.max_concurrent_sessions,
            "slo_timeout_seconds": self.slo_timeout,
            "supported_logout_methods": ["GET", "POST"],
            "logout_token_supported": True,
            "session_tracking_enabled": True,
            "cross_domain_logout": True,
            "logout_coordination": True
        }

    async def get_session_statistics(self) -> Dict[str, Any]:
        """Get session management statistics."""
        current_time = datetime.utcnow()
        
        stats = {
            "active_sessions": 0,
            "expired_sessions": 0,
            "total_users_with_sessions": 0,
            "active_logout_coordinations": 0,
            "average_session_duration_minutes": 0,
            "sessions_by_client": {},
            "logout_success_rate": 0.0
        }
        
        # Count active sessions
        user_session_counts = {}
        for key, session_info in self.session_cache.items():
            if key.startswith("oauth_session:") and isinstance(session_info, dict):
                if session_info.get("expires_at", datetime.min) > current_time:
                    stats["active_sessions"] += 1
                    
                    user_id = session_info.get("user_id")
                    if user_id:
                        user_session_counts[user_id] = user_session_counts.get(user_id, 0) + 1
                    
                    client_id = session_info.get("client_id", "unknown")
                    stats["sessions_by_client"][client_id] = \
                        stats["sessions_by_client"].get(client_id, 0) + 1
                else:
                    stats["expired_sessions"] += 1
        
        stats["total_users_with_sessions"] = len(user_session_counts)
        
        # Count active logout coordinations
        for coordination in self.logout_coordination.values():
            if coordination.get("status") == "in_progress":
                stats["active_logout_coordinations"] += 1
        
        return stats