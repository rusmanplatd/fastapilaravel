from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, final, Union
import logging
import sys
import json
from pathlib import Path

from app.Console.Command import Command
from app.Scopes import (
    ScopeRegistry, GlobalScopeManager, 
    ActiveScope, PublishedScope, VerifiedScope, TenantScope,
    ArchiveScope, DateRangeScope, OwnerScope, VisibilityScope, StatusScope
)


@final
class ScopeListCommand(Command):
    """
    List all registered global scopes and their statistics.
    
    Usage:
        python artisan.py scope:list
        python artisan.py scope:list --model=User
        python artisan.py scope:list --detailed
    """
    
    signature = "scope:list {--model=} {--detailed} {--stats}"
    description = "List global scopes and their statistics"
    
    async def handle(self) -> None:
        """Execute the command."""
        try:
            model_name = self.option('model')
            detailed = self.option('detailed')
            show_stats = self.option('stats')
            
            if model_name:
                return self._show_model_scopes(model_name, detailed)
            else:
                return self._list_all_scopes(detailed, show_stats)
                
        except Exception as e:
            self.error(f"Failed to list global scopes: {e}")
            self._exit_code = 1
    
    def _list_all_scopes(self, detailed: bool, show_stats: bool) -> int:
        """List all registered global scopes."""
        managers = ScopeRegistry.get_all_managers()
        
        if not managers:
            self.info("No global scopes registered.")
            self._exit_code = 0
        
        self.line("")
        self.line("<fg=green>Global Scopes Registry</fg=green>")
        self.line("=" * 50)
        
        if show_stats:
            stats = ScopeRegistry.get_global_stats()
            self.line(f"<fg=cyan>Total Models:</fg=cyan> {stats['total_models']}")
            self.line(f"<fg=cyan>Total Scopes:</fg=cyan> {stats['total_scopes']}")
            self.line(f"<fg=cyan>Total Applications:</fg=cyan> {stats['total_applications']}")
            self.line("")
        
        for model_class, manager in managers.items():
            model_name = model_class.__name__ if hasattr(model_class, '__name__') else 'Unknown'
            scopes = manager.get_scopes()
            enabled_count = len(manager.get_enabled_scopes())
            
            self.line(f"<fg=yellow>{model_name}</fg=yellow>:")
            self.line(f"  Total scopes: {len(scopes)}")
            self.line(f"  Enabled: {enabled_count}")
            self.line(f"  Applications: {manager.application_count}")
            
            if detailed:
                for name, scope in scopes.items():
                    status = "✓" if manager.is_scope_enabled(name) else "✗"
                    priority = getattr(scope, 'priority', 0)
                    scope_type = scope.__class__.__name__
                    self.line(f"    {status} {name} ({scope_type}, priority: {priority})")
            else:
                scope_names = list(scopes.keys())
                if scope_names:
                    self.line(f"  Scopes: {', '.join(scope_names)}")
                else:
                    self.line("  No scopes registered")
            
            self.line("")
        
        return 0
    
    def _show_model_scopes(self, model_name: str, detailed: bool) -> int:
        """Show scopes for a specific model."""
        # For this example, we'll try to find the model by name
        # In a real implementation, you'd have a model registry
        managers = ScopeRegistry.get_all_managers()
        
        target_manager = None
        target_model = None
        
        for model_class, manager in managers.items():
            if hasattr(model_class, '__name__') and model_class.__name__ == model_name:
                target_manager = manager
                target_model = model_class
                break
        
        if not target_manager:
            self.error(f"No global scopes found for model: {model_name}")
            self._exit_code = 1
        
        scopes = target_manager.get_scopes()
        debug_info = target_manager.debug_info()
        
        self.line("")
        self.line(f"<fg=green>Global Scopes for {model_name}</fg=green>")
        self.line("=" * 50)
        
        self.line(f"<fg=cyan>Total Scopes:</fg=cyan> {debug_info['total_scopes']}")
        self.line(f"<fg=cyan>Enabled Count:</fg=cyan> {debug_info['enabled_count']}")
        self.line(f"<fg=cyan>Application Count:</fg=cyan> {debug_info['application_count']}")
        self.line("")
        
        if not scopes:
            self.info("No scopes registered for this model.")
            self._exit_code = 0
        
        self.line("<fg=yellow>Registered Scopes:</fg=yellow>")
        for name, details in debug_info['scopes'].items():
            status_icon = "✓" if details['enabled'] else "✗"
            self.line(f"  {status_icon} <fg=cyan>{name}</fg=cyan>")
            self.line(f"    Type: {details['type']}")
            self.line(f"    Priority: {details['priority']}")
            self.line(f"    Enabled: {'Yes' if details['enabled'] else 'No'}")
            
            if detailed and 'can_apply' in details:
                self.line(f"    Can Apply: {'Yes' if details['can_apply'] else 'No'}")
                if 'conditions' in details and details['conditions']:
                    self.line(f"    Conditions: {json.dumps(details['conditions'], indent=6)}")
            
            self.line("")
        
        if detailed:
            perf_stats = target_manager.get_performance_stats()
            self.line("<fg=yellow>Performance Statistics:</fg=yellow>")
            for key, value in perf_stats.items():
                if key != 'scope_names':
                    self.line(f"  {key.replace('_', ' ').title()}: {value}")
        
        return 0


