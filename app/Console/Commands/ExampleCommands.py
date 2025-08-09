from __future__ import annotations

import asyncio
import random
from typing import List, Any
from datetime import datetime

from ..Command import Command


class GreetingCommand(Command):
    """Example command demonstrating basic features."""
    
    signature = "example:greet {name : The name to greet} {--shout : Shout the greeting} {--repeat=1 : Number of times to repeat}"
    description = "Greet a user with various options"
    help = "This command demonstrates basic argument and option handling"
    
    async def handle(self) -> None:
        """Execute the greeting command."""
        name = self.argument("name")
        shout = self.option("shout", False)
        repeat = int(self.option("repeat", 1))
        
        greeting = f"Hello, {name}!"
        
        if shout:
            greeting = greeting.upper()
        
        for i in range(repeat):
            if repeat > 1:
                self.info(f"#{i+1}: {greeting}")
            else:
                self.info(greeting)


class InteractiveCommand(Command):
    """Example command demonstrating user interaction."""
    
    signature = "example:interactive"
    description = "Demonstrate interactive user input"
    help = "This command shows various ways to get user input"
    
    async def handle(self) -> None:
        """Execute the interactive command."""
        self.info("Interactive Command Example")
        self.line("=" * 40)
        
        # Basic question
        name = self.ask("What is your name?", "Anonymous")
        self.info(f"Nice to meet you, {name}!")
        
        # Choice question
        color = self.choice(
            "What is your favorite color?",
            ["Red", "Green", "Blue", "Yellow"],
            "Blue"
        )
        self.comment(f"Great choice! {color} is a wonderful color.")
        
        # Confirmation
        if self.confirm("Would you like to continue?", True):
            self.info("Continuing...")
        else:
            self.warn("Stopping here.")
            return
        
        # Secret input
        if self.confirm("Would you like to enter a secret password?"):
            password = self.secret("Enter your secret password")
            self.info(f"Your password has {len(password)} characters.")
        
        # Anticipate with suggestions
        framework = self.anticipate(
            "What's your favorite Python web framework?",
            ["FastAPI", "Django", "Flask", "Tornado", "Starlette"]
        )
        self.info(f"Excellent choice! {framework} is a great framework.")
        
        self.new_line()
        self.info("Interactive demo completed!")


class ProgressCommand(Command):
    """Example command demonstrating progress bars."""
    
    signature = "example:progress {--items=100 : Number of items to process} {--delay=0.1 : Delay between items in seconds}"
    description = "Demonstrate progress bar functionality"
    help = "This command shows how to use progress bars for long-running tasks"
    
    async def handle(self) -> None:
        """Execute the progress command."""
        items = int(self.option("items", 100))
        delay = float(self.option("delay", 0.1))
        
        self.info(f"Processing {items} items with {delay}s delay...")
        
        # Manual progress bar
        self.comment("Manual progress bar:")
        bar = self.progress_bar(items)
        
        for i in range(items):
            # Simulate work
            await asyncio.sleep(delay)
            bar.advance()
        
        bar.finish()
        self.new_line()
        
        # Progress bar with collection
        self.comment("Automated progress bar with collection:")
        data = list(range(items))
        
        async def process_item(item: int) -> str:
            await asyncio.sleep(delay / 10)  # Faster for demo
            return f"Processed item {item}"
        
        # Create a sync wrapper for the async function
        def process_item_sync(item: int) -> str:
            return f"Processed item {item}"
        
        results = self.with_progress_bar(data, process_item_sync)
        
        self.new_line()
        self.info(f"Successfully processed {len(results)} items!")


class TableCommand(Command):
    """Example command demonstrating table output."""
    
    signature = "example:table {--format=default : Table format (default|compact|minimal)}"
    description = "Demonstrate table output formatting"
    help = "This command shows how to display data in table format"
    
    async def handle(self) -> None:
        """Execute the table command."""
        self.info("Table Output Example")
        self.line("=" * 40)
        
        # Sample data
        users = [
            ["1", "John Doe", "john@example.com", "Admin", "Active"],
            ["2", "Jane Smith", "jane@example.com", "User", "Active"],
            ["3", "Bob Johnson", "bob@example.com", "Moderator", "Inactive"],
            ["4", "Alice Brown", "alice@example.com", "User", "Active"],
            ["5", "Charlie Wilson", "charlie@example.com", "User", "Pending"],
        ]
        
        headers = ["ID", "Name", "Email", "Role", "Status"]
        
        self.comment("User Management Table:")
        self.table(headers, users)
        
        self.new_line()
        
        # Another table example
        stats = [
            ["Total Users", "5"],
            ["Active Users", "3"],
            ["Inactive Users", "1"],
            ["Pending Users", "1"],
            ["Admin Users", "1"],
        ]
        
        self.comment("Statistics Summary:")
        self.table(["Metric", "Value"], stats)


