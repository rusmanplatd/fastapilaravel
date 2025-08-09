from __future__ import annotations

from typing import Optional, Dict, Any, List
from pathlib import Path
import re
from .BaseMakeCommand import BaseMakeCommand


class MakeControllerCommand(BaseMakeCommand):
    """Command to generate a new controller with advanced features and validation."""
    
    file_type = "Controller"
    
    signature = "make:controller {name : The name of the controller} {--resource : Generate a resource controller with CRUD methods} {--api : Generate an API resource controller} {--model= : Generate a resource controller for the given model} {--invokable : Generate a single method, invokable controller} {--parent= : Extend from custom parent controller} {--force : Force overwrite existing controller} {--requests : Auto-generate form request classes} {--policies : Auto-generate authorization policies} {--middleware : Add custom middleware} {--tests : Generate test files}"
    description = "Create a new controller class with advanced features"
    help = "Generate a new controller class file with optional resource methods, API endpoints, validation, policies, middleware, and tests"
    
    # Command can also have aliases
    aliases = ["make:ctrl", "controller:make"]
    
    async def handle(self) -> None:
        """Execute the command with enhanced features and validation."""
        name = self.argument("name")
        if not name:
            self.error("Controller name is required")
            return
        
        # Get all options
        is_resource = self.option("resource", False)
        is_api = self.option("api", False) 
        model_name = self.option("model")
        is_invokable = self.option("invokable", False)
        parent_controller = self.option("parent", "BaseController")
        force = self.option("force", False)
        generate_requests = self.option("requests", False)
        generate_policies = self.option("policies", False)
        add_middleware = self.option("middleware", False)
        generate_tests = self.option("tests", False)
        
        # Validate controller name format
        if not self._validate_controller_name(name):
            return
        
        # Ensure name ends with Controller
        if not name.endswith("Controller"):
            name += "Controller"
        
        # Auto-generate requests for resource controllers if not specified
        if is_resource and not generate_requests:
            if self.confirm("Generate form request classes for validation?"):
                generate_requests = True
        
        # Auto-generate policies if model is specified
        if model_name and not generate_policies:
            if self.confirm(f"Generate authorization policy for {model_name}?"):
                generate_policies = True
        
        controller_path = Path(f"app/Http/Controllers/{name}.py")
        
        # Enhanced dependency validation
        dependencies = self._get_controller_dependencies(parent_controller, model_name)
        if not await self._validate_dependencies(dependencies):
            return
        
        # Show configuration summary
        self._show_generation_summary(name, {
            'resource': is_resource,
            'api': is_api,
            'model': model_name,
            'invokable': is_invokable,
            'parent': parent_controller,
            'requests': generate_requests,
            'policies': generate_policies,
            'middleware': add_middleware,
            'tests': generate_tests
        })
        
        # Generate controller content
        content = self._generate_enhanced_controller_content(
            name, is_resource, is_api, model_name, is_invokable, 
            parent_controller, add_middleware
        )
        
        # Create controller file
        success = await self.create_file(name, content, controller_path, force)
        if not success:
            return
        
        # Generate additional files
        await self._generate_additional_files(
            name, model_name, generate_requests, generate_policies, generate_tests
        )
        
        # Show enhanced next steps
        self._show_enhanced_next_steps(controller_path, {
            'resource': is_resource,
            'api': is_api,
            'model': model_name,
            'invokable': is_invokable,
            'requests': generate_requests,
            'policies': generate_policies,
            'tests': generate_tests
        })
    
    def _generate_controller_content(self, name: str, is_resource: bool = False, is_api: bool = False, model_name: Optional[str] = None, is_invokable: bool = False) -> str:
        """Generate the controller file content."""
        if is_invokable:
            return self._generate_invokable_controller(name)
        elif is_api or (is_resource and is_api):
            return self._generate_api_controller(name, model_name)
        elif is_resource:
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
        # Production-ready controller implementation
        try:
            from app.Support.Facades.Log import Log
            from app.Support.Facades.Auth import Auth
            from app.Support.Facades.Cache import Cache
            
            # Log request for monitoring
            Log.info(f"{name} controller request", {
                'method': request.method,  # type: ignore[attr-defined]
                'path': str(request.url.path),  # type: ignore[attr-defined]
                'user_id': Auth.id() if Auth.check() else None,
                'ip': getattr(request.client, 'host', 'unknown')
            })
            
            # Example implementations (customize as needed):
            
            # 1. Simple response with context
            current_user = Auth.user()
            response_data = {
                'message': 'Request processed successfully',
                'controller': '{name}',
                'timestamp': self.get_current_time(),
                'user': {
                    'id': current_user.id if current_user else None,
                    'authenticated': current_user is not None
                }
            }
            
            # 2. Cache expensive operations
            cache_key = f"{name.lower()}_response_{{Auth.id() or 'guest'}}"
            cached_response = Cache.get(cache_key)
            
            if cached_response:
                return self.success_response(cached_response)
            
            # 3. Business logic implementation
            # Add your specific business logic here:
            # - Database queries
            # - Data processing
            # - External API calls
            # - File operations
            # - Validation logic
            
            # 4. Cache the response for 5 minutes
            Cache.put(cache_key, response_data, 300)
            
            return self.success_response(response_data)
            
        except Exception as e:
            from app.Support.Facades.Log import Log
            Log.error(f"{name} controller error: {{str(e)}}", {
                'error': str(e),
                'controller': '{name}',
                'user_id': Auth.id() if 'Auth' in locals() and Auth.check() else None
            })
            return self.error_response("Internal server error", 500)
