from __future__ import annotations

import click
import os
from pathlib import Path
from typing import Optional


@click.group()
def make() -> None:
    """Laravel-style make commands for generating code."""
    pass


@make.command()
@click.argument('name')
@click.option('--resource', '-r', is_flag=True, help='Create a resource controller')
@click.option('--api', is_flag=True, help='Create an API controller')
@click.option('--model', '-m', help='Create a model with this controller')
def controller(name: str, resource: bool, api: bool, model: Optional[str]) -> None:
    """Create a new controller class."""
    
    # Convert name to proper format
    controller_name = name if name.endswith('Controller') else f"{name}Controller"
    
    # Create controller content
    content = f"""from __future__ import annotations

from typing import Dict, Any, List
from fastapi import Depends, HTTPException
from app.Http.Controllers.BaseController import BaseController
"""
    
    if model:
        content += f"from app.Models.{model} import {model}\n"
        
    content += f"""

class {controller_name}(BaseController):
    \"\"\"
    {controller_name.replace('Controller', '')} Controller.
    \"\"\"
    
    def __init__(self) -> None:
        super().__init__()
"""
    
    if resource:
        content += f"""
    async def index(self) -> List[Dict[str, Any]]:
        \"\"\"Display a listing of the resource.\"\"\"
        from app.Foundation.Application import app
        db = app.resolve('db')
        
        # Return paginated list of resources
        try:
            # TODO: Replace with actual model logic
            return []
        except Exception as error:
            raise HTTPException(status_code=500, detail="Failed to fetch resources: " + str(error))
    
    async def show(self, id: int) -> Dict[str, Any]:
        \"\"\"Display the specified resource.\"\"\"
        from app.Foundation.Application import app
        db = app.resolve('db')
        
        # Find resource by ID
        try:
            # TODO: Replace with actual model logic
            return {{"id": id}}
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(status_code=500, detail="Failed to fetch resource: " + str(error))
    
    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"Store a newly created resource.\"\"\"
        from app.Foundation.Application import app
        db = app.resolve('db')
        
        # Create new resource
        try:
            if model:
                model_class = getattr(__import__(f'app.Models.{model}', fromlist=[model]), model)
                
                # Validate required fields
                fillable = getattr(model_class, 'fillable', [])
                resource_data = {{k: v for k, v in data.items() if k in fillable}}
                
                if not resource_data:
                    raise HTTPException(status_code=400, detail="No valid data provided")
                
                resource = model_class(**resource_data)
                db.add(resource)
                db.commit()
                db.refresh(resource)
                
                return {{
                    'id': resource.id,
                    'message': 'Resource created successfully',
                    **resource_data
                }}
            return data
        except HTTPException:
            raise
        except Exception as error:
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to create resource: " + str(error))
    
    async def update(self, id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"Update the specified resource.\"\"\"
        from app.Foundation.Application import app
        db = app.resolve('db')
        
        # Update existing resource
        try:
            if model:
                model_class = getattr(__import__(f'app.Models.{model}', fromlist=[model]), model)
                resource = db.query(model_class).filter(model_class.id == id).first()
                
                if not resource:
                    raise HTTPException(status_code=404, detail="Resource not found")
                
                # Validate and update only fillable fields
                fillable = getattr(model_class, 'fillable', [])
                update_data = {{k: v for k, v in data.items() if k in fillable}}
                
                if not update_data:
                    raise HTTPException(status_code=400, detail="No valid data provided")
                
                for key, value in update_data.items():
                    setattr(resource, key, value)
                
                db.commit()
                db.refresh(resource)
                
                return {{
                    'id': resource.id,
                    'message': 'Resource updated successfully',
                    **update_data
                }}
            return {{"id": id, **data}}
        except HTTPException:
            raise
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update resource: {{str(exc)}}")
    
    async def destroy(self, id: int) -> Dict[str, str]:
        \"\"\"Remove the specified resource.\"\"\"
        from app.Foundation.Application import app
        db = app.resolve('db')
        
        # Delete resource by ID
        try:
            if model:
                model_class = getattr(__import__(f'app.Models.{model}', fromlist=[model]), model)
                resource = db.query(model_class).filter(model_class.id == id).first()
                
                if not resource:
                    raise HTTPException(status_code=404, detail="Resource not found")
                
                db.delete(resource)
                db.commit()
                
                return {{
                    "message": f"Resource with ID {{id}} deleted successfully",
                    "deleted_id": id
                }}
            return {{"message": "Resource deleted"}}
        except HTTPException:
            raise
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete resource: {{str(exc)}}")
"""
    else:
        content += """
    async def handle(self) -> Dict[str, Any]:
        \"\"\"Handle the request.\"\"\"
        from app.Foundation.Application import app
        
        # Implement your business logic here
        try:
            # Get application context
            from app.Support.Facades.Auth import Auth
            from app.Support.Facades.Cache import Cache
            
            # Example: Get current user if authenticated
            current_user = Auth.user()
            user_info = {{
                'user_id': current_user.id if current_user else None,
                'authenticated': current_user is not None
            }}
            
            # Example: Use caching for expensive operations
            cache_key = f"controller_response_{{hash(str(user_info))}}"
            cached_response = Cache.get(cache_key)
            
            if cached_response:
                return cached_response
            
            response = {{
                "message": "Controller executed successfully",
                "timestamp": app.resolve('datetime').utcnow().isoformat(),
                "user": user_info,
                "status": "success"
            }}
            
            # Cache the response for 5 minutes
            Cache.put(cache_key, response, 300)
            
            return response
            
        except Exception as exc:
            return {{
                "message": "Controller execution failed",
                "error": str(exc),
                "status": "error"
            }}
"""
    
    # Write the file
    controller_path = Path("app/Http/Controllers") / f"{controller_name}.py"
    controller_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(controller_path, 'w') as f:
        f.write(content)
    
    click.echo(f"Controller created: {controller_path}")
    
    if model:
        # Also create the model if requested
        create_model(model)


