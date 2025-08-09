from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable, Type, Tuple, TYPE_CHECKING
import asyncio
import sys
import argparse
import importlib
import pkgutil
from pathlib import Path
from datetime import datetime, timedelta

from .Command import Command

if TYPE_CHECKING:
    from app.Console.Scheduling.Schedule import Schedule


class Artisan:
    """Laravel-style Artisan command kernel."""
    
    def __init__(self) -> None:
        self.commands: Dict[str, Command] = {}
        self.aliases: Dict[str, str] = {}
        self._command_paths: List[str] = []
        self._scheduled_commands: List[ScheduledCommand] = []
        self._command_groups: Dict[str, List[str]] = {}
        self._before_callbacks: List[Callable[..., Any]] = []
        self._after_callbacks: List[Callable[..., Any]] = []
        
        # Register default command paths
        self.add_command_path('app.Console.Commands')
        
        # Auto-discover commands
        self.discover_commands()
    
    def register(self, command: Union[Command, Type[Command]], name: Optional[str] = None) -> None:
        """Register a command."""
        if isinstance(command, type):
            command = command()
            
        command_name = name or command.get_name()
        self.commands[command_name] = command
        
        # Register aliases
        for alias in command.get_aliases():
            self.aliases[alias] = command_name
        
        # Auto-group commands by namespace
        if ':' in command_name:
            group = command_name.split(':', 1)[0]
            if group not in self._command_groups:
                self._command_groups[group] = []
            self._command_groups[group].append(command_name)
    
    def group(self, namespace: str, commands: List[Union[str, Type[Command]]]) -> None:
        """Register a group of commands with a namespace."""
        for command in commands:
            if isinstance(command, str):
                # String command name
                if command in self.commands:
                    full_name = f"{namespace}:{command}"
                    self.commands[full_name] = self.commands[command]
                    if namespace not in self._command_groups:
                        self._command_groups[namespace] = []
                    self._command_groups[namespace].append(full_name)
            else:
                # Command class
                cmd_instance = command() if isinstance(command, type) else command
                full_name = f"{namespace}:{cmd_instance.get_name()}"
                self.register(cmd_instance, full_name)
    
    def before(self, callback: Callable[..., Any]) -> None:
        """Register a before callback."""
        self._before_callbacks.append(callback)
    
    def after(self, callback: Callable[..., Any]) -> None:
        """Register an after callback."""
        self._after_callbacks.append(callback)
    
    def schedule(self) -> 'Schedule':
        """Get the command scheduler."""
        from app.Console.Scheduling.Schedule import Schedule
        return Schedule()
    
    def command(self, signature: str, callback: Optional[Callable[..., Any]] = None, 
                description: str = "") -> Union[Callable[..., Any], Command]:
        """Register a closure-based command."""
        if callback is None:
            # Decorator usage
            def decorator(func: Callable[..., Any]) -> Command:
                cmd = ClosureCommand(signature, func, description)
                self.register(cmd)
                return cmd
            return decorator
        else:
            # Direct usage
            cmd = ClosureCommand(signature, callback, description)
            self.register(cmd)
            return cmd
    
    def add_command_path(self, path: str) -> None:
        """Add a path to search for commands."""
        if path not in self._command_paths:
            self._command_paths.append(path)
    
    def discover_commands(self) -> None:
        """Auto-discover commands from registered paths."""
        for path in self._command_paths:
            try:
                self._discover_commands_in_path(path)
            except ImportError:
                continue
    
    def _discover_commands_in_path(self, path: str) -> None:
        """Discover commands in a specific path."""
        try:
            module = importlib.import_module(path)
            if hasattr(module, '__path__'):
                # It's a package, iterate through modules
                for _, name, _ in pkgutil.iter_modules(module.__path__):
                    try:
                        submodule = importlib.import_module(f"{path}.{name}")
                        self._register_commands_from_module(submodule)
                    except ImportError as e:
                        # Log import errors if in debug mode
                        if self._is_debug_mode():
                            print(f"Debug: Failed to import {path}.{name}: {e}")
                        continue
                    except Exception as e:
                        # Log other errors if in debug mode
                        if self._is_debug_mode():
                            print(f"Debug: Error loading commands from {path}.{name}: {e}")
                        continue
            else:
                # It's a single module
                self._register_commands_from_module(module)
        except ImportError as e:
            if self._is_debug_mode():
                print(f"Debug: Could not import command path {path}: {e}")
        except Exception as e:
            if self._is_debug_mode():
                print(f"Debug: Error discovering commands in {path}: {e}")
    
    def _is_debug_mode(self) -> bool:
        """Check if running in debug mode."""
        import os
        return os.getenv('DEBUG', '').lower() in ['true', '1', 'yes']
    
    def _register_commands_from_module(self, module: Any) -> None:
        """Register commands found in a module."""
        commands_found = 0
        for attr_name in dir(module):
            try:
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, Command) and 
                    attr != Command):
                    try:
                        command_instance = attr()
                        self.register(command_instance)
                        commands_found += 1
                        
                        if self._is_debug_mode():
                            print(f"Debug: Registered command {command_instance.get_name()} from {module.__name__}")
                            
                    except Exception as e:
                        if self._is_debug_mode():
                            print(f"Debug: Failed to register command {attr_name}: {e}")
                        continue
            except Exception as e:
                if self._is_debug_mode():
                    print(f"Debug: Error inspecting {attr_name} in {module.__name__}: {e}")
                continue
        
        if self._is_debug_mode() and commands_found == 0:
            print(f"Debug: No commands found in {module.__name__}")
    
    def get(self, name: str) -> Optional[Command]:
        """Get a command by name or alias."""
        if name in self.commands:
            return self.commands[name]
        elif name in self.aliases:
            return self.commands[self.aliases[name]]
        return None
    
    def has(self, name: str) -> bool:
        """Check if a command exists."""
        return name in self.commands or name in self.aliases
    
    def all(self) -> Dict[str, Command]:
        """Get all registered commands."""
        return self.commands.copy()
    
    def visible_commands(self) -> Dict[str, Command]:
        """Get all visible (non-hidden) commands."""
        return {name: cmd for name, cmd in self.commands.items() 
                if not cmd.is_hidden()}
    
    async def call(self, command: str, arguments: Optional[Dict[str, Any]] = None) -> int:
        """Call a command programmatically."""
        cmd = self.get(command)
        if not cmd:
            print(f"Command '{command}' not found.", file=sys.stderr)
            return 1
        
        # Set arguments and options
        args = arguments or {}
        cmd.arguments = {k: v for k, v in args.items() 
                        if not k.startswith('--')}
        cmd.options = {k[2:]: v for k, v in args.items() 
                      if k.startswith('--')}
        
        # Run before callbacks
        for callback in self._before_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(command, arguments)
                else:
                    callback(command, arguments)
            except Exception as e:
                if self._is_debug_mode():
                    print(f"Debug: Before callback failed: {e}")
        
        try:
            await cmd.handle()
            exit_code = 0
        except Exception as e:
            print(f"Command failed: {e}", file=sys.stderr)
            exit_code = 1
        
        # Run after callbacks
        for callback in self._after_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(command, arguments, exit_code)
                else:
                    callback(command, arguments, exit_code)
            except Exception as e:
                if self._is_debug_mode():
                    print(f"Debug: After callback failed: {e}")
        
        return exit_code
    
    def queue(self, command: str, arguments: Optional[Dict[str, Any]] = None) -> 'QueuedCommand':
        """Queue a command for background execution."""
        return QueuedCommand(command, arguments or {}, self)
    
    async def run(self, argv: Optional[List[str]] = None) -> int:
        """Run the Artisan console application."""
        argv = argv or sys.argv[1:]
        
        if not argv:
            self._show_help()
            return 0
        
        command_name = argv[0]
        
        # Handle built-in commands
        if command_name == 'list':
            self._list_commands()
            return 0
        elif command_name == 'help':
            if len(argv) > 1:
                return self._show_command_help(argv[1])
            else:
                self._show_help()
                return 0
        
        # Get the command
        command = self.get(command_name)
        if not command:
            # Suggest similar commands
            suggestions = self._get_command_suggestions(command_name)
            error_msg = f"Command '{command_name}' is not defined."
            
            if suggestions:
                error_msg += f"\n\nDid you mean one of these?\n"
                for suggestion in suggestions:
                    error_msg += f"  {suggestion}\n"
            else:
                error_msg += f"\n\nRun 'python artisan.py list' to see all available commands."
            
            print(error_msg, file=sys.stderr)
            return 1
        
        # Parse arguments and options
        try:
            self._parse_input(command, argv[1:])
        except Exception as e:
            print(f"Error parsing arguments: {e}", file=sys.stderr)
            return 1
        
        # Execute the command
        try:
            await command.handle()
            return 0
        except KeyboardInterrupt:
            print("\\nCommand interrupted.", file=sys.stderr)
            return 130
        except Exception as e:
            # Enhanced error reporting
            error_msg = f"Command '{command_name}' failed: {e}"
            
            if self._is_debug_mode():
                import traceback
                error_msg += f"\\n\\nStack trace:\\n{traceback.format_exc()}"
            else:
                error_msg += f"\\n\\nRun with DEBUG=true for detailed error information."
            
            print(error_msg, file=sys.stderr)
            return 1
    
    def _get_command_suggestions(self, command_name: str) -> List[str]:
        """Get similar command suggestions using fuzzy matching."""
        suggestions: List[str] = []
        all_commands = list(self.commands.keys()) + list(self.aliases.keys())
        
        # Simple similarity scoring
        def similarity_score(cmd: str, target: str) -> float:
            target = target.lower()
            cmd = cmd.lower()
            
            # Exact substring match
            if target in cmd:
                return 0.9
            
            # Check if starts with target
            if cmd.startswith(target):
                return 0.8
            
            # Simple character overlap
            common_chars = len(set(target) & set(cmd))
            max_len = max(len(target), len(cmd))
            return common_chars / max_len if max_len > 0 else 0.0
        
        # Score all commands and get best matches
        scored_commands = []
        for cmd in all_commands:
            score = similarity_score(cmd, command_name)
            if score > 0.3:  # Minimum similarity threshold
                scored_commands.append((cmd, score))
        
        # Sort by score and return top 3
        scored_commands.sort(key=lambda x: x[1], reverse=True)
        return [cmd for cmd, score in scored_commands[:3]]
    
    def _parse_input(self, command: Command, args: List[str]) -> None:
        """Parse command arguments and options."""
        parser = argparse.ArgumentParser(
            description=command.get_description(),
            add_help=False
        )
        
        # Add arguments as positional
        for arg_def in command._input_definitions:
            if arg_def.is_array:
                parser.add_argument(
                    arg_def.name,
                    nargs='*' if not arg_def.required else '+',
                    default=arg_def.default,
                    help=arg_def.description
                )
            else:
                parser.add_argument(
                    arg_def.name,
                    nargs='?' if not arg_def.required else None,
                    default=arg_def.default,
                    help=arg_def.description
                )
        
        # Add options
        for opt_def in command._option_definitions:
            option_args = [f"--{opt_def.name}"]
            if opt_def.shortcut:
                option_args.append(f"-{opt_def.shortcut}")
            
            if opt_def.mode == "none":
                # Boolean option
                parser.add_argument(
                    *option_args,
                    action='store_true',
                    help=opt_def.description
                )
            elif opt_def.is_array:
                parser.add_argument(
                    *option_args,
                    action='append',
                    default=[],
                    help=opt_def.description
                )
            else:
                parser.add_argument(
                    *option_args,
                    default=opt_def.default,
                    help=opt_def.description
                )
        
        # Parse the arguments
        parsed_args = parser.parse_args(args)
        
        # Set command arguments and options
        command.arguments = {}
        command.options = {}
        
        for arg_def in command._input_definitions:
            value = getattr(parsed_args, arg_def.name, arg_def.default)
            command.arguments[arg_def.name] = value
        
        for opt_def in command._option_definitions:
            value = getattr(parsed_args, opt_def.name, opt_def.default)
            command.options[opt_def.name] = value
    
    def _show_help(self) -> None:
        """Show general help."""
        print("Laravel-style Artisan Console Tool\\n")
        print("Usage:")
        print("  python artisan.py <command> [options] [arguments]\\n")
        print("Available commands:")
        
        for name, command in sorted(self.visible_commands().items()):
            description = command.get_description()
            print(f"  {name:<30} {description}")
        
        print("\\nFor help on a specific command, use: python artisan.py help <command>")
    
    def _list_commands(self) -> None:
        """List all available commands."""
        print("Available commands:\\n")
        
        # Group commands by namespace
        grouped: Dict[str, List[tuple[str, Command]]] = {}
        for name, command in sorted(self.visible_commands().items()):
            if ':' in name:
                namespace = name.split(':', 1)[0]
            else:
                namespace = 'default'
            
            if namespace not in grouped:
                grouped[namespace] = []
            grouped[namespace].append((name, command))
        
        # Add custom command groups
        for group_name, command_names in self._command_groups.items():
            if group_name not in grouped:
                grouped[group_name] = []
            for cmd_name in command_names:
                if cmd_name in self.commands and cmd_name not in [c[0] for c in grouped[group_name]]:
                    grouped[group_name].append((cmd_name, self.commands[cmd_name]))
        
        for namespace, commands in sorted(grouped.items()):
            if namespace != 'default':
                print(f"{namespace}:")
            
            for name, command in commands:
                description = command.get_description()
                indent = "  " if namespace != 'default' else ""
                print(f"{indent}{name:<30} {description}")
            
            if namespace != 'default':
                print()
    
    def _show_command_help(self, command_name: str) -> int:
        """Show help for a specific command."""
        command = self.get(command_name)
        if not command:
            print(f"Command '{command_name}' is not defined.", file=sys.stderr)
            return 1
        
        print(f"Description:\\n  {command.get_description()}\\n")
        print(f"Usage:\\n  {command.signature}\\n")
        
        if command._input_definitions:
            print("Arguments:")
            for arg_def in command._input_definitions:
                required = " (required)" if arg_def.required else " (optional)"
                array_marker = " (multiple values)" if arg_def.is_array else ""
                print(f"  {arg_def.name:<20} {arg_def.description}{required}{array_marker}")
            print()
        
        if command._option_definitions:
            print("Options:")
            for opt_def in command._option_definitions:
                option_name = f"--{opt_def.name}"
                if opt_def.shortcut:
                    option_name += f", -{opt_def.shortcut}"
                
                mode_info = ""
                if opt_def.mode == "required":
                    mode_info = " (required value)"
                elif opt_def.mode == "optional":
                    mode_info = " (optional value)"
                
                array_marker = " (multiple values)" if opt_def.is_array else ""
                print(f"  {option_name:<20} {opt_def.description}{mode_info}{array_marker}")
        
        return 0


