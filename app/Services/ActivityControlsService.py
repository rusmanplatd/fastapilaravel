"""Activity Controls Service

This service implements modern activity controls for managing user data collection,
privacy settings, and auto-delete functionality.
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.Models.User import User
from app.Support.ServiceContainer import container


class ActivityControlsService:
    """Service for managing user activity controls and privacy settings."""
    
    def __init__(self) -> None:
        """Initialize the service."""
        pass
    
    def get_activity_controls(self, user: User) -> Dict[str, Any]:
        """
        Get comprehensive activity controls for a user.
        
        Args:
            user: GoogleUser instance
            
        Returns:
            Activity controls configuration
        """
        return {
            'user_id': str(user.id),
            'controls': {
                'web_app_activity': {
                    'enabled': user.web_app_activity_enabled,
                    'include_voice_audio': user.voice_audio_activity_enabled,
                    'include_device_info': user.device_info_enabled,
                    'description': 'Saves your activity on Google sites and apps to give you faster searches, better recommendations, and more personalized experiences.'
                },
                'location_history': {
                    'enabled': user.location_history_enabled,
                    'description': 'Saves where you go with your devices to give you personalized maps, recommendations based on places you\'ve visited, and more.'
                },
                'search_history': {
                    'enabled': user.search_history_enabled,
                    'description': 'Saves your search queries to provide better search suggestions and personalized results.'
                },
                'youtube_history': {
                    'enabled': user.youtube_history_enabled,
                    'description': 'Saves your YouTube watch and search history to improve recommendations and remember where you left off.'
                },
                'ad_personalization': {
                    'enabled': user.ad_personalization_enabled,
                    'description': 'Uses your activity to personalize ads across Google services and partner websites.'
                }
            },
            'auto_delete': {
                'enabled': user.auto_delete_activity_months is not None,
                'months': user.auto_delete_activity_months,
                'available_options': [3, 6, 12, 18, 24, 36],
                'description': 'Automatically delete activity older than the selected time period.'
            },
            'data_summary': {
                'total_search_queries': len(user._get_json_field('search_history') or []),
                'total_login_events': len(user._get_json_field('login_history') or []),
                'storage_used_mb': user.storage_used_mb,
                'last_activity_cleanup': self._get_last_cleanup_date(user)
            }
        }
    
    def update_activity_controls(
        self, 
        user: User, 
        controls: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """
        Update user activity controls.
        
        Args:
            user: GoogleUser instance
            controls: New control settings
            db: Database session
            
        Returns:
            Update result
        """
        changes = {}
        
        # Update Web & App Activity
        if 'web_app_activity' in controls:
            web_app = controls['web_app_activity']
            if isinstance(web_app, dict):
                if 'enabled' in web_app and web_app['enabled'] != user.web_app_activity_enabled:
                    changes['web_app_activity_enabled'] = {
                        'old': user.web_app_activity_enabled,
                        'new': web_app['enabled']
                    }
                    user.web_app_activity_enabled = web_app['enabled']
                
                if 'include_voice_audio' in web_app:
                    user.voice_audio_activity_enabled = web_app['include_voice_audio']
                
                if 'include_device_info' in web_app:
                    user.device_info_enabled = web_app['include_device_info']
        
        # Update Location History
        if 'location_history' in controls:
            location = controls['location_history']
            if isinstance(location, dict) and 'enabled' in location:
                if location['enabled'] != user.location_history_enabled:
                    changes['location_history_enabled'] = {
                        'old': user.location_history_enabled,
                        'new': location['enabled']
                    }
                    user.location_history_enabled = location['enabled']
        
        # Update other controls
        control_mappings = {
            'search_history': 'search_history_enabled',
            'youtube_history': 'youtube_history_enabled',
            'ad_personalization': 'ad_personalization_enabled'
        }
        
        for control_key, attr_name in control_mappings.items():
            if control_key in controls:
                control_value = controls[control_key]
                enabled = control_value.get('enabled', True) if isinstance(control_value, dict) else control_value
                
                current_value = getattr(user, attr_name)
                if enabled != current_value:
                    changes[attr_name] = {
                        'old': current_value,
                        'new': enabled
                    }
                    setattr(user, attr_name, enabled)
        
        # Update auto-delete settings
        if 'auto_delete_months' in controls:
            months = controls['auto_delete_months']
            if months != user.auto_delete_activity_months:
                changes['auto_delete_activity_months'] = {
                    'old': user.auto_delete_activity_months,
                    'new': months
                }
                user.auto_delete_activity_months = months
        
        # Save changes
        if changes:
            user.updated_at = datetime.now(timezone.utc)
            
            # Log the changes
            user._record_security_event('activity_controls_updated', {
                'changes': list(changes.keys()),
                'updated_at': user.updated_at.isoformat(),
                'change_details': changes
            })
            
            db.commit()
            db.refresh(user)
        
        return {
            'success': True,
            'changes_made': len(changes),
            'changes': changes,
            'updated_controls': self.get_activity_controls(user)
        }
    
    def pause_all_activity(self, user: User, db: Session) -> Dict[str, Any]:
        """
        Pause all activity tracking (bulk action).
        
        Args:
            user: User instance
            db: Database session
            
        Returns:
            Pause result
        """
        paused_controls = []
        
        # Pause all activity controls
        controls_to_pause = [
            ('web_app_activity_enabled', 'Web & App Activity'),
            ('location_history_enabled', 'Location History'),
            ('search_history_enabled', 'Search History'),
            ('youtube_history_enabled', 'YouTube History'),
            ('ad_personalization_enabled', 'Ad Personalization')
        ]
        
        for attr_name, display_name in controls_to_pause:
            if getattr(user, attr_name):
                setattr(user, attr_name, False)
                paused_controls.append(display_name)
        
        if paused_controls:
            user.updated_at = datetime.now(timezone.utc)
            
            # Log bulk pause action
            user._record_security_event('bulk_activity_controls_paused', {
                'paused_controls': paused_controls,
                'paused_at': user.updated_at.isoformat(),
                'action_type': 'bulk_pause'
            })
            
            db.commit()
            db.refresh(user)
        
        return {
            'success': True,
            'paused_controls': paused_controls,
            'message': f'Paused {len(paused_controls)} activity controls'
        }
    
    def delete_activity_data(
        self, 
        user: User, 
        activity_types: List[str],
        date_range: Optional[Dict[str, str]] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Delete specific activity data (My Activity style).
        
        Args:
            user: User instance
            activity_types: Types of activity to delete
            date_range: Optional date range for deletion
            db: Database session
            
        Returns:
            Deletion result
        """
        deleted_data = {}
        
        # Delete search history
        if 'search' in activity_types:
            search_history = user._get_json_field('search_history') or []
            if date_range:
                # Filter by date range (placeholder implementation)
                filtered_history = self._filter_by_date_range(search_history, date_range)
                remaining_history = [item for item in search_history if item not in filtered_history]
                user._set_json_field('search_history', remaining_history)
                deleted_data['search_queries'] = len(filtered_history)
            else:
                deleted_data['search_queries'] = len(search_history)
                user._set_json_field('search_history', [])
        
        # Delete login history (security events)
        if 'login' in activity_types:
            login_history = user._get_json_field('login_history') or []
            if date_range:
                filtered_logins = self._filter_by_date_range(login_history, date_range)
                remaining_logins = [item for item in login_history if item not in filtered_logins]
                user._set_json_field('login_history', remaining_logins)
                deleted_data['login_events'] = len(filtered_logins)
            else:
                deleted_data['login_events'] = len(login_history)
                user._set_json_field('login_history', [])
        
        # Delete location history
        if 'location' in activity_types:
            location_history = user._get_json_field('location_history') or []
            if date_range:
                filtered_locations = self._filter_by_date_range(location_history, date_range)
                remaining_locations = [item for item in location_history if item not in filtered_locations]
                user._set_json_field('location_history', remaining_locations)
                deleted_data['location_events'] = len(filtered_locations)
            else:
                deleted_data['location_events'] = len(location_history)
                user._set_json_field('location_history', [])
        
        if deleted_data and db:
            user.updated_at = datetime.now(timezone.utc)
            
            # Log activity deletion
            user._record_security_event('activity_data_deleted', {
                'deleted_types': activity_types,
                'deleted_counts': deleted_data,
                'date_range': date_range,
                'deleted_at': user.updated_at.isoformat()
            })
            
            db.commit()
            db.refresh(user)
        
        return {
            'success': True,
            'deleted_data': deleted_data,
            'message': f'Deleted activity data for {len(activity_types)} categories'
        }
    
    def setup_auto_delete(
        self, 
        user: User, 
        months: Optional[int],
        db: Session
    ) -> Dict[str, Any]:
        """
        Setup auto-delete for activity data.
        
        Args:
            user: User instance
            months: Number of months to keep data (None to disable)
            db: Database session
            
        Returns:
            Setup result
        """
        valid_months = [3, 6, 12, 18, 24, 36]
        
        if months is not None and months not in valid_months:
            return {
                'success': False,
                'error': f'Invalid auto-delete period. Must be one of: {valid_months}'
            }
        
        old_setting = user.auto_delete_activity_months
        user.auto_delete_activity_months = months
        user.updated_at = datetime.now(timezone.utc)
        
        # Log auto-delete setting change
        user._record_security_event('auto_delete_configured', {
            'old_months': old_setting,
            'new_months': months,
            'enabled': months is not None,
            'configured_at': user.updated_at.isoformat()
        })
        
        db.commit()
        db.refresh(user)
        
        return {
            'success': True,
            'auto_delete_months': months,
            'enabled': months is not None,
            'message': f'Auto-delete {"enabled" if months else "disabled"}'
        }
    
    def run_auto_delete_cleanup(self, user: User, db: Session) -> Dict[str, Any]:
        """
        Run auto-delete cleanup for a user.
        
        Args:
            user: User instance
            db: Database session
            
        Returns:
            Cleanup result
        """
        if not user.auto_delete_activity_months:
            return {
                'success': False,
                'message': 'Auto-delete not enabled for this user'
            }
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=user.auto_delete_activity_months * 30)
        cutoff_str = cutoff_date.isoformat()
        
        cleaned_data = {}
        
        # Clean search history
        search_history = user._get_json_field('search_history') or []
        original_count = len(search_history)
        cleaned_search = [
            item for item in search_history 
            if item.get('timestamp', '') > cutoff_str
        ]
        if len(cleaned_search) != original_count:
            user._set_json_field('search_history', cleaned_search)
            cleaned_data['search_queries'] = original_count - len(cleaned_search)
        
        # Clean login history
        login_history = user._get_json_field('login_history') or []
        original_count = len(login_history)
        cleaned_login = [
            item for item in login_history 
            if item.get('timestamp', '') > cutoff_str
        ]
        if len(cleaned_login) != original_count:
            user._set_json_field('login_history', cleaned_login)
            cleaned_data['login_events'] = original_count - len(cleaned_login)
        
        # Clean security events (keep recent ones)
        security_events = user._get_json_field('security_events') or []
        original_count = len(security_events)
        cleaned_security = [
            item for item in security_events 
            if item.get('timestamp', '') > cutoff_str
        ]
        if len(cleaned_security) != original_count:
            user._set_json_field('security_events', cleaned_security)
            cleaned_data['security_events'] = original_count - len(cleaned_security)
        
        if cleaned_data:
            user.updated_at = datetime.now(timezone.utc)
            
            # Log cleanup
            user._record_security_event('auto_delete_cleanup', {
                'cutoff_date': cutoff_str,
                'cleaned_data': cleaned_data,
                'cleanup_at': user.updated_at.isoformat()
            })
            
            db.commit()
            db.refresh(user)
        
        return {
            'success': True,
            'cleaned_data': cleaned_data,
            'cutoff_date': cutoff_str,
            'total_items_deleted': sum(cleaned_data.values())
        }
    
    def _filter_by_date_range(
        self, 
        data: List[Dict[str, Any]], 
        date_range: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Filter data by date range.
        
        Args:
            data: List of data items with timestamps
            date_range: Date range with 'start' and 'end' keys
            
        Returns:
            Filtered data list
        """
        start_date = date_range.get('start')
        end_date = date_range.get('end')
        
        filtered = []
        for item in data:
            item_date = item.get('timestamp')
            if not item_date:
                continue
            
            if start_date and item_date < start_date:
                continue
            
            if end_date and item_date > end_date:
                continue
            
            filtered.append(item)
        
        return filtered
    
    def _get_last_cleanup_date(self, user: User) -> Optional[str]:
        """Get the last auto-delete cleanup date."""
        security_events = user._get_json_field('security_events') or []
        
        for event in reversed(security_events):
            if event.get('type') == 'auto_delete_cleanup':
                return event.get('timestamp')
        
        return None


__all__ = ["ActivityControlsService"]