class SignalCommand(Command):
    """Example command demonstrating signal handling."""
    
    signature = "example:signals {--duration=30 : How long to run in seconds}"
    description = "Demonstrate signal handling"
    help = "This command shows how to handle system signals gracefully"
    
    async def handle(self) -> None:
        """Execute the signal command."""
        import signal
        
        duration = int(self.option("duration", 30))
        
        self.info(f"Running for {duration} seconds. Press Ctrl+C to stop gracefully.")
        
        # Set up signal handler
        def signal_handler(sig_num: int) -> None:
            signal_name = signal.Signals(sig_num).name
            self.warn(f"Received {signal_name} signal. Stopping gracefully...")
            self._should_keep_running = False
        
        self.trap([signal.SIGTERM, signal.SIGINT], signal_handler)
        
        start_time = datetime.now()
        counter = 0
        
        while self._should_keep_running:
            elapsed = (datetime.now() - start_time).seconds
            if elapsed >= duration:
                break
            
            counter += 1
            self.line(f"Working... ({counter}) - {elapsed}s elapsed")
            await asyncio.sleep(1)
        
        if self._should_keep_running:
            self.info("Command completed normally.")
        else:
            self.info("Command stopped by signal.")


class CallCommand(Command):
    """Example command demonstrating calling other commands."""
    
    signature = "example:call"
    description = "Demonstrate calling other commands"
    help = "This command shows how to call other Artisan commands"
    
    async def handle(self) -> None:
        """Execute the call command."""
        self.info("Calling Other Commands Example")
        self.line("=" * 40)
        
        # Call another command
        self.comment("Calling the greeting command...")
        await self.call("example:greet", {"name": "World", "--shout": True})
        
        self.new_line()
        
        # Call a command silently
        self.comment("Calling a command silently (no output)...")
        result = self.call_silently("example:greet", {"name": "Silent User"})
        self.info(f"Silent command returned: {result}")
        
        self.new_line()
        self.info("Command calling demonstration completed!")


class ValidationCommand(Command):
    """Example command demonstrating input validation."""
    
    signature = "example:validate"
    description = "Demonstrate input validation"
    help = "This command shows various input validation techniques"
    
    async def handle(self) -> None:
        """Execute the validation command."""
        self.info("Input Validation Example")
        self.line("=" * 40)
        
        # Email validation
        def is_valid_email(email: str) -> bool:
            import re
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
            return re.match(pattern, email) is not None
        
        email = self.ask(
            "Enter your email address",
            validate=is_valid_email
        )
        self.info(f"Valid email: {email}")
        
        # Number validation
        def is_positive_number(value: str) -> bool:
            try:
                return int(value) > 0
            except ValueError:
                return False
        
        number = self.ask(
            "Enter a positive number",
            validate=is_positive_number
        )
        self.info(f"Valid number: {number}")
        
        # Multiple choice with validation
        languages = self.choice(
            "Select your programming languages (you can choose multiple)",
            ["Python", "JavaScript", "Go", "Rust", "Java", "C++"],
            multiple=True
        )
        self.info(f"Selected languages: {', '.join(languages)}")


class ErrorHandlingCommand(Command):
    """Example command demonstrating error handling."""
    
    signature = "example:errors {--fail : Force the command to fail} {--error-type=generic : Type of error to demonstrate}"
    description = "Demonstrate error handling patterns"
    help = "This command shows different error handling approaches"
    
    async def handle(self) -> None:
        """Execute the error handling command."""
        should_fail = self.option("fail", False)
        error_type = self.option("error-type", "generic")
        
        self.info("Error Handling Example")
        self.line("=" * 40)
        
        if not should_fail:
            self.info("Command executed successfully!")
            self.comment("Use --fail to see error handling in action")
            return
        
        # Demonstrate different error types
        if error_type == "validation":
            self.error("Validation failed: Invalid input provided")
            self.fail("Command failed due to validation errors", 2)
        elif error_type == "network":
            self.error("Network error: Could not connect to remote server")
            self.fail("Command failed due to network issues", 3)
        elif error_type == "permission":
            self.error("Permission error: Access denied")
            self.fail("Command failed due to insufficient permissions", 4)
        else:
            self.error("An unexpected error occurred")
            self.fail("Command failed with generic error", 1)


class LongRunningCommand(Command):
    """Example command for long-running processes."""
    
    signature = "example:long-running {--workers=3 : Number of worker processes} {--duration=60 : Duration to run}"
    description = "Simulate a long-running process"
    help = "This command simulates long-running background processes"
    
    async def handle(self) -> None:
        """Execute the long-running command."""
        workers = int(self.option("workers", 3))
        duration = int(self.option("duration", 60))
        
        self.info(f"Starting {workers} workers for {duration} seconds...")
        
        async def worker(worker_id: int) -> None:
            start_time = datetime.now()
            processed = 0
            
            while (datetime.now() - start_time).seconds < duration:
                # Simulate work
                await asyncio.sleep(random.uniform(0.5, 2.0))
                processed += 1
                
                if processed % 5 == 0:  # Log every 5 items
                    elapsed = (datetime.now() - start_time).seconds
                    self.comment(f"Worker {worker_id}: Processed {processed} items in {elapsed}s")
            
            self.info(f"Worker {worker_id} completed: {processed} items processed")
        
        # Start all workers
        tasks = [worker(i + 1) for i in range(workers)]
        
        try:
            await asyncio.gather(*tasks)
            self.info("All workers completed successfully!")
        except KeyboardInterrupt:
            self.warn("Workers interrupted by user")
            self.fail("Process interrupted", 130)
# Register commands 
from app.Console.Artisan import register_command

register_command(GreetingCommand)
register_command(InteractiveCommand) 
register_command(ProgressCommand)
register_command(TableCommand)
register_command(SignalCommand)
