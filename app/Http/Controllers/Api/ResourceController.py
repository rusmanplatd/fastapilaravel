"""
Laravel-style Resource Controller for RESTful operations
"""
from __future__ import annotations

from typing import Dict, List, Optional, Type, TypeVar, Generic, Union
from abc import ABC, abstractmethod
from datetime import datetime
from fastapi import HTTPException, status, Request
from pydantic import BaseModel as PydanticModel

from app.Models.BaseModel import BaseModel
from app.Http.Controllers.BaseController import BaseController
from app.Http.Resources.JsonResource import JsonResource

T = TypeVar('T', bound=BaseModel)
ResourceType = TypeVar('ResourceType', bound=JsonResource)


class ResourceController(BaseController, Generic[T, ResourceType], ABC):
    """
    Laravel-style Resource Controller base class
    Provides standard RESTful operations (index, show, store, update, destroy)
    """
    
    # Define these in subclasses
    model_class: Optional[Type[T]] = None
    resource_class: Optional[Type[ResourceType]] = None
    create_schema: Optional[Type[PydanticModel]] = None
    update_schema: Optional[Type[PydanticModel]] = None
    
    # Pagination
    per_page: int = 15
    max_per_page: int = 100
    
    # Middleware and validation
    middleware: List[str] = []
    
    def __init__(self) -> None:
        super().__init__()
        if not self.model_class:
            raise ValueError(f"{self.__class__.__name__} must define model_class")
        if not self.resource_class:
            raise ValueError(f"{self.__class__.__name__} must define resource_class")
    
    async def index(self, request: Request) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Dict[str, Union[str, int, bool, None]]]]]:
        """
        Display a listing of the resource (GET /)
        Laravel equivalent: public function index()
        """
        # Get query parameters
        page = int(request.query_params.get('page', 1))
        per_page = min(int(request.query_params.get('per_page', self.per_page)), self.max_per_page)
        search = request.query_params.get('search', '')
        sort_by = request.query_params.get('sort_by', 'created_at')
        sort_order = request.query_params.get('sort_order', 'desc')
        
        # Build query
        query = self.build_index_query(request)
        
        # Apply search if provided
        if search:
            query = self.apply_search(query, search)
        
        # Apply sorting
        query = self.apply_sorting(query, sort_by, sort_order)
        
        # Get total count
        total = await self.count_query(query)
        
        # Apply pagination
        offset = (page - 1) * per_page
        items: List[T] = await self.paginate_query(query, offset, per_page)
        
        # Transform with resource
        if not self.resource_class:
            raise ValueError("resource_class must be defined")
        resource_collection = [self.resource_class(item) for item in items]
        
        return {
            'data': [resource.to_dict() for resource in resource_collection],
            'meta': {
                'total': total,
                'per_page': per_page,
                'current_page': page,
                'last_page': (total + per_page - 1) // per_page,
                'from': offset + 1 if items else None,
                'to': offset + len(items) if items else None,
            },
            'links': self.build_pagination_links(request, page, per_page, total)
        }
    
    async def show(self, id: str, request: Request) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Dict[str, Union[str, int, bool, None]]]]]:
        """
        Display the specified resource (GET /{id})
        Laravel equivalent: public function show($id)
        """
        item = await self.find_or_fail(id)
        
        # Load relationships if specified
        with_relations = request.query_params.get('with', '').split(',')
        if with_relations and with_relations[0]:
            item = await self.load_relationships(item, with_relations)
        
        if not self.resource_class:
            raise ValueError("resource_class must be defined")
        resource = self.resource_class(item)
        return {'data': resource.to_dict()}
    
    async def store(self, data: Dict[str, Union[str, int, bool, List[str]]], request: Request) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Dict[str, Union[str, int, bool, None]]]]]:
        """
        Store a newly created resource (POST /)
        Laravel equivalent: public function store(Request $request)
        """
        # Validate with create schema
        if self.create_schema:
            validated_data = self.validate_with_schema(data, self.create_schema)
        else:
            validated_data = data
        
        # Create the item
        item = await self.create_item(validated_data, request)
        
        # Transform with resource
        if not self.resource_class:
            raise ValueError("resource_class must be defined")
        if not self.model_class:
            raise ValueError("model_class must be defined")
        resource = self.resource_class(item)
        
        return {
            'data': resource.to_dict(),
            'message': f'{self.model_class.__name__} created successfully'
        }
    
    async def update(self, id: str, data: Dict[str, Union[str, int, bool, List[str]]], request: Request) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Dict[str, Union[str, int, bool, None]]]]]:
        """
        Update the specified resource (PUT/PATCH /{id})
        Laravel equivalent: public function update(Request $request, $id)
        """
        item = await self.find_or_fail(id)
        
        # Validate with update schema
        if self.update_schema:
            validated_data = self.validate_with_schema(data, self.update_schema)
        else:
            validated_data = data
        
        # Update the item
        updated_item = await self.update_item(item, validated_data, request)
        
        # Transform with resource
        if not self.resource_class:
            raise ValueError("resource_class must be defined")
        if not self.model_class:
            raise ValueError("model_class must be defined")
        resource = self.resource_class(updated_item)
        
        return {
            'data': resource.to_dict(),
            'message': f'{self.model_class.__name__} updated successfully'
        }
    
    async def destroy(self, id: str, request: Request) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Dict[str, Union[str, int, bool, None]]]]]:
        """
        Remove the specified resource (DELETE /{id})
        Laravel equivalent: public function destroy($id)
        """
        item = await self.find_or_fail(id)
        
        await self.delete_item(item, request)
        
        if not self.model_class:
            raise ValueError("model_class must be defined")
        return {
            'message': f'{self.model_class.__name__} deleted successfully'
        }
    
    # Helper methods that can be overridden in subclasses
    
    def build_index_query(self, request: Request) -> object:
        """Build the base query for index method"""
        from app.Foundation.Application import app
        
        if not self.model_class:
            raise ValueError("model_class must be defined")
        
        # Get database session from the application container
        db = app().make('db')
        if db is None:
            raise ValueError("Database session not available in container")
        
        return db.query(self.model_class)
    
    def apply_search(self, query: object, search: str) -> object:
        """Apply search filters to query"""
        # Override in subclasses to implement search
        return query
    
    def apply_sorting(self, query: object, sort_by: str, sort_order: str) -> object:
        """Apply sorting to query"""
        # Override in subclasses to implement sorting
        return query
    
    async def count_query(self, query: object) -> int:
        """Count total records for pagination"""
        try:
            count_result = query.count()
            return int(count_result)
        except Exception:
            return 0
    
    async def paginate_query(self, query: object, offset: int, limit: int) -> List[T]:
        """Apply pagination to query"""
        try:
            from typing import cast
            result = query.offset(offset).limit(limit).all()
            return cast(List[T], result)
        except Exception:
            return []
    
    async def find_or_fail(self, id: str) -> T:
        """Find item by ID or raise 404"""
        from app.Foundation.Application import app
        
        if not self.model_class:
            raise ValueError("model_class must be defined")
        
        # Get database session from the application container
        db = app().make('db')
        if db is None:
            raise ValueError("Database session not available in container")
        
        try:
            # Convert string ID to appropriate type
            try:
                item_id = int(id) if id.isdigit() else id
            except ValueError:
                item_id = id
                
            item = db.query(self.model_class).filter(self.model_class.id == item_id).first()
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.model_class.__name__} not found"
                )
            from typing import cast
            return cast(T, item)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving {self.model_class.__name__}: {str(e)}"
            )
    
    async def load_relationships(self, item: T, relations: List[str]) -> T:
        """Load specified relationships"""
        # Implementation depends on your ORM setup
        return item
    
    async def create_item(self, data: Dict[str, Union[str, int, bool, List[str]]], request: Request) -> T:
        """Create new item"""
        from app.Foundation.Application import app
        
        if not self.model_class:
            raise ValueError("model_class must be defined")
        
        # Get database session from the application container
        db = app().make('db')
        if db is None:
            raise ValueError("Database session not available in container")
        
        # Use fillable attributes if defined
        if hasattr(self.model_class, '__fillable__'):
            filtered_data = {k: v for k, v in data.items() if k in self.model_class.__fillable__}
        else:
            filtered_data = data
        
        try:
            item = self.model_class(**filtered_data)
            db.add(item)
            db.commit()
            db.refresh(item)
            return item
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating {self.model_class.__name__}: {str(e)}"
            )
    
    async def update_item(self, item: T, data: Dict[str, Union[str, int, bool, List[str]]], request: Request) -> T:
        """Update existing item"""
        from app.Foundation.Application import app
        
        if not self.model_class:
            raise ValueError("model_class must be defined")
        
        # Get database session from the application container
        db = app().make('db')
        if db is None:
            raise ValueError("Database session not available in container")
        
        # Use fillable attributes if defined
        if hasattr(self.model_class, '__fillable__'):
            filtered_data = {k: v for k, v in data.items() if k in self.model_class.__fillable__}
        else:
            filtered_data = data
        
        try:
            # Update attributes
            for key, value in filtered_data.items():
                setattr(item, key, value)
            
            db.commit()
            db.refresh(item)
            return item
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating {self.model_class.__name__}: {str(e)}"
            )
    
    async def delete_item(self, item: T, request: Request) -> None:
        """Delete item"""
        from app.Foundation.Application import app
        
        # Get database session from the application container
        db = app().make('db')
        if db is None:
            raise ValueError("Database session not available in container")
        
        try:
            db.delete(item)
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting item: {str(e)}"
            )
    
    def validate_with_schema(self, data: Dict[str, Union[str, int, bool, List[str]]], schema_class: Type[PydanticModel]) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Dict[str, Union[str, int, bool, None]]]]]:
        """Validate data with Pydantic schema"""
        try:
            validated = schema_class(**data)
            if hasattr(validated, 'dict'):
                return validated.dict()
            else:
                return validated.__dict__
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )
    
    def build_pagination_links(self, request: Request, current_page: int, per_page: int, total: int) -> Dict[str, Optional[str]]:
        """Build pagination links"""
        base_url = str(getattr(request, 'url', '')).split('?')[0]
        last_page = (total + per_page - 1) // per_page
        
        def build_link(page: int) -> str:
            return f"{base_url}?page={page}&per_page={per_page}"
        
        return {
            'first': build_link(1) if current_page > 1 else None,
            'last': build_link(last_page) if current_page < last_page else None,
            'prev': build_link(current_page - 1) if current_page > 1 else None,
            'next': build_link(current_page + 1) if current_page < last_page else None,
        }


