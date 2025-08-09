from __future__ import annotations

import sys
import os
from typing import Dict, List, Optional, Any, Type, Callable, Union
from pathlib import Path
import argparse
import importlib
import inspect
from abc import ABC, abstractmethod
import asyncio
from datetime import datetime
import json
from enum import Enum
import traceback
from contextlib import contextmanager


class CommandSignatureParser:
    """Laravel 12 style command signature parser."""
    
    @staticmethod
    def parse(signature: str) -> Dict[str, Any]:
        """Parse Laravel-style command signature."""
        parts = signature.split()
        if not parts:
            return {"name": "", "arguments": [], "options": []}
        
        name = parts[0]
        arguments = []
        options = []
        
        for part in parts[1:]:
            if part.startswith('{') and part.endswith('}'):
                # Argument
                arg_content = part[1:-1]
                if arg_content.endswith('?'):
                    arguments.append({"name": arg_content[:-1], "required": False})
                else:
                    arguments.append({"name": arg_content, "required": True})
            elif part.startswith('--'):
                # Long option
                option_name = part[2:]
                if '=' in option_name:
                    name_part, default = option_name.split('=', 1)
                    options.append({"name": name_part, "has_value": True, "default": default})
                else:
                    options.append({"name": option_name, "has_value": False, "default": False})
        
        return {"name": name, "arguments": arguments, "options": options}


class OutputStyle(Enum):
    """Command output styles matching Laravel 12."""
    INFO = "info"
    COMMENT = "comment" 
    QUESTION = "question"
    ERROR = "error"
    WARNING = "warn"
    SUCCESS = "success"
    LINE = "line"
    TITLE = "title"
    SECTION = "section"


