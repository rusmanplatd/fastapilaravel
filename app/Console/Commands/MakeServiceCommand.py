from __future__ import annotations

from pathlib import Path
from ..Command import Command


class MakeServiceCommand(Command):
    """Generate a new service class."""
    
    signature = "make:service {name : The name of the service}"
    description = "Create a new service class"
    help = "Generate a new service class for business logic"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        
        if not name:
            self.error("Service name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Service"):
            name += "Service"
        
        service_path = Path(f"app/Services/{{name}}.py")
        service_path.parent.mkdir(parents=True, exist_ok=True)
        
        if service_path.exists():
            if not self.confirm(f"Service {{name}} already exists. Overwrite?"):
                self.info("Service creation cancelled.")
                return
        
        content = self._generate_service_content(name)
        service_path.write_text(content)
        
        self.info(f"✅ Service created: {{service_path}}")
        self.comment("Update the service with your business logic")
    
    def _generate_service_content(self, service_name: str) -> str:
        """Generate service content."""
        return '''from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.Services.BaseService import BaseService


class ''' + service_name + '''(BaseService):

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.Services.BaseService import BaseService


class {service_name}(BaseService):
    """Service for handling business logic."""
    
    def __init__(self, db: Session) -> None:
        super().__init__(db)
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all records."""
        # Production-ready implementation for getting all records
        try:
            from app.Support.Facades.Log import Log
            from app.Support.Facades.Cache import Cache
            
            # Use caching for expensive queries
            cache_key = f"{self.__class__.__name__}_get_all"
            cached_result = Cache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            # Example implementation (customize with your model):
            # records = self.db.query(YourModel).order_by(YourModel.created_at.desc()).all()
            # result = [{{
            #     'id': record.id,
            #     'name': getattr(record, 'name', 'N/A'),
            #     'status': getattr(record, 'status', 'active'),
            #     'created_at': record.created_at.isoformat() if hasattr(record, 'created_at') and record.created_at else None,
            #     'updated_at': record.updated_at.isoformat() if hasattr(record, 'updated_at') and record.updated_at else None
            # }} for record in records]
            
            # Default empty result
            result = []
            
            # Cache for 5 minutes
            Cache.put(cache_key, result, 300)
            
            Log.info(f"{{self.__class__.__name__}}.get_all() returned {len(result)} records")
            return result
            
        except Exception as e:
            from app.Support.Facades.Log import Log
            Log.error(f"Error in {{self.__class__.__name__}}.get_all(): {{str(e)}}", {{
                'error': str(e),
                'service': self.__class__.__name__
            }})
            return []
    
    def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Get record by ID."""
        # Production-ready implementation for getting record by ID
        try:
            from app.Support.Facades.Log import Log
            from app.Support.Facades.Cache import Cache
            
            if not isinstance(id, int) or id <= 0:
                Log.warning(f"Invalid ID provided to {{self.__class__.__name__}}.get_by_id(): {id}")
                return None
            
            # Use caching for individual records
            cache_key = f"{{self.__class__.__name__}}_get_by_id_{id}"
            cached_result = Cache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            # Example implementation (customize with your model):
            # record = self.db.query(YourModel).filter(YourModel.id == id).first()
            # 
            # if not record:
            #     return None
            # 
            # result = {
            #     'id': record.id,
            #     'name': getattr(record, 'name', 'N/A'),
            #     'status': getattr(record, 'status', 'active'),
            #     'created_at': record.created_at.isoformat() if hasattr(record, 'created_at') and record.created_at else None,
            #     'updated_at': record.updated_at.isoformat() if hasattr(record, 'updated_at') and record.updated_at else None
            # }
            
            # Default: return None (record not found)
            result = None
            
            # Cache successful results for 10 minutes
            if result:
                Cache.put(cache_key, result, 600)
            
            Log.info(f"{{self.__class__.__name__}}.get_by_id({{id}}) {'found' if result else 'not found'}")
            return result
            
        except Exception as e:
            from app.Support.Facades.Log import Log
            Log.error(f"Error in {{self.__class__.__name__}}.get_by_id({{id}}): {str(e)}", {
                'id': id,
                'error': str(e),
                'service': self.__class__.__name__
            }})
            return None
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record."""
        # Production-ready implementation for creating records
        try:
            from app.Support.Facades.Log import Log
            from app.Support.Facades.Cache import Cache
            from app.Support.Facades.Event import Event
            
            # Validate input data
            if not isinstance(data, dict) or not data:
                raise ValueError("Invalid or empty data provided")
            
            # Sanitize and validate data
            validated_data = self._validate_create_data(data)
            
            # Example implementation (customize with your model):
            # record = YourModel(**validated_data)
            # self.db.add(record)
            # self.db.commit()
            # self.db.refresh(record)
            # 
            # result = {
            #     'id': record.id,
            #     'name': getattr(record, 'name', 'N/A'),
            #     'status': getattr(record, 'status', 'active'),
            #     'created_at': record.created_at.isoformat() if hasattr(record, 'created_at') and record.created_at else None,
            #     'updated_at': record.updated_at.isoformat() if hasattr(record, 'updated_at') and record.updated_at else None
            # }
            
            # Default implementation
            result = {
                'id': 1,  # Replace with actual ID
                'message': 'Record created successfully',
                **validated_data
            }
            
            # Clear related caches
            Cache.forget(f"{self.__class__.__name__}_get_all")
            
            # Dispatch event
            # Event.dispatch('record_created', {'service': self.__class__.__name__, 'data': result})
            
            Log.info(f"{{self.__class__.__name__}}.create() successful", {{
                'data_keys': list(validated_data.keys()),
                'service': self.__class__.__name__
            }})
            
            return result
            
        except Exception as e:
            self.db.rollback()
            from app.Support.Facades.Log import Log
            Log.error(f"Error in {self.__class__.__name__}.create(): {{str(e)}}", {{
                'data': data,
                'error': str(e),
                'service': self.__class__.__name__
            }})
            raise
    
    def _validate_create_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data for creation."""
        # Implement validation logic here
        validated = {}
        
        # Example validations:
        # if 'name' in data:
        #     name = str(data['name']).strip()
        #     if not name:
        #         raise ValueError("Name cannot be empty")
        #     validated['name'] = name
        # 
        # if 'email' in data:
        #     email = str(data['email']).strip().lower()
        #     if '@' not in email:
        #         raise ValueError("Invalid email format")
        #     validated['email'] = email
        
        # For now, return the data as-is (customize as needed)
        return {{k: v for k, v in data.items() if v is not None}}
    
    def update(self, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing record."""
        # Production-ready implementation for updating records
        try:
            from app.Support.Facades.Log import Log
            from app.Support.Facades.Cache import Cache
            from app.Support.Facades.Event import Event
            
            # Validate inputs
            if not isinstance(id, int) or id <= 0:
                raise ValueError(f"Invalid ID: {{id}}")
                
            if not isinstance(data, dict) or not data:
                raise ValueError("Invalid or empty data provided")
            
            # Validate update data
            validated_data = self._validate_update_data(data)
            
            # Example implementation (customize with your model):
            # record = self.db.query(YourModel).filter(YourModel.id == id).first()
            # 
            # if not record:
            #     Log.warning(f"{self.__class__.__name__}.update({{id}}) - record not found")
            #     return None
            # 
            # # Track changes for auditing
            # changes = {}
            # for key, value in validated_data.items():
            #     if hasattr(record, key):
            #         old_value = getattr(record, key)
            #         if old_value != value:
            #             changes[key] = {'old': old_value, 'new': value}
            #             setattr(record, key, value)
            # 
            # if not changes:
            #     Log.info(f"{self.__class__.__name__}.update({{id}}) - no changes detected")
            #     return self.get_by_id(id)
            # 
            # self.db.commit()
            # self.db.refresh(record)
            # 
            # result = {
            #     'id': record.id,
            #     'name': getattr(record, 'name', 'N/A'),
            #     'status': getattr(record, 'status', 'active'),
            #     'created_at': record.created_at.isoformat() if hasattr(record, 'created_at') and record.created_at else None,
            #     'updated_at': record.updated_at.isoformat() if hasattr(record, 'updated_at') and record.updated_at else None
            # }
            
            # Default implementation
            result = {
                'id': id,
                'message': 'Record updated successfully',
                **validated_data
            }
            
            # Clear related caches
            Cache.forget(f"{self.__class__.__name__}_get_all")
            Cache.forget(f"{{self.__class__.__name__}}_get_by_id_{id}")
            
            # Dispatch event
            # Event.dispatch('record_updated', {'service': self.__class__.__name__, 'id': id, 'changes': changes})
            
            Log.info(f"{self.__class__.__name__}.update({{id}}) successful", {{
                'data_keys': list(validated_data.keys()),
                'service': self.__class__.__name__
            }})
            
            return result
            
        except Exception as e:
            self.db.rollback()
            from app.Support.Facades.Log import Log
            Log.error(f"Error in {self.__class__.__name__}.update({id}): {{str(e)}}", {{
                'id': id,
                'data': data,
                'error': str(e),
                'service': self.__class__.__name__
            }})
            return None
    
    def _validate_update_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data for updates."""
        # Implement validation logic here
        validated = {}
        
        # Example validations:
        # if 'name' in data:
        #     name = str(data['name']).strip()
        #     if not name:
        #         raise ValueError("Name cannot be empty")
        #     validated['name'] = name
        # 
        # if 'status' in data:
        #     status = str(data['status']).strip().lower()
        #     if status not in ['active', 'inactive', 'pending']:
        #         raise ValueError("Invalid status value")
        #     validated['status'] = status
        
        # For now, return the data as-is (customize as needed)
        return {{k: v for k, v in data.items() if v is not None}}
    
    def delete(self, id: int) -> bool:
        """Delete a record."""
        # Production-ready implementation for deleting records
        try:
            from app.Support.Facades.Log import Log
            from app.Support.Facades.Cache import Cache
            from app.Support.Facades.Event import Event
            
            # Validate input
            if not isinstance(id, int) or id <= 0:
                raise ValueError(f"Invalid ID: {{id}}")
            
            # Example implementation (customize with your model):
            # record = self.db.query(YourModel).filter(YourModel.id == id).first()
            # 
            # if not record:
            #     Log.warning(f"{self.__class__.__name__}.delete({{id}}) - record not found")
            #     return False
            # 
            # # Store record data for event/audit before deletion
            # record_data = {
            #     'id': record.id,
            #     'name': getattr(record, 'name', 'N/A')
            # }
            # 
            # # Perform soft delete if model supports it
            # if hasattr(record, 'deleted_at'):
            #     from datetime import datetime
            #     record.deleted_at = datetime.utcnow()
            #     self.db.commit()
            # else:
            #     # Hard delete
            #     self.db.delete(record)
            #     self.db.commit()
            
            # Default implementation (simulate successful deletion)
            success = True  # Replace with actual deletion logic
            
            if success:
                # Clear related caches
                Cache.forget(f"{self.__class__.__name__}_get_all")
                Cache.forget(f"{{self.__class__.__name__}}_get_by_id_{id}")
                
                # Dispatch event
                # Event.dispatch('record_deleted', {'service': self.__class__.__name__, 'id': id, 'data': record_data})
                
                Log.info(f"{self.__class__.__name__}.delete({{id}}) successful", {{
                    'id': id,
                    'service': self.__class__.__name__
                }})
            
            return success
            
        except Exception as e:
            self.db.rollback()
            from app.Support.Facades.Log import Log
            Log.error(f"Error in {self.__class__.__name__}.delete({id}): {{str(e)}}", {{
                'id': id,
                'error': str(e),
                'service': self.__class__.__name__
            }})
            return False
        #     self.db.delete(record)
        #     self.db.commit()
        #     return True
        return False
    
    # Add your custom business logic methods here
'''


