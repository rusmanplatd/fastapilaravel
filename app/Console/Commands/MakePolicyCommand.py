from __future__ import annotations

from pathlib import Path
from ..Command import Command


class MakePolicyCommand(Command):
    """Generate a new policy class."""
    
    signature = "make:policy {name : The name of the policy} {--model= : The model for the policy}"
    description = "Create a new policy class"
    help = "Generate a new authorization policy class"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        model_name = self.option("model")
        
        if not name:
            self.error("Policy name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Policy"):
            name += "Policy"
        
        # Determine model name
        if not model_name:
            model_name = name.replace("Policy", "")
        
        policy_path = Path(f"app/Policies/{name}.py")
        policy_path.parent.mkdir(parents=True, exist_ok=True)
        
        if policy_path.exists():
            if not self.confirm(f"Policy {name} already exists. Overwrite?"):
                self.info("Policy creation cancelled.")
                return
        
        content = self._generate_policy_content(name, model_name)
        policy_path.write_text(content)
        
        self.info(f"✅ Policy created: {policy_path}")
        self.comment("Register the policy in your authorization configuration")
        self.comment("Update the methods with your authorization logic")
    
    def _generate_policy_content(self, policy_name: str, model_name: str) -> str:
        """Generate policy content."""
        return f'''from __future__ import annotations

from typing import Optional
from app.Models.User import User
from app.Models.{model_name} import {model_name}
from app.Policies.Policy import Policy


class {policy_name}(Policy):
    """Authorization policy for {model_name} model."""
    
    def view_any(self, user: Optional[User]) -> bool:
        """Determine whether the user can view any models."""
        # Example: return user is not None and user.can("view_{model_name.lower()}s")
        return True
    
    def view(self, user: Optional[User], model: {model_name}) -> bool:
        """Determine whether the user can view the model."""
        # Example: return user is not None and (user.id == model.user_id or user.can("view_{model_name.lower()}"))
        return True
    
    def create(self, user: Optional[User]) -> bool:
        """Determine whether the user can create models."""
        # Example: return user is not None and user.can("create_{model_name.lower()}")
        return True
    
    def update(self, user: Optional[User], model: {model_name}) -> bool:
        """Determine whether the user can update the model."""
        # Example: return user is not None and (user.id == model.user_id or user.can("edit_{model_name.lower()}"))
        return True
    
    def delete(self, user: Optional[User], model: {model_name}) -> bool:
        """Determine whether the user can delete the model."""
        # Example: return user is not None and (user.id == model.user_id or user.can("delete_{model_name.lower()}"))
        return True
    
    def restore(self, user: Optional[User], model: {model_name}) -> bool:
        """Determine whether the user can restore the model."""
        # Example: return user is not None and user.can("restore_{model_name.lower()}")
        return False
    
    def force_delete(self, user: Optional[User], model: {model_name}) -> bool:
        """Determine whether the user can permanently delete the model."""
        # Example: return user is not None and user.can("force_delete_{model_name.lower()}")
        return False
    
    # Custom authorization methods
    def publish(self, user: Optional[User], model: {model_name}) -> bool:
        """Determine whether the user can publish the model."""
        # Example: return user is not None and user.can("publish_{model_name.lower()}")
        return False
    
    def unpublish(self, user: Optional[User], model: {model_name}) -> bool:
        """Determine whether the user can unpublish the model."""
        # Example: return user is not None and user.can("unpublish_{model_name.lower()}")
        return False
    
    def moderate(self, user: Optional[User], model: {model_name}) -> bool:
        """Determine whether the user can moderate the model."""
        # Example: return user is not None and user.has_role("moderator")
        return False
    
    # Helper methods
    def is_owner(self, user: Optional[User], model: {model_name}) -> bool:
        """Check if user is the owner of the model."""
        return user is not None and hasattr(model, "user_id") and user.id == model.user_id
    
    def is_admin(self, user: Optional[User]) -> bool:
        """Check if user is an admin."""
        return user is not None and user.has_role("admin")
    
    def is_moderator(self, user: Optional[User]) -> bool:
        """Check if user is a moderator."""
        return user is not None and user.has_role("moderator")
'''