class Command(ABC):
    """Base Artisan command class."""
    
    signature: str = ''
    description: str = ''
    help: str = ''
    hidden: bool = False
    
    # Laravel 12 style properties
    aliases: List[str] = []
    enabled: bool = True
    verbosity: int = 1
    
    def __init__(self) -> None:
        self.args: argparse.Namespace = argparse.Namespace()
        self.output_lines: List[str] = []
        self.start_time: Optional[datetime] = None
        self.output_buffer: List[tuple[OutputStyle, str]] = []
        self._parsed_signature: Optional[Dict[str, Any]] = None
    
    @abstractmethod
    def handle(self) -> int:
        """Execute the command."""
        pass
    
    async def handle_async(self) -> int:
        """Async command handler for Laravel 12 compatibility."""
        return self.handle()
    
    def configure(self) -> None:
        """Configure the command (Laravel 12 style)."""
        pass
    
    def initialize(self) -> None:
        """Initialize the command before execution."""
        self.start_time = datetime.now()
        self.configure()
    
    def finalize(self, exit_code: int) -> None:
        """Finalize the command after execution."""
        if self.start_time:
            duration = datetime.now() - self.start_time
            if self.verbosity >= 2:
                self.line(f"Command completed in {duration.total_seconds():.2f}s")
    
    def argument(self, name: str, default: Any = None) -> Any:
        """Get command argument."""
        return getattr(self.args, name, default)
    
    def option(self, name: str, default: Any = None) -> Any:
        """Get command option."""
        return getattr(self.args, name, default)
    
    def line(self, message: str = '', style: Optional[OutputStyle] = None) -> None:
        """Write a line to output."""
        if style:
            self.output_buffer.append((style, message))
        
        formatted_message = self._format_message(message, style or OutputStyle.LINE)
        print(formatted_message)
        self.output_lines.append(formatted_message)
    
    def _format_message(self, message: str, style: OutputStyle) -> str:
        """Format message with Laravel 12 style colors."""
        color_codes = {
            OutputStyle.INFO: "\033[94m",      # Blue
            OutputStyle.COMMENT: "\033[90m",   # Gray
            OutputStyle.QUESTION: "\033[93m",  # Yellow
            OutputStyle.ERROR: "\033[91m",     # Red
            OutputStyle.WARNING: "\033[93m",   # Yellow
            OutputStyle.SUCCESS: "\033[92m",   # Green
            OutputStyle.TITLE: "\033[95m",     # Magenta
            OutputStyle.SECTION: "\033[96m",   # Cyan
            OutputStyle.LINE: "",              # No color
        }
        
        reset_code = "\033[0m"
        color_code = color_codes.get(style, "")
        
        if color_code:
            return f"{color_code}{message}{reset_code}"
        return message
    
    def info(self, message: str) -> None:
        """Write info message."""
        self.line(f"ℹ️  {message}", OutputStyle.INFO)
    
    def comment(self, message: str) -> None:
        """Write comment message."""
        self.line(f"💬 {message}", OutputStyle.COMMENT)
    
    def question(self, message: str) -> None:
        """Write question message."""
        self.line(f"❓ {message}", OutputStyle.QUESTION)
    
    def error(self, message: str) -> None:
        """Write error message."""
        self.line(f"❌ {message}", OutputStyle.ERROR)
    
    def warn(self, message: str) -> None:
        """Write warning message."""
        self.line(f"⚠️  {message}", OutputStyle.WARNING)
    
    def success(self, message: str) -> None:
        """Write success message."""
        self.line(f"✅ {message}", OutputStyle.SUCCESS)
    
    def title(self, message: str) -> None:
        """Write title message (Laravel 12)."""
        self.line(f"\n{message}", OutputStyle.TITLE)
        self.line("=" * len(message), OutputStyle.TITLE)
    
    def section(self, message: str) -> None:
        """Write section message (Laravel 12)."""
        self.line(f"\n{message}", OutputStyle.SECTION)
        self.line("-" * len(message), OutputStyle.SECTION)
    
    def newLine(self, count: int = 1) -> None:
        """Write new lines (Laravel 12)."""
        for _ in range(count):
            self.line()
    
    def table(self, headers: List[str], rows: List[List[str]]) -> None:
        """Display a table."""
        if not rows:
            return
        
        # Calculate column widths
        widths = [len(header) for header in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(widths):
                    widths[i] = max(widths[i], len(str(cell)))
        
        # Print header
        header_line = ' | '.join(h.ljust(w) for h, w in zip(headers, widths))
        self.line(header_line)
        self.line('-' * len(header_line))
        
        # Print rows
        for row in rows:
            row_line = ' | '.join(str(cell).ljust(widths[i]) for i, cell in enumerate(row))
            self.line(row_line)
    
    def ask(self, question: str, default: Optional[str] = None) -> str:
        """Ask user for input."""
        prompt = question
        if default:
            prompt += f" [{default}]"
        prompt += ": "
        
        try:
            response = input(prompt).strip()
            return response if response else (default or '')
        except KeyboardInterrupt:
            self.line("\nOperation cancelled.")
            sys.exit(1)
    
    def confirm(self, question: str, default: bool = False) -> bool:
        """Ask for confirmation."""
        default_str = "Y/n" if default else "y/N"
        response = self.ask(f"{question} ({default_str})", "y" if default else "n")
        return response.lower() in ['y', 'yes', '1', 'true']
    
    def choice(self, question: str, choices: List[str], default: Optional[str] = None) -> str:
        """Ask user to choose from options."""
        self.line(question)
        for i, choice in enumerate(choices, 1):
            marker = " (default)" if choice == default else ""
            self.line(f"  {i}. {choice}{marker}")
        
        while True:
            try:
                response = input("Please select an option: ").strip()
                
                if not response and default:
                    return default
                
                if response.isdigit():
                    index = int(response) - 1
                    if 0 <= index < len(choices):
                        return choices[index]
                
                if response in choices:
                    return response
                
                self.error("Invalid choice. Please try again.")
            except KeyboardInterrupt:
                self.line("\nOperation cancelled.")
                sys.exit(1)
    
    def secret(self, question: str) -> str:
        """Ask for secret input (hidden)."""
        import getpass
        try:
            return getpass.getpass(f"{question}: ")
        except KeyboardInterrupt:
            self.line("\nOperation cancelled.")
            sys.exit(1)
    
    def anticipate(self, question: str, choices: List[str]) -> str:
        """Ask with auto-completion suggestions."""
        self.line(f"Suggestions: {', '.join(choices)}")
        return self.ask(question)
    
    def progressStart(self, max_steps: int = 0) -> None:
        """Start a progress bar (Laravel 12)."""
        self._progress_max = max_steps
        self._progress_current = 0
        if max_steps > 0:
            self.line(f"Progress: 0/{max_steps}")
    
    def progressAdvance(self, steps: int = 1) -> None:
        """Advance progress bar (Laravel 12)."""
        if hasattr(self, '_progress_max'):
            self._progress_current += steps
            if self._progress_max > 0:
                percentage = (self._progress_current / self._progress_max) * 100
                self.line(f"Progress: {self._progress_current}/{self._progress_max} ({percentage:.1f}%)")
    
    def progressFinish(self) -> None:
        """Finish progress bar (Laravel 12)."""
        if hasattr(self, '_progress_max') and self._progress_max > 0:
            self.line(f"Progress: {self._progress_max}/{self._progress_max} (100%)")
        delattr(self, '_progress_max')
        delattr(self, '_progress_current')
    
    @contextmanager
    def withProgressBar(self, items: List[Any], description: str = "") -> Any:
        """Context manager for progress bar (Laravel 12)."""
        if description:
            self.info(description)
        
        self.progressStart(len(items))
        try:
            for item in items:
                yield item
                self.progressAdvance()
        finally:
            self.progressFinish()
    
    def callSilent(self, command: str, parameters: Optional[Dict[str, Any]] = None) -> int:
        """Call another command silently (Laravel 12)."""
        from app.Console.Artisan import kernel
        return kernel.call(command, parameters)
    
    def call(self, command: str, parameters: Optional[Dict[str, Any]] = None) -> int:
        """Call another command with output (Laravel 12)."""
        self.info(f"Calling command: {command}")
        return self.callSilent(command, parameters)
    
    def getParsedSignature(self) -> Dict[str, Any]:
        """Get parsed command signature (Laravel 12)."""
        if self._parsed_signature is None:
            self._parsed_signature = CommandSignatureParser.parse(self.signature)
        return self._parsed_signature


class Kernel:
    """Laravel 12 style Artisan command kernel."""
    
    def __init__(self) -> None:
        self.commands: Dict[str, Type[Command]] = {}
        self.command_aliases: Dict[str, str] = {}
        self.command_paths: List[str] = [
            'app.Console.Commands',
        ]
        self.starting_callbacks: List[Callable[[], None]] = []
        self.terminating_callbacks: List[Callable[[], None]] = []
        self.before_callbacks: List[Callable[[Command], None]] = []
        self.after_callbacks: List[Callable[[Command, int], None]] = []
        self.exception_handlers: List[Callable[[Exception], Optional[int]]] = []
        self.schedule: Dict[str, Any] = {}
        self._discover_commands()
    
    def _discover_commands(self) -> None:
        """Discover and register commands."""
        for command_path in self.command_paths:
            self._discover_commands_in_path(command_path)
    
    def _discover_commands_in_path(self, path: str) -> None:
        """Discover commands in a specific path."""
        try:
            module = importlib.import_module(path)
            module_dir = Path(module.__file__).parent if module.__file__ else None
            
            if module_dir and module_dir.exists():
                for file_path in module_dir.glob('*.py'):
                    if file_path.name.startswith('_'):
                        continue
                    
                    module_name = f"{path}.{file_path.stem}"
                    try:
                        command_module = importlib.import_module(module_name)
                        self._register_commands_from_module(command_module)
                    except (ImportError, Exception):
                        # Skip modules that fail to import
                        continue
        except ImportError:
            pass
    
    def _register_commands_from_module(self, module: Any) -> None:
        """Register commands from a module."""
        for name in dir(module):
            obj = getattr(module, name)
            if (inspect.isclass(obj) and 
                issubclass(obj, Command) and 
                obj != Command and
                hasattr(obj, 'signature') and
                obj.signature):
                
                command_name = self._parse_command_name(obj.signature)
                if command_name:
                    self.commands[command_name] = obj
    
    def _parse_command_name(self, signature: str) -> Optional[str]:
        """Parse command name from signature."""
        parts = signature.split()
        return parts[0] if parts else None
    
    def register(self, command_class: Type[Command]) -> None:
        """Register a command class (Laravel 12 style)."""
        if hasattr(command_class, 'signature') and command_class.signature:
            command_name = self._parse_command_name(command_class.signature)
            if command_name:
                self.commands[command_name] = command_class
                
                # Register aliases
                if hasattr(command_class, 'aliases'):
                    for alias in command_class.aliases:
                        self.command_aliases[alias] = command_name
    
    def registerIf(self, condition: bool, command_class: Type[Command]) -> None:
        """Register command conditionally (Laravel 12)."""
        if condition:
            self.register(command_class)
    
    def resolveCommands(self, commands: List[Union[str, Type[Command]]]) -> None:
        """Resolve and register multiple commands (Laravel 12)."""
        for command in commands:
            if isinstance(command, str):
                try:
                    module = importlib.import_module(command)
                    self._register_commands_from_module(module)
                except ImportError:
                    continue
            else:
                self.register(command)
    
    def call(self, command: str, parameters: Optional[Dict[str, Any]] = None) -> int:
        """Call a command programmatically (Laravel 12 enhanced)."""
        # Resolve alias
        if command in self.command_aliases:
            command = self.command_aliases[command]
        
        if command not in self.commands:
            print(f"Command '{command}' not found.")
            return 1
        
        command_class = self.commands[command]
        command_instance = command_class()
        
        # Set parameters as args
        if parameters:
            for key, value in parameters.items():
                setattr(command_instance.args, key, value)
        
        # Execute before callbacks
        for callback in self.before_callbacks:
            try:
                callback(command_instance)
            except Exception as e:
                print(f"Error in before callback: {e}")
        
        try:
            command_instance.initialize()
            result = command_instance.handle()
            
            # Handle async commands
            if asyncio.iscoroutine(result):
                exit_code: int = asyncio.run(result) or 0
            else:
                exit_code = result if isinstance(result, int) else 0
                
            command_instance.finalize(exit_code)
            
            # Execute after callbacks
            for after_callback in self.after_callbacks:
                try:
                    after_callback(command_instance, exit_code)
                except Exception as e:
                    print(f"Error in after callback: {e}")
            
            return exit_code
            
        except Exception as e:
            # Handle exceptions
            for handler in self.exception_handlers:
                try:
                    handler_result = handler(e)
                    if handler_result is not None and isinstance(handler_result, int):
                        return handler_result
                except Exception:
                    continue
            
            print(f"Command failed with error: {e}")
            if command_instance.verbosity >= 2:
                traceback.print_exc()
            return 1
    
    def starting(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called when starting command execution."""
        self.starting_callbacks.append(callback)
    
    def terminating(self, callback: Callable[[], None]) -> None:
        """Register a callback to be called when terminating command execution."""
        self.terminating_callbacks.append(callback)
    
    def before(self, callback: Callable[[Command], None]) -> None:
        """Register a before command callback (Laravel 12)."""
        self.before_callbacks.append(callback)
    
    def after(self, callback: Callable[[Command, int], None]) -> None:
        """Register an after command callback (Laravel 12)."""
        self.after_callbacks.append(callback)
    
    def resolveHandler(self, exception_handler: Callable[[Exception], Optional[int]]) -> None:
        """Register exception handler (Laravel 12)."""
        self.exception_handlers.append(exception_handler)
    
    async def callAsync(self, command: str, parameters: Optional[Dict[str, Any]] = None) -> int:
        """Call command asynchronously (Laravel 12)."""
        # Resolve alias
        if command in self.command_aliases:
            command = self.command_aliases[command]
        
        if command not in self.commands:
            print(f"Command '{command}' not found.")
            return 1
        
        command_class = self.commands[command]
        command_instance = command_class()
        
        # Set parameters as args
        if parameters:
            for key, value in parameters.items():
                setattr(command_instance.args, key, value)
        
        try:
            command_instance.initialize()
            exit_code = await command_instance.handle_async()
            command_instance.finalize(exit_code)
            return exit_code
        except Exception as e:
            print(f"Async command failed with error: {e}")
            return 1
    
    def bootstrap(self) -> None:
        """Bootstrap the console application."""
        for callback in self.starting_callbacks:
            callback()
    
    def terminate(self) -> None:
        """Terminate the console application."""
        for callback in self.terminating_callbacks:
            callback()

    def handle(self, argv: Optional[List[str]] = None) -> int:
        """Handle command line input."""
        if argv is None:
            argv = sys.argv[1:]
        
        # Bootstrap the application
        self.bootstrap()
        
        try:
            if not argv:
                return self._show_command_list()
            
            command_name = argv[0]
            
            if command_name in ['help', '--help', '-h']:
                if len(argv) > 1:
                    return self._show_command_help(argv[1])
                return self._show_command_list()
            
            if command_name not in self.commands:
                print(f"Command '{command_name}' not found.")
                return 1
            
            return self._execute_command(command_name, argv[1:])
        finally:
            # Always terminate
            self.terminate()
    
    def _show_command_list(self) -> int:
        """Show list of available commands (Laravel 12 style)."""
        print("\033[95mLaravel FastAPI Artisan Console v12\033[0m")
        print("\033[95m===================================\033[0m")
        print()
        print("\033[93mUsage:\033[0m")
        print("  python artisan.py <command> [options] [arguments]")
        print()
        print("\033[93mOptions:\033[0m")
        print("  -h, --help     Display help for the given command")
        print("  -q, --quiet    Do not output any message")
        print("  -v, --verbose  Increase the verbosity of messages")
        print()
        print("\033[93mAvailable commands:\033[0m")
        
        groups: Dict[str, List[tuple[str, str, List[str]]]] = {}
        
        for name, command_class in sorted(self.commands.items()):
            if hasattr(command_class, 'hidden') and command_class.hidden:
                continue
            
            if not hasattr(command_class, 'enabled') or command_class.enabled:
                description = getattr(command_class, 'description', '')
                aliases = getattr(command_class, 'aliases', [])
                
                # Group commands by namespace
                if ':' in name:
                    namespace = name.split(':')[0]
                else:
                    namespace = 'general'
                
                if namespace not in groups:
                    groups[namespace] = []
                
                groups[namespace].append((name, description, aliases))
        
        for namespace, commands in groups.items():
            if namespace != 'general':
                print(f"\n\033[96m{namespace}:\033[0m")
            
            for cmd_name, cmd_desc, cmd_aliases in commands:
                alias_text = f" [{', '.join(cmd_aliases)}]" if cmd_aliases else ""
                print(f"  \033[92m{cmd_name:<25}\033[0m {cmd_desc}{alias_text}")
        
        # Show aliases
        if self.command_aliases:
            print("\n\033[96mAliases:\033[0m")
            for alias, command in sorted(self.command_aliases.items()):
                print(f"  \033[92m{alias:<25}\033[0m -> {command}")
        
        return 0
    
    def _show_command_help(self, command_name: str) -> int:
        """Show help for a specific command."""
        if command_name not in self.commands:
            print(f"Command '{command_name}' not found.")
            return 1
        
        command_class = self.commands[command_name]
        
        print(f"Description:")
        print(f"  {getattr(command_class, 'description', 'No description available')}")
        print()
        print(f"Usage:")
        print(f"  {getattr(command_class, 'signature', command_name)}")
        
        help_text = getattr(command_class, 'help', '')
        if help_text:
            print()
            print("Help:")
            print(f"  {help_text}")
        
        return 0
    
    def _execute_command(self, command_name: str, args: List[str]) -> int:
        """Execute a command."""
        command_class = self.commands[command_name]
        command_instance = command_class()
        
        # Parse arguments based on signature
        parsed_args = self._parse_arguments(command_class, args)
        command_instance.args = parsed_args
        
        try:
            result = command_instance.handle()
            
            # Handle async commands
            if asyncio.iscoroutine(result):
                async_result = asyncio.run(result)
                return async_result if isinstance(async_result, int) else 0
            
            return result if isinstance(result, int) else 0
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return 1
        except Exception as e:
            print(f"Error executing command: {e}")
            return 1
    
    def _parse_arguments(self, command_class: Type[Command], args: List[str]) -> argparse.Namespace:
        """Parse command arguments."""
        parser = argparse.ArgumentParser(
            prog=getattr(command_class, 'signature', '').split()[0],
            description=getattr(command_class, 'description', ''),
            add_help=False
        )
        
        # Parse signature to add arguments and options
        signature = getattr(command_class, 'signature', '')
        self._add_arguments_from_signature(parser, signature)
        
        try:
            return parser.parse_args(args)
        except SystemExit:
            # argparse calls sys.exit on error, catch it
            return argparse.Namespace()
    
    def _add_arguments_from_signature(self, parser: argparse.ArgumentParser, signature: str) -> None:
        """Add arguments and options from command signature."""
        if not signature:
            return
        
        # Basic parsing - this could be enhanced
        parts = signature.split()
        for part in parts[1:]:  # Skip command name
            if part.startswith('{') and part.endswith('}'):
                # Required argument
                arg_name = part[1:-1]
                parser.add_argument(arg_name)
            elif part.startswith('{') and part.endswith('?}'):
                # Optional argument
                arg_name = part[1:-2]
                parser.add_argument(arg_name, nargs='?')
            elif part.startswith('--'):
                # Long option
                parser.add_argument(part, action='store_true')
            elif part.startswith('-'):
                # Short option
                parser.add_argument(part, action='store_true')


# Global kernel instance
kernel = Kernel()


def register_command(command_class: Type[Command]) -> None:
    """Register a command globally."""
    kernel.register(command_class)


def call(command: str, parameters: Optional[Dict[str, Any]] = None) -> int:
    """Call an Artisan command programmatically."""
    return kernel.call(command, parameters)


# Laravel 12 style built-in commands
class ListCommand(Command):
    """List all available commands."""
    
    signature = 'list'
    description = 'List all available Artisan commands'
    aliases = ['ls']
    
    def handle(self) -> int:
        return kernel._show_command_list()


class HelpCommand(Command):
    """Show help for a command."""
    
    signature = 'help {command?}'
    description = 'Show help for a specific command'
    aliases = ['--help', '-h']
    
    def handle(self) -> int:
        command_name = self.argument('command')
        if command_name:
            return kernel._show_command_help(command_name)
        return kernel._show_command_list()


class ClearCacheCommand(Command):
    """Clear application cache."""
    
    signature = 'cache:clear {--tags=* : Clear only specific cache tags}'
    description = 'Clear the application cache'
    aliases = ['clear:cache']
    
    def handle(self) -> int:
        tags = self.option('tags', [])
        
        if tags:
            self.info(f"Clearing cache for tags: {', '.join(tags)}")
        else:
            self.info("Clearing application cache...")
        
        # Clear cache directories
        cache_dirs = [
            'storage/cache',
            'storage/framework/cache', 
            'bootstrap/cache'
        ]
        
        cleared_count = 0
        
        self.progressStart(len(cache_dirs))
        
        for cache_dir in cache_dirs:
            cache_path = Path(cache_dir)
            if cache_path.exists():
                for file_path in cache_path.rglob('*'):
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        try:
                            # If tags specified, only clear tagged files
                            if tags:
                                # This would integrate with actual cache tagging system
                                pass
                            file_path.unlink()
                            cleared_count += 1
                        except Exception:
                            pass
            self.progressAdvance()
        
        self.progressFinish()
        self.success(f"Application cache cleared! Removed {cleared_count} cached files.")
        return 0


class RouteListCommand(Command):
    """List all registered routes."""
    
    signature = 'route:list {--compact : Show compact route list} {--name= : Filter by route name} {--method= : Filter by HTTP method}'
    description = 'List all registered routes'
    aliases = ['routes']
    
    def handle(self) -> int:
        compact = self.option('compact', False)
        name_filter = self.option('name')
        method_filter = self.option('method')
        
        self.title("Registered Routes")
        
        if name_filter:
            self.info(f"Filtering by name: {name_filter}")
        if method_filter:
            self.info(f"Filtering by method: {method_filter}")
        
        # This would integrate with the actual routing system
        routes = [
            ['GET', '/api/v1/users', 'UserController@index', 'api.users.index', 'auth,throttle'],
            ['POST', '/api/v1/users', 'UserController@store', 'api.users.store', 'auth,validate'],
            ['GET', '/api/v1/users/{id}', 'UserController@show', 'api.users.show', 'auth'],
            ['PUT', '/api/v1/users/{id}', 'UserController@update', 'api.users.update', 'auth,validate'],
            ['DELETE', '/api/v1/users/{id}', 'UserController@destroy', 'api.users.destroy', 'auth'],
        ]
        
        # Apply filters
        if name_filter:
            routes = [r for r in routes if name_filter in r[3]]
        if method_filter:
            routes = [r for r in routes if r[0].upper() == method_filter.upper()]
        
        if compact:
            headers = ['Method', 'URI', 'Name']
            display_routes = [[r[0], r[1], r[3]] for r in routes]
        else:
            headers = ['Method', 'URI', 'Action', 'Name', 'Middleware']
            display_routes = routes
        
        if not routes:
            self.warn("No routes found matching the criteria.")
            return 0
        
        self.table(headers, display_routes)
        self.info(f"\nShowing {len(routes)} route(s)")
        
        return 0


# Laravel 12 style enhanced commands
class AboutCommand(Command):
    """Display basic information about your application."""
    
    signature = 'about {--only=* : Show only specific sections} {--json : Output as JSON}'
    description = 'Display basic information about your application'
    
    def handle(self) -> int:
        only_sections = self.option('only', [])
        json_output = self.option('json', False)
        
        info = {
            "Environment": {
                "Application Name": "Laravel FastAPI",
                "Environment": "local",
                "Debug Mode": "ON",
                "URL": "http://localhost:8000",
                "Timezone": "UTC"
            },
            "Cache": {
                "Config": "file",
                "Route": "file", 
                "View": "file"
            },
            "Drivers": {
                "Broadcasting": "pusher",
                "Cache": "file",
                "Database": "sqlite",
                "Logs": "stack",
                "Mail": "smtp",
                "Queue": "database",
                "Session": "file"
            }
        }
        
        if json_output:
            print(json.dumps(info, indent=2))
            return 0
        
        self.title("Application Information")
        
        for section_name, section_data in info.items():
            if only_sections and section_name.lower() not in [s.lower() for s in only_sections]:
                continue
                
            self.section(section_name)
            for key, value in section_data.items():
                self.line(f"  {key:<20} {value}")
            self.newLine()
        
        return 0


class InspireCommand(Command):
    """Display an inspiring quote."""
    
    signature = 'inspire'
    description = 'Display an inspiring quote'
    
    def handle(self) -> int:
        quotes = [
            "The way to get started is to quit talking and begin doing. - Walt Disney",
            "Innovation distinguishes between a leader and a follower. - Steve Jobs",
            "Life is what happens to you while you're busy making other plans. - John Lennon",
            "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
            "You miss 100% of the shots you don't take. - Wayne Gretzky"
        ]
        
        import random
        quote = random.choice(quotes)
        
        self.info(quote)
        return 0


class EnvironmentCommand(Command):
    """Display the current framework environment."""
    
    signature = 'env'
    description = 'Display the current framework environment'
    
    def handle(self) -> int:
        env = os.getenv('APP_ENV', 'local')
        self.line(env)
        return 0


# Register built-in commands
register_command(ListCommand)
register_command(HelpCommand)
register_command(ClearCacheCommand)
register_command(RouteListCommand)
register_command(AboutCommand)
register_command(InspireCommand)
register_command(EnvironmentCommand)

# Import and register all available commands
command_modules = [
    'MigrationCommands',
    'FactoryCommands', 
    'MakeControllerCommand',
    'MakeModelCommand',
    'MakeServiceCommand',
    'MakeJobCommand',
    'MakeCommandCommand',
    'MakePolicyCommand',
    'MakeMailCommand',
    'MakeComponentCommand',
    'MakeProviderCommand',
    'MakeExceptionCommand',
    'MakeTransformerCommand',
    'MakeChannelCommand',
    'MakeTraitCommand',
    'MakeEnumCommand',
    'MakeCastCommand',
    'MakeFormCommand',
    'MakeInterfaceCommand',
    'MakeScopeCommand',
    'MakeDTOCommand',
    'DatabaseCommands',
    'QueueCommands',
    'CacheCommands',
    'ConfigCommands',
    'RouteListCommand',
    'RouteCacheCommands',
    'RoutePerformanceCommand', 
    'RouteSecurityCommand',
    'ScheduleCommands',
    'EventCommands',
    'NotificationCommands',
    'StorageCommands',
    'SessionCommands',
    'MaintenanceCommands',
    'HealthCheckCommand',
    'OptimizeCommand',
    'ServeCommand',
    'TinkerCommand',
    'TestCommands',
    'VendorCommands',
    'TranslationCommands',
    'EnvironmentCommands',
    'ConfigEncryptCommand',
    'ConfigValidateCommand',
    'KeyGenerateCommand',
    'JobRecoveryCommand',
    'ChainDebugCommand',
    'ExampleCommands',
    'SoftDeleteCommands',
    'GlobalScopeCommands',
    'AccessorMutatorCommands',
    'MigrationManagementCommands',
    'inspire',
    'make'
]

for module_name in command_modules:
    try:
        module_path = f"app.Console.Commands.{module_name}"
        importlib.import_module(module_path)
    except ImportError:
        continue  # Skip modules that fail to import