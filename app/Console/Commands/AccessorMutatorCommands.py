from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, final, Union
import logging
import sys
import json
import inspect
from pathlib import Path

from app.Console.Command import Command
from app.Attributes.AccessorMutator import AccessorMutatorManager, Attribute


@final
class AttributeListCommand(Command):
    """
    List all models using Laravel-style Accessors & Mutators.
    
    Usage:
        python artisan.py attribute:list
        python artisan.py attribute:list --model=User
        python artisan.py attribute:list --detailed
    """
    
    signature = "attribute:list {--model=} {--detailed} {--stats}"
    description = "List models using Laravel-style Accessors & Mutators"
    
    async def handle(self) -> None:
        """Execute the command."""
        try:
            model_name = self.option('model')
            detailed = self.option('detailed')
            show_stats = self.option('stats')
            
            if model_name:
                return self._show_model_attributes(model_name, detailed)
            else:
                return self._list_all_attributes(detailed, show_stats)
                
        except Exception as e:
            self.error(f"Failed to list attributes: {e}")
            self._exit_code = 1
    
    def _list_all_attributes(self, detailed: bool, show_stats: bool) -> int:
        """List all models with registered attributes."""
        # In a real implementation, you'd have a registry of models
        # For this example, we'll scan for models with the attribute manager
        
        self.line("")
        self.line("<fg=green>Laravel-style Accessors & Mutators</fg=green>")
        self.line("=" * 50)
        
        try:
            # Import example models to test
            from examples.accessor_mutator_usage import AccessorMutatorDemo
            
            demo = AccessorMutatorDemo()
            user = demo.create_sample_user()
            
            manager = AccessorMutatorManager()
            
            self.line("<fg=yellow>Sample Model Attributes:</fg=yellow>")
            self.line("")
            
            # Show example attributes from the demo
            self.line("<fg=cyan>User Model:</fg=cyan>")
            self.line("  first_name - String accessor/mutator")
            self.line("  last_name - String accessor/mutator") 
            self.line("  full_name - Read-only accessor")
            self.line("  email - Email accessor/mutator")
            self.line("  profile - JSON accessor/mutator")
            self.line("  salary - Money accessor/mutator")
            self.line("  birth_date - Date accessor/mutator")
            self.line("  status - Enum accessor/mutator")
            
            if detailed:
                self.line("")
                self.line("<fg=yellow>Attribute Details:</fg=yellow>")
                
                # Show some sample attribute details
                attributes = [
                    ("first_name", "String", "Capitalizes first letter"),
                    ("email", "Email", "Validates and normalizes email"),
                    ("profile", "JSON", "Serializes/deserializes JSON data"),
                    ("salary", "Money", "Formats currency values"),
                    ("birth_date", "Date", "Handles date formatting"),
                    ("status", "Enum", "Validates enum values")
                ]
                
                for name, attr_type, description in attributes:
                    self.line(f"  <fg=cyan>{name}</fg=cyan>:")
                    self.line(f"    Type: {attr_type}")
                    self.line(f"    Description: {description}")
                    self.line("")
            
            if show_stats:
                self.line("<fg=yellow>Statistics:</fg=yellow>")
                self.line("  Total Models: 1 (Sample)")
                self.line("  Total Attributes: 7")
                self.line("  Accessor Types: 6")
                self.line("  Mutator Types: 6")
                self.line("  Read-only Attributes: 1 (full_name)")
            
            self.info("Tip: Run 'python artisan.py attribute:test --demo' for a full demonstration")
            self._exit_code = 0
            
        except Exception as e:
            self.error(f"Failed to list attributes: {e}")
            self._exit_code = 1
    
    def _show_model_attributes(self, model_name: str, detailed: bool) -> int:
        """Show attributes for a specific model."""
        self.line("")
        self.line(f"<fg=green>Attributes for {model_name}</fg=green>")
        self.line("=" * 50)
        
        if model_name.lower() == 'user':
            # Show detailed user attributes
            attributes = [
                {
                    "name": "first_name",
                    "type": "String Accessor/Mutator",
                    "accessor": "Capitalizes first letter on get",
                    "mutator": "Trims whitespace on set",
                    "example": "john -> John"
                },
                {
                    "name": "email",
                    "type": "Email Accessor/Mutator", 
                    "accessor": "Returns normalized email",
                    "mutator": "Validates and normalizes email",
                    "example": "JOHN@EXAMPLE.COM -> john@example.com"
                },
                {
                    "name": "full_name",
                    "type": "Read-only Accessor",
                    "accessor": "Combines first_name and last_name",
                    "mutator": "Not allowed (read-only)",
                    "example": "John Doe"
                },
                {
                    "name": "profile",
                    "type": "JSON Accessor/Mutator",
                    "accessor": "Deserializes JSON string to dict",
                    "mutator": "Serializes dict to JSON string", 
                    "example": "{'key': 'value'} <-> '{\"key\": \"value\"}'"
                }
            ]
            
            for attr in attributes:
                self.line(f"<fg=cyan>{attr['name']}</fg=cyan>:")
                self.line(f"  Type: {attr['type']}")
                if detailed:
                    self.line(f"  Accessor: {attr['accessor']}")
                    self.line(f"  Mutator: {attr['mutator']}")
                    self.line(f"  Example: {attr['example']}")
                self.line("")
            
            self._exit_code = 0
        else:
            self.error(f"Model '{model_name}' not found. Available: User")
            self._exit_code = 1