class MakeRuleCommand(Command):
    """Generate a new validation rule class."""
    
    signature = "make:rule {name : The name of the validation rule}"
    description = "Create a new validation rule class"
    help = "Generate a new custom validation rule class"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        
        if not name:
            self.error("Rule name is required")
            return
        
        # Format rule name (convert to camelCase)
        rule_name = ''.join(word.capitalize() for word in name.split('_'))
        
        rule_path = Path(f"app/Validation/Rules/{rule_name}.py")
        rule_path.parent.mkdir(parents=True, exist_ok=True)
        
        if rule_path.exists():
            if not self.confirm(f"Rule {rule_name} already exists. Overwrite?"):
                self.info("Rule creation cancelled.")
                return
        
        content = self._generate_rule_content(rule_name)
        rule_path.write_text(content)
        
        self.info(f"✅ Validation rule created: {rule_path}")
        self.comment("Update the passes() and message() methods")
        self.comment(f"Use with: rules = ['{name}']")
    
    def _generate_rule_content(self, rule_name: str) -> str:
        """Generate validation rule content."""
        return f'''from __future__ import annotations

from typing import Any, Optional
from app.Validation.Rules.Rule import Rule


class {rule_name}(Rule):
    """Custom validation rule."""
    
    def __init__(self, *args, **kwargs) -> None:
        """Initialize the rule."""
        # Store rule parameters here
        # Example:
        # self.min_value = args[0] if args else 0
        # self.max_value = args[1] if len(args) > 1 else 100
        pass
    
    def passes(self, attribute: str, value: Any) -> bool:
        """Determine if the validation rule passes."""
        try:
            # Basic validation implementation
            if value is None:
                return False
            
            # String validation
            if isinstance(value, str):
                # Check if not empty
                if not value.strip():
                    return False
                
                # Basic format validation (alphanumeric with underscores)
                import re
                if not re.match(r'^[a-zA-Z0-9_\\s\\-\\.]+$', value):
                    return False
            
            # Numeric validation
            elif isinstance(value, (int, float)):
                # Check for reasonable numeric ranges
                if not (-1000000 <= value <= 1000000):
                    return False
            
            # List/Dict validation
            elif isinstance(value, (list, dict)):
                # Check size limits
                if len(value) > 1000:
                    return False
            
            return True
            
        except Exception:
            # If validation fails for any reason, consider it invalid
            return False
    
    def message(self) -> str:
        """Get the validation error message."""
        return "The :attribute field is invalid."
    
    def __str__(self) -> str:
        """String representation of the rule."""
        return f"{self.__class__.__name__}"
    
    # Optional: Custom error message with parameters
    def message_with_params(self, attribute: str, value: Any) -> str:
        """Get a customized error message."""
        # Example:
        # return f"The {{attribute}} must be between {{self.min_value}} and {{self.max_value}}."
        return self.message().replace(":attribute", attribute)
'''


class MakeTestCommand(Command):
    """Generate a new test class."""
    
    signature = "make:test {name : The name of the test} {--unit : Create a unit test} {--feature : Create a feature test}"
    description = "Create a new test class"
    help = "Generate a new test class for testing"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        is_unit = self.option("unit", False)
        is_feature = self.option("feature", False)
        
        if not name:
            self.error("Test name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Test"):
            name += "Test"
        
        # Determine test type and path
        if is_unit:
            test_type = "unit"
            test_path = Path(f"tests/Unit/{name}.py")
        elif is_feature:
            test_type = "feature"
            test_path = Path(f"tests/Feature/{name}.py")
        else:
            # Ask user for test type
            test_type_result = self.choice("Test type:", ["unit", "feature"], "feature")
            test_type = test_type_result if isinstance(test_type_result, str) else test_type_result[0]
            if test_type == "unit":
                test_path = Path(f"tests/Unit/{name}.py")
            else:
                test_path = Path(f"tests/Feature/{name}.py")
        
        test_path.parent.mkdir(parents=True, exist_ok=True)
        
        if test_path.exists():
            if not self.confirm(f"Test {name} already exists. Overwrite?"):
                self.info("Test creation cancelled.")
                return
        
        content = self._generate_test_content(name, test_type)
        test_path.write_text(content)
        
        self.info(f"✅ Test created: {test_path}")
        self.comment(f"Run with: pytest {test_path}")
    
    def _generate_test_content(self, test_name: str, test_type: str) -> str:
        """Generate test content."""
        if test_type == "unit":
            imports = """import pytest
from unittest.mock import Mock, patch
from app.Testing.TestCase import TestCase"""
            
            base_class = "TestCase"
            test_methods = """
    def test_example(self) -> None:
        \"\"\"Test example functionality.\"\"\"
        # Arrange
        # Set up your test data and mocks
        
        # Act
        # Execute the code you want to test
        result = True  # Replace with actual code
        
        # Assert
        # Verify the results
        assert result is True
    
    def test_with_mock(self) -> None:
        \"\"\"Test with mocked dependencies.\"\"\"
        with patch('app.Services.SomeService') as mock_service:
            # Configure the mock
            mock_service.return_value.some_method.return_value = "mocked_result"
            
            # Test your code
            # result = your_function_that_uses_service()
            
            # Assertions
            # assert result == "expected_result"
            # mock_service.return_value.some_method.assert_called_once()
            pass
    
    def test_exception_handling(self) -> None:
        \"\"\"Test exception handling.\"\"\"
        with pytest.raises(ValueError) as exc_info:
            # Code that should raise ValueError
            pass
        
        # assert str(exc_info.value) == "Expected error message"
"""
        else:
            imports = """import pytest
from httpx import AsyncClient
from app.Testing.TestCase import TestCase"""
            
            base_class = "TestCase"
            test_methods = """
    async def test_endpoint_success(self) -> None:
        \"\"\"Test successful API endpoint response.\"\"\"
        async with AsyncClient(app=self.app, base_url="http://test") as client:
            response = await client.get("/api/endpoint")
            
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
    
    async def test_endpoint_authentication_required(self) -> None:
        \"\"\"Test that authentication is required.\"\"\"
        async with AsyncClient(app=self.app, base_url="http://test") as client:
            response = await client.post("/api/protected-endpoint")
            
            assert response.status_code == 401
    
    async def test_endpoint_with_authenticated_user(self) -> None:
        \"\"\"Test endpoint with authenticated user.\"\"\"
        user = await self.create_user()
        
        async with AsyncClient(app=self.app, base_url="http://test") as client:
            # Set authentication headers
            headers = {"Authorization": f"Bearer {self.get_access_token(user)}"}
            response = await client.get("/api/user/profile", headers=headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == user.id
    
    async def test_endpoint_validation(self) -> None:
        \"\"\"Test endpoint input validation.\"\"\"
        async with AsyncClient(app=self.app, base_url="http://test") as client:
            # Test with invalid data
            invalid_data = {"field": ""}
            response = await client.post("/api/endpoint", json=invalid_data)
            
            assert response.status_code == 422
            errors = response.json()
            assert "field" in errors["detail"]
"""
        
        return f'''from __future__ import annotations

{imports}


class {test_name}({base_class}):
    """Test class for testing functionality."""
    
    def setup_method(self) -> None:
        """Set up test dependencies before each test method."""
        # Initialize test data, mocks, etc.
        pass
    
    def teardown_method(self) -> None:
        """Clean up after each test method."""
        # Clean up test data, reset mocks, etc.
        pass
{test_methods}
    
    # Helper methods
    async def create_user(self, **kwargs):
        \"\"\"Helper method to create a test user.\"\"\"
        # Create and return a test user
        pass
    
    def get_access_token(self, user):
        \"\"\"Helper method to get access token for user.\"\"\"
        # Generate and return access token for user
        pass
'''


