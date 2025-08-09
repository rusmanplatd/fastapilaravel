from __future__ import annotations

from typing import Any, Dict, List, Union, Callable, Optional
from app.View.View import view_manager, View as ViewClass


class View:
    """Laravel-style View facade."""
    
    @staticmethod
    def make(view: str, data: Optional[Dict[str, Any]] = None, merge_data: Optional[Dict[str, Any]] = None) -> ViewClass:
        """Create a view instance."""
        return view_manager.make(view, data, merge_data)
    
    @staticmethod
    def exists(view: str) -> bool:
        """Check if view exists."""
        return view_manager.exists(view)
    
    @staticmethod
    def share(key: Union[str, Dict[str, Any]], value: Any = None) -> None:
        """Share data with all views."""
        view_manager.share(key, value)
    
    @staticmethod
    def composer(views: Union[str, List[str]], callback: Callable) -> None:
        """Register view composer."""
        view_manager.composer(views, callback)
    
    @staticmethod
    def render(view: str, data: Optional[Dict[str, Any]] = None) -> str:
        """Render view to string."""
        return view_manager.render(view, data)
    
    @staticmethod
    def add_extension(extension: str) -> None:
        """Add template file extension."""
        view_manager.add_extension(extension)
    
    @staticmethod
    def add_path(path: str) -> None:
        """Add template search path."""
        view_manager.add_path(path)
    
    @staticmethod
    def first(views: List[str], data: Optional[Dict[str, Any]] = None) -> ViewClass:
        """Get the first view that exists."""
        for view_name in views:
            if view_manager.exists(view_name):
                return view_manager.make(view_name, data)
        
        raise FileNotFoundError(f"None of the views exist: {', '.join(views)}")
    
    @staticmethod
    def get_shared() -> Dict[str, Any]:
        """Get all shared view data."""
        return view_manager._shared_data.copy()
    
    @staticmethod
    def get_composers() -> Dict[str, List[Callable]]:
        """Get all view composers."""
        return view_manager._composers.copy()
    
    @staticmethod
    def flush_shared() -> None:
        """Clear all shared view data."""
        view_manager._shared_data.clear()
    
    @staticmethod
    def flush_composers() -> None:
        """Clear all view composers."""
        view_manager._composers.clear()