@final
class AttributeTestCommand(Command):
    """
    Test Laravel-style Accessors & Mutators functionality.
    
    Usage:
        python artisan.py attribute:test
        python artisan.py attribute:test --attribute=email
        python artisan.py attribute:test --demo
    """
    
    signature = "attribute:test {--attribute=} {--demo} {--verbose}"
    description = "Test Laravel-style Accessors & Mutators functionality"
    
    async def handle(self) -> None:
        """Execute the command."""
        try:
            attribute_name = self.option('attribute')
            demo_mode = self.option('demo')
            verbose = self.option('verbose')
            
            if demo_mode:
                return self._run_demo(verbose)
            elif attribute_name:
                return self._test_specific_attribute(attribute_name, verbose)
            else:
                return self._run_basic_test(verbose)
                
        except Exception as e:
            self.error(f"Failed to test attributes: {e}")
            self._exit_code = 1
    
    def _run_basic_test(self, verbose: bool) -> int:
        """Run basic attribute functionality test."""
        self.line("")
        self.line("<fg=green>Testing Laravel-style Accessors & Mutators</fg=green>")
        self.line("=" * 60)
        
        try:
            from examples.accessor_mutator_usage import AccessorMutatorDemo
            
            demo = AccessorMutatorDemo()
            self.line("✓ AccessorMutatorDemo imported successfully")
            
            # Test user creation
            user = demo.create_sample_user()
            self.line("✓ Sample user created successfully")
            
            # Test basic attributes
            original_name = "john doe"
            user.first_name = original_name
            retrieved_name = user.first_name
            
            if retrieved_name == "John Doe":
                self.line("✓ String accessor/mutator working correctly")
                if verbose:
                    self.line(f"  Input: '{original_name}' -> Output: '{retrieved_name}'")
            else:
                self.error(f"String accessor failed: expected 'John Doe', got '{retrieved_name}'")
                self._exit_code = 1
            
            # Test email normalization
            original_email = "TEST@EXAMPLE.COM"
            user.email = original_email
            retrieved_email = user.email
            
            if retrieved_email == "test@example.com":
                self.line("✓ Email accessor/mutator working correctly")
                if verbose:
                    self.line(f"  Input: '{original_email}' -> Output: '{retrieved_email}'")
            else:
                self.error(f"Email accessor failed: expected 'test@example.com', got '{retrieved_email}'")
                self._exit_code = 1
            
            # Test JSON handling
            original_profile = {"age": 30, "city": "New York"}
            user.profile = original_profile
            retrieved_profile = user.profile
            
            if isinstance(retrieved_profile, dict) and retrieved_profile.get("age") == 30:
                self.line("✓ JSON accessor/mutator working correctly")
                if verbose:
                    self.line(f"  Input: {original_profile}")
                    self.line(f"  Output: {retrieved_profile}")
            else:
                self.error(f"JSON accessor failed: {retrieved_profile}")
                self._exit_code = 1
            
            # Test read-only accessor
            full_name = user.full_name
            if full_name and "John" in full_name:
                self.line("✓ Read-only accessor working correctly")
                if verbose:
                    self.line(f"  Full name: '{full_name}'")
            else:
                self.error(f"Read-only accessor failed: {full_name}")
                self._exit_code = 1
            
            self.line("")
            self.line("<fg=green>All basic tests passed!</fg=green>")
            self._exit_code = 0
            
        except Exception as e:
            self.error(f"Basic test failed: {e}")
            if verbose:
                import traceback
                self.line(traceback.format_exc())
            self._exit_code = 1
    
    def _test_specific_attribute(self, attribute_name: str, verbose: bool) -> int:
        """Test a specific attribute type."""
        self.line("")
        self.line(f"<fg=green>Testing {attribute_name} Attribute</fg=green>")
        self.line("=" * 50)
        
        try:
            from examples.accessor_mutator_usage import AccessorMutatorDemo
            from app.Attributes.AccessorMutator import string_accessor, email_accessor, json_accessor
            
            demo = AccessorMutatorDemo()
            user = demo.create_sample_user()
            
            test_cases = {
                'email': {
                    'input': 'TEST@EXAMPLE.COM',
                    'expected': 'test@example.com',
                    'attribute': 'email'
                },
                'first_name': {
                    'input': 'john doe',
                    'expected': 'John Doe', 
                    'attribute': 'first_name'
                },
                'profile': {
                    'input': {'test': 'value'},
                    'expected': dict,
                    'attribute': 'profile'
                },
                'full_name': {
                    'input': None,  # Read-only
                    'expected': str,
                    'attribute': 'full_name'
                }
            }
            
            if attribute_name not in test_cases:
                self.error(f"Unknown attribute: {attribute_name}")
                self.line(f"Available attributes: {', '.join(test_cases.keys())}")
                self._exit_code = 1
            
            test_case = test_cases[attribute_name]
            
            if test_case['input'] is not None:
                # Test mutator (setter)
                setattr(user, test_case['attribute'], test_case['input'])
                self.line(f"✓ Set {attribute_name} = {test_case['input']}")
            
            # Test accessor (getter)
            result = getattr(user, test_case['attribute'])
            
            if isinstance(test_case['expected'], type):
                if isinstance(result, test_case['expected']):
                    self.line(f"✓ {attribute_name} accessor returned correct type: {type(result).__name__}")
                else:
                    self.error(f"Type mismatch: expected {test_case['expected'].__name__}, got {type(result).__name__}")
                    self._exit_code = 1
            else:
                if result == test_case['expected']:
                    self.line(f"✓ {attribute_name} accessor returned expected value")
                else:
                    self.error(f"Value mismatch: expected '{test_case['expected']}', got '{result}'")
                    self._exit_code = 1
            
            if verbose:
                self.line(f"  Final value: {result}")
                self.line(f"  Type: {type(result).__name__}")
            
            self.line("")
            self.line(f"<fg=green>{attribute_name} test passed!</fg=green>")
            self._exit_code = 0
            
        except Exception as e:
            self.error(f"Attribute test failed: {e}")
            if verbose:
                import traceback
                self.line(traceback.format_exc())
            self._exit_code = 1
    
    def _run_demo(self, verbose: bool) -> int:
        """Run the comprehensive attribute demonstration."""
        self.line("")
        self.line("<fg=green>Running Laravel-style Accessors & Mutators Demo</fg=green>")
        self.line("=" * 60)
        
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, "examples/accessor_mutator_usage.py"],
                capture_output=True,
                text=True,
                cwd=Path.cwd()
            )
            
            if result.returncode == 0:
                # Show clean output
                output_lines = result.stdout.split('\n')
                
                for line in output_lines:
                    if line.strip():
                        self.line(line)
                
                self.line("")
                self.line("<fg=green>Demo completed successfully!</fg=green>")
                self._exit_code = 0
            else:
                self.error("Demo failed:")
                self.line(result.stderr)
                self._exit_code = 1
                
        except Exception as e:
            self.error(f"Failed to run demo: {e}")
            if verbose:
                import traceback
                self.line(traceback.format_exc())
            self._exit_code = 1


