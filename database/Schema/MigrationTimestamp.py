from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional


class MigrationTimestamp:
    """Handles migration file timestamp management."""
    
    @staticmethod
    def generate_timestamp() -> str:
        """Generate timestamp in Laravel format: YYYY_MM_DD_HHMMSS."""
        return datetime.now().strftime("%Y_%m_%d_%H%M%S")
    
    @staticmethod
    def parse_timestamp(timestamp: str) -> Optional[datetime]:
        """Parse timestamp string back to datetime object."""
        try:
            return datetime.strptime(timestamp, "%Y_%m_%d_%H%M%S")
        except ValueError:
            return None
    
    @staticmethod
    def extract_timestamp_from_filename(filename: str) -> Optional[str]:
        """Extract timestamp from migration filename."""
        # Match Laravel-style timestamp at beginning: YYYY_MM_DD_HHMMSS_
        match = re.match(r'^(\d{4}_\d{2}_\d{2}_\d{6})_', filename)
        return match.group(1) if match else None
    
    @staticmethod
    def extract_name_from_filename(filename: str) -> str:
        """Extract migration name without timestamp and extension."""
        # Remove .py extension
        name = filename.replace('.py', '')
        
        # Remove timestamp prefix if present
        match = re.match(r'^\d{4}_\d{2}_\d{2}_\d{6}_(.+)$', name)
        return match.group(1) if match else name
    
    @staticmethod
    def has_timestamp(filename: str) -> bool:
        """Check if filename already has timestamp."""
        return MigrationTimestamp.extract_timestamp_from_filename(filename) is not None
    
    @staticmethod
    def add_timestamp_to_existing_files(migrations_path: str = "database/migrations") -> Dict[str, str]:
        """Add timestamps to existing migration files that don't have them."""
        path = Path(migrations_path)
        if not path.exists():
            return {}
        
        renamed_files = {}
        migration_files = []
        
        # Get all migration files (exclude utility classes)
        for file in path.glob("*.py"):
            if file.name in [
                'Migration.py', 'MigrationManager.py', 'MigrationRunner.py',
                'MigrationSquasher.py', 'MigrationTemplates.py', 'MigrationValidator.py',
                'MigrationDependency.py', 'MigrationMonitor.py', 'MigrationTimestamp.py'
            ]:
                continue
            migration_files.append(file)
        
        # Sort files to maintain order (older files get earlier timestamps)
        migration_files.sort(key=lambda f: f.stat().st_mtime)
        
        # Add timestamps with 1-minute intervals to maintain order
        base_time = datetime.now().replace(second=0, microsecond=0)
        
        for i, file in enumerate(migration_files):
            if not MigrationTimestamp.has_timestamp(file.name):
                # Generate timestamp with minute intervals to maintain order
                timestamp_time = base_time.replace(minute=i % 60, hour=base_time.hour - (i // 60))
                timestamp = timestamp_time.strftime("%Y_%m_%d_%H%M%S")
                
                old_name = file.name
                new_name = f"{timestamp}_{old_name}"
                new_path = file.parent / new_name
                
                # Rename the file
                file.rename(new_path)
                renamed_files[old_name] = new_name
                
                print(f"Renamed: {old_name} → {new_name}")
        
        return renamed_files
    
    @staticmethod
    def generate_timestamped_filename(migration_name: str) -> str:
        """Generate timestamped filename for new migration."""
        timestamp = MigrationTimestamp.generate_timestamp()
        
        # Clean up the migration name
        clean_name = migration_name.lower().replace(' ', '_').replace('-', '_')
        clean_name = re.sub(r'[^a-z0-9_]', '', clean_name)
        
        # Ensure it doesn't already have timestamp
        if not MigrationTimestamp.has_timestamp(clean_name):
            return f"{timestamp}_{clean_name}.py"
        else:
            return f"{clean_name}.py"
    
    @staticmethod
    def get_migration_order(migrations_path: str = "database/migrations") -> List[Tuple[str, Optional[datetime]]]:
        """Get migrations in chronological order based on timestamps."""
        path = Path(migrations_path)
        if not path.exists():
            return []
        
        migrations = []
        for file in path.glob("*.py"):
            if file.name in [
                'Migration.py', 'MigrationManager.py', 'MigrationRunner.py',
                'MigrationSquasher.py', 'MigrationTemplates.py', 'MigrationValidator.py',
                'MigrationDependency.py', 'MigrationMonitor.py', 'MigrationTimestamp.py'
            ]:
                continue
            
            timestamp_str = MigrationTimestamp.extract_timestamp_from_filename(file.name)
            timestamp_obj = MigrationTimestamp.parse_timestamp(timestamp_str) if timestamp_str else None
            
            # If no timestamp, use file modification time
            if not timestamp_obj:
                timestamp_obj = datetime.fromtimestamp(file.stat().st_mtime)
            
            migrations.append((file.name, timestamp_obj))
        
        # Sort by timestamp
        migrations.sort(key=lambda x: x[1] if x[1] is not None else datetime.min)
        return migrations
    
    @staticmethod
    def validate_timestamp_format(timestamp: str) -> bool:
        """Validate timestamp format."""
        pattern = r'^\d{4}_\d{2}_\d{2}_\d{6}$'
        if not re.match(pattern, timestamp):
            return False
        
        # Validate actual date/time values
        try:
            datetime.strptime(timestamp, "%Y_%m_%d_%H%M%S")
            return True
        except ValueError:
            return False
    
    @staticmethod
    def get_next_available_timestamp(migrations_path: str = "database/migrations") -> str:
        """Get next available timestamp ensuring no conflicts."""
        base_timestamp = MigrationTimestamp.generate_timestamp()
        path = Path(migrations_path)
        
        if not path.exists():
            return base_timestamp
        
        # Check for conflicts
        existing_timestamps = set()
        for file in path.glob("*.py"):
            timestamp = MigrationTimestamp.extract_timestamp_from_filename(file.name)
            if timestamp:
                existing_timestamps.add(timestamp)
        
        # If no conflict, return base timestamp
        if base_timestamp not in existing_timestamps:
            return base_timestamp
        
        # Generate incremental timestamp
        base_dt = MigrationTimestamp.parse_timestamp(base_timestamp)
        if base_dt is None:
            return base_timestamp
        increment = 1
        
        while True:
            new_dt = base_dt.replace(second=min(59, base_dt.second + increment))
            if new_dt.second == 59 and increment > 1:
                new_dt = new_dt.replace(second=0, minute=base_dt.minute + 1)
            
            new_timestamp = new_dt.strftime("%Y_%m_%d_%H%M%S")
            
            if new_timestamp not in existing_timestamps:
                return new_timestamp
            
            increment += 1
            if increment > 60:  # Safety check
                # Use microseconds as fallback
                return datetime.now().strftime("%Y_%m_%d_%H%M%S")


class MigrationFileManager:
    """Manages migration file operations with timestamp support."""
    
    def __init__(self, migrations_path: str = "database/migrations") -> None:
        self.migrations_path = Path(migrations_path)
        self.migrations_path.mkdir(parents=True, exist_ok=True)
    
    def create_migration_file(self, name: str, content: str) -> str:
        """Create new migration file with timestamp."""
        filename = MigrationTimestamp.generate_timestamped_filename(name)
        filepath = self.migrations_path / filename
        
        # Ensure unique filename
        counter = 1
        while filepath.exists():
            base_name = filename.replace('.py', '')
            filename = f"{base_name}_{counter}.py"
            filepath = self.migrations_path / filename
            counter += 1
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        return str(filepath)
    
    def rename_migration_files_with_timestamps(self) -> Dict[str, str]:
        """Rename existing migration files to include timestamps."""
        return MigrationTimestamp.add_timestamp_to_existing_files(str(self.migrations_path))
    
    def get_migration_list(self) -> List[str]:
        """Get list of migrations in chronological order."""
        migrations = MigrationTimestamp.get_migration_order(str(self.migrations_path))
        return [name for name, _ in migrations]
    
    def backup_migrations(self) -> str:
        """Create backup of migrations before renaming."""
        import shutil
        backup_path = self.migrations_path.parent / "migrations_backup"
        
        if backup_path.exists():
            shutil.rmtree(backup_path)
        
        shutil.copytree(self.migrations_path, backup_path)
        return str(backup_path)