from __future__ import annotations

import os
import secrets
import string
from pathlib import Path
from typing import Optional

from app.Console.Command import Command


class KeyGenerateCommand(Command):
    """Laravel-style key:generate command to generate application encryption key."""
    
    signature = "key:generate {--show : Display the key instead of modifying files} {--force : Force the operation to run when in production}"
    
    description = "Set the application key"
    
    def __init__(self) -> None:
        super().__init__()
    
    async def handle(self) -> None:
        """Handle the key generation command."""
        key = self._generate_random_key()
        
        if self.option('show'):
            self.line(f"base64:{key}")
            return
        
        # Check if we're in production
        if self._is_production() and not self.option('force'):
            self.error("Application is in production! Use --force to override.")
            return
        
        # Check if key already exists
        if self._key_exists() and not self.confirm("This will invalidate all existing tokens. Are you sure?"):
            self.info("Command cancelled.")
            return
        
        # Set the key in environment
        if self._set_key_in_environment(key):
            self.info("Application key set successfully.")
        else:
            self.error("Failed to set application key.")
    
    def _generate_random_key(self) -> str:
        """Generate a random 32-character key."""
        # Generate 32 random bytes and encode as base64
        random_bytes = secrets.token_bytes(32)
        import base64
        return base64.b64encode(random_bytes).decode('utf-8')
    
    def _is_production(self) -> bool:
        """Check if application is in production environment."""
        return os.getenv('APP_ENV', 'production').lower() == 'production'
    
    def _key_exists(self) -> bool:
        """Check if an application key already exists."""
        return bool(os.getenv('APP_KEY'))
    
    def _set_key_in_environment(self, key: str) -> bool:
        """Set the key in the .env file."""
        env_file = Path('.env')
        
        # Read existing .env file
        if env_file.exists():
            with open(env_file, 'r') as f:
                lines = f.readlines()
        else:
            lines = []
        
        # Look for existing APP_KEY line
        key_line_found = False
        new_lines = []
        
        for line in lines:
            if line.strip().startswith('APP_KEY='):
                new_lines.append(f'APP_KEY=base64:{key}\\n')
                key_line_found = True
            else:
                new_lines.append(line)
        
        # If no APP_KEY line found, add it
        if not key_line_found:
            new_lines.append(f'APP_KEY=base64:{key}\\n')
        
        # Write back to .env file
        try:
            with open(env_file, 'w') as f:
                f.writelines(new_lines)
            
            # Update current environment
            os.environ['APP_KEY'] = f'base64:{key}'
            
            return True
        except Exception as e:
            self.error(f"Failed to write to .env file: {e}")
            return False
    
    def _validate_key_format(self, key: str) -> bool:
        """Validate the key format."""
        try:
            if key.startswith('base64:'):
                import base64
                decoded = base64.b64decode(key[7:])
                return len(decoded) == 32
            return len(key) == 32
        except Exception:
            return False
from app.Console.Artisan import register_command
register_command(KeyGenerateCommand)