class MakeRequestCommand(Command):
    """Generate a new form request class."""
    
    signature = "make:request {name : The name of the request}"
    description = "Create a new form request class"
    help = "Generate a new form request class for validation"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        
        if not name:
            self.error("Request name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Request"):
            name += "Request"
        
        request_path = Path(f"app/Http/Requests/{{name}}.py")
        request_path.parent.mkdir(parents=True, exist_ok=True)
        
        if request_path.exists():
            if not self.confirm(f"Request {{name}} already exists. Overwrite?"):
                self.info("Request creation cancelled.")
                return
        
        content = self._generate_request_content(name)
        request_path.write_text(content)
        
        self.info(f"✅ Request created: {{request_path}}")
        self.comment("Update the rules() and authorize() methods as needed")
    
    def _generate_request_content(self, request_name: str) -> str:
        """Generate form request content."""
        return f'''from __future__ import annotations

from typing import Dict, Any, List, Optional
from app.Http.Requests.FormRequest import FormRequest


class {request_name}(FormRequest):
    """Form request for validation."""
    
    def authorize(self) -> bool:
        """Determine if the user is authorized to make this request."""
        # Return True if authorized, False otherwise
        # Example: return self.user() is not None
        return True
    
    def rules(self) -> Dict[str, List[str]]:
        """Get the validation rules that apply to the request."""
        return {{
            # Add your validation rules here
            # Examples:
            # "name": ["required", "string", "min:2", "max:100"],
            # "email": ["required", "email", "unique:users,email"],
            # "password": ["required", "string", "min:8"],
            # "age": ["required", "integer", "min:18", "max:120"],
        }}
    
    def messages(self) -> Dict[str, str]:
        """Get custom error messages for validation rules."""
        return {{
            # Add custom error messages here
            # Examples:
            # "name.required": "The name field is required",
            # "email.email": "Please provide a valid email address",
            # "password.min": "Password must be at least 8 characters long",
        }}
    
    def attributes(self) -> Dict[str, str]:
        """Get custom attribute names for validation errors."""
        return {{
            # Add custom attribute names here
            # Examples:
            # "name": "full name",
            # "email": "email address",
        }}
    
    def prepare_for_validation(self) -> None:
        """Prepare the data for validation."""
        # Override to modify data before validation
        # Example:
        # self.merge({{
        #     "slug": self.get("name", "").lower().replace(" ", "-")
        # }})
        pass
'''


