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
        # Implement index logic: query your model, apply filters, pagination
        # Example: resources = db.query(YourModel).limit(10).all()
        # return self.success_response(JsonResource.collection(resources))
        return self.success_response([], "Resources retrieved successfully")
    
    async def store(
        self,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Store a newly created resource."""
        # Implement store logic: validate request data, create new resource
        # Example: data = await request.json()
        # resource = YourModel(**data)
        # db.add(resource)
        # db.commit()
        # return self.success_response(JsonResource(resource).to_dict())
        return self.success_response(None, "Resource created successfully", 201)
    
    async def show(
        self,
        id: str,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Display the specified resource."""
        # Implement show logic: find resource by ID, handle not found
        # Example: resource = db.get(YourModel, id)
        # if not resource:
        #     raise HTTPException(status_code=404, detail="Resource not found")
        # return self.success_response(JsonResource(resource).to_dict())
        return self.success_response(None, "Resource retrieved successfully")
    
    async def update(
        self,
        id: str,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Update the specified resource."""
        # Implement update logic: find resource, validate data, update
        # Example: resource = db.get(YourModel, id)
        # if not resource:
        #     raise HTTPException(status_code=404, detail="Resource not found")
        # data = await request.json()
        # for key, value in data.items():
        #     setattr(resource, key, value)
        # db.commit()
        # return self.success_response(JsonResource(resource).to_dict())
        return self.success_response(None, "Resource updated successfully")
    
    async def destroy(
        self,
        id: str,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Remove the specified resource."""
        # Implement destroy logic: find resource, delete it
        # Example: resource = db.get(YourModel, id)
        # if not resource:
        #     raise HTTPException(status_code=404, detail="Resource not found")
        # db.delete(resource)
        # db.commit()
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
        # Implement your controller logic here
        # Add your business logic, database operations, etc.
        return self.success_response("Hello from {name}!")
'''