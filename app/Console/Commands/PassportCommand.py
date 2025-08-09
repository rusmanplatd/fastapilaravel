from __future__ import annotations

from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from app.Console.Command import Command
from app.Services.OAuth2ClientService import OAuth2ClientService
from app.Models.OAuth2Client import OAuth2Client
from app.Database.connection import get_db
from app.Utils.ULIDUtils import ULIDUtils


class PassportCommand(Command):
    """Laravel Passport-style OAuth2 client management command."""
    
    signature = "passport {action} {--name=} {--redirect=} {--type=} {--id=} {--regenerate} {--revoked} {--scope=} {--force} {--public} {--personal} {--password-client}"
    description = "Complete Laravel Passport OAuth2 management command"
    aliases = ["passport:client", "oauth:client", "oauth2"]
    
    def __init__(self) -> None:
        super().__init__()
        self.client_service = OAuth2ClientService()
    
    async def handle(self) -> None:
        """Execute the passport command."""
        action = self.argument('action')
        
        if not action:
            await self._show_help()
            return
        
        # Get database session
        db = next(get_db())
        
        try:
            # Client management commands
            if action == "create":
                await self._create_client(db)
            elif action == "list":
                await self._list_clients(db)
            elif action == "show":
                await self._show_client(db)
            elif action == "update":
                await self._update_client(db)
            elif action == "delete":
                await self._delete_client(db)
            elif action == "revoke":
                await self._revoke_client(db)
            elif action == "restore":
                await self._restore_client(db)
            elif action == "secret":
                await self._regenerate_secret(db)
            elif action == "tokens":
                await self._show_tokens(db)
            
            # Key management commands
            elif action == "keys":
                await self._manage_keys(db)
            elif action == "keys:generate":
                await self._generate_keys()
            
            # Scope management commands  
            elif action == "scopes":
                await self._list_scopes(db)
            elif action == "scopes:create":
                await self._create_scope(db)
            elif action == "scopes:delete":
                await self._delete_scope(db)
            
            # Token management commands
            elif action == "tokens:prune":
                await self._prune_tokens(db)
            elif action == "tokens:revoke":
                await self._revoke_tokens(db)
            elif action == "tokens:stats":
                await self._token_stats(db)
            
            # Installation and setup commands
            elif action == "install":
                await self._install_passport(db)
            elif action == "setup":
                await self._setup_passport(db)
            elif action == "purge":
                await self._purge_passport(db)
            
            # Status and diagnostics
            elif action == "status":
                await self._show_status(db)
            elif action == "stats":
                await self._show_stats(db)
            elif action == "health":
                await self._health_check(db)
            
            # Laravel Passport compatibility commands
            elif action == "client":
                await self._legacy_client_command(db)
            else:
                self.error(f"Unknown action: {action}")
                await self._show_help()
        finally:
            db.close()
    
    async def _create_client(self, db: Any) -> None:
        """Create a new OAuth2 client."""
        client_type = self.option('type') or 'authorization_code'
        name = self.option('name')
        redirect_uri = self.option('redirect')
        
        # Interactive prompts if options not provided
        if not name:
            name = self.ask("What should we name the client?", "My Application")
        
        if not redirect_uri and client_type != 'client_credentials':
            if client_type == 'personal_access':
                redirect_uri = "http://localhost"
            else:
                redirect_uri = self.ask("What should the redirect URI be?", "http://localhost/auth/callback")
        
        try:
            # Create client based on type
            if client_type == 'personal_access':
                client = self.client_service.create_personal_access_client(db, name)
                self.success(f"Personal access client created successfully.")
            elif client_type == 'password':
                client = self.client_service.create_password_client(db, name, redirect_uri or "http://localhost")
                self.success(f"Password grant client created successfully.")
            elif client_type == 'client_credentials':
                client = self.client_service.create_client_credentials_client(db, name)
                self.success(f"Client credentials client created successfully.")
            else:  # authorization_code
                confidential = self.confirm("Is this a confidential client?", True)
                client = self.client_service.create_authorization_code_client(db, name, redirect_uri, confidential)
                self.success(f"Authorization code client created successfully.")
            
            # Display client details
            self.new_line()
            self.line("Client created with the following details:")
            self.line("=" * 50)
            self.line(f"Client ID: {client.client_id}")
            if client.client_secret and not client.is_public:
                # Show the plain secret only during creation
                plain_secret = "**Hidden - check your database or regenerate**"
                if hasattr(client, '_plain_secret'):
                    plain_secret = client._plain_secret
                self.line(f"Client Secret: {plain_secret}")
            self.line(f"Name: {client.name}")
            if client.get_redirect_uris():
                self.line(f"Redirect URIs: {', '.join(client.get_redirect_uris())}")
            self.line(f"Type: {client_type}")
            self.line(f"Confidential: {'Yes' if client.is_confidential else 'No'}")
            
            if not client.is_public:
                self.new_line()
                self.comment("⚠️  Store the client secret securely. You won't be able to retrieve it again.")
                self.comment("💡 Use 'passport:client secret --id={client_id}' to regenerate if needed.")
            
        except Exception as e:
            self.error(f"Failed to create client: {str(e)}")
            raise
    
    async def _list_clients(self, db: Any) -> None:
        """List all OAuth2 clients."""
        show_revoked = self.option('revoked', False)
        
        if show_revoked:
            clients = self.client_service.get_all_clients(db, limit=100)
            title = "All OAuth2 Clients (including revoked)"
        else:
            clients = self.client_service.get_active_clients(db, limit=100)
            title = "Active OAuth2 Clients"
        
        if not clients:
            self.comment("No OAuth2 clients found.")
            return
        
        self.line(f"{title}:")
        self.line("=" * 80)
        
        headers = ["ID", "Client ID", "Name", "Type", "Status", "Created"]
        rows = []
        
        for client in clients:
            # Determine client type
            if client.is_personal_access_client:
                client_type = "Personal Access"
            elif client.is_password_client:
                client_type = "Password Grant"
            elif "client_credentials" in client.get_grant_types():
                client_type = "Client Credentials"
            else:
                client_type = "Authorization Code"
            
            # Determine status
            if client.is_revoked:
                status = "Revoked"
            elif not client.is_active:
                status = "Inactive"
            else:
                status = "Active"
            
            rows.append([
                str(client.id)[:8] + "...",
                client.client_id[:12] + "...",
                client.name[:20],
                client_type,
                status,
                client.created_at.strftime("%Y-%m-%d") if client.created_at else "N/A"
            ])
        
        self.table(headers, rows)
        
        self.new_line()
        self.comment(f"Total: {len(clients)} clients")
        if not show_revoked:
            self.comment("💡 Use --revoked to include revoked clients")
    
    async def _show_client(self, db: Any) -> None:
        """Show detailed information about a specific client."""
        client_id = self.option('id')
        
        if not client_id:
            client_id = self.ask("Enter the client database ID:")
        
        try:
            client_ulid = ULIDUtils.from_string(client_id)
            client = self.client_service.get_client_by_id(db, client_ulid)
        except:
            # Try as OAuth2 client ID
            client = self.client_service.get_client_by_client_id(db, client_id)
        
        if not client:
            self.error(f"Client not found: {client_id}")
            return
        
        self.line("OAuth2 Client Details:")
        self.line("=" * 50)
        self.line(f"Database ID: {client.id}")
        self.line(f"Client ID: {client.client_id}")
        self.line(f"Name: {client.name}")
        self.line(f"Confidential: {'Yes' if client.is_confidential else 'No'}")
        self.line(f"Active: {'Yes' if client.is_active else 'No'}")
        self.line(f"Revoked: {'Yes' if client.is_revoked else 'No'}")
        
        if client.get_redirect_uris():
            self.line(f"Redirect URIs:")
            for uri in client.get_redirect_uris():
                self.line(f"  - {uri}")
        
        self.line(f"Allowed Scopes: {', '.join(client.get_allowed_scopes())}")
        self.line(f"Grant Types: {', '.join(client.get_grant_types())}")
        self.line(f"Response Types: {', '.join(client.get_response_types())}")
        
        # Client type flags
        flags = []
        if client.is_personal_access_client:
            flags.append("Personal Access")
        if client.is_password_client:
            flags.append("Password Grant")
        if client.is_first_party:
            flags.append("First Party")
        
        if flags:
            self.line(f"Type Flags: {', '.join(flags)}")
        
        # OpenID Connect details
        if client.supports_openid_connect():
            self.line(f"OpenID Connect: Enabled")
            if client.logo_uri:
                self.line(f"Logo URI: {client.logo_uri}")
            if client.client_uri:
                self.line(f"Client URI: {client.client_uri}")
            self.line(f"Subject Type: {client.subject_type}")
            self.line(f"Token Auth Method: {client.token_endpoint_auth_method}")
        
        # Timestamps
        self.line(f"Created: {client.created_at}")
        self.line(f"Updated: {client.updated_at}")
        if client.expires_at:
            self.line(f"Expires: {client.expires_at}")
        
        # Get stats
        stats = self.client_service.get_client_stats(db, client.id)
        if stats:
            self.new_line()
            self.line("Statistics:")
            self.line(f"Active Access Tokens: {stats['active_access_tokens']}")
            self.line(f"Total Access Tokens: {stats['total_access_tokens']}")
            self.line(f"Active Refresh Tokens: {stats['active_refresh_tokens']}")
            self.line(f"Active Auth Codes: {stats['active_auth_codes']}")
    
    async def _update_client(self, db: Any) -> None:
        """Update an existing OAuth2 client."""
        client_id = self.option('id')
        
        if not client_id:
            client_id = self.ask("Enter the client database ID:")
        
        try:
            client_ulid = ULIDUtils.from_string(client_id)
            client = self.client_service.get_client_by_id(db, client_ulid)
        except:
            self.error("Invalid client ID format")
            return
        
        if not client:
            self.error(f"Client not found: {client_id}")
            return
        
        # Get update values
        name = self.option('name')
        redirect_uri = self.option('redirect')
        
        # Interactive prompts
        if not name:
            current_name = client.name
            name = self.ask(f"Client name (current: {current_name}):", current_name)
        
        if not redirect_uri and not client.is_personal_access_client:
            current_uris = client.get_redirect_uris()
            current_uri = current_uris[0] if current_uris else ""
            redirect_uri = self.ask(f"Redirect URI (current: {current_uri}):", current_uri)
        
        try:
            updated_client = self.client_service.update_client(db, client_ulid, name, redirect_uri)
            if updated_client:
                self.success("Client updated successfully.")
                
                self.new_line()
                self.line("Updated client details:")
                self.line(f"Name: {updated_client.name}")
                if updated_client.get_redirect_uris():
                    self.line(f"Redirect URIs: {', '.join(updated_client.get_redirect_uris())}")
            else:
                self.error("Failed to update client.")
                
        except Exception as e:
            self.error(f"Failed to update client: {str(e)}")
            raise
    
    async def _delete_client(self, db: Any) -> None:
        """Delete an OAuth2 client."""
        client_id = self.option('id')
        
        if not client_id:
            client_id = self.ask("Enter the client database ID:")
        
        try:
            client_ulid = ULIDUtils.from_string(client_id)
            client = self.client_service.get_client_by_id(db, client_ulid)
        except:
            self.error("Invalid client ID format")
            return
        
        if not client:
            self.error(f"Client not found: {client_id}")
            return
        
        # Confirmation
        if not self.confirm(f"Are you sure you want to delete client '{client.name}'? This action cannot be undone.", False):
            self.comment("Operation cancelled.")
            return
        
        # Get stats before deletion
        stats = self.client_service.get_client_stats(db, client.id)
        
        try:
            success = self.client_service.delete_client(db, client_ulid)
            if success:
                self.success(f"Client '{client.name}' deleted successfully.")
                
                if stats and (stats['active_access_tokens'] > 0 or stats['active_refresh_tokens'] > 0):
                    self.warning(f"⚠️  Deleted {stats['active_access_tokens']} access tokens and {stats['active_refresh_tokens']} refresh tokens")
            else:
                self.error("Failed to delete client.")
                
        except Exception as e:
            self.error(f"Failed to delete client: {str(e)}")
            raise
    
    async def _revoke_client(self, db: Any) -> None:
        """Revoke an OAuth2 client."""
        client_id = self.option('id')
        
        if not client_id:
            client_id = self.ask("Enter the client database ID:")
        
        try:
            client_ulid = ULIDUtils.from_string(client_id)
            client = self.client_service.get_client_by_id(db, client_ulid)
        except:
            self.error("Invalid client ID format")
            return
        
        if not client:
            self.error(f"Client not found: {client_id}")
            return
        
        if client.is_revoked:
            self.comment("Client is already revoked.")
            return
        
        try:
            success = self.client_service.revoke_client(db, client_ulid)
            if success:
                self.success(f"Client '{client.name}' revoked successfully.")
                self.comment("All associated tokens have been revoked.")
            else:
                self.error("Failed to revoke client.")
                
        except Exception as e:
            self.error(f"Failed to revoke client: {str(e)}")
            raise
    
    async def _restore_client(self, db: Any) -> None:
        """Restore a revoked OAuth2 client."""
        client_id = self.option('id')
        
        if not client_id:
            client_id = self.ask("Enter the client database ID:")
        
        try:
            client_ulid = ULIDUtils.from_string(client_id)
            client = self.client_service.get_client_by_id(db, client_ulid)
        except:
            self.error("Invalid client ID format")
            return
        
        if not client:
            self.error(f"Client not found: {client_id}")
            return
        
        if not client.is_revoked:
            self.comment("Client is not revoked.")
            return
        
        try:
            success = self.client_service.restore_client(db, client_ulid)
            if success:
                self.success(f"Client '{client.name}' restored successfully.")
                self.comment("Client is now active again.")
            else:
                self.error("Failed to restore client.")
                
        except Exception as e:
            self.error(f"Failed to restore client: {str(e)}")
            raise
    
    async def _regenerate_secret(self, db: Any) -> None:
        """Regenerate client secret."""
        client_id = self.option('id')
        
        if not client_id:
            client_id = self.ask("Enter the client database ID:")
        
        try:
            client_ulid = ULIDUtils.from_string(client_id)
            client = self.client_service.get_client_by_id(db, client_ulid)
        except:
            self.error("Invalid client ID format")
            return
        
        if not client:
            self.error(f"Client not found: {client_id}")
            return
        
        if client.is_public:
            self.error("Cannot regenerate secret for public clients.")
            return
        
        if not self.confirm(f"Regenerate secret for client '{client.name}'? This will invalidate the current secret.", False):
            self.comment("Operation cancelled.")
            return
        
        try:
            result = self.client_service.regenerate_client_secret(db, client_ulid)
            if result:
                updated_client, plain_secret = result
                self.success("Client secret regenerated successfully.")
                
                self.new_line()
                self.line("New client credentials:")
                self.line("=" * 40)
                self.line(f"Client ID: {updated_client.client_id}")
                self.line(f"Client Secret: {plain_secret}")
                
                self.new_line()
                self.warning("⚠️  Store the new secret securely. You won't be able to retrieve it again.")
                self.comment("💡 Update your application configuration with the new secret.")
            else:
                self.error("Failed to regenerate client secret.")
                
        except Exception as e:
            self.error(f"Failed to regenerate secret: {str(e)}")
            raise
    
    async def _show_stats(self, db: Any) -> None:
        """Show OAuth2 system statistics."""
        # Get all clients
        all_clients = self.client_service.get_all_clients(db, limit=1000)
        active_clients = [c for c in all_clients if not c.is_revoked]
        
        # Count by type
        personal_access = len([c for c in active_clients if c.is_personal_access_client])
        password_grant = len([c for c in active_clients if c.is_password_client])
        confidential = len([c for c in active_clients if c.is_confidential])
        public = len([c for c in active_clients if not c.is_confidential])
        
        self.line("OAuth2 System Statistics:")
        self.line("=" * 50)
        self.line(f"Total Clients: {len(all_clients)}")
        self.line(f"Active Clients: {len(active_clients)}")
        self.line(f"Revoked Clients: {len(all_clients) - len(active_clients)}")
        
        self.new_line()
        self.line("Client Types:")
        self.line(f"  Personal Access: {personal_access}")
        self.line(f"  Password Grant: {password_grant}")
        self.line(f"  Authorization Code: {len(active_clients) - personal_access - password_grant}")
        
        self.new_line()
        self.line("Client Confidentiality:")
        self.line(f"  Confidential: {confidential}")
        self.line(f"  Public: {public}")
        
        # Show recent activity
        recent_clients = sorted(all_clients, key=lambda x: x.created_at or datetime.min, reverse=True)[:5]
        
        if recent_clients:
            self.new_line()
            self.line("Recent Clients:")
            for client in recent_clients:
                created = client.created_at.strftime("%Y-%m-%d %H:%M") if client.created_at else "Unknown"
                status = "Revoked" if client.is_revoked else "Active"
                self.line(f"  {client.name} ({status}) - {created}")
    
    async def _show_tokens(self, db: Any) -> None:
        """Show tokens for a specific client."""
        client_id = self.option('id')
        
        if not client_id:
            client_id = self.ask("Enter the client database ID:")
        
        try:
            client_ulid = ULIDUtils.from_string(client_id)
            client = self.client_service.get_client_by_id(db, client_ulid)
        except:
            self.error("Invalid client ID format")
            return
        
        if not client:
            self.error(f"Client not found: {client_id}")
            return
        
        tokens = self.client_service.get_client_tokens(db, client_ulid, active_only=False, limit=50)
        
        self.line(f"Tokens for client '{client.name}':")
        self.line("=" * 60)
        
        # Access tokens
        access_tokens = tokens['access_tokens']
        self.line(f"Access Tokens ({len(access_tokens)}):")
        
        if access_tokens:
            headers = ["ID", "Name", "User ID", "Scopes", "Status", "Created", "Expires"]
            rows = []
            
            for token in access_tokens:
                status = []
                if token['revoked']:
                    status.append("Revoked")
                if token['expired']:
                    status.append("Expired")
                if not status:
                    status.append("Active")
                
                rows.append([
                    str(token['id'])[:8] + "...",
                    token['name'] or "N/A",
                    str(token['user_id'])[:8] + "..." if token['user_id'] else "N/A",
                    ', '.join(token['scopes'][:2]) + ("..." if len(token['scopes']) > 2 else ""),
                    ', '.join(status),
                    token['created_at'].strftime("%Y-%m-%d") if token['created_at'] else "N/A",
                    token['expires_at'].strftime("%Y-%m-%d") if token['expires_at'] else "Never"
                ])
            
            self.table(headers, rows)
        else:
            self.comment("  No access tokens found.")
        
        self.new_line()
        
        # Refresh tokens
        refresh_tokens = tokens['refresh_tokens']
        self.line(f"Refresh Tokens ({len(refresh_tokens)}):")
        
        if refresh_tokens:
            headers = ["ID", "Access Token", "Status", "Created", "Expires"]
            rows = []
            
            for token in refresh_tokens:
                status = []
                if token['revoked']:
                    status.append("Revoked")
                if token['expired']:
                    status.append("Expired")
                if not status:
                    status.append("Active")
                
                rows.append([
                    str(token['id'])[:8] + "...",
                    str(token['access_token_id'])[:8] + "...",
                    ', '.join(status),
                    token['created_at'].strftime("%Y-%m-%d") if token['created_at'] else "N/A",
                    token['expires_at'].strftime("%Y-%m-%d") if token['expires_at'] else "Never"
                ])
            
            self.table(headers, rows)
        else:
            self.comment("  No refresh tokens found.")
    
    async def _install_passport(self, db: Any) -> None:
        """Install default Passport clients."""
        self.comment("Installing Laravel Passport OAuth2 clients...")
        
        try:
            # Create personal access client
            personal_client = self.client_service.create_personal_access_client(
                db, "Personal Access Client"
            )
            self.success("✅ Personal Access Client created")
            
            # Create password grant client  
            password_client = self.client_service.create_password_client(
                db, "Password Grant Client", "http://localhost"
            )
            self.success("✅ Password Grant Client created")
            
            self.new_line()
            self.line("Passport installation complete!")
            self.line("=" * 50)
            self.line("Created clients:")
            self.line(f"Personal Access - ID: {personal_client.client_id}")
            self.line(f"Password Grant - ID: {password_client.client_id}")
            
            self.new_line()
            self.comment("💡 Use 'passport:client list' to view all clients")
            self.comment("💡 Use 'passport:client create' to create additional clients")
            
        except Exception as e:
            self.error(f"Failed to install Passport: {str(e)}")
            raise
    
    # Key Management Methods
    async def _manage_keys(self, db: Any) -> None:
        """Manage OAuth2 encryption keys."""
        self.line("OAuth2 Key Management:")
        self.line("=" * 50)
        
        # Check if keys exist
        try:
            from app.Utils.JWTUtils import JWTUtils
            jwt_utils = JWTUtils()
            
            # Check for RSA keys
            private_key_path = Path("storage/oauth2/oauth-private.key")
            public_key_path = Path("storage/oauth2/oauth-public.key")
            
            if private_key_path.exists() and public_key_path.exists():
                self.success("✅ RSA key pair exists")
                self.line(f"Private key: {private_key_path}")
                self.line(f"Public key: {public_key_path}")
                
                # Show key info
                with open(public_key_path, 'r') as f:
                    public_key_content = f.read()
                    self.line(f"Public key length: {len(public_key_content)} characters")
            else:
                self.warning("⚠️  RSA key pair not found")
                self.comment("Use 'passport keys:generate' to create new keys")
            
            # Check JWT secret
            from config.oauth2 import oauth2_settings
            if oauth2_settings.oauth2_secret_key != "your-oauth2-secret-key-change-in-production":
                self.success("✅ JWT secret configured")
            else:
                self.warning("⚠️  Default JWT secret detected")
                self.comment("Update your .env file with a secure JWT_SECRET")
                
        except Exception as e:
            self.error(f"Failed to check keys: {str(e)}")
    
    async def _generate_keys(self) -> None:
        """Generate new OAuth2 encryption keys."""
        if not self.option('force'):
            private_key_path = Path("storage/oauth2/oauth-private.key")
            public_key_path = Path("storage/oauth2/oauth-public.key")
            
            if private_key_path.exists() or public_key_path.exists():
                if not self.confirm("Encryption keys already exist. Overwrite?", False):
                    self.comment("Key generation cancelled.")
                    return
        
        try:
            # Create storage directory
            storage_dir = Path("storage/oauth2")
            storage_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate RSA key pair
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Serialize private key
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            # Serialize public key
            public_key = private_key.public_key()
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            # Write keys to files
            with open("storage/oauth2/oauth-private.key", "wb") as f:
                f.write(private_pem)
            
            with open("storage/oauth2/oauth-public.key", "wb") as f:
                f.write(public_pem)
            
            # Set proper permissions
            import os
            os.chmod("storage/oauth2/oauth-private.key", 0o600)
            os.chmod("storage/oauth2/oauth-public.key", 0o644)
            
            self.success("✅ Encryption keys generated successfully")
            self.line("Private key: storage/oauth2/oauth-private.key")
            self.line("Public key: storage/oauth2/oauth-public.key")
            
            self.new_line()
            self.comment("💡 Keys are used for JWT token signing and OpenID Connect")
            
        except Exception as e:
            self.error(f"Failed to generate keys: {str(e)}")
    
    # Scope Management Methods
    async def _list_scopes(self, db: Any) -> None:
        """List all OAuth2 scopes."""
        from config.oauth2 import oauth2_settings
        
        self.line("OAuth2 Scopes:")
        self.line("=" * 50)
        
        supported_scopes = oauth2_settings.oauth2_supported_scopes
        default_scope = oauth2_settings.oauth2_default_scope
        
        headers = ["Scope", "Type", "Description"]
        rows = []
        
        scope_descriptions = {
            "openid": "OpenID Connect identity token",
            "profile": "User profile information", 
            "email": "User email address",
            "phone": "User phone number",
            "address": "User address information",
            "offline_access": "Refresh token access",
            "read": "Read access to resources",
            "write": "Write access to resources", 
            "admin": "Administrative access",
            "users": "User management access",
            "roles": "Role management access",
            "permissions": "Permission management access",
            "oauth-clients": "OAuth client management",
            "oauth-tokens": "OAuth token management",
            "api": "General API access",
            "mobile": "Mobile application access",
            "web": "Web application access"
        }
        
        for scope in supported_scopes:
            scope_type = "Default" if scope == default_scope else "Standard"
            if scope.startswith("openid") or scope in ["profile", "email", "phone", "address"]:
                scope_type = "OpenID Connect"
            elif scope in ["admin", "users", "roles", "permissions"]:
                scope_type = "Administrative"
            
            description = scope_descriptions.get(scope, "Custom scope")
            rows.append([scope, scope_type, description])
        
        self.table(headers, rows)
        
        self.new_line()
        self.comment(f"Total: {len(supported_scopes)} scopes")
        self.comment(f"Default scope: {default_scope}")
    
    async def _create_scope(self, db: Any) -> None:
        """Create a new OAuth2 scope."""
        scope_name = self.option('scope')
        
        if not scope_name:
            scope_name = self.ask("Enter scope name:")
        
        description = self.ask("Enter scope description:", f"Access to {scope_name} resources")
        
        # This would typically update your configuration
        self.comment("⚠️  Scope creation requires configuration file updates")
        self.line("Add the following to your oauth2.py configuration:")
        self.line(f"'{scope_name}': '{description}'")
        
        self.new_line()
        self.comment("💡 Restart your application after updating configuration")
    
    async def _delete_scope(self, db: Any) -> None:
        """Delete an OAuth2 scope."""
        scope_name = self.option('scope')
        
        if not scope_name:
            scope_name = self.ask("Enter scope name to delete:")
        
        self.warning(f"⚠️  Deleting scope '{scope_name}' will affect existing tokens")
        if self.confirm("Are you sure?", False):
            self.comment("Scope deletion requires configuration file updates")
            self.line(f"Remove '{scope_name}' from oauth2_supported_scopes in oauth2.py")
        else:
            self.comment("Scope deletion cancelled.")
    
    # Token Management Methods
    async def _prune_tokens(self, db: Any) -> None:
        """Prune expired tokens."""
        from app.Models.OAuth2AccessToken import OAuth2AccessToken
        from app.Models.OAuth2RefreshToken import OAuth2RefreshToken
        from app.Models.OAuth2AuthorizationCode import OAuth2AuthorizationCode
        from datetime import datetime
        
        try:
            # Count expired tokens before deletion
            now = datetime.now()
            
            expired_access_tokens = db.query(OAuth2AccessToken).filter(
                OAuth2AccessToken.expires_at < now,
                OAuth2AccessToken.revoked == False
            ).count()
            
            expired_refresh_tokens = db.query(OAuth2RefreshToken).filter(
                OAuth2RefreshToken.expires_at < now,
                OAuth2RefreshToken.revoked == False
            ).count()
            
            expired_auth_codes = db.query(OAuth2AuthorizationCode).filter(
                OAuth2AuthorizationCode.expires_at < now,
                OAuth2AuthorizationCode.revoked == False
            ).count()
            
            total_expired = expired_access_tokens + expired_refresh_tokens + expired_auth_codes
            
            if total_expired == 0:
                self.comment("No expired tokens found.")
                return
            
            self.line(f"Found {total_expired} expired tokens:")
            self.line(f"  Access tokens: {expired_access_tokens}")
            self.line(f"  Refresh tokens: {expired_refresh_tokens}")
            self.line(f"  Authorization codes: {expired_auth_codes}")
            
            if not self.option('force'):
                if not self.confirm("Delete expired tokens?", True):
                    self.comment("Token pruning cancelled.")
                    return
            
            # Delete expired tokens
            deleted_access = db.query(OAuth2AccessToken).filter(
                OAuth2AccessToken.expires_at < now,
                OAuth2AccessToken.revoked == False
            ).delete()
            
            deleted_refresh = db.query(OAuth2RefreshToken).filter(
                OAuth2RefreshToken.expires_at < now,
                OAuth2RefreshToken.revoked == False
            ).delete()
            
            deleted_codes = db.query(OAuth2AuthorizationCode).filter(
                OAuth2AuthorizationCode.expires_at < now,
                OAuth2AuthorizationCode.revoked == False
            ).delete()
            
            db.commit()
            
            total_deleted = deleted_access + deleted_refresh + deleted_codes
            self.success(f"✅ Pruned {total_deleted} expired tokens")
            
        except Exception as e:
            db.rollback()
            self.error(f"Failed to prune tokens: {str(e)}")
    
    async def _revoke_tokens(self, db: Any) -> None:
        """Revoke tokens for a specific client."""
        client_id = self.option('id')
        
        if not client_id:
            client_id = self.ask("Enter client database ID:")
        
        try:
            from app.Utils.ULIDUtils import ULIDUtils
            client_ulid = ULIDUtils.from_string(client_id)
            client = self.client_service.get_client_by_id(db, client_ulid)
        except:
            self.error("Invalid client ID format")
            return
        
        if not client:
            self.error(f"Client not found: {client_id}")
            return
        
        # Get token counts
        stats = self.client_service.get_client_stats(db, client.id)
        active_tokens = stats['active_access_tokens'] + stats['active_refresh_tokens']
        
        if active_tokens == 0:
            self.comment(f"No active tokens found for client '{client.name}'")
            return
        
        self.warning(f"⚠️  This will revoke {active_tokens} active tokens for '{client.name}'")
        if not self.confirm("Continue?", False):
            self.comment("Token revocation cancelled.")
            return
        
        try:
            # Revoke all client tokens
            success = self.client_service.revoke_client_tokens(db, client_ulid)
            if success:
                self.success(f"✅ Revoked all tokens for client '{client.name}'")
            else:
                self.error("Failed to revoke tokens")
                
        except Exception as e:
            self.error(f"Failed to revoke tokens: {str(e)}")
    
    async def _token_stats(self, db: Any) -> None:
        """Show detailed token statistics."""
        from app.Models.OAuth2AccessToken import OAuth2AccessToken
        from app.Models.OAuth2RefreshToken import OAuth2RefreshToken
        from app.Models.OAuth2AuthorizationCode import OAuth2AuthorizationCode
        from datetime import datetime, timedelta
        
        try:
            now = datetime.now()
            
            # Access token stats
            total_access_tokens = db.query(OAuth2AccessToken).count()
            active_access_tokens = db.query(OAuth2AccessToken).filter(
                OAuth2AccessToken.expires_at > now,
                OAuth2AccessToken.revoked == False
            ).count()
            expired_access_tokens = db.query(OAuth2AccessToken).filter(
                OAuth2AccessToken.expires_at <= now
            ).count()
            revoked_access_tokens = db.query(OAuth2AccessToken).filter(
                OAuth2AccessToken.revoked == True
            ).count()
            
            # Refresh token stats
            total_refresh_tokens = db.query(OAuth2RefreshToken).count()
            active_refresh_tokens = db.query(OAuth2RefreshToken).filter(
                OAuth2RefreshToken.expires_at > now,
                OAuth2RefreshToken.revoked == False
            ).count()
            
            # Authorization code stats
            total_auth_codes = db.query(OAuth2AuthorizationCode).count()
            active_auth_codes = db.query(OAuth2AuthorizationCode).filter(
                OAuth2AuthorizationCode.expires_at > now,
                OAuth2AuthorizationCode.revoked == False
            ).count()
            
            # Recent activity (last 24 hours)
            yesterday = now - timedelta(hours=24)
            recent_access_tokens = db.query(OAuth2AccessToken).filter(
                OAuth2AccessToken.created_at >= yesterday
            ).count()
            recent_refresh_tokens = db.query(OAuth2RefreshToken).filter(
                OAuth2RefreshToken.created_at >= yesterday
            ).count()
            
            self.line("OAuth2 Token Statistics:")
            self.line("=" * 50)
            
            self.line("Access Tokens:")
            self.line(f"  Total: {total_access_tokens}")
            self.line(f"  Active: {active_access_tokens}")
            self.line(f"  Expired: {expired_access_tokens}")
            self.line(f"  Revoked: {revoked_access_tokens}")
            self.line(f"  Created (24h): {recent_access_tokens}")
            
            self.new_line()
            self.line("Refresh Tokens:")
            self.line(f"  Total: {total_refresh_tokens}")
            self.line(f"  Active: {active_refresh_tokens}")
            self.line(f"  Created (24h): {recent_refresh_tokens}")
            
            self.new_line()
            self.line("Authorization Codes:")
            self.line(f"  Total: {total_auth_codes}")
            self.line(f"  Active: {active_auth_codes}")
            
            # Health indicators
            self.new_line()
            self.line("Health Indicators:")
            
            if expired_access_tokens > total_access_tokens * 0.5:
                self.warning(f"⚠️  High expired token ratio ({expired_access_tokens/total_access_tokens*100:.1f}%)")
                self.comment("Consider running 'passport tokens:prune' to clean up")
            else:
                self.success("✅ Token expiration ratio is healthy")
            
            if recent_access_tokens > 1000:
                self.warning(f"⚠️  High token creation rate ({recent_access_tokens} in 24h)")
            else:
                self.success("✅ Token creation rate is normal")
                
        except Exception as e:
            self.error(f"Failed to get token statistics: {str(e)}")
    
    # Setup and Installation Methods
    async def _setup_passport(self, db: Any) -> None:
        """Complete Passport setup wizard."""
        self.line("Laravel Passport Setup Wizard")
        self.line("=" * 50)
        
        # Step 1: Generate keys
        self.line("Step 1: Encryption Keys")
        await self._generate_keys()
        
        self.new_line()
        
        # Step 2: Install clients
        self.line("Step 2: Default Clients")
        await self._install_passport(db)
        
        self.new_line()
        
        # Step 3: Configuration check
        self.line("Step 3: Configuration")
        from config.oauth2 import oauth2_settings
        
        if oauth2_settings.oauth2_secret_key == "your-oauth2-secret-key-change-in-production":
            self.warning("⚠️  Default JWT secret detected")
            self.comment("Update your .env file with a secure JWT_SECRET")
        else:
            self.success("✅ JWT secret configured")
        
        if not oauth2_settings.oauth2_enforce_https:
            self.warning("⚠️  HTTPS not enforced (development mode)")
            self.comment("Enable HTTPS enforcement in production")
        else:
            self.success("✅ HTTPS enforcement enabled")
        
        self.new_line()
        self.success("🎉 Passport setup complete!")
        self.comment("Your OAuth2 server is ready to use.")
    
    async def _purge_passport(self, db: Any) -> None:
        """Purge all Passport data."""
        self.warning("⚠️  This will delete ALL OAuth2 data!")
        self.line("This includes:")
        self.line("  - All clients")
        self.line("  - All access tokens")
        self.line("  - All refresh tokens") 
        self.line("  - All authorization codes")
        self.line("  - Encryption keys")
        
        if not self.confirm("Are you absolutely sure?", False):
            self.comment("Purge cancelled.")
            return
        
        if not self.confirm("Type 'PURGE' to confirm:", False):
            self.comment("Purge cancelled.")
            return
        
        try:
            # Delete all OAuth2 data
            from app.Models.OAuth2AccessToken import OAuth2AccessToken
            from app.Models.OAuth2RefreshToken import OAuth2RefreshToken
            from app.Models.OAuth2AuthorizationCode import OAuth2AuthorizationCode
            
            db.query(OAuth2AccessToken).delete()
            db.query(OAuth2RefreshToken).delete()
            db.query(OAuth2AuthorizationCode).delete()
            db.query(OAuth2Client).delete()
            
            db.commit()
            
            # Delete encryption keys
            key_files = [
                "storage/oauth2/oauth-private.key",
                "storage/oauth2/oauth-public.key"
            ]
            
            for key_file in key_files:
                key_path = Path(key_file)
                if key_path.exists():
                    key_path.unlink()
            
            self.success("✅ All Passport data purged")
            self.comment("Run 'passport setup' to reinstall Passport")
            
        except Exception as e:
            db.rollback()
            self.error(f"Failed to purge Passport data: {str(e)}")
    
    # Status and Diagnostic Methods
    async def _show_status(self, db: Any) -> None:
        """Show Passport system status."""
        self.line("Laravel Passport Status:")
        self.line("=" * 50)
        
        # Check database tables
        try:
            client_count = db.query(OAuth2Client).count()
            self.success(f"✅ Database connected ({client_count} clients)")
        except Exception as e:
            self.error(f"❌ Database error: {str(e)}")
            return
        
        # Check encryption keys
        private_key_path = Path("storage/oauth2/oauth-private.key")
        public_key_path = Path("storage/oauth2/oauth-public.key")
        
        if private_key_path.exists() and public_key_path.exists():
            self.success("✅ Encryption keys present")
        else:
            self.error("❌ Encryption keys missing")
        
        # Check configuration
        from config.oauth2 import oauth2_settings
        
        if oauth2_settings.oauth2_secret_key != "your-oauth2-secret-key-change-in-production":
            self.success("✅ JWT secret configured")
        else:
            self.error("❌ Default JWT secret in use")
        
        # Check default clients
        personal_client = db.query(OAuth2Client).filter(
            OAuth2Client.is_personal_access_client == True
        ).first()
        
        password_client = db.query(OAuth2Client).filter(
            OAuth2Client.is_password_client == True
        ).first()
        
        if personal_client:
            self.success("✅ Personal access client exists")
        else:
            self.warning("⚠️  Personal access client missing")
        
        if password_client:
            self.success("✅ Password grant client exists")  
        else:
            self.warning("⚠️  Password grant client missing")
        
        # Overall status
        self.new_line()
        all_good = (
            client_count > 0 and
            private_key_path.exists() and
            public_key_path.exists() and
            oauth2_settings.oauth2_secret_key != "your-oauth2-secret-key-change-in-production" and
            personal_client and
            password_client
        )
        
        if all_good:
            self.success("🎉 Passport is fully configured and ready!")
        else:
            self.warning("⚠️  Passport setup incomplete")
            self.comment("Run 'passport setup' to complete configuration")
    
    async def _health_check(self, db: Any) -> None:
        """Perform comprehensive health check."""
        self.line("Passport Health Check:")
        self.line("=" * 50)
        
        health_score = 0
        total_checks = 8
        
        # Database connectivity
        try:
            db.query(OAuth2Client).count()
            self.success("✅ Database connectivity")
            health_score += 1
        except Exception as e:
            self.error(f"❌ Database error: {str(e)}")
        
        # Encryption keys
        private_key_path = Path("storage/oauth2/oauth-private.key")
        public_key_path = Path("storage/oauth2/oauth-public.key")
        
        if private_key_path.exists() and public_key_path.exists():
            self.success("✅ Encryption keys present")
            health_score += 1
        else:
            self.error("❌ Encryption keys missing")
        
        # JWT configuration
        from config.oauth2 import oauth2_settings
        
        if oauth2_settings.oauth2_secret_key != "your-oauth2-secret-key-change-in-production":
            self.success("✅ JWT secret configured")
            health_score += 1
        else:
            self.error("❌ Default JWT secret")
        
        # Token expiration settings
        if oauth2_settings.oauth2_access_token_expire_minutes <= 1440:  # <= 24 hours
            self.success("✅ Reasonable access token expiration")
            health_score += 1
        else:
            self.warning("⚠️  Long access token expiration")
        
        # Security settings
        if oauth2_settings.oauth2_require_pkce:
            self.success("✅ PKCE required")
            health_score += 1
        else:
            self.warning("⚠️  PKCE not required")
        
        # Client existence
        active_clients = db.query(OAuth2Client).filter(
            OAuth2Client.is_active == True,
            OAuth2Client.is_revoked == False
        ).count()
        
        if active_clients > 0:
            self.success(f"✅ Active clients ({active_clients})")
            health_score += 1
        else:
            self.warning("⚠️  No active clients")
        
        # Recent token activity
        from app.Models.OAuth2AccessToken import OAuth2AccessToken
        from datetime import datetime, timedelta
        
        recent_tokens = db.query(OAuth2AccessToken).filter(
            OAuth2AccessToken.created_at >= datetime.now() - timedelta(days=1)
        ).count()
        
        if recent_tokens >= 0:  # Any activity is good
            self.success(f"✅ Recent activity ({recent_tokens} tokens in 24h)")
            health_score += 1
        
        # Expired token ratio
        total_tokens = db.query(OAuth2AccessToken).count()
        expired_tokens = db.query(OAuth2AccessToken).filter(
            OAuth2AccessToken.expires_at <= datetime.now()
        ).count()
        
        if total_tokens == 0 or (expired_tokens / total_tokens) < 0.5:
            self.success("✅ Healthy token expiration ratio")
            health_score += 1
        else:
            self.warning("⚠️  High expired token ratio")
        
        # Health score
        self.new_line()
        health_percentage = (health_score / total_checks) * 100
        
        if health_percentage >= 90:
            self.success(f"🎉 Health Score: {health_percentage:.0f}% (Excellent)")
        elif health_percentage >= 70:
            self.warning(f"⚠️  Health Score: {health_percentage:.0f}% (Good)")  
        else:
            self.error(f"❌ Health Score: {health_percentage:.0f}% (Needs Attention)")
        
        if health_percentage < 100:
            self.new_line()
            self.comment("💡 Run 'passport setup' to improve health score")
    
    # Legacy Compatibility Methods
    async def _legacy_client_command(self, db: Any) -> None:
        """Handle legacy 'passport client' command format."""
        self.comment("Using legacy command format. Consider using 'passport create' instead.")
        await self._create_client(db)
    
    async def _show_help(self) -> None:
        """Show comprehensive command help."""
        self.line("Laravel Passport OAuth2 Management")
        self.line("=" * 50)
        self.line("")
        self.line("Usage:")
        self.line("  passport <action> [options]")
        self.line("")
        
        self.line("CLIENT MANAGEMENT:")
        self.line("  create         Create a new OAuth2 client")
        self.line("  list           List all OAuth2 clients")  
        self.line("  show           Show details of a specific client")
        self.line("  update         Update an existing client")
        self.line("  delete         Delete a client permanently")
        self.line("  revoke         Revoke a client (deactivate)")
        self.line("  restore        Restore a revoked client")
        self.line("  secret         Regenerate client secret")
        self.line("  tokens         Show tokens for a client")
        self.line("")
        
        self.line("KEY MANAGEMENT:")
        self.line("  keys           Show current encryption keys")
        self.line("  keys:generate  Generate new encryption keys")
        self.line("")
        
        self.line("SCOPE MANAGEMENT:")
        self.line("  scopes         List all OAuth2 scopes")
        self.line("  scopes:create  Create a new scope")
        self.line("  scopes:delete  Delete a scope")
        self.line("")
        
        self.line("TOKEN MANAGEMENT:")
        self.line("  tokens:prune   Remove expired tokens")
        self.line("  tokens:revoke  Revoke all tokens for a client")
        self.line("  tokens:stats   Show detailed token statistics")
        self.line("")
        
        self.line("SETUP & MAINTENANCE:")
        self.line("  install        Install default Passport clients")
        self.line("  setup          Complete setup wizard")
        self.line("  purge          Remove all Passport data")
        self.line("  status         Show system status")
        self.line("  stats          Show basic statistics")
        self.line("  health         Comprehensive health check")
        self.line("")
        
        self.line("Options:")
        self.line("  --name         Client name")
        self.line("  --redirect     Redirect URI")
        self.line("  --type         Client type (authorization_code, personal_access, password, client_credentials)")
        self.line("  --id           Client database ID")
        self.line("  --revoked      Include revoked clients in list")
        self.line("  --scope        Scope name for scope commands")
        self.line("  --force        Skip confirmations")
        self.line("  --public       Create public client (no secret)")
        self.line("  --personal     Create personal access client")
        self.line("  --password-client  Create password grant client")
        self.line("")
        
        self.line("Examples:")
        self.line("  passport create --name='My App' --redirect='https://myapp.com/callback'")
        self.line("  passport create --personal --name='Personal Tokens'")
        self.line("  passport list --revoked")
        self.line("  passport show --id=01H...")
        self.line("  passport secret --id=01H...")
        self.line("  passport keys:generate --force")
        self.line("  passport tokens:prune")
        self.line("  passport setup")
        self.line("  passport health")