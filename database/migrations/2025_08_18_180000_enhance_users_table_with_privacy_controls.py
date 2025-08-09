"""Enhance Users Table Migration

This migration enhances the existing users table with modern user management features
including privacy controls, security settings, activity tracking, and comprehensive
user management capabilities.
"""

from __future__ import annotations

from database.Schema.Migration import AlterTableMigration
from database.Schema.Blueprint import Blueprint


class EnhanceUsersTableWithPrivacyControls(AlterTableMigration):
    """Enhance existing users table with comprehensive user management features."""
    
    def up(self) -> None:
        """Run the migrations to enhance users table."""
        def enhance_users_table(table: Blueprint) -> None:
            # Enhanced Privacy and Activity Controls
            table.boolean("web_app_activity_enabled").default(True).comment("Enable Web & App Activity")
            table.boolean("search_history_enabled").default(True).comment("Enable search history tracking")
            table.boolean("youtube_history_enabled").default(True).comment("Enable YouTube watch/search history")
            table.boolean("location_history_enabled").default(False).comment("Enable location history (Timeline)")
            table.boolean("ad_personalization_enabled").default(True).comment("Enable personalized ads")
            table.boolean("voice_audio_activity_enabled").default(False).comment("Include voice and audio activity")
            table.boolean("device_info_enabled").default(True).comment("Include device information")
            table.integer("auto_delete_activity_months").nullable().comment("Auto-delete activity after N months")
            
            # Service Integration
            table.boolean("photos_face_grouping_enabled").default(True).comment("Enable face grouping in Photos")
            table.boolean("drive_suggestions_enabled").default(True).comment("Enable Drive suggestions")
            table.boolean("purchase_history_enabled").default(True).comment("Track purchase history")
            table.text("payments_profile").nullable().comment("Payment profile information")
            
            # Enhanced Privacy and Data Management
            table.text("privacy_settings").nullable().comment("User privacy preferences")
            table.text("data_sharing_consent").nullable().comment("Data sharing agreements")
            table.boolean("analytics_consent").default(False).comment("Analytics data consent")
            table.boolean("marketing_consent").default(False).comment("Marketing communications consent")
            table.boolean("data_processing_consent").default(False).comment("Data processing consent")
            table.text("data_export_requests").nullable().comment("Data export request history")
            table.text("data_deletion_requests").nullable().comment("Data deletion request history")
            
            # Privacy Dashboard tracking
            table.timestamp("last_privacy_checkup").nullable().comment("Last privacy checkup timestamp")
            table.boolean("privacy_checkup_required").default(True).comment("Privacy checkup required flag")
            
            # Enhanced Activity Tracking
            table.text("search_history").nullable().comment("Search history data")
            table.text("location_history").nullable().comment("Location history data")
            
            # Enhanced Account Management
            table.string("account_type", 20).default("personal").comment("Account type (personal, business, etc.)")
            table.boolean("is_organization_account").default(False).comment("Part of organization")
            table.string("organization_domain").nullable().comment("Organization domain")
            table.text("linked_accounts").nullable().comment("Linked external accounts")
            table.text("app_passwords").nullable().comment("Application-specific passwords")
            table.integer("storage_quota_gb").default(15).comment("Storage quota in GB")
            table.integer("storage_used_mb").default(0).comment("Storage used in MB")
            
            # Enhanced Security Features
            table.text("backup_codes").nullable().comment("MFA backup codes")
            table.text("security_keys").nullable().comment("WebAuthn security keys")
            table.text("trusted_devices").nullable().comment("Trusted device tokens")
            table.boolean("security_checkup_required").default(False).comment("Security review needed")
            table.timestamp("last_security_checkup").nullable().comment("Last security review")
            table.text("suspicious_activities").nullable().comment("Flagged suspicious activities")
            table.boolean("compromised_password_check").default(True).comment("Check against breached passwords")
            
            # Enhanced Personalization
            table.string("theme", 20).default("system").comment("UI theme preference")
            table.text("notification_settings").nullable().comment("Notification preferences")
            table.text("accessibility_settings").nullable().comment("Accessibility preferences")
            
            # API and Developer Features
            table.integer("api_rate_limit").default(1000).comment("API rate limit per hour")
            table.text("api_scopes").nullable().comment("Granted API scopes")
            table.text("oauth_applications").nullable().comment("Authorized OAuth applications")
            table.text("webhooks").nullable().comment("Configured webhooks")
            
            # Compliance and Legal
            table.timestamp("terms_accepted_at").nullable().comment("Terms of service acceptance")
            table.string("terms_version").nullable().comment("Accepted terms version")
            table.timestamp("privacy_policy_accepted_at").nullable().comment("Privacy policy acceptance")
            table.string("privacy_policy_version").nullable().comment("Accepted privacy policy version")
            table.text("gdpr_consents").nullable().comment("GDPR consent records")
            
            # Enhanced Features
            table.text("feature_flags").nullable().comment("Enabled feature flags")
            table.text("experiments").nullable().comment("A/B test participations")
            table.text("metadata").nullable().comment("Additional metadata")
            table.text("tags").nullable().comment("User classification tags")
            
            # Enhanced Profile Information
            table.string("job_title").nullable().comment("Job title or role")
            table.string("department").nullable().comment("Department or team")
            table.string("employee_id").nullable().comment("Employee identifier")
            table.string("manager_email").nullable().comment("Manager's email address")
            table.text("work_location").nullable().comment("Work location information")
            table.text("skills").nullable().comment("Professional skills")
            table.text("social_links").nullable().comment("Social media profile links")
            table.text("education").nullable().comment("Educational background")
            table.text("certifications").nullable().comment("Professional certifications")
            table.text("interests").nullable().comment("Personal interests")
            table.text("custom_fields").nullable().comment("Custom profile fields")
            
            # Audit Fields
            table.string("created_by").nullable().comment("User creator identifier")
            table.string("updated_by").nullable().comment("Last updater identifier")
            table.timestamp("deleted_at").nullable().comment("Soft delete timestamp")
            table.string("deleted_by").nullable().comment("User who deleted account")
            table.text("deletion_reason").nullable().comment("Reason for account deletion")
            
            # Add indexes for performance
            table.index(["web_app_activity_enabled"])
            table.index(["ad_personalization_enabled"])
            table.index(["privacy_checkup_required"])
            table.index(["last_privacy_checkup"])
            table.index(["deleted_at"])
            
        # Use table modification instead of creation
        self.schema.table("users", enhance_users_table)
    
    def down(self) -> None:
        """Reverse the migrations."""
        def remove_enhancements(table: Blueprint) -> None:
            # Remove added columns (in reverse order)
            columns_to_drop = [
                "web_app_activity_enabled", "search_history_enabled", "youtube_history_enabled",
                "location_history_enabled", "ad_personalization_enabled", "voice_audio_activity_enabled",
                "device_info_enabled", "auto_delete_activity_months", "photos_face_grouping_enabled",
                "drive_suggestions_enabled", "purchase_history_enabled", "payments_profile",
                "privacy_settings", "data_sharing_consent", "analytics_consent", "marketing_consent",
                "data_processing_consent", "data_export_requests", "data_deletion_requests",
                "last_privacy_checkup", "privacy_checkup_required", "search_history", "location_history",
                "account_type", "is_organization_account", "organization_domain", "linked_accounts",
                "app_passwords", "storage_quota_gb", "storage_used_mb", "backup_codes", "security_keys",
                "trusted_devices", "security_checkup_required", "last_security_checkup",
                "suspicious_activities", "compromised_password_check", "theme", "notification_settings",
                "accessibility_settings", "api_rate_limit", "api_scopes", "oauth_applications",
                "webhooks", "terms_accepted_at", "terms_version", "privacy_policy_accepted_at",
                "privacy_policy_version", "gdpr_consents", "feature_flags", "experiments",
                "metadata", "tags", "job_title", "department", "employee_id", "manager_email",
                "work_location", "skills", "social_links", "education", "certifications",
                "interests", "custom_fields", "created_by", "updated_by", "deleted_at",
                "deleted_by", "deletion_reason"
            ]
            
            for column in columns_to_drop:
                table.drop_column(column)
        
        self.schema.table("users", remove_enhancements)


__all__ = ["EnhanceUsersTableWithPrivacyControls"]