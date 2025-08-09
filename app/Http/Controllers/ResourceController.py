"""
Laravel-style Resource Controller for RESTful operations
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, TypeVar
from abc import ABC, abstractmethod
from fastapi import HTTPException, status, Request
from pydantic import BaseModel as PydanticModel

from app.Models.BaseModel import BaseModel
from app.Http.Controllers.BaseController import BaseController
from app.Http.Resources.JsonResource import JsonResource

T = TypeVar('T', bound=BaseModel)
ResourceType = TypeVar('ResourceType', bound=JsonResource)


class ResourceController(BaseController, ABC):
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
    
    def __init__(self):
        super().__init__()
        if not self.model_class:
            raise ValueError(f"{self.__class__.__name__} must define model_class")
        if not self.resource_class:
            raise ValueError(f"{self.__class__.__name__} must define resource_class")
    
    async def index(self, request: Request) -> Dict[str, Any]:
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
        items = await self.paginate_query(query, offset, per_page)
        
        # Transform with resource
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
    
    async def show(self, id: str, request: Request) -> Dict[str, Any]:
        """
        Display the specified resource (GET /{id})
        Laravel equivalent: public function show($id)
        """
        item = await self.find_or_fail(id)
        
        # Load relationships if specified
        with_relations = request.query_params.get('with', '').split(',')
        if with_relations and with_relations[0]:
            item = await self.load_relationships(item, with_relations)
        
        resource = self.resource_class(item)
        return {'data': resource.to_dict()}
    
    async def store(self, data: Dict[str, Any], request: Request) -> Dict[str, Any]:
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
        resource = self.resource_class(item)
        
        return {
            'data': resource.to_dict(),
            'message': f'{self.model_class.__name__} created successfully'
        }
    
    async def update(self, id: str, data: Dict[str, Any], request: Request) -> Dict[str, Any]:
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
        resource = self.resource_class(updated_item)
        
        return {
            'data': resource.to_dict(),
            'message': f'{self.model_class.__name__} updated successfully'
        }
    
    async def destroy(self, id: str, request: Request) -> Dict[str, Any]:
        """
        Remove the specified resource (DELETE /{id})
        Laravel equivalent: public function destroy($id)
        """
        item = await self.find_or_fail(id)
        
        await self.delete_item(item, request)
        
        return {
            'message': f'{self.model_class.__name__} deleted successfully'
        }
    
    # Helper methods that can be overridden in subclasses
    
    def build_index_query(self, request: Request):
        """Build the base query for index method"""
        # This would return a SQLAlchemy query
        # Implementation depends on your database setup
        return self.model_class.query()
    
    def apply_search(self, query, search: str):
        """Apply search filters to query"""
        # Override in subclasses to implement search
        return query
    
    def apply_sorting(self, query, sort_by: str, sort_order: str):
        """Apply sorting to query"""
        # Override in subclasses to implement sorting
        return query
    
    async def count_query(self, query) -> int:
        """Count total records for pagination"""
        # Implementation depends on your database setup
        return 0
    
    async def paginate_query(self, query, offset: int, limit: int) -> List[T]:
        """Apply pagination to query"""
        # Implementation depends on your database setup
        return []
    
    async def find_or_fail(self, id: str) -> T:
        """Find item by ID or raise 404"""
        # Implementation depends on your database setup
        item = await self.model_class.find(id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{self.model_class.__name__} not found"
            )
        return item
    
    async def load_relationships(self, item: T, relations: List[str]) -> T:
        """Load specified relationships"""
        # Implementation depends on your ORM setup
        return item
    
    async def create_item(self, data: Dict[str, Any], request: Request) -> T:
        """Create new item"""
        # Use fillable attributes if defined
        if hasattr(self.model_class, '__fillable__'):
            filtered_data = {k: v for k, v in data.items() if k in self.model_class.__fillable__}
        else:
            filtered_data = data
        
        # Implementation depends on your database setup
        item = self.model_class(**filtered_data)
        await item.save()
        return item
    
    async def update_item(self, item: T, data: Dict[str, Any], request: Request) -> T:
        """Update existing item"""
        # Use fillable attributes if defined
        if hasattr(self.model_class, '__fillable__'):
            filtered_data = {k: v for k, v in data.items() if k in self.model_class.__fillable__}
        else:
            filtered_data = data
        
        # Update attributes
        for key, value in filtered_data.items():
            setattr(item, key, value)
        
        await item.save()
        return item
    
    async def delete_item(self, item: T, request: Request) -> None:
        """Delete item"""
        await item.delete()
    
    def validate_with_schema(self, data: Dict[str, Any], schema_class: Type[PydanticModel]) -> Dict[str, Any]:
        """Validate data with Pydantic schema"""
        try:
            validated = schema_class(**data)
            return validated.model_dump()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )
    
    def build_pagination_links(self, request: Request, current_page: int, per_page: int, total: int) -> Dict[str, Optional[str]]:
        """Build pagination links"""
        base_url = str(request.url).split('?')[0]
        last_page = (total + per_page - 1) // per_page
        
        def build_link(page: int) -> str:
            return f"{base_url}?page={page}&per_page={per_page}"
        
        return {
            'first': build_link(1) if current_page > 1 else None,
            'last': build_link(last_page) if current_page < last_page else None,
            'prev': build_link(current_page - 1) if current_page > 1 else None,
            'next': build_link(current_page + 1) if current_page < last_page else None,
        }


class ApiResourceController(ResourceController):
    """
    API Resource Controller with additional API-specific features
    """
    
    # API-specific settings
    api_version: str = 'v1'
    rate_limit: Optional[str] = None
    
    def __init__(self):
        super().__init__()
        # Add API-specific middleware
        self.middleware.extend(['throttle', 'auth:api'])
    
    async def index(self, request: Request) -> Dict[str, Any]:
        """API version of index with additional metadata"""
        result = await super().index(request)
        
        # Add API metadata
        result['meta'].update({
            'api_version': self.api_version,
            'timestamp': self.get_current_timestamp(),
        })
        
        return result
    
    async def bulk_store(self, data: List[Dict[str, Any]], request: Request) -> Dict[str, Any]:
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
        resource_collection = [self.resource_class(item) for item in created_items]
        
        return {
            'data': [resource.to_dict() for resource in resource_collection],
            'message': f'{len(created_items)} {self.model_class.__name__} records created successfully'
        }
    
    async def bulk_update(self, updates: List[Dict[str, Any]], request: Request) -> Dict[str, Any]:
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
        resource_collection = [self.resource_class(item) for item in updated_items]
        
        return {
            'data': [resource.to_dict() for resource in resource_collection],
            'message': f'{len(updated_items)} {self.model_class.__name__} records updated successfully'
        }
    
    async def bulk_destroy(self, ids: List[str], request: Request) -> Dict[str, Any]:
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
        
        return {
            'message': f'{deleted_count} {self.model_class.__name__} records deleted successfully'
        }