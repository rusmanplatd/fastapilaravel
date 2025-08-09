from __future__ import annotations

from pathlib import Path
from ..Command import Command


class MakeCommandCommand(Command):
    """Generate a new Artisan command."""
    
    signature = "make:command {name : The name of the command class}"
    description = "Create a new Artisan command class"
    help = "Generate a new console command class file"
    
    aliases = ["make:cmd"]
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        if not name:
            self.error("Command name is required")
            return
        
        # Ensure name ends with Command
        if not name.endswith("Command"):
            name += "Command"
        
        command_path = Path(f"app/Console/Commands/{name}.py")
        
        if command_path.exists():
            if not self.confirm(f"Command {name} already exists. Overwrite?"):
                self.info("Command creation cancelled.")
                return
        
        # Ask for command signature
        signature = self.ask("Enter the command signature (e.g., 'app:example {user}'):", "app:example")
        description = self.ask("Enter a description for the command:", "Example command")
        
        # Generate command content
        content = self._generate_command_content(name, signature, description)
        
        # Write the file
        command_path.parent.mkdir(parents=True, exist_ok=True)
        command_path.write_text(content)
        
        self.info(f"Command {name} created successfully.")
        self.comment(f"Location: {command_path}")
        self.comment(f"Run with: python artisan.py {signature.split()[0]}")
    
    def _generate_command_content(self, name: str, signature: str, description: str) -> str:
        """Generate the command file content."""
        return f'''from __future__ import annotations

from ..Command import Command


class {name}(Command):
    """Generated Artisan command."""
    
    signature = "{signature}"
    description = "{description}"
    help = "Auto-generated command - update this help text"
    
    async def handle(self) -> None:
        """Execute the command."""
        self.info("Hello from {name}!")
        
        # Example: Get arguments and options
        # arg_value = self.argument("arg_name")
        # option_value = self.option("option_name", "default")
        
        # Example: User interaction
        # name = self.ask("What is your name?", "User")
        # confirmed = self.confirm("Are you sure?", True)
        
        # Example: Display output
        # self.info("This is an info message")
        # self.comment("This is a comment")
        # self.warn("This is a warning")
        # self.error("This is an error")
        
        # Example: Progress bar
        # items = list(range(10))
        # self.with_progress_bar(items, lambda x: self.line(f"Processing {{x}}"))
        
        # Example: Table output
        # headers = ["ID", "Name", "Status"]
        # rows = [["1", "Item 1", "Active"], ["2", "Item 2", "Inactive"]]
        # self.table(headers, rows)
        
        self.info("Command executed successfully!")
'''
# Register the command
from app.Console.Artisan import register_command
register_command(MakeCommandCommand)
