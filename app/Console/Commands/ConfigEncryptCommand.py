from __future__ import annotations

import os
import base64
import json
from typing import Any, Dict, List, Optional
from pathlib import Path
from ..Command import Command


class ConfigEncryptCommand(Command):
    """Encrypt and decrypt sensitive configuration values."""
    
    signature = "config:encrypt {action : encrypt or decrypt} {--key= : Specific configuration key} {--value= : Value to encrypt} {--all : Process all sensitive keys} {--output= : Output file for encrypted config} {--force : Overwrite existing encrypted values}"
    description = "Encrypt or decrypt sensitive configuration values"
    help = "Securely encrypt sensitive configuration values for safe storage"
    
    def __init__(self) -> None:
        super().__init__()
        self.encryption_key: Optional[bytes] = None
        self.sensitive_keys = [
            'APP_KEY', 'DATABASE_URL', 'REDIS_PASSWORD',
            'MAIL_PASSWORD', 'OAUTH2_ENCRYPTION_KEY',
            'JWT_SECRET', 'API_SECRET', 'WEBHOOK_SECRET'
        ]
    
    async def handle(self) -> None:
        """Execute encryption/decryption operation."""
        action = self.argument("action")
        specific_key = self.option("key")
        value = self.option("value")
        process_all = self.option("all", False)
        output_file = self.option("output")
        force = self.option("force", False)
        
        if action not in ['encrypt', 'decrypt']:
            self.error("Action must be 'encrypt' or 'decrypt'")
            return
        
        # Initialize encryption
        if not await self._initialize_encryption():
            return
        
        if action == 'encrypt':
            await self._handle_encryption(specific_key, value, process_all, output_file, force)
        else:
            await self._handle_decryption(specific_key, process_all, output_file)
    
    async def _initialize_encryption(self) -> bool:
        """Initialize encryption key."""
        # Try to get encryption key from environment
        app_key = os.getenv('APP_KEY', '')
        
        if not app_key:
            self.error("APP_KEY not found. Run 'key:generate' first.")
            return False
        
        try:
            # Decode base64 key if it has the prefix
            if app_key.startswith('base64:'):
                key_data = base64.b64decode(app_key[7:])
            else:
                key_data = app_key.encode('utf-8')
            
            # Ensure key is 32 bytes (256 bits) for AES
            if len(key_data) < 32:
                key_data = key_data.ljust(32, b'0')
            else:
                key_data = key_data[:32]
            
            self.encryption_key = key_data
            return True
            
        except Exception as e:
            self.error(f"Failed to initialize encryption: {e}")
            return False
    
    async def _handle_encryption(
        self, 
        specific_key: Optional[str], 
        value: Optional[str],
        process_all: bool,
        output_file: Optional[str],
        force: bool
    ) -> None:
        """Handle encryption operations."""
        if specific_key and value:
            # Encrypt a specific key-value pair
            await self._encrypt_key_value(specific_key, value, output_file)
        
        elif process_all:
            # Encrypt all sensitive keys in environment
            await self._encrypt_all_sensitive(output_file, force)
        
        elif specific_key:
            # Encrypt a specific key from environment
            await self._encrypt_environment_key(specific_key, output_file)
        
        else:
            self.error("Must specify --key with --value, --key alone, or --all")
            self.comment("Examples:")
            self.comment("  config:encrypt encrypt --key=DATABASE_URL --value='postgresql://...'")
            self.comment("  config:encrypt encrypt --key=DATABASE_URL")
            self.comment("  config:encrypt encrypt --all")
    
    async def _encrypt_key_value(
        self, 
        key: str, 
        value: str, 
        output_file: Optional[str]
    ) -> None:
        """Encrypt a specific key-value pair."""
        try:
            encrypted_value = await self._encrypt_value(value)
            
            result = {
                'key': key,
                'encrypted_value': encrypted_value,
                'original_length': len(value),
                'timestamp': self._get_timestamp()
            }
            
            if output_file:
                await self._save_encrypted_config(output_file, {key: result})
                self.info(f"✅ Encrypted {key} saved to {output_file}")
            else:
                self.info(f"🔒 Encrypted value for {key}:")
                self.line(f"ENC[{encrypted_value}]")
                self.new_line()
                self.comment("Add this to your .env file:")
                self.line(f"{key}=ENC[{encrypted_value}]")
                
        except Exception as e:
            self.error(f"Failed to encrypt {key}: {e}")
    
    async def _encrypt_environment_key(
        self, 
        key: str, 
        output_file: Optional[str]
    ) -> None:
        """Encrypt a key from environment variables."""
        # Check .env file first, then environment
        env_file = Path(".env")
        env_vars = {}
        
        if env_file.exists():
            env_vars = self._parse_env_file(env_file)
        
        # Get value from env file or environment
        value = env_vars.get(key) or os.getenv(key)
        
        if not value:
            self.error(f"Key {key} not found in environment or .env file")
            return
        
        # Check if already encrypted
        if value.startswith('ENC[') and value.endswith(']'):
            self.warn(f"Key {key} appears to already be encrypted")
            if not self.confirm("Encrypt anyway?"):
                return
        
        await self._encrypt_key_value(key, value, output_file)
    
    async def _encrypt_all_sensitive(
        self, 
        output_file: Optional[str], 
        force: bool
    ) -> None:
        """Encrypt all sensitive environment variables."""
        self.info("🔍 Scanning for sensitive configuration keys...")
        
        # Load environment variables
        env_file = Path(".env")
        env_vars = {}
        
        if env_file.exists():
            env_vars = self._parse_env_file(env_file)
        
        # Add environment variables
        for key in self.sensitive_keys:
            if key in os.environ and key not in env_vars:
                env_vars[key] = os.environ[key]
        
        # Filter to only sensitive keys that exist
        keys_to_encrypt = []
        for key in self.sensitive_keys:
            if key in env_vars:
                value = env_vars[key]
                
                # Skip if already encrypted
                if value.startswith('ENC[') and value.endswith(']'):
                    if not force:
                        self.comment(f"Skipping {key} (already encrypted)")
                        continue
                
                keys_to_encrypt.append(key)
        
        if not keys_to_encrypt:
            self.info("No sensitive keys found to encrypt")
            return
        
        self.info(f"Found {len(keys_to_encrypt)} keys to encrypt:")
        for key in keys_to_encrypt:
            self.line(f"  • {key}")
        
        if not force and not self.confirm("Proceed with encryption?"):
            return
        
        # Encrypt all keys
        encrypted_configs = {}
        progress_bar = self.progress_bar(len(keys_to_encrypt), "Encrypting keys")
        
        for key in keys_to_encrypt:
            try:
                value = env_vars[key]
                encrypted_value = await self._encrypt_value(value)
                
                encrypted_configs[key] = {
                    'key': key,
                    'encrypted_value': encrypted_value,
                    'original_length': len(value),
                    'timestamp': self._get_timestamp()
                }
                
            except Exception as e:
                self.warn(f"Failed to encrypt {key}: {e}")
            
            progress_bar.advance()
        
        progress_bar.finish()
        
        # Save results
        if output_file:
            await self._save_encrypted_config(output_file, encrypted_configs)
            self.info(f"✅ Encrypted {len(encrypted_configs)} keys saved to {output_file}")
        else:
            await self._update_env_file_with_encrypted(encrypted_configs)
    
    async def _handle_decryption(
        self,
        specific_key: Optional[str],
        process_all: bool,
        output_file: Optional[str]
    ) -> None:
        """Handle decryption operations."""
        if specific_key:
            await self._decrypt_environment_key(specific_key, output_file)
        elif process_all:
            await self._decrypt_all_encrypted(output_file)
        else:
            self.error("Must specify --key or --all for decryption")
    
    async def _decrypt_environment_key(
        self, 
        key: str, 
        output_file: Optional[str]
    ) -> None:
        """Decrypt a specific key from environment."""
        # Load environment variables
        env_file = Path(".env")
        env_vars = {}
        
        if env_file.exists():
            env_vars = self._parse_env_file(env_file)
        
        # Get encrypted value
        encrypted_value = env_vars.get(key) or os.getenv(key)
        
        if not encrypted_value:
            self.error(f"Key {key} not found in environment")
            return
        
        if not (encrypted_value.startswith('ENC[') and encrypted_value.endswith(']')):
            self.warn(f"Key {key} does not appear to be encrypted")
            return
        
        # Extract encrypted data
        encrypted_data = encrypted_value[4:-1]  # Remove ENC[ and ]
        
        try:
            decrypted_value = await self._decrypt_value(encrypted_data)
            
            if output_file:
                result = {key: decrypted_value}
                await self._save_decrypted_config(output_file, result)
                self.info(f"✅ Decrypted {key} saved to {output_file}")
            else:
                self.info(f"🔓 Decrypted value for {key}:")
                # Mask the value for security
                masked_value = self._mask_sensitive_value(decrypted_value)
                self.line(f"{key}={masked_value}")
                
                if self.confirm("Show full decrypted value?", False):
                    self.warn("⚠️  Displaying sensitive value:")
                    self.line(f"{key}={decrypted_value}")
                    
        except Exception as e:
            self.error(f"Failed to decrypt {key}: {e}")
    
    async def _decrypt_all_encrypted(self, output_file: Optional[str]) -> None:
        """Decrypt all encrypted values in environment."""
        self.info("🔍 Scanning for encrypted values...")
        
        # Load environment variables
        env_file = Path(".env")
        env_vars = {}
        
        if env_file.exists():
            env_vars = self._parse_env_file(env_file)
        
        # Find encrypted keys
        encrypted_keys = []
        for key, value in env_vars.items():
            if isinstance(value, str) and value.startswith('ENC[') and value.endswith(']'):
                encrypted_keys.append(key)
        
        if not encrypted_keys:
            self.info("No encrypted keys found")
            return
        
        self.info(f"Found {len(encrypted_keys)} encrypted keys:")
        for key in encrypted_keys:
            self.line(f"  • {key}")
        
        if not self.confirm("Decrypt all keys?"):
            return
        
        # Decrypt all keys
        decrypted_configs = {}
        progress_bar = self.progress_bar(len(encrypted_keys), "Decrypting keys")
        
        for key in encrypted_keys:
            try:
                encrypted_value = env_vars[key]
                encrypted_data = encrypted_value[4:-1]  # Remove ENC[ and ]
                decrypted_value = await self._decrypt_value(encrypted_data)
                decrypted_configs[key] = decrypted_value
                
            except Exception as e:
                self.warn(f"Failed to decrypt {key}: {e}")
            
            progress_bar.advance()
        
        progress_bar.finish()
        
        # Save or display results
        if output_file:
            await self._save_decrypted_config(output_file, decrypted_configs)
            self.info(f"✅ Decrypted {len(decrypted_configs)} keys saved to {output_file}")
        else:
            self.info("🔓 Decrypted values:")
            for key, value in decrypted_configs.items():
                masked_value = self._mask_sensitive_value(value)
                self.line(f"  {key}={masked_value}")
    
    async def _encrypt_value(self, value: str) -> str:
        """Encrypt a value using AES encryption."""
        try:
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            
            if self.encryption_key is None:
                raise ValueError("Encryption key not set")
            
            # Derive key from APP_KEY
            salt = b'fastapilaravel_salt'  # In production, use random salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key))
            fernet = Fernet(key)
            
            # Encrypt the value
            encrypted = fernet.encrypt(value.encode('utf-8'))
            return base64.b64encode(encrypted).decode('utf-8')
            
        except ImportError:
            self.error("cryptography package required. Install with: pip install cryptography")
            raise
        except Exception as e:
            raise Exception(f"Encryption failed: {e}")
    
    async def _decrypt_value(self, encrypted_data: str) -> str:
        """Decrypt a value using AES decryption."""
        try:
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            
            if self.encryption_key is None:
                raise ValueError("Encryption key not set")
            
            # Derive key from APP_KEY
            salt = b'fastapilaravel_salt'  # Should match encryption salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key))
            fernet = Fernet(key)
            
            # Decrypt the value
            encrypted_bytes = base64.b64decode(encrypted_data)
            decrypted = fernet.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
            
        except ImportError:
            self.error("cryptography package required. Install with: pip install cryptography")
            raise
        except Exception as e:
            raise Exception(f"Decryption failed: {e}")
    
    def _parse_env_file(self, env_file: Path) -> Dict[str, str]:
        """Parse .env file."""
        env_vars = {}
        
        try:
            content = env_file.read_text()
            for line in content.split('\n'):
                line = line.strip()
                
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    env_vars[key] = value
        
        except Exception as e:
            self.warn(f"Failed to parse .env file: {e}")
        
        return env_vars
    
    async def _save_encrypted_config(self, output_file: str, configs: Dict[str, Dict[str, Any]]) -> None:
        """Save encrypted configuration to file."""
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'timestamp': self._get_timestamp(),
                'encryption_info': {
                    'algorithm': 'AES-256',
                    'format': 'Fernet',
                    'total_keys': len(configs)
                },
                'encrypted_configs': configs
            }
            
            output_path.write_text(json.dumps(data, indent=2))
            
        except Exception as e:
            raise Exception(f"Failed to save encrypted config: {e}")
    
    async def _save_decrypted_config(self, output_file: str, configs: Dict[str, str]) -> None:
        """Save decrypted configuration to file."""
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create .env format content
            content = f"# Decrypted configuration - {self._get_timestamp()}\n"
            content += "# WARNING: This file contains sensitive data!\n\n"
            
            for key, value in configs.items():
                content += f"{key}={value}\n"
            
            output_path.write_text(content)
            
            # Set restrictive permissions
            import stat
            output_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600
            
        except Exception as e:
            raise Exception(f"Failed to save decrypted config: {e}")
    
    async def _update_env_file_with_encrypted(self, encrypted_configs: Dict[str, Dict[str, Any]]) -> None:
        """Update .env file with encrypted values."""
        env_file = Path(".env")
        
        if not env_file.exists():
            self.warn(".env file not found. Creating new file.")
            env_content = ""
        else:
            env_content = env_file.read_text()
        
        # Update or add encrypted values
        lines = env_content.split('\n')
        updated_lines = []
        updated_keys = set()
        
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                key = line.split('=', 1)[0].strip()
                
                if key in encrypted_configs:
                    # Replace with encrypted value
                    encrypted_value = encrypted_configs[key]['encrypted_value']
                    updated_lines.append(f"{key}=ENC[{encrypted_value}]")
                    updated_keys.add(key)
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
        
        # Add any new encrypted keys
        for key, config in encrypted_configs.items():
            if key not in updated_keys:
                encrypted_value = config['encrypted_value']
                updated_lines.append(f"{key}=ENC[{encrypted_value}]")
        
        # Write updated content
        try:
            # Backup original
            if env_file.exists():
                backup_file = env_file.with_suffix('.env.backup')
                env_file.rename(backup_file)
                self.comment(f"Original .env backed up to {backup_file}")
            
            # Write new content
            env_file.write_text('\n'.join(updated_lines))
            
            # Set restrictive permissions
            import stat
            env_file.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600
            
            self.info(f"✅ Updated .env file with {len(encrypted_configs)} encrypted values")
            
        except Exception as e:
            self.error(f"Failed to update .env file: {e}")
    
    def _mask_sensitive_value(self, value: str) -> str:
        """Mask sensitive value for display."""
        if len(value) <= 8:
            return '*' * len(value)
        else:
            return value[:2] + '*' * (len(value) - 4) + value[-2:]
    
    def _get_timestamp(self) -> str:
        """Get formatted timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


# Register command
from app.Console.Artisan import register_command
register_command(ConfigEncryptCommand)