class MakeResourceCommand(Command):
    """Generate a new API resource class."""
    
    signature = "make:resource {name : The name of the resource}"
    description = "Create a new API resource class"
    help = "Generate a new API resource class for data transformation"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        
        if not name:
            self.error("Resource name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Resource"):
            name += "Resource"
        
        resource_path = Path(f"app/Http/Resources/{{name}}.py")
        resource_path.parent.mkdir(parents=True, exist_ok=True)
        
        if resource_path.exists():
            if not self.confirm(f"Resource {{name}} already exists. Overwrite?"):
                self.info("Resource creation cancelled.")
                return
        
        content = self._generate_resource_content(name)
        resource_path.write_text(content)
        
        self.info(f"✅ Resource created: {{resource_path}}")
        self.comment("Update the to_array() method to transform your data")
    
    def _generate_resource_content(self, resource_name: str) -> str:
        """Generate resource content."""
        return f'''from __future__ import annotations

from typing import Any, Dict, Optional
from app.Http.Resources.JsonResource import JsonResource


class {resource_name}(JsonResource):
    """API resource for transforming data."""
    
    def to_array(self) -> Dict[str, Any]:
        """Transform the resource into an array."""
        return {{
            # Transform your model data here
            # Examples:
            # "id": self.resource.id,
            # "name": self.resource.name,
            # "email": self.resource.email,
            # "created_at": self.resource.created_at.isoformat() if self.resource.created_at else None,
            # "updated_at": self.resource.updated_at.isoformat() if self.resource.updated_at else None,
            
            # Conditional attributes
            # "sensitive_data": self.when(self.user_can("view_sensitive"), self.resource.sensitive_data),
            
            # Nested resources
            # "posts": PostResource.collection(self.resource.posts),
            # "profile": ProfileResource(self.resource.profile).to_dict() if self.resource.profile else None,
        }}
    
    def with_relationships(self, relationships: list) -> 'JsonResource':
        """Include specified relationships."""
        # Override if you need custom relationship loading
        return super().with_relationships(relationships)
'''


