# Laravel-style Artisan Commands

This document describes the newly implemented Artisan commands that replace the Laravel-specific Makefile commands.

## Migration from Makefile to Artisan

Previously, Laravel-specific commands were implemented in the Makefile with complex shell scripts. These have been migrated to proper Laravel-style Artisan commands following the framework's standard patterns.

### Removed Makefile Commands

The following commands were removed from the Makefile and replaced with Artisan commands:

- `soft-delete-*` commands → `soft-delete:*` Artisan commands (already existed)
- `accessor-mutator-*` commands → `attribute:*` Artisan commands
- `scope-*` commands → `scope:*` Artisan commands

## Global Scopes Commands

Laravel-style Global Scopes provide automatic query filtering across all model queries.

### `scope:list`

List all registered global scopes and their statistics.

```bash
# List all scopes across all models
python artisan.py scope:list

# List scopes for a specific model
python artisan.py scope:list --model=User

# Show detailed information
python artisan.py scope:list --detailed

# Include statistics
python artisan.py scope:list --stats
```

**Options:**
- `--model=ModelName` - Show scopes only for the specified model
- `--detailed` - Show detailed scope information (type, priority, conditions)
- `--stats` - Include performance and usage statistics

### `scope:stats`

Show detailed global scope statistics and performance metrics.

```bash
# Show global statistics
python artisan.py scope:stats

# Show statistics for a specific model
python artisan.py scope:stats --model=User

# Include performance metrics
python artisan.py scope:stats --performance

# Output as JSON
python artisan.py scope:stats --json
```

**Options:**
- `--model=ModelName` - Show statistics only for the specified model
- `--performance` - Include detailed performance metrics
- `--json` - Output in JSON format for integration

### `scope:clear`

Clear global scopes from models or the entire registry.

```bash
# Clear all scopes from all models (with confirmation)
python artisan.py scope:clear

# Clear all scopes from a specific model
python artisan.py scope:clear --model=User

# Clear a specific scope from a model
python artisan.py scope:clear --model=User --scope=active

# Force clear without confirmation
python artisan.py scope:clear --force
```

**Options:**
- `--model=ModelName` - Target specific model
- `--scope=ScopeName` - Target specific scope (requires --model)
- `--force` - Skip confirmation prompts

**⚠️ Warning:** This operation is destructive and cannot be undone.

### `scope:test`

Test global scope functionality with sample data.

```bash
# Run basic functionality test
python artisan.py scope:test

# Test a specific scope type
python artisan.py scope:test --scope=active

# Run comprehensive demo
python artisan.py scope:test --demo
```

**Options:**
- `--scope=ScopeName` - Test specific scope type (active, published, verified, etc.)
- `--demo` - Run the comprehensive scope demonstration

**Available Scope Types:**
- `active` - ActiveScope for filtering active records
- `published` - PublishedScope for published content
- `verified` - VerifiedScope for verified records
- `archive` - ArchiveScope for excluding archived records
- `visibility` - VisibilityScope for content visibility
- `status` - StatusScope for generic status filtering

## Accessor/Mutator Commands

Laravel-style Accessors & Mutators provide automatic attribute transformation using modern Laravel 9+ syntax.

### `attribute:list`

List all models using Laravel-style Accessors & Mutators.

```bash
# List all models with attributes
python artisan.py attribute:list

# List attributes for a specific model
python artisan.py attribute:list --model=User

# Show detailed attribute information
python artisan.py attribute:list --detailed

# Include usage statistics
python artisan.py attribute:list --stats
```

**Options:**
- `--model=ModelName` - Show attributes only for the specified model
- `--detailed` - Show detailed attribute information (types, descriptions, examples)
- `--stats` - Include usage and performance statistics

### `attribute:test`

Test Laravel-style Accessors & Mutators functionality.

```bash
# Run basic functionality test
python artisan.py attribute:test

# Test a specific attribute type
python artisan.py attribute:test --attribute=email

# Run comprehensive demo
python artisan.py attribute:test --demo

# Enable verbose output
python artisan.py attribute:test --verbose
```

**Options:**
- `--attribute=AttributeName` - Test specific attribute (email, first_name, profile, etc.)
- `--demo` - Run the comprehensive attribute demonstration
- `--verbose` - Show detailed test output and debugging information

**Available Attribute Types:**
- `email` - Email normalization and validation
- `first_name` - String capitalization and trimming
- `profile` - JSON serialization/deserialization
- `full_name` - Read-only computed attribute

### `attribute:stats`