@make.command()
@click.argument('name')
@click.option('--migration', '-m', is_flag=True, help='Create a migration file')
@click.option('--controller', '-c', is_flag=True, help='Create a controller')
@click.option('--resource', '-r', is_flag=True, help='Create a resource controller')
def model(name: str, migration: bool, controller: bool, resource: bool) -> None:
    """Create a new Eloquent model."""
    create_model(name, migration, controller, resource)


def create_model(name: str, migration: bool = False, controller: bool = False, resource: bool = False) -> None:
    """Create a model file."""
    
    content = f"""from __future__ import annotations

from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.Models.BaseModel import BaseModel


class {name}(BaseModel):
    \"\"\"
    {name} Model.
    \"\"\"
    
    __tablename__ = '{name.lower()}s'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Fillable attributes
    fillable = ['name']
    
    # Hidden attributes (not included in serialization)
    hidden: List[str] = []
    
    def __repr__(self) -> str:
        return f"<{name}(id={{self.id}}, name='{{self.name}}')>"
"""
    
    # Write the file
    model_path = Path("app/Models") / f"{name}.py"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(model_path, 'w') as f:
        f.write(content)
    
    click.echo(f"Model created: {model_path}")
    
    if migration:
        create_migration(f"create_{name.lower()}s_table")
    
    if controller:
        from app.Console.Commands.make import controller as create_controller
        create_controller(f"{name}Controller", resource, False, name)


@make.command()
@click.argument('name')
@click.option('--create', help='Create a new table')
@click.option('--table', help='Modify an existing table')
def migration(name: str, create: Optional[str], table: Optional[str]) -> None:
    """Create a new database migration."""
    create_migration(name, create, table)


def create_migration(name: str, create: Optional[str] = None, table: Optional[str] = None) -> None:
    """Create a migration file."""
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
    migration_name = f"{timestamp}_{name}"
    
    if create:
        table_name = create
        content = f"""from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers
revision = '{timestamp}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    \"\"\"Create {table_name} table.\"\"\"
    op.create_table('{table_name}',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    \"\"\"Drop {table_name} table.\"\"\"
    op.drop_table('{table_name}')
"""
    else:
        content = f"""from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers  
revision = '{timestamp}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    \"\"\"Migration up.\"\"\"
    # Add your migration logic here
    # Example: op.create_table(...), op.add_column(...), etc.
    pass


def downgrade() -> None:
    \"\"\"Migration down.\"\"\"
    # Add your rollback logic here
    # Example: op.drop_table(...), op.drop_column(...), etc.
    pass
"""
    
    # Write the file
    migration_path = Path("database/migrations") / f"{migration_name}.py"
    migration_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(migration_path, 'w') as f:
        f.write(content)
    
    click.echo(f"Migration created: {migration_path}")


@make.command() 
@click.argument('name')
def middleware(name: str) -> None:
    """Create a new middleware class."""
    
    middleware_name = name if name.endswith('Middleware') else f"{name}Middleware"
    
    content = f"""from __future__ import annotations

from typing import Callable, Awaitable, Any
from starlette.requests import Request
from fastapi import Response
from app.Http.Middleware.BaseMiddleware import BaseMiddleware


class {middleware_name}(BaseMiddleware):
    \"\"\"
    {middleware_name.replace('Middleware', '')} Middleware.
    \"\"\"
    
    async def __call__(
        self, 
        request: Request, 
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        \"\"\"Process the request.\"\"\"
        
        # Before request processing
        # Add your pre-processing logic here
        
        response = await call_next(request)
        
        # After request processing  
        # Add your post-processing logic here
        
        return response
"""
    
    # Write the file
    middleware_path = Path("app/Http/Middleware") / f"{middleware_name}.py"
    middleware_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(middleware_path, 'w') as f:
        f.write(content)
    
    click.echo(f"Middleware created: {middleware_path}")


@make.command()
@click.argument('name')
def command(name: str) -> None:
    """Create a new Artisan command."""
    
    command_name = name if name.endswith('Command') else f"{name}Command"
    
    content = f"""from __future__ import annotations

import click
from app.Console.Command import Command


class {command_name}(Command):
    \"\"\"
    {command_name.replace('Command', '')} command.
    \"\"\"
    
    # Command signature
    signature = '{name.lower()}'
    
    # Command description
    description = 'Command description'
    
    @click.command()
    def handle(self) -> None:
        \"\"\"Execute the command.\"\"\"
        self.info('Command executed successfully!')
        
        # Add your command logic here
"""
    
    # Write the file  
    command_path = Path("app/Console/Commands") / f"{command_name}.py"
    command_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(command_path, 'w') as f:
        f.write(content)
    
    click.echo(f"Command created: {command_path}")


if __name__ == '__main__':
    make()