@final
class ScopeStatsCommand(Command):
    """
    Show detailed global scope statistics and performance metrics.
    
    Usage:
        python artisan.py scope:stats
        python artisan.py scope:stats --model=User
        python artisan.py scope:stats --performance
    """
    
    signature = "scope:stats {--model=} {--performance} {--json}"
    description = "Show global scope statistics and performance metrics"
    
    async def handle(self) -> None:
        """Execute the command."""
        try:
            model_name = self.option('model')
            show_performance = self.option('performance')
            json_output = self.option('json')
            
            if model_name:
                return self._show_model_stats(model_name, show_performance, json_output)
            else:
                return self._show_global_stats(show_performance, json_output)
                
        except Exception as e:
            self.error(f"Failed to show scope statistics: {e}")
            self._exit_code = 1
    
    def _show_global_stats(self, show_performance: bool, json_output: bool) -> int:
        """Show global statistics for all scopes."""
        global_stats = ScopeRegistry.get_global_stats()
        managers = ScopeRegistry.get_all_managers()
        
        if json_output:
            output_data = {
                'global_stats': global_stats,
                'models': {}
            }
            
            for model_class, manager in managers.items():
                model_name = model_class.__name__ if hasattr(model_class, '__name__') else 'Unknown'
                output_data['models'][model_name] = manager.get_performance_stats()
            
            self.line(json.dumps(output_data, indent=2))
            self._exit_code = 0
        
        self.line("")
        self.line("<fg=green>Global Scope Statistics</fg=green>")
        self.line("=" * 50)
        
        for key, value in global_stats.items():
            display_key = key.replace('_', ' ').title()
            if isinstance(value, list):
                self.line(f"<fg=cyan>{display_key}:</fg=cyan> {', '.join(map(str, value))}")
            else:
                self.line(f"<fg=cyan>{display_key}:</fg=cyan> {value}")
        
        if show_performance and managers:
            self.line("")
            self.line("<fg=yellow>Model Performance Details:</fg=yellow>")
            self.line("-" * 30)
            
            for model_class, manager in managers.items():
                model_name = model_class.__name__ if hasattr(model_class, '__name__') else 'Unknown'
                perf_stats = manager.get_performance_stats()
                
                self.line(f"<fg=cyan>{model_name}:</fg=cyan>")
                for key, value in perf_stats.items():
                    if key != 'scope_names':
                        display_key = key.replace('_', ' ').title()
                        if isinstance(value, float):
                            self.line(f"  {display_key}: {value:.3f}")
                        else:
                            self.line(f"  {display_key}: {value}")
                self.line("")
        
        return 0
    
    def _show_model_stats(self, model_name: str, show_performance: bool, json_output: bool) -> int:
        """Show statistics for a specific model."""
        managers = ScopeRegistry.get_all_managers()
        
        target_manager = None
        for model_class, manager in managers.items():
            if hasattr(model_class, '__name__') and model_class.__name__ == model_name:
                target_manager = manager
                break
        
        if not target_manager:
            self.error(f"No global scopes found for model: {model_name}")
            self._exit_code = 1
        
        debug_info = target_manager.debug_info()
        perf_stats = target_manager.get_performance_stats()
        
        if json_output:
            output_data = {
                'model': model_name,
                'debug_info': debug_info,
                'performance': perf_stats
            }
            self.line(json.dumps(output_data, indent=2))
            self._exit_code = 0
        
        self.line("")
        self.line(f"<fg=green>Scope Statistics for {model_name}</fg=green>")
        self.line("=" * 50)
        
        self.line(f"<fg=cyan>Model:</fg=cyan> {debug_info['model']}")
        self.line(f"<fg=cyan>Total Scopes:</fg=cyan> {debug_info['total_scopes']}")
        self.line(f"<fg=cyan>Enabled Count:</fg=cyan> {debug_info['enabled_count']}")
        self.line(f"<fg=cyan>Application Count:</fg=cyan> {debug_info['application_count']}")
        
        if show_performance:
            self.line("")
            self.line("<fg=yellow>Performance Metrics:</fg=yellow>")
            for key, value in perf_stats.items():
                if key != 'scope_names':
                    display_key = key.replace('_', ' ').title()
                    if isinstance(value, float):
                        self.line(f"  <fg=cyan>{display_key}:</fg=cyan> {value:.3f}")
                    else:
                        self.line(f"  <fg=cyan>{display_key}:</fg=cyan> {value}")
        
        return 0