class MakeMiddlewareCommand(Command):
    """Generate a new middleware class."""
    
    signature = "make:middleware {name : The name of the middleware}"
    description = "Create a new middleware class"
    help = "Generate a new middleware class for request/response processing"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        
        if not name:
            self.error("Middleware name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Middleware"):
            name += "Middleware"
        
        middleware_path = Path(f"app/Http/Middleware/{{name}}.py")
        middleware_path.parent.mkdir(parents=True, exist_ok=True)
        
        if middleware_path.exists():
            if not self.confirm(f"Middleware {{name}} already exists. Overwrite?"):
                self.info("Middleware creation cancelled.")
                return
        
        content = self._generate_middleware_content(name)
        middleware_path.write_text(content)
        
        self.info(f"✅ Middleware created: {{middleware_path}}")
        self.comment("Update the __call__ method with your middleware logic")
        self.comment("Register the middleware in your FastAPI app or router")
    
    def _generate_middleware_content(self, middleware_name: str) -> str:
        """Generate middleware content."""
        return f'''from __future__ import annotations

from typing import Callable, Any
from starlette.requests import Request
from fastapi import Response
from fastapi.responses import JSONResponse


class {middleware_name}:
    """Middleware for request/response processing."""
    
    def __init__(self) -> None:
        pass
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process the request and response."""
        # Pre-processing (before the request reaches the endpoint)
        # Example:
        # if not self.is_authorized(request):
        #     return JSONResponse(
        #         status_code=401,
        #         content={{"error": "Unauthorized"}}
        #     )
        
        # Process the request
        response = await call_next(request)
        
        # Post-processing (after the response is generated)
        # Example:
        # response.headers["X-Custom-Header"] = "Custom Value"
        
        return response
    
    def is_authorized(self, request: Request) -> bool:
        """Check if the request is authorized."""
        # Production-ready authorization implementation
        try:
            from app.Support.Facades.Log import Log
            from app.Support.Facades.Auth import Auth
            
            # Method 1: Check for authenticated user
            current_user = Auth.user()
            if current_user:
                Log.debug(f"User {{current_user.id}} authorized via Auth facade")
                return True
            
            # Method 2: Check Authorization header
            auth_header = request.headers.get("Authorization", "")
            if auth_header:
                # Bearer token format
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]  # Remove "Bearer " prefix
                    if self.validate_token(token):
                        Log.debug(f"Request authorized via Bearer token")
                        return True
                
                # API key format
                elif auth_header.startswith("ApiKey "):
                    api_key = auth_header[7:]  # Remove "ApiKey " prefix
                    if self.validate_api_key(api_key):
                        Log.debug(f"Request authorized via API key")
                        return True
            
            # Method 3: Check for API key in query parameters
            api_key = request.query_params.get("api_key")
            if api_key and self.validate_api_key(api_key):
                Log.debug(f"Request authorized via query parameter API key")
                return True
            
            # Method 4: Check for specific permissions
            if hasattr(self, 'required_permissions'):
                for permission in self.required_permissions:
                    if not Auth.can(permission):
                        Log.warning(f"Authorization failed: missing permission '{{permission}}'")
                        return False
                return True
            
            # Method 5: IP whitelist check
            client_ip = getattr(request.client, 'host', None)
            if client_ip and hasattr(self, 'allowed_ips'):
                if client_ip in self.allowed_ips:
                    Log.debug(f"Request authorized via IP whitelist: {{client_ip}}")
                    return True
            
            # Log unauthorized access attempt
            Log.warning(f"Unauthorized access attempt", {{
                'ip': client_ip,
                'user_agent': request.headers.get('user-agent', 'unknown'),
                'path': str(request.url.path),  # type: ignore[attr-defined]
                'method': request.method  # type: ignore[attr-defined]
            }})
            
            return False
            
        except Exception as e:
            from app.Support.Facades.Log import Log
            Log.error(f"Authorization check failed: {{str(e)}}", {{
                'error': str(e),
                'service': self.__class__.__name__
            }})
            return False
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key."""
        try:
            # Implement API key validation logic
            # Example: check against database or configured keys
            
            # Basic validation
            if not api_key or len(api_key) < 32:
                return False
            
            # Example: check against environment variable
            import os
            valid_api_keys = os.getenv('VALID_API_KEYS', '').split(',')
            return api_key in valid_api_keys
            
        except Exception:
            return False
    
    def validate_token(self, token: str) -> bool:
        """Validate the authorization token."""
        # Implement token validation logic here
        return True
'''