class ApiResourceController(ResourceController[T, ResourceType]):
    """
    API Resource Controller with additional API-specific features
    """
    
    # API-specific settings
    api_version: str = 'v1'
    rate_limit: Optional[str] = None
    
    def __init__(self) -> None:
        super().__init__()
        # Add API-specific middleware
        self.middleware.extend(['throttle', 'auth:api'])
    
    async def index(self, request: Request) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Dict[str, Union[str, int, bool, None]]]]]:
        """API version of index with additional metadata"""
        result = await super().index(request)
        
        # Add API metadata
        result['meta'].update({
            'api_version': self.api_version,
            'timestamp': datetime.now().isoformat(),
        })
        
        return result
    
    async def bulk_store(self, data: List[Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]]]]], request: Request) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Dict[str, Union[str, int, bool, None]]]]]:
        """Bulk create multiple resources (POST /bulk)"""
        created_items = []
        
        for item_data in data:
            if self.create_schema:
                validated_data = self.validate_with_schema(item_data, self.create_schema)
            else:
                validated_data = item_data
            
            item = await self.create_item(validated_data, request)
            created_items.append(item)
        
        # Transform with resources
        if not self.resource_class:
            raise ValueError("resource_class must be defined")
        if not self.model_class:
            raise ValueError("model_class must be defined")
        resource_collection = [self.resource_class(item) for item in created_items]
        
        return {
            'data': [resource.to_dict() for resource in resource_collection],
            'message': f'{len(created_items)} {self.model_class.__name__} records created successfully'
        }
    
    async def bulk_update(self, updates: List[Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]]]]], request: Request) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Dict[str, Union[str, int, bool, None]]]]]:
        """Bulk update multiple resources (PUT /bulk)"""
        updated_items = []
        
        for update_data in updates:
            if 'id' not in update_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Each update must include an 'id' field"
                )
            
            item_id = update_data.pop('id')
            item = await self.find_or_fail(item_id)
            
            if self.update_schema:
                validated_data = self.validate_with_schema(update_data, self.update_schema)
            else:
                validated_data = update_data
            
            updated_item = await self.update_item(item, validated_data, request)
            updated_items.append(updated_item)
        
        # Transform with resources
        if not self.resource_class:
            raise ValueError("resource_class must be defined")
        if not self.model_class:
            raise ValueError("model_class must be defined")
        resource_collection = [self.resource_class(item) for item in updated_items]
        
        return {
            'data': [resource.to_dict() for resource in resource_collection],
            'message': f'{len(updated_items)} {self.model_class.__name__} records updated successfully'
        }
    
    async def bulk_destroy(self, ids: List[str], request: Request) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Dict[str, Union[str, int, bool, None]]]]]:
        """Bulk delete multiple resources (DELETE /bulk)"""
        deleted_count = 0
        
        for item_id in ids:
            try:
                item = await self.find_or_fail(item_id)
                await self.delete_item(item, request)
                deleted_count += 1
            except HTTPException:
                # Skip items that don't exist
                continue
        
        if not self.model_class:
            raise ValueError("model_class must be defined")
        return {
            'message': f'{deleted_count} {self.model_class.__name__} records deleted successfully'
        }