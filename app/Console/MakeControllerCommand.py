from __future__ import annotations

from typing import Optional
from pathlib import Path
from .Command import Command


class MakeControllerCommand(Command):
    """Command to generate a new controller."""
    
    signature = "make:controller {name} {--resource : Generate a resource controller}"
    description = "Create a new controller class"
    
    def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        if not name:
            self.error("Controller name is required")
            return
        
        is_resource = self.option("resource", False)
        
        # Ensure name ends with Controller
        if not name.endswith("Controller"):
            name += "Controller"
        
        controller_path = Path(f"app/Http/Controllers/{name}.py")
        
        if controller_path.exists():
            if not self.confirm(f"Controller {name} already exists. Overwrite?"):
                self.info("Controller creation cancelled.")
                return
        
        # Generate controller content
        content = self._generate_controller_content(name, is_resource)
        
        # Write the file
        controller_path.parent.mkdir(parents=True, exist_ok=True)
        controller_path.write_text(content)
        
        self.info(f"Controller {name} created successfully.")
        if is_resource:
            self.comment("Don't forget to register the routes for your resource controller!")
    
    def _generate_controller_content(self, name: str, is_resource: bool) -> str:
        """Generate the controller file content."""
        if is_resource:
            return f'''from __future__ import annotations

from typing import Any, Dict, List
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Http.Resources.JsonResource import JsonResource
from app.Http.Requests.FormRequest import BaseFormRequest
from config.database import get_db


class {name}(BaseController):
    """Resource controller for managing resources."""
    
    def __init__(self) -> None:
        super().__init__()
    
    async def index(
        self,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Display a listing of the resource."""
        # TODO: Implement index logic
        return self.success_response([], "Resources retrieved successfully")
    
    async def store(
        self,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Store a newly created resource."""
        # TODO: Implement store logic
        return self.success_response(None, "Resource created successfully", 201)
    
    async def show(
        self,
        id: str,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Display the specified resource."""
        # TODO: Implement show logic
        return self.success_response(None, "Resource retrieved successfully")
    
    async def update(
        self,
        id: str,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Update the specified resource."""
        # TODO: Implement update logic
        return self.success_response(None, "Resource updated successfully")
    
    async def destroy(
        self,
        id: str,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Remove the specified resource."""
        # TODO: Implement destroy logic
        return self.success_response(None, "Resource deleted successfully")
'''
        else:
            return f'''from __future__ import annotations

from typing import Any, Dict
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from config.database import get_db


class {name}(BaseController):
    """Controller for handling requests."""
    
    def __init__(self) -> None:
        super().__init__()
    
    async def index(
        self,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Handle the incoming request."""
        # TODO: Implement your logic here
        return self.success_response("Hello from {name}!")
'''