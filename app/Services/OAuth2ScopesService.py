"""OAuth2 Scopes Management Service - Laravel Passport Style

This service handles OAuth2 scopes management including creation, validation,
and scope-based access control similar to Laravel Passport.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.Utils.ULIDUtils import ULID

from app.Models.OAuth2Scope import OAuth2Scope
from app.Models.OAuth2AccessToken import OAuth2AccessToken


class OAuth2ScopesService:
    """Service for managing OAuth2 scopes."""
    
    def __init__(self) -> None:
        pass
    
    def create_scope(
        self,
        db: Session,
        scope_id: str,
        name: str,
        description: str
    ) -> OAuth2Scope:
        """
        Create a new OAuth2 scope.
        
        Args:
            db: Database session
            scope_id: Unique scope identifier
            name: Human-readable scope name
            description: Scope description
        
        Returns:
            Created OAuth2Scope instance
        
        Raises:
            ValueError: If scope_id already exists
        """
        # Check if scope already exists
        existing_scope = self.get_scope_by_id(db, scope_id)
        if existing_scope:
            raise ValueError(f"Scope with ID '{scope_id}' already exists")
        
        # Create new scope
        scope = OAuth2Scope(
            scope_id=scope_id,
            name=name,
            description=description
        )
        
        db.add(scope)
        db.commit()
        db.refresh(scope)
        
        return scope
    
    def get_scope_by_id(self, db: Session, scope_id: str) -> Optional[OAuth2Scope]:
        """
        Get scope by scope ID.
        
        Args:
            db: Database session
            scope_id: Scope identifier
        
        Returns:
            OAuth2Scope instance or None if not found
        """
        return db.query(OAuth2Scope).filter(OAuth2Scope.scope_id == scope_id).first()
    
    def get_scope_by_name(self, db: Session, name: str) -> Optional[OAuth2Scope]:
        """
        Get scope by name.
        
        Args:
            db: Database session
            name: Scope name
        
        Returns:
            OAuth2Scope instance or None if not found
        """
        return db.query(OAuth2Scope).filter(OAuth2Scope.name == name).first()
    
    def get_all_scopes(self, db: Session) -> List[OAuth2Scope]:
        """
        Get all available scopes.
        
        Args:
            db: Database session
        
        Returns:
            List of all OAuth2Scope instances
        """
        return db.query(OAuth2Scope).order_by(OAuth2Scope.name).all()
    
    def get_scopes_by_ids(self, db: Session, scope_ids: List[str]) -> List[OAuth2Scope]:
        """
        Get multiple scopes by their IDs.
        
        Args:
            db: Database session
            scope_ids: List of scope identifiers
        
        Returns:
            List of OAuth2Scope instances
        """
        return db.query(OAuth2Scope).filter(OAuth2Scope.scope_id.in_(scope_ids)).all()
    
    def update_scope(
        self,
        db: Session,
        scope_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[OAuth2Scope]:
        """
        Update an existing scope.
        
        Args:
            db: Database session
            scope_id: Scope identifier
            name: New name (optional)
            description: New description (optional)
        
        Returns:
            Updated OAuth2Scope instance or None if not found
        """
        scope = self.get_scope_by_id(db, scope_id)
        if not scope:
            return None
        
        if name is not None:
            scope.name = name
        
        if description is not None:
            scope.description = description
        
        db.commit()
        db.refresh(scope)
        
        return scope
    
    def delete_scope(self, db: Session, scope_id: str) -> bool:
        """
        Delete a scope.
        
        Args:
            db: Database session
            scope_id: Scope identifier
        
        Returns:
            True if scope was deleted, False if not found
        """
        scope = self.get_scope_by_id(db, scope_id)
        if not scope:
            return False
        
        db.delete(scope)
        db.commit()
        
        return True
    
    def validate_scopes(self, db: Session, requested_scopes: List[str]) -> List[str]:
        """
        Validate requested scopes against available scopes.
        
        Args:
            db: Database session
            requested_scopes: List of requested scope IDs
        
        Returns:
            List of valid scope IDs
        """
        if not requested_scopes:
            return []
        
        # Get available scope IDs
        available_scopes = db.query(OAuth2Scope.scope_id).all()
        available_scope_ids = {scope[0] for scope in available_scopes}
        
        # Return only valid scopes
        return [scope for scope in requested_scopes if scope in available_scope_ids]
    
    def get_default_scopes(self, db: Session) -> List[str]:
        """
        Get default scopes (all available scopes).
        You might want to implement a mechanism to mark certain scopes as default.
        
        Args:
            db: Database session
        
        Returns:
            List of default scope IDs
        """
        # For now, return all available scopes
        # In a real implementation, you might have a 'is_default' flag
        scopes = db.query(OAuth2Scope.scope_id).all()
        return [scope[0] for scope in scopes]
    
    def scope_exists(self, db: Session, scope_id: str) -> bool:
        """
        Check if a scope exists.
        
        Args:
            db: Database session
            scope_id: Scope identifier
        
        Returns:
            True if scope exists, False otherwise
        """
        return self.get_scope_by_id(db, scope_id) is not None
    
    def get_scopes_info(self, db: Session, scope_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get detailed information about scopes.
        
        Args:
            db: Database session
            scope_ids: List of scope identifiers
        
        Returns:
            List of scope information dictionaries
        """
        scopes = self.get_scopes_by_ids(db, scope_ids)
        
        return [
            {
                "scope_id": scope.scope_id,
                "name": scope.name,
                "description": scope.description,
                "created_at": scope.created_at,
                "updated_at": scope.updated_at
            }
            for scope in scopes
        ]
    
    def search_scopes(
        self,
        db: Session,
        query: str,
        limit: int = 20
    ) -> List[OAuth2Scope]:
        """
        Search scopes by name or description.
        
        Args:
            db: Database session
            query: Search query
            limit: Maximum number of results
        
        Returns:
            List of matching OAuth2Scope instances
        """
        search_pattern = f"%{query}%"
        
        return db.query(OAuth2Scope).filter(
            or_(
                OAuth2Scope.name.ilike(search_pattern),
                OAuth2Scope.description.ilike(search_pattern),
                OAuth2Scope.scope_id.ilike(search_pattern)
            )
        ).limit(limit).all()
    
    def get_scopes_usage_stats(self, db: Session) -> List[Dict[str, Any]]:
        """
        Get usage statistics for all scopes.
        
        Args:
            db: Database session
        
        Returns:
            List of scope usage statistics
        """
        from sqlalchemy import func
        import json
        
        # This is a complex query that would need optimization in production
        all_scopes = self.get_all_scopes(db)
        stats = []
        
        for scope in all_scopes:
            # Count active tokens with this scope
            # Note: This is not efficient for large datasets
            active_tokens = db.query(OAuth2AccessToken).filter(
                OAuth2AccessToken.revoked == False
            ).all()
            
            count = 0
            for token in active_tokens:
                try:
                    token_scopes = json.loads(token.scopes or "[]")
                    if scope.scope_id in token_scopes:
                        count += 1
                except (json.JSONDecodeError, TypeError):
                    continue
            
            stats.append({
                "scope_id": scope.scope_id,
                "name": scope.name,
                "description": scope.description,
                "active_tokens": count,
                "created_at": scope.created_at
            })
        
        return stats
    
    def create_default_scopes(self, db: Session) -> List[OAuth2Scope]:
        """
        Create default OAuth2 scopes.
        
        Args:
            db: Database session
        
        Returns:
            List of created scopes
        """
        default_scopes_data = [
            {
                "scope_id": "read",
                "name": "Read Access",
                "description": "Read access to your account information and data"
            },
            {
                "scope_id": "write",
                "name": "Write Access",
                "description": "Write and modify your account information and data"
            },
            {
                "scope_id": "admin",
                "name": "Admin Access",
                "description": "Full administrative access to all resources"
            },
            {
                "scope_id": "users",
                "name": "User Management",
                "description": "Manage user accounts and profiles"
            },
            {
                "scope_id": "roles",
                "name": "Role Management",
                "description": "Manage roles and permissions"
            },
            {
                "scope_id": "oauth-clients",
                "name": "OAuth Client Management",
                "description": "Manage OAuth2 clients and applications"
            },
            {
                "scope_id": "profile",
                "name": "Profile Access",
                "description": "Access to your basic profile information"
            },
            {
                "scope_id": "email",
                "name": "Email Access",
                "description": "Access to your email address"
            }
        ]
        
        created_scopes = []
        
        for scope_data in default_scopes_data:
            # Check if scope already exists
            existing_scope = self.get_scope_by_id(db, scope_data["scope_id"])
            if not existing_scope:
                try:
                    scope = self.create_scope(
                        db=db,
                        scope_id=scope_data["scope_id"],
                        name=scope_data["name"],
                        description=scope_data["description"]
                    )
                    created_scopes.append(scope)
                except ValueError:
                    # Scope already exists, skip
                    continue
        
        return created_scopes
    
    def is_scope_subset(
        self,
        db: Session,
        requested_scopes: List[str],
        allowed_scopes: List[str]
    ) -> bool:
        """
        Check if requested scopes are a subset of allowed scopes.
        
        Args:
            db: Database session
            requested_scopes: List of requested scope IDs
            allowed_scopes: List of allowed scope IDs
        
        Returns:
            True if all requested scopes are in allowed scopes
        """
        return all(scope in allowed_scopes for scope in requested_scopes)
    
    def expand_scope_wildcards(self, db: Session, scopes: List[str]) -> List[str]:
        """
        Expand wildcard scopes (e.g., "admin" might expand to multiple scopes).
        This is a placeholder for more complex scope expansion logic.
        
        Args:
            db: Database session
            scopes: List of scope IDs that might contain wildcards
        
        Returns:
            Expanded list of scope IDs
        """
        expanded = []
        
        for scope in scopes:
            if scope == "*" or scope == "all":
                # Get all available scopes
                all_scopes = self.get_all_scopes(db)
                expanded.extend([s.scope_id for s in all_scopes])
            elif scope == "admin":
                # Admin scope might include other scopes
                expanded.extend(["read", "write", "users", "roles", "oauth-clients"])
            else:
                expanded.append(scope)
        
        # Remove duplicates and return
        return list(set(expanded))