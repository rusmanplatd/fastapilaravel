from __future__ import annotations

import argparse
from typing import Optional, List

from database.Schema.MigrationRunner import MigrationRunner


class MigrateCommand:
    """Laravel-style migrate command."""
    
    @staticmethod
    def handle(args: Optional[List[str]] = None) -> None:
        """Handle the migrate command."""
        parser = argparse.ArgumentParser(
            description="Run database migrations",
            prog="python -m app.Console.Commands.MigrateCommand"
        )
        
        parser.add_argument(
            '--step', 
            type=int, 
            default=None,
            help='Number of migrations to run'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force the operation to run in production'
        )
        
        parsed_args = parser.parse_args(args)
        
        runner = MigrationRunner()
        runner.migrate(parsed_args.step)


class MigrateRollbackCommand:
    """Laravel-style migrate:rollback command."""
    
    @staticmethod
    def handle(args: Optional[List[str]] = None) -> None:
        """Handle the migrate:rollback command."""
        parser = argparse.ArgumentParser(
            description="Rollback database migrations",
            prog="python -m app.Console.Commands.MigrateCommand rollback"
        )
        
        parser.add_argument(
            '--step', 
            type=int, 
            default=1,
            help='Number of migration batches to rollback'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force the operation to run in production'
        )
        
        parsed_args = parser.parse_args(args)
        
        runner = MigrationRunner()
        runner.rollback(parsed_args.step)


class MigrateResetCommand:
    """Laravel-style migrate:reset command."""
    
    @staticmethod
    def handle(args: Optional[List[str]] = None) -> None:
        """Handle the migrate:reset command."""
        parser = argparse.ArgumentParser(
            description="Reset all database migrations",
            prog="python -m app.Console.Commands.MigrateCommand reset"
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force the operation to run in production'
        )
        
        parsed_args = parser.parse_args(args)
        
        runner = MigrationRunner()
        runner.reset()


class MigrateRefreshCommand:
    """Laravel-style migrate:refresh command."""
    
    @staticmethod
    def handle(args: Optional[List[str]] = None) -> None:
        """Handle the migrate:refresh command."""
        parser = argparse.ArgumentParser(
            description="Reset and re-run all migrations",
            prog="python -m app.Console.Commands.MigrateCommand refresh"
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force the operation to run in production'
        )
        
        parsed_args = parser.parse_args(args)
        
        runner = MigrationRunner()
        runner.refresh()


class MigrateStatusCommand:
    """Laravel-style migrate:status command."""
    
    @staticmethod
    def handle(args: Optional[List[str]] = None) -> None:
        """Handle the migrate:status command."""
        parser = argparse.ArgumentParser(
            description="Show migration status",
            prog="python -m app.Console.Commands.MigrateCommand status"
        )
        
        parsed_args = parser.parse_args(args)
        
        runner = MigrationRunner()
        runner.status()


class MakeMigrationCommand:
    """Laravel-style make:migration command."""
    
    @staticmethod
    def handle(args: Optional[List[str]] = None) -> None:
        """Handle the make:migration command."""
        parser = argparse.ArgumentParser(
            description="Create a new migration file",
            prog="python -m app.Console.Commands.MigrateCommand make"
        )
        
        parser.add_argument(
            'name',
            help='Name of the migration'
        )
        
        parser.add_argument(
            '--create',
            type=str,
            default=None,
            help='Create a new table with the given name'
        )
        
        parser.add_argument(
            '--table',
            type=str,
            default=None,
            help='Modify an existing table'
        )
        
        parsed_args = parser.parse_args(args)
        
        runner = MigrationRunner()
        runner.make_migration(parsed_args.name, parsed_args.create)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        args = sys.argv[2:]
        
        commands = {
            'migrate': MigrateCommand.handle,
            'rollback': MigrateRollbackCommand.handle,
            'reset': MigrateResetCommand.handle,
            'refresh': MigrateRefreshCommand.handle,
            'status': MigrateStatusCommand.handle,
            'make': MakeMigrationCommand.handle,
        }
        
        if command in commands:
            commands[command](args)
        else:
            print(f"Unknown command: {command}")
            print(f"Available commands: {', '.join(commands.keys())}")
    else:
        MigrateCommand.handle()