class MakeCommandCommand(Command):
    """Generate a new Artisan command class."""
    
    signature = "make:command {name : The name of the command} {--signature= : The command signature}"
    description = "Create a new Artisan command class"
    help = "Generate a new Artisan command class"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        signature = self.option("signature")
        
        if not name:
            self.error("Command name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Command"):
            name += "Command"
        
        # Generate default signature if not provided
        if not signature:
            command_name = name.replace("Command", "").lower()
            signature = f"{command_name} {{argument : Description of argument}}"
        
        command_path = Path(f"app/Console/Commands/{name}.py")
        command_path.parent.mkdir(parents=True, exist_ok=True)
        
        if command_path.exists():
            if not self.confirm(f"Command {name} already exists. Overwrite?"):
                self.info("Command creation cancelled.")
                return
        
        content = self._generate_command_content(name, signature)
        command_path.write_text(content)
        
        self.info(f"✅ Command created: {command_path}")
        self.comment("Update the handle() method with your command logic")
        self.comment("The command will be auto-discovered by the Artisan kernel")
    
    def _generate_command_content(self, command_name: str, signature: str) -> str:
        """Generate command content."""
        return f'''from __future__ import annotations

from typing import Any
from app.Console.Command import Command


class {command_name}(Command):
    """Custom Artisan command."""
    
    signature = "{signature}"
    description = "Custom command description"
    help = "Detailed help text for the command"
    
    # Optional command aliases
    aliases = ["shortcut"]
    
    async def handle(self) -> None:
        """Execute the command."""
        # Get command arguments and options
        # argument_value = self.argument("argument")
        # option_value = self.option("option", "default_value")
        
        # Command logic goes here
        self.info("Command executed successfully!")
        
        # Available output methods:
        # self.line("Regular output")
        # self.info("Info message")
        # self.comment("Comment message")
        # self.question("Question message")
        # self.error("Error message")
        # self.warn("Warning message")
        # self.new_line()  # Print empty line
        
        # Interactive methods:
        # answer = self.ask("What is your name?", "default")
        # secret = self.secret("Enter password:")
        # confirmed = self.confirm("Are you sure?", True)
        # choice = self.choice("Select option:", ["option1", "option2"], "option1")
        
        # Progress bar:
        # with self.progress_bar(100, "Processing...") as progress:
        #     for i in range(100):
        #         # Do work
        #         progress.advance()
        
        # Call other commands:
        # await self.call("another:command", {{"argument": "value", "--option": True}})
        
        # Examples of command logic:
        
        # 1. Database operations
        # from config.database import get_db
        # db = next(get_db())
        # users = db.query(User).all()
        # self.info(f"Found {{len(users)}} users")
        
        # 2. File operations
        # from pathlib import Path
        # file_path = Path("output.txt")
        # file_path.write_text("Command output")
        # self.info(f"Created file: {{file_path}}")
        
        # 3. API calls
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     response = await client.get("https://api.example.com/data")
        #     self.info(f"API Response: {{response.status_code}}")
        
        # 4. Queue jobs
        # from app.Jobs.ExampleJob import ExampleJob
        # job_id = ExampleJob.dispatch("data")
        # self.info(f"Queued job: {{job_id}}")
'''
# Register the command
from app.Console.Artisan import register_command
register_command(MakePolicyCommand)
