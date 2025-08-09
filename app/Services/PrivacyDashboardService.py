"""Privacy Dashboard Service

This service implements modern privacy dashboard functionality including
privacy checkups, data export, connected apps management, and privacy controls.
"""

from __future__ import annotations

import json
import secrets
import zipfile
import tempfile
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy.orm import Session

from app.Models.User import User


class PrivacyDashboardService:
    """Service for managing user privacy dashboard and controls."""
    
    def __init__(self) -> None:
        """Initialize the service."""
        pass
    
    def get_privacy_dashboard(self, user: User) -> Dict[str, Any]:
        """
        Get comprehensive privacy dashboard for a user.
        
        Args:
            user: User instance
            
        Returns:
            Privacy dashboard data
        """
        return {
            'user_id': str(user.id),
            'privacy_checkup': {
                'needed': user._needs_privacy_checkup(),
                'last_completed': user.last_privacy_checkup.isoformat() if user.last_privacy_checkup else None,
                'next_due': self._get_next_checkup_date(user),
                'completion_rate': self._calculate_privacy_completion_rate(user)
            },
            'activity_controls': self._get_activity_controls_summary(user),
            'data_management': {
                'storage_usage': {
                    'used_gb': round(user.storage_used_mb / 1024, 2),
                    'total_gb': user.storage_quota_gb,
                    'percentage': round((user.storage_used_mb / (user.storage_quota_gb * 1024)) * 100, 1)
                },
                'auto_delete_enabled': user.auto_delete_activity_months is not None,
                'auto_delete_months': user.auto_delete_activity_months,
                'recent_exports': self._get_recent_exports(user)
            },
            'third_party_access': self._get_third_party_access_summary(user),
            'privacy_settings': self._get_privacy_settings_summary(user),
            'security_overview': {
                'security_score': user.calculate_security_score(),
                'mfa_enabled': user.mfa_enabled,
                'recent_security_events': len(user._get_recent_security_events(limit=10))
            }
        }
    
    def run_privacy_checkup(self, user: User, db: Session) -> Dict[str, Any]:
        """
        Run comprehensive privacy checkup for a user.
        
        Args:
            user: User instance
            db: Database session
            
        Returns:
            Privacy checkup results
        """
        checkup_items = []
        
        # Check activity controls
        activity_status = self._check_activity_controls(user)
        checkup_items.append({
            'category': 'Activity Controls',
            'status': activity_status['status'],
            'recommendations': activity_status['recommendations'],
            'action_required': activity_status['action_required']
        })
        
        # Check privacy settings
        privacy_status = self._check_privacy_settings(user)
        checkup_items.append({
            'category': 'Privacy Settings',
            'status': privacy_status['status'],
            'recommendations': privacy_status['recommendations'],
            'action_required': privacy_status['action_required']
        })
        
        # Check data management
        data_status = self._check_data_management(user)
        checkup_items.append({
            'category': 'Data Management',
            'status': data_status['status'],
            'recommendations': data_status['recommendations'],
            'action_required': data_status['action_required']
        })
        
        # Check third-party access
        third_party_status = self._check_third_party_access(user)
        checkup_items.append({
            'category': 'Third-party Access',
            'status': third_party_status['status'],
            'recommendations': third_party_status['recommendations'],
            'action_required': third_party_status['action_required']
        })
        
        # Check security settings
        security_status = self._check_security_settings(user)
        checkup_items.append({
            'category': 'Security Settings',
            'status': security_status['status'],
            'recommendations': security_status['recommendations'],
            'action_required': security_status['action_required']
        })
        
        # Calculate overall score
        total_score = sum(item['status']['score'] for item in checkup_items)
        max_score = len(checkup_items) * 100
        overall_score = round((total_score / max_score) * 100)
        
        # Mark checkup as completed
        user.complete_privacy_checkup()
        db.commit()
        db.refresh(user)
        
        return {
            'checkup_completed': True,
            'completed_at': user.last_privacy_checkup.isoformat(),
            'overall_score': overall_score,
            'next_checkup_due': self._get_next_checkup_date(user),
            'checkup_items': checkup_items,
            'summary': {
                'total_items': len(checkup_items),
                'items_needing_attention': len([item for item in checkup_items if item['action_required']]),
                'privacy_level': self._get_privacy_level(overall_score)
            }
        }
    
    def export_user_data(
        self, 
        user: User, 
        export_format: str = 'json',
        include_sections: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Export user data in Google Takeout style.
        
        Args:
            user: User instance
            export_format: Export format (json, csv, xml)
            include_sections: Sections to include in export
            
        Returns:
            Export information
        """
        export_id = secrets.token_urlsafe(16)
        export_data = {}
        
        # Default sections if none specified
        if include_sections is None:
            include_sections = [
                'profile', 'activity', 'security', 'privacy', 'preferences'
            ]
        
        # Export profile data
        if 'profile' in include_sections:
            export_data['profile'] = self._export_profile_data(user)
        
        # Export activity data
        if 'activity' in include_sections:
            export_data['activity'] = self._export_activity_data(user)
        
        # Export security data
        if 'security' in include_sections:
            export_data['security'] = self._export_security_data(user)
        
        # Export privacy data
        if 'privacy' in include_sections:
            export_data['privacy'] = self._export_privacy_data(user)
        
        # Export preferences
        if 'preferences' in include_sections:
            export_data['preferences'] = self._export_preferences_data(user)
        
        # Record export request
        user._add_to_history('data_export_requests', {
            'export_id': export_id,
            'format': export_format,
            'sections': include_sections,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'processing',
            'estimated_size_mb': self._estimate_export_size(export_data)
        })
        
        return {
            'export_id': export_id,
            'format': export_format,
            'sections_included': include_sections,
            'estimated_completion': '15-30 minutes',
            'estimated_size_mb': self._estimate_export_size(export_data),
            'download_expires_days': 7,
            'export_data': export_data if export_format == 'json' else None,
            'message': 'Export initiated. You will receive an email when ready.'
        }
    
    def manage_connected_apps(
        self, 
        user: User, 
        action: str,
        app_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Manage connected third-party applications.
        
        Args:
            user: User instance
            action: Action to perform (list, revoke, audit)
            app_id: App ID for specific actions
            db: Database session
            
        Returns:
            Connected apps management result
        """
        connected_apps = user._get_json_field('oauth_applications') or []
        
        if action == 'list':
            # Return detailed app information
            app_details = []
            for app in connected_apps:
                app_details.append({
                    'id': app.get('id'),
                    'name': app.get('name'),
                    'permissions': app.get('permissions', []),
                    'connected_date': app.get('connected_at'),
                    'last_used': app.get('last_used_at'),
                    'risk_level': self._assess_app_risk(app)
                })
            
            return {
                'connected_apps': app_details,
                'total_apps': len(connected_apps),
                'high_risk_apps': len([app for app in app_details if app['risk_level'] == 'high']),
                'recommendations': self._get_app_recommendations(app_details)
            }
        
        elif action == 'revoke' and app_id:
            # Revoke access for specific app
            app_to_revoke = None
            updated_apps = []
            
            for app in connected_apps:
                if app.get('id') == app_id:
                    app_to_revoke = app
                else:
                    updated_apps.append(app)
            
            if app_to_revoke:
                user._set_json_field('oauth_applications', updated_apps)
                
                # Log revocation
                user._record_security_event('app_access_revoked', {
                    'app_id': app_id,
                    'app_name': app_to_revoke.get('name'),
                    'revoked_at': datetime.now(timezone.utc).isoformat(),
                    'reason': 'user_requested'
                })
                
                if db:
                    db.commit()
                    db.refresh(user)
                
                return {
                    'success': True,
                    'revoked_app': app_to_revoke.get('name'),
                    'remaining_apps': len(updated_apps),
                    'message': f'Revoked access for {app_to_revoke.get("name")}'
                }
            else:
                return {
                    'success': False,
                    'error': f'App with ID {app_id} not found'
                }
        
        elif action == 'audit':
            # Audit all connected apps for security
            audit_results = []
            for app in connected_apps:
                audit_results.append({
                    'app_id': app.get('id'),
                    'app_name': app.get('name'),
                    'risk_assessment': self._assess_app_risk(app),
                    'excessive_permissions': self._check_excessive_permissions(app),
                    'last_used': app.get('last_used_at'),
                    'recommendation': self._get_app_recommendation(app)
                })
            
            return {
                'audit_completed': True,
                'audit_date': datetime.now(timezone.utc).isoformat(),
                'total_apps_audited': len(connected_apps),
                'audit_results': audit_results,
                'summary': {
                    'high_risk_apps': len([r for r in audit_results if r['risk_assessment'] == 'high']),
                    'unused_apps': len([r for r in audit_results if self._is_app_unused(r)]),
                    'excessive_permissions': len([r for r in audit_results if r['excessive_permissions']])
                }
            }
        
        else:
            return {
                'success': False,
                'error': 'Invalid action or missing required parameters'
            }
    
    def update_privacy_settings(
        self, 
        user: User, 
        settings: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """
        Update comprehensive privacy settings.
        
        Args:
            user: User instance
            settings: Privacy settings to update
            db: Database session
            
        Returns:
            Update result
        """
        changes = {}
        
        # Update consent settings
        consent_fields = ['analytics_consent', 'marketing_consent', 'data_processing_consent']
        for field in consent_fields:
            if field in settings and getattr(user, field) != settings[field]:
                changes[field] = {
                    'old': getattr(user, field),
                    'new': settings[field]
                }
                setattr(user, field, settings[field])
        
        # Update visibility settings
        if 'visibility' in settings:
            current_privacy = user._get_json_field('privacy_settings') or {}
            current_privacy.update({'visibility': settings['visibility']})
            user.privacy_settings = json.dumps(current_privacy)
            changes['visibility_settings'] = settings['visibility']
        
        # Update activity controls
        if 'activity_controls' in settings:
            activity_controls = settings['activity_controls']
            for control, enabled in activity_controls.items():
                attr_name = f"{control}_enabled"
                if hasattr(user, attr_name) and getattr(user, attr_name) != enabled:
                    changes[attr_name] = {
                        'old': getattr(user, attr_name),
                        'new': enabled
                    }
                    setattr(user, attr_name, enabled)
        
        if changes:
            user.updated_at = datetime.now(timezone.utc)
            
            # Log privacy settings update
            user._record_security_event('privacy_settings_bulk_update', {
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
            'updated_settings': self._get_privacy_settings_summary(user)
        }
    
    # Private helper methods
    
    def _get_next_checkup_date(self, user: User) -> Optional[str]:
        """Get the next privacy checkup due date."""
        if user.last_privacy_checkup:
            next_date = user.last_privacy_checkup + timedelta(days=180)
            return next_date.isoformat()
        return None
    
    def _calculate_privacy_completion_rate(self, user: User) -> int:
        """Calculate privacy settings completion percentage."""
        total_settings = 10
        completed = 0
        
        # Check if basic privacy settings are configured
        if user.privacy_settings:
            completed += 2
        if user.analytics_consent is not None:
            completed += 1
        if user.marketing_consent is not None:
            completed += 1
        if user.data_processing_consent is not None:
            completed += 1
        if user.auto_delete_activity_months is not None:
            completed += 2
        if user.mfa_enabled:
            completed += 2
        if user.backup_codes:
            completed += 1
        
        return round((completed / total_settings) * 100)
    
    def _get_activity_controls_summary(self, user: User) -> Dict[str, Any]:
        """Get activity controls summary."""
        return {
            'web_app_activity': user.web_app_activity_enabled,
            'location_history': user.location_history_enabled,
            'search_history': user.search_history_enabled,
            'youtube_history': user.youtube_history_enabled,
            'ad_personalization': user.ad_personalization_enabled,
            'auto_delete_enabled': user.auto_delete_activity_months is not None
        }
    
    def _get_recent_exports(self, user: User) -> List[Dict[str, Any]]:
        """Get recent data export requests."""
        exports = user._get_json_field('data_export_requests') or []
        return exports[-5:] if exports else []  # Last 5 exports
    
    def _get_third_party_access_summary(self, user: User) -> Dict[str, Any]:
        """Get third-party access summary."""
        connected_apps = user._get_json_field('oauth_applications') or []
        return {
            'total_connected_apps': len(connected_apps),
            'high_risk_apps': len([app for app in connected_apps if self._assess_app_risk(app) == 'high']),
            'last_audit_date': self._get_last_audit_date(user),
            'audit_needed': len(connected_apps) > 0
        }
    
    def _get_privacy_settings_summary(self, user: User) -> Dict[str, Any]:
        """Get privacy settings summary."""
        privacy_settings = user._get_json_field('privacy_settings') or {}
        return {
            'profile_visibility': privacy_settings.get('visibility', {}).get('profile_visibility', 'public'),
            'email_visibility': privacy_settings.get('visibility', {}).get('email_visibility', 'private'),
            'analytics_consent': user.analytics_consent,
            'marketing_consent': user.marketing_consent,
            'data_processing_consent': user.data_processing_consent
        }
    
    def _check_activity_controls(self, user: User) -> Dict[str, Any]:
        """Check activity controls for privacy checkup."""
        score = 80  # Base score
        recommendations = []
        action_required = False
        
        # Check if too many controls are enabled
        enabled_controls = sum([
            user.web_app_activity_enabled,
            user.location_history_enabled,
            user.search_history_enabled,
            user.youtube_history_enabled
        ])
        
        if enabled_controls >= 4:
            score -= 20
            recommendations.append("Consider disabling some activity tracking for better privacy")
            action_required = True
        
        if not user.auto_delete_activity_months:
            score -= 10
            recommendations.append("Enable auto-delete to automatically remove old activity")
        
        return {
            'status': {'score': max(score, 0), 'level': 'good' if score >= 70 else 'needs_attention'},
            'recommendations': recommendations,
            'action_required': action_required
        }
    
    def _check_privacy_settings(self, user: User) -> Dict[str, Any]:
        """Check privacy settings for privacy checkup."""
        score = 70  # Base score
        recommendations = []
        action_required = False
        
        if user.analytics_consent:
            score -= 10
            recommendations.append("Consider disabling analytics to improve privacy")
        
        if user.marketing_consent:
            score -= 10
            recommendations.append("Consider disabling marketing communications")
        
        if not user.privacy_settings:
            score -= 20
            recommendations.append("Configure detailed privacy settings")
            action_required = True
        
        return {
            'status': {'score': max(score, 0), 'level': 'good' if score >= 70 else 'needs_attention'},
            'recommendations': recommendations,
            'action_required': action_required
        }
    
    def _check_data_management(self, user: User) -> Dict[str, Any]:
        """Check data management for privacy checkup."""
        score = 80
        recommendations = []
        action_required = False
        
        if not user.auto_delete_activity_months:
            score -= 30
            recommendations.append("Enable auto-delete to manage data retention")
            action_required = True
        
        # Check storage usage
        storage_percentage = (user.storage_used_mb / (user.storage_quota_gb * 1024)) * 100
        if storage_percentage > 80:
            score -= 10
            recommendations.append("Consider deleting old data or requesting more storage")
        
        return {
            'status': {'score': max(score, 0), 'level': 'good' if score >= 70 else 'needs_attention'},
            'recommendations': recommendations,
            'action_required': action_required
        }
    
    def _check_third_party_access(self, user: User) -> Dict[str, Any]:
        """Check third-party access for privacy checkup."""
        connected_apps = user._get_json_field('oauth_applications') or []
        score = 90
        recommendations = []
        action_required = False
        
        if len(connected_apps) > 10:
            score -= 20
            recommendations.append("Review and remove unused connected apps")
            action_required = True
        
        # Check for high-risk apps
        high_risk_apps = [app for app in connected_apps if self._assess_app_risk(app) == 'high']
        if high_risk_apps:
            score -= 30
            recommendations.append(f"Review {len(high_risk_apps)} high-risk connected apps")
            action_required = True
        
        return {
            'status': {'score': max(score, 0), 'level': 'good' if score >= 70 else 'needs_attention'},
            'recommendations': recommendations,
            'action_required': action_required
        }
    
    def _check_security_settings(self, user: User) -> Dict[str, Any]:
        """Check security settings for privacy checkup."""
        score = user.calculate_security_score()
        recommendations = []
        action_required = False
        
        if score < 80:
            recommendations.append("Improve security settings for better privacy protection")
            action_required = True
        
        if not user.mfa_enabled:
            recommendations.append("Enable two-factor authentication")
        
        return {
            'status': {'score': score, 'level': 'good' if score >= 80 else 'needs_attention'},
            'recommendations': recommendations,
            'action_required': action_required
        }
    
    def _get_privacy_level(self, score: int) -> str:
        """Get privacy level description."""
        if score >= 90:
            return "Excellent Privacy"
        elif score >= 80:
            return "Good Privacy"
        elif score >= 70:
            return "Fair Privacy"
        elif score >= 60:
            return "Needs Improvement"
        else:
            return "Poor Privacy"
    
    def _export_profile_data(self, user: User) -> Dict[str, Any]:
        """Export profile data section."""
        return {
            'basic_info': {
                'name': user.name,
                'email': user.email,
                'given_name': user.given_name,
                'family_name': user.family_name,
                'phone_number': user.phone_number,
                'created_at': user.created_at.isoformat()
            },
            'profile_details': {
                'bio': user.bio,
                'website': user.website,
                'gender': user.gender,
                'birthdate': user.birthdate,
                'location': user._get_json_field('address')
            }
        }
    
    def _export_activity_data(self, user: User) -> Dict[str, Any]:
        """Export activity data section."""
        return {
            'search_history': user._get_json_field('search_history') or [],
            'login_history': user._get_json_field('login_history') or [],
            'location_history': user._get_json_field('location_history') or [],
            'activity_summary': {
                'total_logins': user.login_count,
                'last_login': user.last_login_at.isoformat() if user.last_login_at else None
            }
        }
    
    def _export_security_data(self, user: User) -> Dict[str, Any]:
        """Export security data section."""
        return {
            'security_overview': user.get_account_security_overview(),
            'security_events': user._get_json_field('security_events') or [],
            'mfa_enabled': user.mfa_enabled,
            'security_score': user.security_score
        }
    
    def _export_privacy_data(self, user: User) -> Dict[str, Any]:
        """Export privacy data section."""
        return {
            'privacy_settings': user._get_json_field('privacy_settings') or {},
            'data_consents': {
                'analytics': user.analytics_consent,
                'marketing': user.marketing_consent,
                'data_processing': user.data_processing_consent
            },
            'activity_controls': self._get_activity_controls_summary(user)
        }
    
    def _export_preferences_data(self, user: User) -> Dict[str, Any]:
        """Export preferences data section."""
        return {
            'language': user.language,
            'timezone': user.zoneinfo,
            'theme': user.theme,
            'notification_settings': user._get_json_field('notification_settings') or {},
            'accessibility_settings': user._get_json_field('accessibility_settings') or {}
        }
    
    def _estimate_export_size(self, export_data: Dict[str, Any]) -> float:
        """Estimate export size in MB."""
        json_str = json.dumps(export_data)
        size_bytes = len(json_str.encode('utf-8'))
        size_mb = size_bytes / (1024 * 1024)
        return round(size_mb, 2)
    
    def _assess_app_risk(self, app: Dict[str, Any]) -> str:
        """Assess risk level of a connected app."""
        permissions = app.get('permissions', [])
        
        # High-risk permissions
        high_risk_permissions = [
            'read_all_data', 'write_all_data', 'admin_access', 
            'financial_data', 'location_data'
        ]
        
        if any(perm in permissions for perm in high_risk_permissions):
            return 'high'
        elif len(permissions) > 5:
            return 'medium'
        else:
            return 'low'
    
    def _check_excessive_permissions(self, app: Dict[str, Any]) -> bool:
        """Check if app has excessive permissions."""
        permissions = app.get('permissions', [])
        return len(permissions) > 8  # Arbitrary threshold
    
    def _get_app_recommendation(self, app: Dict[str, Any]) -> str:
        """Get recommendation for a specific app."""
        risk = self._assess_app_risk(app)
        last_used = app.get('last_used_at')
        
        if risk == 'high':
            return "Consider revoking access due to high risk permissions"
        elif not last_used or self._is_app_unused({'last_used': last_used}):
            return "Consider removing - app appears unused"
        elif self._check_excessive_permissions(app):
            return "Review permissions - app has excessive access"
        else:
            return "App appears safe"
    
    def _get_app_recommendations(self, apps: List[Dict[str, Any]]) -> List[str]:
        """Get general app recommendations."""
        recommendations = []
        
        high_risk_count = len([app for app in apps if app['risk_level'] == 'high'])
        if high_risk_count > 0:
            recommendations.append(f"Review {high_risk_count} high-risk apps")
        
        if len(apps) > 15:
            recommendations.append("Consider reducing the number of connected apps")
        
        unused_apps = len([app for app in apps if self._is_app_unused(app)])
        if unused_apps > 0:
            recommendations.append(f"Remove {unused_apps} unused apps")
        
        return recommendations
    
    def _is_app_unused(self, app: Dict[str, Any]) -> bool:
        """Check if an app appears to be unused."""
        last_used = app.get('last_used')
        if not last_used:
            return True
        
        # Consider unused if not used in 90 days
        try:
            last_used_date = datetime.fromisoformat(last_used.replace('Z', '+00:00'))
            cutoff = datetime.now(timezone.utc) - timedelta(days=90)
            return last_used_date < cutoff
        except (ValueError, AttributeError):
            return True
    
    def _get_last_audit_date(self, user: User) -> Optional[str]:
        """Get the last third-party apps audit date."""
        security_events = user._get_json_field('security_events') or []
        
        for event in reversed(security_events):
            if event.get('type') == 'third_party_apps_audit':
                return event.get('timestamp')
        
        return None


__all__ = ["PrivacyDashboardService"]