class ClosureCommand(Command):
    """A command defined by a closure."""
    
    def __init__(self, signature: str, callback: Callable[..., Any], description: str = "") -> None:
        self.signature = signature
        self.description = description
        self.callback = callback
        super().__init__()
    
    async def handle(self) -> None:
        """Execute the closure."""
        if asyncio.iscoroutinefunction(self.callback):
            await self.callback(self)
        else:
            self.callback(self)


class QueuedCommand:
    """Represents a queued command."""
    
    def __init__(self, command: str, arguments: Dict[str, Any], artisan: Artisan) -> None:
        self.command = command
        self.arguments = arguments
        self.artisan = artisan
        self.connection: Optional[str] = None
        self.queue: Optional[str] = None
    
    def on_connection(self, connection: str) -> 'QueuedCommand':
        """Set the queue connection."""
        self.connection = connection
        return self
    
    def on_queue(self, queue: str) -> 'QueuedCommand':
        """Set the queue name."""
        self.queue = queue
        return self
    
    async def dispatch(self) -> None:
        """Dispatch the command to the queue."""
        # This would integrate with your queue system
        # For now, just execute immediately
        await self.artisan.call(self.command, self.arguments)


class ScheduledCommand:
    """Represents a scheduled command."""
    
    def __init__(self, command: str, arguments: Optional[Dict[str, Any]] = None) -> None:
        self.command = command
        self.arguments = arguments or {}
        self.cron_expression = ""
        self.next_run: Optional[datetime] = None
    
    def daily(self) -> 'ScheduledCommand':
        """Run daily at midnight."""
        self.cron_expression = "0 0 * * *"
        return self
    
    def hourly(self) -> 'ScheduledCommand':
        """Run hourly."""
        self.cron_expression = "0 * * * *"
        return self
    
    def every_minute(self) -> 'ScheduledCommand':
        """Run every minute."""
        self.cron_expression = "* * * * *"
        return self
    
    def at(self, time: str) -> 'ScheduledCommand':
        """Run at specific time."""
        # Parse time and set cron expression
        return self


