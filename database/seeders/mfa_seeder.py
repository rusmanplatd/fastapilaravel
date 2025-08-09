from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets

from app.Models import User, UserMFASettings, WebAuthnCredential
from app.Models.User import User as UserModel
from app.Models.UserMFASettings import UserMFASettings as MFASettingsModel
from app.Models.WebAuthnCredential import WebAuthnCredential as WebAuthnCredentialModel


def seed_mfa_data(db: Session) -> None:
    """Seed MFA test data"""
    print("🔐 Seeding MFA test data...")
    
    # Get test users
    test_user = db.query(UserModel).filter(UserModel.email == "test@example.com").first()
    admin_user = db.query(UserModel).filter(UserModel.email == "admin@example.com").first()
    
    if test_user:
        # Enable TOTP for test user
        mfa_settings = MFASettingsModel(
            user_id=test_user.id,
            totp_enabled=True,
            totp_secret="JBSWY3DPEHPK3PXP",  # Test secret for "Hello World"
            totp_backup_tokens="BACKUP01,BACKUP02,BACKUP03,BACKUP04,BACKUP05",
            webauthn_enabled=False,
            sms_enabled=False,
            is_required=True,
            last_used_at=datetime.utcnow() - timedelta(hours=1)
        )
        db.merge(mfa_settings)
        print(f"   ✓ TOTP enabled for {test_user.email}")
    
    if admin_user:
        # Enable both TOTP and WebAuthn for admin user
        mfa_settings = MFASettingsModel(
            user_id=admin_user.id,
            totp_enabled=True,
            totp_secret="JBSWY3DPEHPK3PXQ",  # Different test secret
            totp_backup_tokens="ADMIN01,ADMIN02,ADMIN03,ADMIN04,ADMIN05",
            webauthn_enabled=True,
            sms_enabled=False,
            is_required=False,  # Optional for admin
            last_used_at=datetime.utcnow() - timedelta(minutes=30)
        )
        db.merge(mfa_settings)
        
        # Add sample WebAuthn credential for admin
        webauthn_credential = WebAuthnCredentialModel(
            user_id=admin_user.id,
            credential_id="sample-credential-id-12345",
            public_key="sample-public-key-base64-encoded-here",
            sign_count=0,
            name="YubiKey 5",
            aaguid="f8a011f3-8c0a-4d15-8006-17111f9edc7d",
            last_used_at=None
        )
        db.merge(webauthn_credential)
        print(f"   ✓ TOTP and WebAuthn enabled for {admin_user.email}")
    
    # Create an MFA-required user
    mfa_required_user = db.query(UserModel).filter(UserModel.email == "mfa@example.com").first()
    if not mfa_required_user:
        from app.Utils import PasswordUtils
        mfa_required_user = UserModel(
            name="MFA Required User",
            email="mfa@example.com",
            password=PasswordUtils.hash_password("password123"),
            is_active=True,
            is_verified=True,
            email_verified_at=datetime.utcnow()
        )
        db.add(mfa_required_user)
        db.flush()  # Get the ID
        
        # Enable MFA requirement
        mfa_settings = MFASettingsModel(
            user_id=mfa_required_user.id,
            totp_enabled=True,
            totp_secret="JBSWY3DPEHPK3PXR",
            totp_backup_tokens="REQMFA01,REQMFA02,REQMFA03,REQMFA04,REQMFA05",
            webauthn_enabled=False,
            sms_enabled=False,
            is_required=True
        )
        db.add(mfa_settings)
        print(f"   ✓ Created MFA-required user: {mfa_required_user.email}")
    
    # Create a WebAuthn-only user
    webauthn_user = db.query(UserModel).filter(UserModel.email == "webauthn@example.com").first()
    if not webauthn_user:
        from app.Utils import PasswordUtils
        webauthn_user = UserModel(
            name="WebAuthn User",
            email="webauthn@example.com",
            password=PasswordUtils.hash_password("password123"),
            is_active=True,
            is_verified=True,
            email_verified_at=datetime.utcnow()
        )
        db.add(webauthn_user)
        db.flush()  # Get the ID
        
        # Enable only WebAuthn
        mfa_settings = MFASettingsModel(
            user_id=webauthn_user.id,
            totp_enabled=False,
            webauthn_enabled=True,
            sms_enabled=False,
            is_required=False
        )
        db.add(mfa_settings)
        
        # Add sample WebAuthn credential
        webauthn_credential = WebAuthnCredentialModel(
            user_id=webauthn_user.id,
            credential_id="webauthn-only-credential-67890",
            public_key="webauthn-public-key-base64-encoded",
            sign_count=5,
            name="Touch ID",
            aaguid="08987058-cadc-4b81-b6e1-30de50dcbe96",
            last_used_at=datetime.utcnow() - timedelta(days=2)
        )
        db.add(webauthn_credential)
        print(f"   ✓ Created WebAuthn-only user: {webauthn_user.email}")
    
    db.commit()
    print("✅ MFA seeding completed!")


def seed_mfa_test_scenarios(db: Session) -> None:
    """Seed additional test scenarios for MFA"""
    print("🧪 Seeding MFA test scenarios...")
    
    # User with multiple WebAuthn devices
    multi_device_user = db.query(UserModel).filter(UserModel.email == "multidevice@example.com").first()
    if not multi_device_user:
        from app.Utils import PasswordUtils
        multi_device_user = UserModel(
            name="Multi Device User",
            email="multidevice@example.com",
            password=PasswordUtils.hash_password("password123"),
            is_active=True,
            is_verified=True,
            email_verified_at=datetime.utcnow()
        )
        db.add(multi_device_user)
        db.flush()
        
        # Enable WebAuthn
        mfa_settings = MFASettingsModel(
            user_id=multi_device_user.id,
            totp_enabled=False,
            webauthn_enabled=True,
            sms_enabled=False,
            is_required=True
        )
        db.add(mfa_settings)
        
        # Add multiple WebAuthn credentials
        credentials = [
            {
                "credential_id": "device-1-yubikey-credential",
                "public_key": "yubikey-public-key-base64",
                "name": "YubiKey Security Key",
                "aaguid": "f8a011f3-8c0a-4d15-8006-17111f9edc7d",
                "sign_count": 15
            },
            {
                "credential_id": "device-2-touchid-credential", 
                "public_key": "touchid-public-key-base64",
                "name": "MacBook Touch ID",
                "aaguid": "08987058-cadc-4b81-b6e1-30de50dcbe96",
                "sign_count": 42
            },
            {
                "credential_id": "device-3-faceid-credential",
                "public_key": "faceid-public-key-base64", 
                "name": "iPhone Face ID",
                "aaguid": "00000000-0000-0000-0000-000000000000",
                "sign_count": 8
            }
        ]
        
        for cred_data in credentials:
            credential = WebAuthnCredentialModel(
                user_id=multi_device_user.id,
                credential_id=cred_data["credential_id"],
                public_key=cred_data["public_key"],
                sign_count=cred_data["sign_count"],
                name=cred_data["name"],
                aaguid=cred_data["aaguid"],
                last_used_at=datetime.utcnow() - timedelta(hours=secrets.randbelow(72))
            )
            db.add(credential)
        
        print(f"   ✓ Created multi-device user: {multi_device_user.email}")
    
    db.commit()
    print("✅ MFA test scenarios completed!")


if __name__ == "__main__":
    from config.database import SessionLocal
    
    db = SessionLocal()
    try:
        seed_mfa_data(db)
        seed_mfa_test_scenarios(db)
    finally:
        db.close()