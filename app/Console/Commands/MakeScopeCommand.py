from __future__ import annotations

from pathlib import Path
from typing import Optional
from ..Command import Command


class MakeScopeCommand(Command):
    """Generate a new query scope class."""
    
    signature = "make:scope {name : The name of the scope} {--model= : The model to create scope for}"
    description = "Create a new query scope class"
    help = "Generate a new query scope class for model queries"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        model_name = self.option("model")
        
        if not name:
            self.error("Scope name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Scope"):
            name += "Scope"
        
        scope_path = Path(f"app/Scopes/{name}.py")
        scope_path.parent.mkdir(parents=True, exist_ok=True)
        
        if scope_path.exists():
            if not self.confirm(f"Scope {name} already exists. Overwrite?"):
                self.info("Scope creation cancelled.")
                return
        
        content = self._generate_scope_content(name, model_name)
        scope_path.write_text(content)
        
        self.info(f"✅ Scope created: {scope_path}")
        self.comment("Update the apply() method with your query logic")
        
        if model_name:
            self.comment(f"Mix the scope into your {model_name} model:")
            self.comment(f"class {model_name}(BaseModel, {name}):")
            self.comment("    pass")
    
    def _generate_scope_content(self, scope_name: str, model_name: Optional[str] = None) -> str:
        """Generate scope content."""
        model_import = ""
        if model_name:
            model_import = f"\nfrom app.Models.{model_name} import {model_name}"
        
        return f'''from __future__ import annotations

from typing import Any
from sqlalchemy import Select
from abc import ABC, abstractmethod{model_import}


class Scope(ABC):
    """Base scope contract."""
    
    @abstractmethod
    def apply(self, query: Select[Any], model: Any) -> Select[Any]:
        """Apply the scope to the given Eloquent query builder."""
        pass


class {scope_name}(Scope):
    """Custom query scope for filtering and modifying queries."""
    
    def apply(self, query: Select[Any], model: Any) -> Select[Any]:
        """Apply the scope to the query."""
        # Production-ready scope implementation
        # Override this method with your specific logic
        
        # Example implementations (uncomment and modify as needed):
        
        # Filter by active status
        # if hasattr(model, 'status'):
        #     return query.where(model.status == 'active')
        
        # Order by creation date (most recent first)
        # if hasattr(model, 'created_at'):
        #     return query.order_by(model.created_at.desc())
        
        # Filter by date range (last 30 days)
        # if hasattr(model, 'created_at'):
        #     from datetime import datetime, timedelta
        #     return query.where(model.created_at >= datetime.utcnow() - timedelta(days=30))
        
        # Filter by user ownership
        # if hasattr(model, 'user_id'):
        #     from app.Support.Facades.Auth import Auth
        #     current_user = Auth.user()
        #     if current_user:
        #         return query.where(model.user_id == current_user.id)
        
        # Complex filtering with multiple conditions
        # if hasattr(model, 'status') and hasattr(model, 'published_at'):
        #     from datetime import datetime
        #     return query.where(
        #         (model.status == 'published') & 
        #         (model.published_at <= datetime.utcnow())
        #     )
        
        # Join with related model
        # from app.Models.RelatedModel import RelatedModel
        # return query.join(RelatedModel).where(RelatedModel.active == True)
        
        # Default: return query unchanged
        return query


# Mixin class for adding scope methods to models
class {scope_name}Mixin:
    """Mixin to add scope methods to models."""
    
    @classmethod
    def scope_{scope_name.lower().replace('scope', '')}(cls, query: Select[Any]) -> Select[Any]:
        """Apply the {scope_name.lower().replace('scope', '')} scope."""
        scope = {scope_name}()
        return scope.apply(query, cls)


# Example usage in model:
# 
# Method 1: Using the scope directly
# class User(BaseModel):
#     @classmethod 
#     def active_users(cls, db):
#         scope = {scope_name}()
#         query = db.query(cls)
#         return scope.apply(query, cls).all()
# 
# Method 2: Using the mixin
# class User(BaseModel, {scope_name}Mixin):
#     pass
# 
# # Then use: User.scope_{scope_name.lower().replace('scope', '')}(query)
'''
# Register command
from app.Console.Artisan import register_command
register_command(MakeScopeCommand)
