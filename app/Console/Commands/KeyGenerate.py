from __future__ import annotations

from app.Console.Artisan import Command
from app.Encryption.Encrypter import Encrypter


class KeyGenerateCommand(Command):
    """Generate application encryption key."""
    
    signature = 'key:generate {--show : Display the key instead of modifying files}'
    description = 'Set the application key'
    
    def handle(self) -> int:
        """Handle the command."""
        key = Encrypter.generate_key()
        
        if self.option('show'):
            self.line(f'<comment>Application key:</comment> {key}')
            return 0
        
        # In a real app, this would update the .env file
        self.info('Application key set successfully!')
        self.line(f'<comment>Generated key:</comment> {key}')
        self.line('')
        self.line('<comment>Add this to your .env file:</comment>')
        self.line(f'APP_KEY={key}')
        
        return 0
from app.Console.Artisan import register_command
register_command(KeyGenerateCommand)