Show statistics about Laravel-style Accessors & Mutators usage.

```bash
# Show usage statistics
python artisan.py attribute:stats

# Output as JSON
python artisan.py attribute:stats --json

# Include performance metrics
python artisan.py attribute:stats --performance
```

**Options:**
- `--json` - Output in JSON format for integration
- `--performance` - Include detailed performance metrics (cache hits, transformation times)

## Soft Delete Commands (Existing)

These commands were already implemented and follow the proper Artisan pattern:

### `soft-delete:list`

List models with soft deletes and show statistics.

```bash
# List all soft delete models with statistics
python artisan.py soft-delete:list --stats

# Include deleted records in listing
python artisan.py soft-delete:list --show-deleted --stats
```

### `soft-delete:restore`

Restore soft deleted records.

```bash
# Restore specific record by ID
python artisan.py soft-delete:restore User --id=123

# Restore all deleted records
python artisan.py soft-delete:restore User --all

# Restore records older than specified time
python artisan.py soft-delete:restore User --older-than="7 days"

# Dry run to see what would be restored
python artisan.py soft-delete:restore User --all --dry-run
```

### `soft-delete:purge`

Permanently delete soft deleted records.

```bash
# Purge all deleted records (with confirmation)
python artisan.py soft-delete:purge User --all

# Purge records older than specified time
python artisan.py soft-delete:purge User --older-than="30 days"

# Force purge without confirmation
python artisan.py soft-delete:purge User --all --force

# Dry run to see what would be purged
python artisan.py soft-delete:purge User --all --dry-run
```

## Command Development Guidelines

### Creating New Commands

Follow these guidelines when creating new Artisan commands:

1. **Extend the Command Class**
   ```python
   from app.Console.Command import Command
   
   class MyCommand(Command):
       signature = "my:command {argument} {--option=}"
       description = "Description of what the command does"
   ```

2. **Implement Async Handle Method**
   ```python
   async def handle(self) -> None:
       try:
           # Command logic here
           self.info("Command completed successfully")
           self._exit_code = 0
       except Exception as e:
           self.error(f"Command failed: {e}")
           self._exit_code = 1
   ```

3. **Use Proper Output Methods**
   - `self.line(message)` - Regular output
   - `self.info(message)` - Success/info message (green)
   - `self.comment(message)` - Comment message (yellow)
   - `self.error(message)` - Error message (red)
   - `self.ask(question)` - Interactive input

4. **Handle Options and Arguments**
   ```python
   model_name = self.option('model')
   force = self.option('force')
   argument_value = self.argument('argument')
   ```

5. **Set Exit Codes**
   - `self._exit_code = 0` - Success
   - `self._exit_code = 1` - Error

### Command Registration

Commands are automatically discovered if they:
1. Are located in `app/Console/Commands/`
2. Extend the `Command` class
3. Are included in the module's `__all__` list

### Testing Commands

Use the test script to verify commands work correctly:

```bash
python3 test_artisan_commands.py
```

## Benefits of Artisan Commands over Makefile

1. **Consistency**: All commands follow Laravel's standard patterns
2. **Type Safety**: Full type checking with proper error handling
3. **Async Support**: Native async/await support for database operations
4. **Auto-discovery**: Commands are automatically registered
5. **Rich Output**: Colored output with proper formatting
6. **Error Handling**: Comprehensive error handling and recovery
7. **Testability**: Easy to unit test and mock
8. **Documentation**: Built-in help and signature documentation

## Migration Checklist

When migrating from Makefile to Artisan commands:

- [x] Remove Laravel-specific commands from Makefile
- [x] Implement Global Scopes commands (`scope:*`)
- [x] Implement Accessor/Mutator commands (`attribute:*`)
- [x] Verify existing Soft Delete commands work correctly
- [x] Test all new commands
- [x] Update documentation

## Usage Examples

```bash
# Global Scopes
python artisan.py scope:list --detailed --stats
python artisan.py scope:test --demo
python artisan.py scope:stats --performance --json
python artisan.py scope:clear --model=User --scope=active

# Accessors & Mutators  
python artisan.py attribute:list --model=User --detailed
python artisan.py attribute:test --demo --verbose
python artisan.py attribute:stats --performance

# Soft Deletes
python artisan.py soft-delete:list --show-deleted --stats
python artisan.py soft-delete:restore User --older-than="7 days"
python artisan.py soft-delete:purge User --older-than="30 days" --force
```

This migration provides a more maintainable, testable, and Laravel-standard approach to command-line operations while preserving all existing functionality.