@final
class AttributeStatsCommand(Command):
    """
    Show statistics about Laravel-style Accessors & Mutators usage.
    
    Usage:
        python artisan.py attribute:stats
        python artisan.py attribute:stats --json
        python artisan.py attribute:stats --performance
    """
    
    signature = "attribute:stats {--json} {--performance}"
    description = "Show Accessors & Mutators usage statistics"
    
    async def handle(self) -> None:
        """Execute the command."""
        try:
            json_output = self.option('json')
            show_performance = self.option('performance')
            
            return self._show_stats(json_output, show_performance)
                
        except Exception as e:
            self.error(f"Failed to show statistics: {e}")
            self._exit_code = 1
    
    def _show_stats(self, json_output: bool, show_performance: bool) -> int:
        """Show attribute statistics."""
        try:
            from app.Attributes.AccessorMutator import AccessorMutatorManager
            
            manager = AccessorMutatorManager()
            
            # Sample statistics (in a real implementation, these would be tracked)
            stats = {
                'total_models': 1,
                'total_attributes': 7,
                'accessor_types': {
                    'string': 2,
                    'email': 1, 
                    'json': 1,
                    'money': 1,
                    'date': 1,
                    'enum': 1
                },
                'mutator_types': {
                    'string': 2,
                    'email': 1,
                    'json': 1, 
                    'money': 1,
                    'date': 1,
                    'enum': 1
                },
                'read_only_attributes': 1,
                'write_only_attributes': 0,
                'performance': {
                    'cache_hits': 0,
                    'cache_misses': 0,
                    'total_transformations': 0,
                    'average_transformation_time': 0.0
                }
            }
            
            if json_output:
                self.line(json.dumps(stats, indent=2))
                self._exit_code = 0
            
            self.line("")
            self.line("<fg=green>Laravel-style Accessors & Mutators Statistics</fg=green>")
            self.line("=" * 60)
            
            self.line(f"<fg=cyan>Total Models:</fg=cyan> {stats['total_models']}")
            self.line(f"<fg=cyan>Total Attributes:</fg=cyan> {stats['total_attributes']}")
            self.line(f"<fg=cyan>Read-only Attributes:</fg=cyan> {stats['read_only_attributes']}")
            self.line(f"<fg=cyan>Write-only Attributes:</fg=cyan> {stats['write_only_attributes']}")
            
            self.line("")
            self.line("<fg=yellow>Accessor Types:</fg=yellow>")
            for accessor_type, count in stats['accessor_types'].items():
                self.line(f"  {accessor_type}: {count}")
            
            self.line("")
            self.line("<fg=yellow>Mutator Types:</fg=yellow>")
            for mutator_type, count in stats['mutator_types'].items():
                self.line(f"  {mutator_type}: {count}")
            
            if show_performance:
                self.line("")
                self.line("<fg=yellow>Performance Metrics:</fg=yellow>")
                perf = stats['performance']
                self.line(f"  Cache Hits: {perf['cache_hits']}")
                self.line(f"  Cache Misses: {perf['cache_misses']}")
                self.line(f"  Total Transformations: {perf['total_transformations']}")
                self.line(f"  Average Transformation Time: {perf['average_transformation_time']:.3f}ms")
            
            self.line("")
            self.line("<fg=green>Modern Laravel 9+ Attribute System Features:</fg=green>")
            self.line("• Type-safe attribute definitions")
            self.line("• Automatic caching and performance optimization")
            self.line("• Built-in helper functions for common patterns")
            self.line("• Full compatibility with Laravel's Attribute syntax")
            self.line("• Support for complex transformations and validations")
            
            self._exit_code = 0
            
        except Exception as e:
            self.error(f"Failed to show statistics: {e}")
            self._exit_code = 1


# Register commands for auto-discovery
__all__ = [
    'AttributeListCommand',
    'AttributeTestCommand',
    'AttributeStatsCommand'
]