@final
class ScopeClearCommand(Command):
    """
    Clear global scopes from models or the entire registry.
    
    Usage:
        python artisan.py scope:clear
        python artisan.py scope:clear --model=User
        python artisan.py scope:clear --model=User --scope=active
        python artisan.py scope:clear --force
    """
    
    signature = "scope:clear {--model=} {--scope=} {--force}"
    description = "Clear global scopes from models or registry"
    
    async def handle(self) -> None:
        """Execute the command."""
        try:
            model_name = self.option('model')
            scope_name = self.option('scope')
            force = self.option('force')
            
            if scope_name and not model_name:
                self.error("Cannot specify --scope without --model")
                self._exit_code = 1
            
            if model_name and scope_name:
                return self._clear_specific_scope(model_name, scope_name, force)
            elif model_name:
                return self._clear_model_scopes(model_name, force)
            else:
                return self._clear_all_scopes(force)
                
        except Exception as e:
            self.error(f"Failed to clear scopes: {e}")
            self._exit_code = 1
    
    def _clear_specific_scope(self, model_name: str, scope_name: str, force: bool) -> int:
        """Clear a specific scope from a model."""
        managers = ScopeRegistry.get_all_managers()
        
        target_manager = None
        for model_class, manager in managers.items():
            if hasattr(model_class, '__name__') and model_class.__name__ == model_name:
                target_manager = manager
                break
        
        if not target_manager:
            self.error(f"No global scopes found for model: {model_name}")
            self._exit_code = 1
        
        if not target_manager.has_scope(scope_name):
            self.error(f"Scope '{scope_name}' not found in model {model_name}")
            self._exit_code = 1
        
        if not force:
            confirm = self.ask(f"Remove scope '{scope_name}' from {model_name}? [y/N]")
            if confirm.lower() not in ['y', 'yes']:
                self.info("Operation cancelled.")
                self._exit_code = 0
        
        target_manager.remove_scope(scope_name)
        self.info(f"Removed scope '{scope_name}' from {model_name}")
        return 0
    
    def _clear_model_scopes(self, model_name: str, force: bool) -> int:
        """Clear all scopes from a specific model."""
        managers = ScopeRegistry.get_all_managers()
        
        target_manager = None
        for model_class, manager in managers.items():
            if hasattr(model_class, '__name__') and model_class.__name__ == model_name:
                target_manager = manager
                break
        
        if not target_manager:
            self.error(f"No global scopes found for model: {model_name}")
            self._exit_code = 1
        
        scope_count = target_manager.get_scope_count()
        if scope_count == 0:
            self.info(f"No scopes to clear for {model_name}")
            self._exit_code = 0
        
        if not force:
            confirm = self.ask(f"Clear all {scope_count} scopes from {model_name}? [y/N]")
            if confirm.lower() not in ['y', 'yes']:
                self.info("Operation cancelled.")
                self._exit_code = 0
        
        target_manager.clear_scopes()
        self.info(f"Cleared all scopes from {model_name}")
        return 0
    
    def _clear_all_scopes(self, force: bool) -> int:
        """Clear all scopes from the entire registry."""
        global_stats = ScopeRegistry.get_global_stats()
        
        if global_stats['total_scopes'] == 0:
            self.info("No scopes to clear")
            self._exit_code = 0
        
        if not force:
            confirm = self.ask(
                f"Clear ALL {global_stats['total_scopes']} scopes from "
                f"{global_stats['total_models']} models? [y/N]"
            )
            if confirm.lower() not in ['y', 'yes']:
                self.info("Operation cancelled.")
                self._exit_code = 0
        
        ScopeRegistry.clear_all_scopes()
        self.info("Cleared all global scopes from registry")
        return 0


