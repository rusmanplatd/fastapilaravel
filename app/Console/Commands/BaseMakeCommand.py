from __future__ import annotations

import re
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from ..Command import Command


class BaseMakeCommand(Command):
    """Base class for all make:* commands with standardized error handling."""
    
    # Override in subclasses
    stub_path: str = ""
    file_type: str = "file"
    
    def __init__(self) -> None:
        super().__init__()
    
    async def create_file(self, name: str, content: str, file_path: Path, 
                         force: bool = False, executable: bool = False) -> bool:
        """Standardized file creation with error handling."""
        try:
            # Validate file name
            if not self._is_valid_name(name):
                self.error(f"Invalid {self.file_type} name: {name}")
                self.comment("Names should use PascalCase and contain only letters, numbers, and underscores.")
                return False
            
            # Check if directory exists and create if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file already exists
            if file_path.exists() and not force:
                if not self.confirm(f"{self.file_type} {name} already exists. Overwrite?"):
                    self.info(f"{self.file_type} creation cancelled.")
                    return False
            
            # Validate generated content syntax (basic check)
            if not self._validate_syntax(content):
                self.error("Generated code contains syntax errors.")
                return False
            
            # Write the file
            file_path.write_text(content)
            
            # Set permissions if executable
            if executable:
                os.chmod(file_path, 0o755)
            
            self.info(f"✅ {self.file_type} created: {file_path}")
            return True
            
        except PermissionError:
            self.error(f"Permission denied: Cannot create {file_path}")
            self.comment("Check directory permissions and try again.")
            return False
        except OSError as e:
            self.error(f"File system error: {e}")
            return False
        except Exception as e:
            self.error(f"Failed to create {self.file_type}: {e}")
            return False
    
    def _is_valid_name(self, name: str) -> bool:
        """Validate the name follows conventions."""
        # Remove common suffixes for validation
        clean_name = name
        suffixes = ['Controller', 'Service', 'Model', 'Command', 'Request', 
                   'Resource', 'Policy', 'Observer', 'Job', 'Factory', 'Seeder']
        
        for suffix in suffixes:
            if clean_name.endswith(suffix):
                clean_name = clean_name[:-len(suffix)]
                break
        
        # Check if name is valid Python identifier
        if not clean_name.replace('_', '').replace('-', '').isalnum():
            return False
        
        # Check if starts with letter
        if clean_name and not clean_name[0].isalpha():
            return False
        
        return True
    
    def _validate_syntax(self, content: str) -> bool:
        """Basic syntax validation of generated Python code."""
        try:
            # Try to compile the code to check for syntax errors
            compile(content, '<generated>', 'exec')
            return True
        except SyntaxError as e:
            self.warn(f"Syntax error detected: {e}")
            return False
        except Exception:
            # Other compilation errors, but might still be valid
            return True
    
    def _format_class_name(self, name: str) -> str:
        """Format name to proper PascalCase."""
        # Handle different input formats
        name = name.replace('-', '_').replace(' ', '_')
        
        # Convert to PascalCase
        parts = name.split('_')
        return ''.join(part.capitalize() for part in parts if part)
    
    def _format_file_name(self, name: str) -> str:
        """Format name for file system."""
        # Ensure proper extension
        if not name.endswith('.py'):
            name += '.py'
        return name
    
    def _get_template_variables(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        """Get template variables for file generation."""
        return {
            'class_name': self._format_class_name(name),
            'file_name': self._format_file_name(name),
            'timestamp': self._get_timestamp(),
            **kwargs
        }
    
    def _get_timestamp(self) -> str:
        """Get formatted timestamp."""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _load_stub(self, stub_name: str) -> Optional[str]:
        """Load content from stub file."""
        if not self.stub_path:
            return None
        
        try:
            stub_file = Path(self.stub_path) / f"{stub_name}.stub"
            if stub_file.exists():
                return stub_file.read_text()
        except Exception:
            pass
        
        return None
    
    def _replace_placeholders(self, content: str, variables: Dict[str, Any]) -> str:
        """Replace placeholder variables in content."""
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"  # {{ and }} for literal braces
            content = content.replace(placeholder, str(value))
        
        return content
    
    def _show_next_steps(self, file_path: Path, additional_steps: Optional[List[str]] = None) -> None:
        """Show standardized next steps to user."""
        self.new_line()
        self.comment("Next steps:")
        self.line(f"1. Edit {file_path} to implement your logic")
        
        if additional_steps:
            for i, step in enumerate(additional_steps, 2):
                self.line(f"{i}. {step}")
        
        # Add common suggestions based on file type
        if "Controller" in str(file_path):
            self.line("• Register routes in your router")
            self.line("• Add request validation if needed")
        elif "Model" in str(file_path):
            self.line("• Run migrations to create the database table")
            self.line("• Define relationships with other models")
        elif "Service" in str(file_path):
            self.line("• Inject the service into controllers or other services")
        
        self.comment(f"File location: {file_path}")
    
    async def _validate_dependencies(self, dependencies: List[str]) -> bool:
        """Validate that required dependencies exist."""
        missing = []
        
        for dep in dependencies:
            dep_path = Path(dep)
            if not dep_path.exists():
                missing.append(dep)
        
        if missing:
            self.error("Missing dependencies:")
            for dep in missing:
                self.line(f"  • {dep}")
            self.comment("Create the missing files first, then retry this command.")
            return False
        
        return True
    
    def _ask_for_options(self) -> Dict[str, Any]:
        """Interactive prompts for common options."""
        options: Dict[str, Any] = {}
        
        # This can be overridden in subclasses for specific prompts
        return options
    
    def _generate_import_statements(self, imports: List[str]) -> str:
        """Generate properly formatted import statements."""
        if not imports:
            return "from __future__ import annotations\n"
        
        # Separate future imports, standard library, third-party, and local imports
        future_imports = []
        std_imports = []
        third_party_imports = []
        local_imports = []
        
        for imp in imports:
            if imp.startswith("from __future__"):
                future_imports.append(imp)
            elif imp.startswith("from app.") or imp.startswith("from config.") or imp.startswith("from database."):
                local_imports.append(imp)
            elif any(lib in imp for lib in ['typing', 'datetime', 'pathlib', 'os', 'sys']):
                std_imports.append(imp)
            else:
                third_party_imports.append(imp)
        
        # Build import section
        import_sections = []
        
        if not future_imports:
            future_imports = ["from __future__ import annotations"]
        
        import_sections.append("\n".join(future_imports))
        
        if std_imports:
            import_sections.append("\n".join(sorted(std_imports)))
        
        if third_party_imports:
            import_sections.append("\n".join(sorted(third_party_imports)))
        
        if local_imports:
            import_sections.append("\n".join(sorted(local_imports)))
        
        return "\n\n".join(import_sections) + "\n"