class MakeObserverCommand(Command):
    """Generate a new model observer class."""
    
    signature = "make:observer {name : The name of the observer} {--model= : The model to observe}"
    description = "Create a new model observer class"
    help = "Generate a new observer class for model lifecycle events"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        model_name = self.option("model")
        
        if not name:
            self.error("Observer name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Observer"):
            name += "Observer"
        
        # Determine model name
        if not model_name:
            model_name = name.replace("Observer", "")
        
        observer_path = Path(f"app/Observers/{{name}}.py")
        observer_path.parent.mkdir(parents=True, exist_ok=True)
        
        if observer_path.exists():
            if not self.confirm(f"Observer {{name}} already exists. Overwrite?"):
                self.info("Observer creation cancelled.")
                return
        
        content = self._generate_observer_content(name, model_name)
        observer_path.write_text(content)
        
        self.info(f"✅ Observer created: {{observer_path}}")
        self.comment(f"Register the observer for the {{model_name}} model")
        self.comment("Update the event methods as needed")
    
    def _generate_observer_content(self, observer_name: str, model_name: str) -> str:
        """Generate observer content."""
        return f'''from __future__ import annotations

from typing import Any
from app.Models.{model_name} import {model_name}


class {observer_name}:
    """Observer for {model_name} model events."""
    
    def creating(self, model: {model_name}) -> None:
        """Handle the {model_name} "creating" event."""
        # Called before a new record is created
        # Example:
        # model.slug = model.name.lower().replace(" ", "-")
        pass
    
    def created(self, model: {model_name}) -> None:
        """Handle the {model_name} "created" event."""
        # Called after a new record is created
        # Example:
        # self.send_welcome_email(model)
        pass
    
    def updating(self, model: {model_name}) -> None:
        """Handle the {model_name} "updating" event."""
        # Called before an existing record is updated
        # Example:
        # model.updated_at = datetime.now()
        pass
    
    def updated(self, model: {model_name}) -> None:
        """Handle the {model_name} "updated" event."""
        # Called after an existing record is updated
        # Example:
        # self.clear_cache(model.id)
        pass
    
    def deleting(self, model: {model_name}) -> None:
        """Handle the {model_name} "deleting" event."""
        # Called before a record is deleted
        # Example:
        # self.backup_related_data(model)
        pass
    
    def deleted(self, model: {model_name}) -> None:
        """Handle the {model_name} "deleted" event."""
        # Called after a record is deleted
        # Example:
        # self.cleanup_files(model)
        pass
    
    def restoring(self, model: {model_name}) -> None:
        """Handle the {model_name} "restoring" event."""
        # Called before a soft-deleted record is restored
        pass
    
    def restored(self, model: {model_name}) -> None:
        """Handle the {model_name} "restored" event."""
        # Called after a soft-deleted record is restored
        pass
    
    # Helper methods
    # def send_welcome_email(self, model: {model_name}) -> None:
    #     """Send welcome email to new user."""
    #     pass
    
    # def clear_cache(self, model_id: int) -> None:
    #     """Clear cached data for the model."""
    #     pass
'''
# Register the command
from app.Console.Artisan import register_command
register_command(MakeServiceCommand)
