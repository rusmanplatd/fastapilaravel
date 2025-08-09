#!/usr/bin/env python3
"""
Simple test script for the enhanced Artisan command system
"""

from __future__ import annotations
import sys
import asyncio
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import only the commands we need for testing
from app.Console.Command import Command
from app.Console.Kernel import Artisan


class TestGreetCommand(Command):
    """Test greeting command."""
    
    signature = "test:greet {name : The name to greet} {--shout : Shout the greeting}"
    description = "Test greeting command"
    
    async def handle(self) -> None:
        """Execute the greeting."""
        name = self.argument("name")
        shout = self.option("shout", False)
        
        greeting = f"Hello, {name}!"
        if shout:
            greeting = greeting.upper()
        
        self.info(greeting)


class TestInteractiveCommand(Command):
    """Test interactive command."""
    
    signature = "test:interactive"
    description = "Test interactive features"
    
    async def handle(self) -> None:
        """Execute interactive test."""
        self.info("Testing interactive features...")
        
        name = self.ask("What is your name?", "Anonymous")
        self.info(f"Hello, {name}!")
        
        color = self.choice("Pick a color:", ["Red", "Blue", "Green"], "Blue")
        self.comment(f"You chose {color}")
        
        if self.confirm("Continue?", True):
            self.info("Continuing...")
        else:
            self.warn("Stopping.")


def main() -> int:
    """Test the enhanced Artisan system."""
    # Create a minimal Artisan instance
    artisan = Artisan()
    
    # Clear auto-discovered commands to avoid import issues
    artisan.commands.clear()
    artisan.aliases.clear()
    
    # Manually register test commands
    artisan.register(TestGreetCommand())
    artisan.register(TestInteractiveCommand())
    
    # Run the command system
    return asyncio.run(artisan.run())


if __name__ == "__main__":
    sys.exit(main())