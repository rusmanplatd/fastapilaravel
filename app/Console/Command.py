from __future__ import annotations

from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
import argparse
import sys


class Command(ABC):
    """Laravel-style Artisan command base class."""
    
    # Command signature (to be overridden)
    signature: str = ""
    description: str = ""
    
    def __init__(self) -> None:
        self.arguments: Dict[str, Any] = {}
        self.options: Dict[str, Any] = {}
    
    @abstractmethod
    def handle(self) -> None:
        """Execute the command."""
        pass
    
    def argument(self, key: str, default: Any = None) -> Any:
        """Get an argument value."""
        return self.arguments.get(key, default)
    
    def option(self, key: str, default: Any = None) -> Any:
        """Get an option value."""
        return self.options.get(key, default)
    
    def ask(self, question: str, default: Optional[str] = None) -> str:
        """Ask a question and get user input."""
        prompt = f"{question}"
        if default:
            prompt += f" (default: {default})"
        prompt += ": "
        
        response = input(prompt).strip()
        return response if response else (default or "")
    
    def confirm(self, question: str, default: bool = False) -> bool:
        """Ask a yes/no question."""
        default_text = "Y/n" if default else "y/N"
        response = input(f"{question} ({default_text}): ").strip().lower()
        
        if not response:
            return default
        
        return response in ['y', 'yes', 'true', '1']
    
    def choice(self, question: str, choices: List[str], default: Optional[str] = None) -> str:
        """Ask to choose from a list of options."""
        print(f"{question}")
        for i, choice in enumerate(choices):
            marker = " (default)" if choice == default else ""
            print(f"  [{i}] {choice}{marker}")
        
        while True:
            try:
                response = input("Choose an option: ").strip()
                if not response and default:
                    return default
                
                index = int(response)
                if 0 <= index < len(choices):
                    return choices[index]
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                # Try string matching
                if response in choices:
                    return response
                print("Invalid choice. Please try again.")
    
    def info(self, message: str) -> None:
        """Display an info message."""
        print(f"ℹ️  {message}")
    
    def comment(self, message: str) -> None:
        """Display a comment message."""
        print(f"💬 {message}")
    
    def question(self, message: str) -> None:
        """Display a question message."""
        print(f"❓ {message}")
    
    def error(self, message: str) -> None:
        """Display an error message."""
        print(f"❌ {message}", file=sys.stderr)
    
    def warn(self, message: str) -> None:
        """Display a warning message."""
        print(f"⚠️  {message}")
    
    def line(self, message: str = "") -> None:
        """Display a line of text."""
        print(message)
    
    def new_line(self, count: int = 1) -> None:
        """Add new lines."""
        print("\n" * (count - 1))
    
    def table(self, headers: List[str], rows: List[List[str]]) -> None:
        """Display a table."""
        # Simple table implementation
        col_widths = [max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))]
        
        # Header
        header_row = " | ".join(str(headers[i]).ljust(col_widths[i]) for i in range(len(headers)))
        print(header_row)
        print("-" * len(header_row))
        
        # Rows
        for row in rows:
            data_row = " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row)))
            print(data_row)
    
    def progress_bar(self, total: int) -> ProgressBar:
        """Create a progress bar."""
        return ProgressBar(total)


class ProgressBar:
    """Simple progress bar for commands."""
    
    def __init__(self, total: int) -> None:
        self.total = total
        self.current = 0
    
    def advance(self, step: int = 1) -> None:
        """Advance the progress bar."""
        self.current += step
        self._display()
    
    def set_progress(self, progress: int) -> None:
        """Set the current progress."""
        self.current = progress
        self._display()
    
    def finish(self) -> None:
        """Finish the progress bar."""
        self.current = self.total
        self._display()
        print()  # New line after completion
    
    def _display(self) -> None:
        """Display the progress bar."""
        percent = (self.current / self.total) * 100
        filled = int(percent / 2)  # 50 chars max
        bar = "█" * filled + "░" * (50 - filled)
        print(f"\r[{bar}] {percent:.1f}% ({self.current}/{self.total})", end="", flush=True)


class CommandRegistry:
    """Registry for Artisan commands."""
    
    def __init__(self) -> None:
        self.commands: Dict[str, Command] = {}
    
    def register(self, name: str, command: Command) -> None:
        """Register a command."""
        self.commands[name] = command
    
    def get(self, name: str) -> Optional[Command]:
        """Get a command by name."""
        return self.commands.get(name)
    
    def all(self) -> Dict[str, Command]:
        """Get all registered commands."""
        return self.commands.copy()


# Global command registry
command_registry = CommandRegistry()