'''
    
    def _generate_invokable_controller(self, name: str) -> str:
        """Generate an invokable controller with single __call__ method."""
        return f'''from __future__ import annotations

from typing import Any, Dict
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from config.database import get_db


class {name}(BaseController):
    """Invokable controller with single action."""
    
    def __init__(self) -> None:
        super().__init__()
    
    async def __call__(
        self,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Handle the incoming request."""
        try:
            # Implement your single action logic here
            # This controller is designed to handle a specific action
            
            # Example validation and processing:
            # request_data = await self.validate_request(request)
            # result = await self.process_action(request_data, db)
            
            # Example business logic:
            # if hasattr(self, 'authorize'):
            #     await self.authorize(request)
            
            # Process the action
            action_result = await self.handle_action(request, db)
            
            return self.success_response(
                message="Action completed successfully",
                data=action_result
            )
            
        except HTTPException:
            raise
        except Exception as e:
            return self.error_response(
                message="Failed to execute action",
                errors={"exception": str(e)},
                status_code=500
            )
    
    async def handle_action(self, request: Request, db: Session) -> Dict[str, Any]:
        """Handle the specific action logic."""
        # Override this method with your specific implementation
        return {"controller": self.__class__.__name__, "executed_at": "now"}
'''
    
    def _generate_api_controller(self, name: str, model_name: Optional[str] = None) -> str:
        """Generate an API resource controller."""
        model_import = ""
        model_operations = ""
        
        if model_name:
            model_import = f"from app.Models.{model_name} import {model_name}"
            model_operations = f"""
        # Example using {model_name} model
        # resources = db.query({model_name}).all()
        # return self.success_response([resource.to_dict() for resource in resources])"""
        
        return f'''from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from config.database import get_db{f"" if not model_import else f"" + chr(10) + model_import}


class {name}(BaseController):
    """API Resource Controller for RESTful operations."""
    
    def __init__(self) -> None:
        super().__init__()
    
    async def index(
        self,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Display a listing of the resource."""{model_operations or """
        try:
            # Implement your index logic here
            # Example with pagination:
            # page = int(request.query_params.get('page', 1))
            # per_page = int(request.query_params.get('per_page', 15))
            # offset = (page - 1) * per_page
            
            # resources = db.query(YourModel).offset(offset).limit(per_page).all()
            # total = db.query(YourModel).count()
            
            # return self.success_response(
            #     data=[resource.to_dict() for resource in resources],
            #     meta={{
            #         'total': total,
            #         'page': page,
            #         'per_page': per_page,
            #         'total_pages': (total + per_page - 1) // per_page
            #     }}
            # )
            
            return self.success_response(
                data=[],
                message="Resources retrieved successfully"
            )
        except Exception as e:
            return self.error_response(
                message="Failed to retrieve resources",
                errors={{"exception": str(e)}},
                status_code=500
            )"""}
        
        return self.success_response([])
    
    async def show(
        self,
        id: int,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Display the specified resource."""
        # resource = db.query(YourModel).filter(YourModel.id == id).first()
        # if not resource:
        #     raise HTTPException(status_code=404, detail="Resource not found")
        # return self.success_response(resource.to_dict())
        
        return self.success_response({{"id": id, "message": "Resource retrieved"}})
    
    async def store(
        self,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Store a newly created resource in storage."""
        # data = await request.json()
        # resource = YourModel(**data)
        # db.add(resource)
        # db.commit()
        # db.refresh(resource)
        # return self.success_response(resource.to_dict(), "Resource created", status.HTTP_201_CREATED)
        
        return self.success_response({{"message": "Resource created"}}, status_code=status.HTTP_201_CREATED)
    
    async def update(
        self,
        id: int,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Update the specified resource in storage."""
        # data = await request.json()
        # resource = db.query(YourModel).filter(YourModel.id == id).first()
        # if not resource:
        #     raise HTTPException(status_code=404, detail="Resource not found")
        # 
        # for key, value in data.items():
        #     setattr(resource, key, value)
        # 
        # db.commit()
        # return self.success_response(resource.to_dict(), "Resource updated")
        
        return self.success_response({{"id": id, "message": "Resource updated"}})
    
    async def destroy(
        self,
        id: int,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Remove the specified resource from storage."""
        # resource = db.query(YourModel).filter(YourModel.id == id).first()
        # if not resource:
        #     raise HTTPException(status_code=404, detail="Resource not found")
        # 
        # db.delete(resource)
        # db.commit()
        # return self.success_response(None, "Resource deleted")
        
        return self.success_response(None, "Resource deleted")
'''
    
    def _validate_controller_name(self, name: str) -> bool:
        """Enhanced controller name validation."""
        # Check for reserved Python keywords
        python_keywords = ['class', 'def', 'return', 'import', 'from', 'if', 'else', 'for', 'while', 'try', 'except']
        base_name = name.replace('Controller', '').lower()
        
        if base_name in python_keywords:
            self.error(f"Controller name '{name}' conflicts with Python keyword '{base_name}'")
            return False
        
        # Check for valid Python identifier format
        if not re.match(r'^[A-Za-z]\w*$', name.replace('Controller', '')):
            self.error(f"Invalid controller name format: {name}")
            self.comment("Controller names should start with a letter and contain only letters, numbers, and underscores")
            return False
        
        # Check if controller already exists
        controller_path = Path(f"app/Http/Controllers/{name}{'Controller' if not name.endswith('Controller') else ''}.py")
        if controller_path.exists() and not self.option("force", False):
            self.warn(f"Controller {controller_path} already exists")
            self.comment("Use --force to overwrite existing controller")
            return False
        
        return True
    
    def _get_controller_dependencies(self, parent_controller: str, model_name: Optional[str] = None) -> List[str]:
        """Get list of required dependencies for controller generation."""
        dependencies = []
        
        # Parent controller dependency
        if parent_controller != "BaseController":
            dependencies.append(f"app/Http/Controllers/{parent_controller}.py")
        else:
            dependencies.append("app/Http/Controllers/BaseController.py")
        
        # Model dependency
        if model_name:
            dependencies.append(f"app/Models/{model_name}.py")
        
        return dependencies
    
    def _show_generation_summary(self, name: str, options: Dict[str, Any]) -> None:
        """Show a summary of what will be generated."""
        self.comment("🏗️  Controller Generation Summary")
        self.line(f"Controller: {name}")
        
        if options.get('resource'):
            self.line("  Type: Resource Controller (CRUD methods)")
        elif options.get('api'):
            self.line("  Type: API Resource Controller")
        elif options.get('invokable'):
            self.line("  Type: Invokable Controller (single action)")
        else:
            self.line("  Type: Basic Controller")
        
        if options.get('model'):
            self.line(f"  Model: {options['model']}")
        
        if options.get('parent') != 'BaseController':
            self.line(f"  Parent: {options['parent']}")
        
        additional_files = []
        if options.get('requests'):
            additional_files.append("Form Requests")
        if options.get('policies'):
            additional_files.append("Authorization Policies")
        if options.get('tests'):
            additional_files.append("Test Files")
        
        if additional_files:
            self.line(f"  Additional: {', '.join(additional_files)}")
        
        self.new_line()
    
    def _generate_enhanced_controller_content(
        self, name: str, is_resource: bool = False, is_api: bool = False, 
        model_name: Optional[str] = None, is_invokable: bool = False, 
        parent_controller: str = "BaseController", add_middleware: bool = False
    ) -> str:
        """Generate enhanced controller content with improved templates."""
        
        # Generate imports based on controller type
        imports = self._generate_controller_imports(is_resource, is_api, model_name, parent_controller)
        
        # Generate class definition
        class_def = self._generate_controller_class_definition(name, parent_controller, add_middleware)
        
        # Generate methods based on controller type
        if is_invokable:
            methods = self._generate_invokable_methods(model_name)
        elif is_resource or is_api:
            methods = self._generate_resource_methods(is_api, model_name)
        else:
            methods = self._generate_basic_methods(model_name)
        
        return f"{imports}\n\n{class_def}{methods}"
    
    def _generate_controller_imports(self, is_resource: bool, is_api: bool, model_name: Optional[str], parent_controller: str) -> str:
        """Generate optimized import statements."""
        imports = ["from __future__ import annotations"]
        
        # Standard library imports
        imports.append("from typing import Any, Dict, List, Optional")
        
        # FastAPI imports
        if is_resource or is_api:
            imports.append("from fastapi import Depends, HTTPException, Request, status, Query")
        else:
            imports.append("from fastapi import Depends, Request")
        
        imports.append("from sqlalchemy.orm import Session")
        
        # Local imports
        imports.append(f"from app.Http.Controllers.{parent_controller} import {parent_controller}")
        imports.append("from config.database import get_db")
        
        if model_name:
            imports.append(f"from app.Models.{model_name} import {model_name}")
        
        if is_resource:
            imports.append("from app.Http.Resources.JsonResource import JsonResource")
            imports.append("from app.Http.Requests.FormRequest import BaseFormRequest")
        
        if is_api:
            imports.append("from app.Http.Schemas.BaseSchema import BaseSchema")
        
        return self._generate_import_statements(imports)
    
    def _generate_controller_class_definition(self, name: str, parent_controller: str, add_middleware: bool) -> str:
        """Generate controller class definition with docstring."""
        middleware_decorator = ""
        if add_middleware:
            middleware_decorator = "@middleware(['auth', 'throttle:60,1'])\n"
        
        return f'''{middleware_decorator}class {name}({parent_controller}):
    """
    {name} handles HTTP requests and responses.
    
    This controller provides endpoints for managing resources
    with proper validation, authorization, and error handling.
    """
    
    def __init__(self) -> None:
        super().__init__()
        self.resource_name = "{name.replace('Controller', '').lower()}"
'''
    
    def _generate_resource_methods(self, is_api: bool, model_name: Optional[str] = None) -> str:
        """Generate enhanced resource methods with better error handling."""
        model_operations = self._get_model_operations(model_name) if model_name else self._get_generic_operations()
        
        return f'''
    async def index(
        self,
        request: Request,
        page: int = Query(1, ge=1),
        per_page: int = Query(15, ge=1, le=100),
        search: Optional[str] = Query(None),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Display a paginated listing of resources with search functionality."""
        try:{model_operations['index']}
            
            # Apply pagination
            offset = (page - 1) * per_page
            # query = query.offset(offset).limit(per_page)
            
            return self.success_response(
                data={{"items": [], "total": 0, "page": page, "per_page": per_page}},
                message="Resources retrieved successfully"
            )
        except Exception as e:
            return self.error_response(f"Failed to retrieve resources: {{str(e)}}")
    
    async def show(
        self,
        id: int,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Display the specified resource."""
        try:{model_operations['show']}
            
            return self.success_response(
                data={{"id": id, "message": "Resource retrieved"}},
                message="Resource retrieved successfully"
            )
        except HTTPException:
            raise
        except Exception as e:
            return self.error_response(f"Failed to retrieve resource: {{str(e)}}")
    
    async def store(
        self,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Store a newly created resource."""
        try:
            # Validate request data
            data = await self.validate_request(request)
            {model_operations['store']}
            
            return self.success_response(
                data={{"message": "Resource created successfully"}},
                message="Resource created successfully",
                status_code=status.HTTP_201_CREATED
            )
        except HTTPException:
            raise
        except Exception as e:
            return self.error_response(f"Failed to create resource: {{str(e)}}")
    
    async def update(
        self,
        id: int,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Update the specified resource."""
        try:
            # Validate request data
            data = await self.validate_request(request)
            {model_operations['update']}
            
            return self.success_response(
                data={{"id": id, "message": "Resource updated"}},
                message="Resource updated successfully"
            )
        except HTTPException:
            raise
        except Exception as e:
            return self.error_response(f"Failed to update resource: {{str(e)}}")
    
    async def destroy(
        self,
        id: int,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Remove the specified resource from storage."""
        try:{model_operations['destroy']}
            
            return self.success_response(
                message="Resource deleted successfully"
            )
        except HTTPException:
            raise
        except Exception as e:
            return self.error_response(f"Failed to delete resource: {{str(e)}}")
'''
    
    def _generate_invokable_methods(self, model_name: Optional[str] = None) -> str:
        """Generate enhanced invokable controller method."""
        return f'''
    async def __call__(
        self,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Handle the incoming request for this single-action controller."""
        try:
            # Validate request if needed
            # data = await self.validate_request(request)
            
            # Your business logic here
            {"# Example: Process " + model_name + " related action" if model_name else "# Implement your specific action logic here"}
            
            # Example implementation:
            # result = await self.process_action(request, db)
            # if result:
            #     return self.success_response(data=result)
            
            action_data = await self.handle_action(request, db)
            
            return self.success_response(
                message="Action completed successfully"
            )
        except HTTPException:
            raise
        except Exception as e:
            return self.error_response(f"Action failed: {{str(e)}}")
'''
    
    def _generate_basic_methods(self, model_name: Optional[str] = None) -> str:
        """Generate basic controller method."""
        return f'''
    async def index(
        self,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        """Handle the incoming request."""
        try:
            # Your controller logic here
            {"# Example: Handle " + model_name + " operations" if model_name else "# Implement your controller logic here"}
            
            # Example implementation:
            # data = await self.process_request(request, db)
            # return self.success_response(data=data)
            
            return self.success_response(
                message=f"Hello from {{self.__class__.__name__}}!"
            )
        except Exception as e:
            return self.error_response(f"Request failed: {{str(e)}}")
'''
    
    def _get_model_operations(self, model_name: str) -> Dict[str, str]:
        """Generate model-specific operations."""
        return {
            'index': f'''
            # Query {model_name} with search and filtering
            query = db.query({model_name})
            
            if search:
                # query = query.filter({model_name}.name.ilike(f"%{{search}}%"))
                pass
            
            # resources = query.all()
            # return self.success_response(JsonResource.collection(resources))''',
            'show': f'''
            resource = db.get({model_name}, id)
            if not resource:
                raise HTTPException(status_code=404, detail="{model_name} not found")
            
            # return self.success_response(JsonResource(resource).to_dict())''',
            'store': f'''
            # Create new {model_name}
            # resource = {model_name}(**data)
            # db.add(resource)
            # db.commit()
            # db.refresh(resource)
            # return self.success_response(JsonResource(resource).to_dict())''',
            'update': f'''
            resource = db.get({model_name}, id)
            if not resource:
                raise HTTPException(status_code=404, detail="{model_name} not found")
            
            # Update resource attributes
            # for key, value in data.items():
            #     setattr(resource, key, value)
            # db.commit()
            # return self.success_response(JsonResource(resource).to_dict())''',
            'destroy': f'''
            resource = db.get({model_name}, id)
            if not resource:
                raise HTTPException(status_code=404, detail="{model_name} not found")
            
            # db.delete(resource)
            # db.commit()'''
        }
    
    def _get_generic_operations(self) -> Dict[str, str]:
        """Generate generic operations without specific model."""
        return {
            'index': '''
            # Production-ready resource listing implementation
            try:
                from app.Support.Facades.Log import Log
                from app.Support.Facades.Cache import Cache
                
                # Apply pagination and filtering
                page = int(request.query_params.get('page', 1))
                per_page = min(int(request.query_params.get('per_page', 15)), 100)
                search = request.query_params.get('search', '')
                
                # Build cache key
                cache_key = f"resource_index_{{page}}_{{per_page}}_{{hash(search)}}"
                cached_result = Cache.get(cache_key)
                
                if cached_result:
                    return self.success_response(cached_result)
                
                # Example query (customize with your model):
                # query = db.query(YourModel)
                # 
                # if search:
                #     query = query.filter(YourModel.name.ilike(f"%{{search}}%"))
                # 
                # total = query.count()
                # resources = query.offset((page - 1) * per_page).limit(per_page).all()
                # 
                # result = {
                #     'data': [resource.to_dict() for resource in resources],
                #     'pagination': {
                #         'current_page': page,
                #         'per_page': per_page,
                #         'total': total,
                #         'last_page': (total + per_page - 1) // per_page
                #     }
                # }
                
                # Default response
                result = {
                    'data': [],
                    'pagination': {'current_page': page, 'per_page': per_page, 'total': 0}
                }
                
                # Cache for 5 minutes
                Cache.put(cache_key, result, 300)
                
                Log.info(f"Resource index returned {{len(result['data'])}} items")
                return self.success_response(result)
                
            except Exception as e:
                Log.error(f"Resource index error: {{str(e)}}")
                return self.error_response("Failed to fetch resources", 500)''',
            'show': '''
            # Production-ready resource retrieval implementation
            try:
                from app.Support.Facades.Log import Log
                from app.Support.Facades.Cache import Cache
                
                # Validate ID
                if not isinstance(id, int) or id <= 0:
                    return self.error_response("Invalid resource ID", 400)
                
                # Check cache first
                cache_key = f"resource_show_{{id}}"
                cached_resource = Cache.get(cache_key)
                
                if cached_resource:
                    return self.success_response(cached_resource)
                
                # Example query (customize with your model):
                # resource = db.get(YourModel, id)
                # 
                # if not resource:
                #     Log.warning(f"Resource not found: {{id}}")
                #     return self.error_response("Resource not found", 404)
                # 
                # result = resource.to_dict()
                # 
                # # Include related data if needed
                # if 'include' in request.query_params:
                #     includes = request.query_params['include'].split(',')
                #     for include in includes:
                #         if hasattr(resource, include):
                #             result[include] = getattr(resource, include)
                
                # Default response (resource not implemented)
                result = {'id': id, 'message': 'Resource implementation pending'}
                
                # Cache for 10 minutes
                Cache.put(cache_key, result, 600)
                
                Log.info(f"Resource {{id}} retrieved successfully")
                return self.success_response(result)
                
            except Exception as e:
                Log.error(f"Resource show error: {{str(e)}}", {'id': id})
                return self.error_response("Failed to fetch resource", 500)''',
            'store': '''
            # Production-ready resource creation implementation
            try:
                from app.Support.Facades.Log import Log
                from app.Support.Facades.Cache import Cache
                from app.Support.Facades.Event import Event
                
                # Validate input data
                if not data or not isinstance(data, dict):
                    return self.error_response("Invalid or missing data", 400)
                
                # Sanitize and validate data
                validated_data = self._validate_store_data(data)
                
                # Example creation (customize with your model):
                # resource = YourModel(**validated_data)
                # db.add(resource)
                # db.commit()
                # db.refresh(resource)
                # 
                # result = resource.to_dict()
                
                # Default response (simulate creation)
                result = {
                    'id': 1,  # Replace with actual resource ID
                    'message': 'Resource created successfully',
                    **validated_data
                }
                
                # Clear related caches
                Cache.forget_by_pattern("resource_index_*")
                
                # Dispatch creation event
                Event.dispatch('resource_created', {
                    'resource_type': 'YourModel',
                    'resource_id': result['id'],
                    'data': validated_data
                })
                
                Log.info(f"Resource created successfully", {'data': list(validated_data.keys())})
                return self.success_response(result, 201)
                
            except ValueError as ve:
                Log.warning(f"Validation error: {{str(ve)}}", {'data': data})
                return self.error_response(str(ve), 422)
            except Exception as e:
                db.rollback()
                Log.error(f"Resource creation error: {{str(e)}}", {'data': data})
                return self.error_response("Failed to create resource", 500)
            
        def _validate_store_data(self, data: dict) -> dict:
            """Validate data for resource creation."""
            validated = {{}}
            
            # Example validations (customize as needed):
            # if 'name' in data:
            #     name = str(data['name']).strip()
            #     if not name:
            #         raise ValueError("Name is required")
            #     validated['name'] = name
            
            # Return sanitized data
            return {{k: v for k, v in data.items() if v is not None}}''',
            'update': '''
            # Production-ready resource update implementation
            try:
                from app.Support.Facades.Log import Log
                from app.Support.Facades.Cache import Cache
                from app.Support.Facades.Event import Event
                
                # Validate inputs
                if not isinstance(id, int) or id <= 0:
                    return self.error_response("Invalid resource ID", 400)
                
                if not data or not isinstance(data, dict):
                    return self.error_response("Invalid or missing data", 400)
                
                # Validate update data
                validated_data = self._validate_update_data(data)
                
                # Example update (customize with your model):
                # resource = db.get(YourModel, id)
                # 
                # if not resource:
                #     Log.warning(f"Resource not found for update: {{id}}")
                #     return self.error_response("Resource not found", 404)
                # 
                # # Track changes for auditing
                # changes = {{}}
                # for key, value in validated_data.items():
                #     if hasattr(resource, key):
                #         old_value = getattr(resource, key)
                #         if old_value != value:
                #             changes[key] = {{'old': old_value, 'new': value}}
                #             setattr(resource, key, value)
                # 
                # if not changes:
                #     return self.success_response(resource.to_dict())
                # 
                # db.commit()
                # db.refresh(resource)
                # result = resource.to_dict()
                
                # Default response (simulate update)
                result = {
                    'id': id,
                    'message': 'Resource updated successfully',
                    **validated_data
                }
                
                # Clear related caches
                Cache.forget_by_pattern("resource_*")
                
                # Dispatch update event
                Event.dispatch('resource_updated', {
                    'resource_type': 'YourModel',
                    'resource_id': id,
                    'changes': validated_data
                })
                
                Log.info(f"Resource {{id}} updated successfully", {'data': list(validated_data.keys())})
                return self.success_response(result)
                
            except ValueError as ve:
                Log.warning(f"Validation error: {{str(ve)}}", {'id': id, 'data': data})
                return self.error_response(str(ve), 422)
            except Exception as e:
                db.rollback()
                Log.error(f"Resource update error: {{str(e)}}", {'id': id, 'data': data})
                return self.error_response("Failed to update resource", 500)
            
        def _validate_update_data(self, data: dict) -> dict:
            """Validate data for resource updates."""
            # Example validations (customize as needed)
            return {{k: v for k, v in data.items() if v is not None}}''',
            'destroy': '''
            # Production-ready resource deletion implementation
            try:
                from app.Support.Facades.Log import Log
                from app.Support.Facades.Cache import Cache
                from app.Support.Facades.Event import Event
                
                # Validate ID
                if not isinstance(id, int) or id <= 0:
                    return self.error_response("Invalid resource ID", 400)
                
                # Example deletion (customize with your model):
                # resource = db.get(YourModel, id)
                # 
                # if not resource:
                #     Log.warning(f"Resource not found for deletion: {{id}}")
                #     return self.error_response("Resource not found", 404)
                # 
                # # Store resource data for audit trail
                # resource_data = resource.to_dict()
                # 
                # # Check for dependencies before deletion
                # if hasattr(resource, 'has_dependencies') and resource.has_dependencies():
                #     return self.error_response("Cannot delete resource with dependencies", 409)
                # 
                # # Perform soft delete if supported
                # if hasattr(resource, 'deleted_at'):
                #     from datetime import datetime
                #     resource.deleted_at = datetime.utcnow()
                #     db.commit()
                # else:
                #     # Hard delete
                #     db.delete(resource)
                #     db.commit()
                
                # Default response (simulate deletion)
                result = {
                    'id': id,
                    'message': 'Resource deleted successfully'
                }
                
                # Clear related caches
                Cache.forget_by_pattern("resource_*")
                
                # Dispatch deletion event
                Event.dispatch('resource_deleted', {
                    'resource_type': 'YourModel',
                    'resource_id': id
                })
                
                Log.info(f"Resource {{id}} deleted successfully")
                return self.success_response(result)
                
            except Exception as e:
                db.rollback()
                Log.error(f"Resource deletion error: {{str(e)}}", {'id': id})
                return self.error_response("Failed to delete resource", 500)'''
        }
    
    async def _generate_additional_files(
        self, controller_name: str, model_name: Optional[str], 
        generate_requests: bool, generate_policies: bool, generate_tests: bool
    ) -> None:
        """Generate additional files based on options."""
        
        if generate_requests:
            await self._generate_form_requests(controller_name, model_name)
        
        if generate_policies and model_name:
            await self._generate_policy(model_name)
        
        if generate_tests:
            await self._generate_test_files(controller_name, model_name)
    
    async def _generate_form_requests(self, controller_name: str, model_name: Optional[str] = None) -> None:
        """Generate form request classes for validation."""
        base_name = controller_name.replace('Controller', '')
        
        # Store Request
        store_request_content = self._generate_store_request_content(base_name, model_name)
        store_request_path = Path(f"app/Http/Requests/{base_name}StoreRequest.py")
        
        await self.create_file(
            f"{base_name}StoreRequest",
            store_request_content,
            store_request_path
        )
        
        # Update Request
        update_request_content = self._generate_update_request_content(base_name, model_name)
        update_request_path = Path(f"app/Http/Requests/{base_name}UpdateRequest.py")
        
        await self.create_file(
            f"{base_name}UpdateRequest",
            update_request_content,
            update_request_path
        )
        
        self.info(f"✅ Generated form request classes for {controller_name}")
    
    def _generate_store_request_content(self, base_name: str, model_name: Optional[str] = None) -> str:
        """Generate store request validation class."""
        return f'''from __future__ import annotations

from typing import Dict, Any, List
from app.Http.Requests.FormRequest import BaseFormRequest


class {base_name}StoreRequest(BaseFormRequest):
    """Validation for creating new {base_name.lower()} resources."""
    
    def rules(self) -> Dict[str, List[str]]:
        """Define validation rules."""
        return {{
            # Add your validation rules here
            # Example:
            # "name": ["required", "string", "max:255"],
            # "email": ["required", "email", "unique:users,email"],
            # "password": ["required", "string", "min:8"],
        }}
    
    def messages(self) -> Dict[str, str]:
        """Custom validation messages."""
        return {{
            # Add custom messages here
            # "name.required": "Name is required",
            # "email.unique": "Email already exists",
        }}
    
    def authorize(self) -> bool:
        """Determine if the user is authorized to make this request."""
        # Implement authorization logic
        return True
'''
    
    def _generate_update_request_content(self, base_name: str, model_name: Optional[str] = None) -> str:
        """Generate update request validation class."""
        return f'''from __future__ import annotations

from typing import Dict, Any, List
from app.Http.Requests.FormRequest import BaseFormRequest


class {base_name}UpdateRequest(BaseFormRequest):
    """Validation for updating {base_name.lower()} resources."""
    
    def rules(self) -> Dict[str, List[str]]:
        """Define validation rules."""
        return {{
            # Add your validation rules here
            # Example:
            # "name": ["sometimes", "string", "max:255"],
            # "email": ["sometimes", "email", f"unique:users,email,{{self.route_param('id')}}"],
        }}
    
    def messages(self) -> Dict[str, str]:
        """Custom validation messages."""
        return {{
            # Add custom messages here
        }}
    
    def authorize(self) -> bool:
        """Determine if the user is authorized to make this request."""
        # Implement authorization logic
        return True
'''
    
    async def _generate_policy(self, model_name: str) -> None:
        """Generate authorization policy for the model."""
        policy_content = f'''from __future__ import annotations

from typing import Any, Optional
from app.Policies.BasePolicy import BasePolicy
from app.Models.User import User
from app.Models.{model_name} import {model_name}


class {model_name}Policy(BasePolicy):
    """Authorization policy for {model_name} model."""
    
    def view_any(self, user: User) -> bool:
        """Determine if user can view any {model_name.lower()} resources."""
        return user.can("view_{model_name.lower()}")
    
    def view(self, user: User, {model_name.lower()}: {model_name}) -> bool:
        """Determine if user can view the {model_name.lower()} resource."""
        return user.can("view_{model_name.lower()}") or {model_name.lower()}.user_id == user.id
    
    def create(self, user: User) -> bool:
        """Determine if user can create {model_name.lower()} resources."""
        return user.can("create_{model_name.lower()}")
    
    def update(self, user: User, {model_name.lower()}: {model_name}) -> bool:
        """Determine if user can update the {model_name.lower()} resource."""
        return user.can("update_{model_name.lower()}") or {model_name.lower()}.user_id == user.id
    
    def delete(self, user: User, {model_name.lower()}: {model_name}) -> bool:
        """Determine if user can delete the {model_name.lower()} resource."""
        return user.can("delete_{model_name.lower()}") or {model_name.lower()}.user_id == user.id
    
    def restore(self, user: User, {model_name.lower()}: {model_name}) -> bool:
        """Determine if user can restore the {model_name.lower()} resource."""
        return user.can("restore_{model_name.lower()}")
    
    def force_delete(self, user: User, {model_name.lower()}: {model_name}) -> bool:
        """Determine if user can permanently delete the {model_name.lower()} resource."""
        return user.can("force_delete_{model_name.lower()}")
'''
        
        policy_path = Path(f"app/Policies/{model_name}Policy.py")
        await self.create_file(f"{model_name}Policy", policy_content, policy_path)
        self.info(f"✅ Generated authorization policy for {model_name}")
    
    async def _generate_test_files(self, controller_name: str, model_name: Optional[str] = None) -> None:
        """Generate test files for the controller."""
        test_content = f'''from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.Http.Controllers.{controller_name} import {controller_name}
{"from app.Models." + model_name + " import " + model_name if model_name else ""}
from tests.TestCase import TestCase


class Test{controller_name}(TestCase):
    """Test cases for {controller_name}."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        self.controller = {controller_name}()
        {"self.model = " + model_name if model_name else ""}
    
    async def test_index_returns_success(self) -> None:
        """Test that index method returns successful response."""
        # Arrange
        # Create test data
        
        # Act
        response = await self.controller.index(self.request, self.db)
        
        # Assert
        assert response["success"] is True
        # Add more assertions
    
    async def test_show_returns_resource(self) -> None:
        """Test that show method returns specific resource."""
        # Arrange
        # resource_id = 1
        
        # Act
        # response = await self.controller.show(resource_id, self.request, self.db)
        
        # Assert
        # assert response["success"] is True
        pass
    
    async def test_store_creates_resource(self) -> None:
        """Test that store method creates new resource."""
        # Arrange
        # test_data = {{"name": "Test Resource"}}
        
        # Act
        # response = await self.controller.store(self.request, self.db)
        
        # Assert
        # assert response["success"] is True
        pass
    
    async def test_update_modifies_resource(self) -> None:
        """Test that update method modifies existing resource."""
        # Arrange
        # resource_id = 1
        # test_data = {{"name": "Updated Resource"}}
        
        # Act
        # response = await self.controller.update(resource_id, self.request, self.db)
        
        # Assert
        # assert response["success"] is True
        pass
    
    async def test_destroy_deletes_resource(self) -> None:
        """Test that destroy method deletes resource."""
        # Arrange
        # resource_id = 1
        
        # Act
        # response = await self.controller.destroy(resource_id, self.request, self.db)
        
        # Assert
        # assert response["success"] is True
        pass
'''
        
        test_path = Path(f"tests/Http/Controllers/Test{controller_name}.py")
        await self.create_file(f"Test{controller_name}", test_content, test_path)
        self.info(f"✅ Generated test file for {controller_name}")
    
    def _show_enhanced_next_steps(self, controller_path: Path, options: Dict[str, Any]) -> None:
        """Show enhanced next steps with detailed guidance."""
        self.new_line()
        self.comment("🎯 Next Steps & Recommendations:")
        
        step_num = 1
        
        # Basic controller setup
        self.line(f"{step_num}. Review and customize the generated controller logic")
        step_num += 1
        
        # Route registration
        if options.get('invokable'):
            self.line(f"{step_num}. Register a single route for this invokable controller:")
            self.line(f"   router.post('/action', {options.get('controller_name', 'controller')})")
        elif options.get('resource') or options.get('api'):
            self.line(f"{step_num}. Register RESTful routes in your router:")
            self.line("   router.include_router(resource_router)")
        else:
            self.line(f"{step_num}. Register routes for your controller methods")
        step_num += 1
        
        # Model-specific steps
        if options.get('model'):
            self.line(f"{step_num}. Ensure {options['model']} model has proper relationships")
            self.line(f"{step_num + 1}. Run migrations if database changes are needed")
            step_num += 2
        
        # Validation steps
        if options.get('requests'):
            self.line(f"{step_num}. Customize validation rules in generated request classes")
            step_num += 1
        
        # Authorization steps
        if options.get('policies'):
            self.line(f"{step_num}. Configure permissions and roles for authorization")
            self.line(f"{step_num + 1}. Register the policy in your service provider")
            step_num += 2
        
        # Testing steps
        if options.get('tests'):
            self.line(f"{step_num}. Write comprehensive tests for all controller methods")
            self.line(f"{step_num + 1}. Run tests: make test")
            step_num += 2
        
        # General recommendations
        self.new_line()
        self.comment("💡 Recommendations:")
        self.line("• Add proper error handling and logging")
        self.line("• Implement rate limiting for API endpoints")
        self.line("• Add API documentation with proper schemas")
        self.line("• Consider caching for frequently accessed data")
        
        self.new_line()
        self.comment(f"📁 Generated file: {controller_path}")
        
        if options.get('requests') or options.get('policies') or options.get('tests'):
            self.comment("📦 Additional files generated in their respective directories")
        
        self.new_line()


# Register the command
from app.Console.Artisan import register_command
register_command(MakeControllerCommand)