# Enhanced Artisan Kernel with Laravel-style features
class ArtisanKernel(Artisan):
    """Enhanced Laravel-style Artisan kernel with additional features."""
    
    def __init__(self) -> None:
        super().__init__()
        self._middleware: List[Callable[..., Any]] = []
        self._output_style: str = 'default'
        self._verbosity_level: int = 1
        
        # Register built-in middleware
        self.add_middleware(self._timing_middleware)
        self.add_middleware(self._logging_middleware)
    
    def add_middleware(self, middleware: Callable[..., Any]) -> None:
        """Add command middleware."""
        self._middleware.append(middleware)
    
    def set_output_style(self, style: str) -> None:
        """Set output style (default, json, table, etc.)."""
        self._output_style = style
    
    def set_verbosity(self, level: int) -> None:
        """Set verbosity level (0=quiet, 1=normal, 2=verbose, 3=debug)."""
        self._verbosity_level = level
    
    async def _timing_middleware(self, command: str, arguments: Dict[str, Any], next_handler: Callable[..., Any]) -> Any:
        """Timing middleware to track command execution time."""
        start_time = datetime.now()
        try:
            result = await next_handler()
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            if self._verbosity_level >= 2:
                print(f"\nCommand executed in {execution_time:.3f} seconds")
            
            return result
        except Exception as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            if self._verbosity_level >= 1:
                print(f"\nCommand failed after {execution_time:.3f} seconds")
            
            raise e
    
    async def _logging_middleware(self, command: str, arguments: Dict[str, Any], next_handler: Callable[..., Any]) -> Any:
        """Logging middleware to log command execution."""
        if self._verbosity_level >= 3:
            print(f"Executing command: {command} with arguments: {arguments}")
        
        return await next_handler()
    
    def make(self, command_class: str) -> Optional[Command]:
        """Laravel-style make method to create command instances."""
        try:
            parts = command_class.split('.')
            module_name = '.'.join(parts[:-1])
            class_name = parts[-1]
            
            module = importlib.import_module(module_name)
            command_class_obj = getattr(module, class_name)
            
            if issubclass(command_class_obj, Command):
                return command_class_obj()  # type: ignore[no-any-return]
        except (ImportError, AttributeError, TypeError):
            pass
        
        return None
    
    def forget(self, command_name: str) -> None:
        """Remove a command from the registry."""
        if command_name in self.commands:
            del self.commands[command_name]
        
        # Remove from aliases
        aliases_to_remove = [alias for alias, target in self.aliases.items() if target == command_name]
        for alias in aliases_to_remove:
            del self.aliases[alias]
        
        # Remove from groups
        for group_name, command_names in self._command_groups.items():
            if command_name in command_names:
                command_names.remove(command_name)
    
    def environment(self, *environments: str) -> 'EnvironmentScope':
        """Create an environment scope for commands."""
        return EnvironmentScope(self, environments)
    
    def when(self, condition: bool) -> 'ConditionalScope':
        """Create a conditional scope for commands."""
        return ConditionalScope(self, condition)


class EnvironmentScope:
    """Environment-based command scope."""
    
    def __init__(self, kernel: ArtisanKernel, environments: Tuple[str, ...]) -> None:
        self.kernel = kernel
        self.environments = environments
        self._current_env = self._get_current_environment()
    
    def _get_current_environment(self) -> str:
        """Get current environment."""
        import os
        return os.getenv('APP_ENV', 'production')
    
    def command(self, signature: str, callback: Callable[..., Any], description: str = "") -> Optional[Command]:
        """Register command only in specified environments."""
        if self._current_env in self.environments:
            result = self.kernel.command(signature, callback, description)
            return result if isinstance(result, Command) else None
        return None


class ConditionalScope:
    """Conditional command scope."""
    
    def __init__(self, kernel: ArtisanKernel, condition: bool) -> None:
        self.kernel = kernel
        self.condition = condition
    
    def command(self, signature: str, callback: Callable[..., Any], description: str = "") -> Optional[Command]:
        """Register command only if condition is true."""
        if self.condition:
            result = self.kernel.command(signature, callback, description)
            return result if isinstance(result, Command) else None
        return None


# Global enhanced Artisan kernel instance
artisan = ArtisanKernel()