@final
class ScopeTestCommand(Command):
    """
    Test global scope functionality with sample data.
    
    Usage:
        python artisan.py scope:test
        python artisan.py scope:test --scope=active
        python artisan.py scope:test --demo
    """
    
    signature = "scope:test {--scope=} {--demo}"
    description = "Test global scope functionality"
    
    async def handle(self) -> None:
        """Execute the command."""
        try:
            scope_name = self.option('scope')
            demo_mode = self.option('demo')
            
            if demo_mode:
                return self._run_demo()
            elif scope_name:
                return self._test_specific_scope(scope_name)
            else:
                return self._run_basic_test()
                
        except Exception as e:
            self.error(f"Failed to test scopes: {e}")
            self._exit_code = 1
    
    def _run_basic_test(self) -> int:
        """Run basic scope functionality test."""
        self.line("")
        self.line("<fg=green>Testing Global Scopes Functionality</fg=green>")
        self.line("=" * 50)
        
        try:
            # Test scope creation
            active_scope = ActiveScope()
            self.line("✓ ActiveScope created successfully")
            
            verified_scope = VerifiedScope()
            self.line("✓ VerifiedScope created successfully")
            
            # Test scope registry (basic functionality)
            from examples.global_scopes_usage import User
            
            User.add_global_scope('active', active_scope)
            User.add_global_scope('verified', verified_scope)
            self.line("✓ Scopes added to test model")
            
            manager = User.get_scope_manager()
            scopes = manager.get_enabled_scopes()
            self.line(f"✓ Enabled scopes: {', '.join(scopes)}")
            
            # Test scope management
            manager.disable_scope('verified')
            enabled_after_disable = manager.get_enabled_scopes()
            self.line(f"✓ After disabling 'verified': {', '.join(enabled_after_disable)}")
            
            manager.enable_scope('verified')
            enabled_after_enable = manager.get_enabled_scopes()
            self.line(f"✓ After re-enabling 'verified': {', '.join(enabled_after_enable)}")
            
            # Clean up
            manager.clear_scopes()
            self.line("✓ Scopes cleared successfully")
            
            self.line("")
            self.line("<fg=green>All tests passed!</fg=green>")
            self._exit_code = 0
            
        except Exception as e:
            self.error(f"Test failed: {e}")
            self._exit_code = 1
    
    def _test_specific_scope(self, scope_name: str) -> int:
        """Test a specific scope type."""
        self.line("")
        self.line(f"<fg=green>Testing {scope_name} Scope</fg=green>")
        self.line("=" * 50)
        
        try:
            scope_classes = {
                'active': ActiveScope,
                'published': PublishedScope,
                'verified': VerifiedScope,
                'archive': ArchiveScope,
                'visibility': VisibilityScope,
                'status': StatusScope
            }
            
            if scope_name not in scope_classes:
                self.error(f"Unknown scope type: {scope_name}")
                self.line(f"Available types: {', '.join(scope_classes.keys())}")
                self._exit_code = 1
            
            scope_class = scope_classes[scope_name]
            
            if scope_name == 'status':
                scope = scope_class(['active', 'published'])
            elif scope_name == 'visibility':
                scope = scope_class(['public'])
            else:
                scope = scope_class()
            
            self.line(f"✓ {scope_class.__name__} created successfully")
            self.line(f"  Name: {scope.get_name()}")
            self.line(f"  Priority: {scope.priority}")
            self.line(f"  Enabled: {scope.enabled}")
            
            self.line("")
            self.line("<fg=green>Scope test passed!</fg=green>")
            self._exit_code = 0
            
        except Exception as e:
            self.error(f"Scope test failed: {e}")
            self._exit_code = 1
    
    def _run_demo(self) -> int:
        """Run the comprehensive scope demonstration."""
        self.line("")
        self.line("<fg=green>Running Global Scopes Demo</fg=green>")
        self.line("=" * 50)
        
        try:
            # Import and run the example
            import subprocess
            result = subprocess.run(
                [sys.executable, "examples/global_scopes_usage.py"],
                capture_output=True,
                text=True,
                cwd=Path.cwd()
            )
            
            if result.returncode == 0:
                # Filter out deprecation warnings and show clean output
                output_lines = result.stdout.split('\n')
                clean_lines = [
                    line for line in output_lines 
                    if not any(warning in line for warning in [
                        'MovedIn20Warning', 'DeprecationWarning', 
                        'sqlalchemy.ext.declarative', 'datetime.utcnow'
                    ])
                ]
                
                for line in clean_lines:
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
            self._exit_code = 1


# Register commands for auto-discovery
__all__ = [
    'ScopeListCommand',
    'ScopeStatsCommand', 
    'ScopeClearCommand',
    'ScopeTestCommand'
]