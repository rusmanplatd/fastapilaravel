from __future__ import annotations

from typing import Dict, Any
from datetime import datetime
from app.View.View import ViewComposer


class AppComposer(ViewComposer):
    """Global app data composer."""
    
    def compose(self, view_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add global app data to all views."""
        return {
            'app_name': 'FastAPI Laravel',
            'current_year': datetime.now().year,
            'version': '1.0.0',
            'environment': 'development'
        }


class StatsComposer(ViewComposer):
    """Statistics data composer."""
    
    def compose(self, view_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add statistics data to views."""
        # In a real app, these would query the database
        return {
            'user_count': 150,
            'oauth_client_count': 12,
            'permission_count': 45,
            'role_count': 8
        }


class NavigationComposer(ViewComposer):
    """Navigation data composer."""
    
    def compose(self, view_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add navigation data to views."""
        return {
            'navigation_items': [
                {'name': 'Home', 'url': '/', 'active': True},
                {'name': 'API Docs', 'url': '/docs', 'active': False},
                {'name': 'OAuth2', 'url': '/oauth', 'active': False},
                {'name': 'Queue', 'url': '/queue', 'active': False},
            ]
        }


# Register composers
def register_view_composers() -> None:
    """Register all view composers."""
    from app.View import composer
    
    # Global composer for all views
    composer('*', AppComposer())
    
    # Statistics composer for specific views
    composer(['welcome', 'dashboard.*'], StatsComposer())
    
    # Navigation composer for layout views
    composer(['layouts.*', 'welcome'], NavigationComposer())


# Auto-register when imported
register_view_composers()