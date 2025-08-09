# Multi-Factor Authentication & WebAuthn System

## Overview

The MFA system provides comprehensive multi-factor authentication with support for TOTP (Time-based One-Time Passwords), WebAuthn/FIDO2, SMS, and backup codes. It includes advanced security features, analytics, and policy management.

## MFA Service Architecture

### Current Implementation
**Location:** `app/Services/MFAService.py`

**Supported MFA Methods:**
- **TOTP** - Time-based One-Time Passwords (Google Authenticator, Authy, etc.)
- **WebAuthn/FIDO2** - Hardware security keys, biometric authentication
- **SMS** - Text message verification codes
- **Backup Codes** - Single-use recovery codes
- **App Push** - Mobile app push notifications (planned)

### MFA Service Features

**Core Functionality:**
```python
from app.Services.MFAService import MFAService

# Get comprehensive MFA status
mfa_service = MFAService(db)
mfa_status = mfa_service.get_mfa_status(user)

# Example response
{
    "mfa_enabled": True,
    "mfa_required": False,
    "methods": {
        "totp": {"enabled": True, "setup": True},
        "webauthn": {"enabled": True, "credentials_count": 2},
        "sms": {"enabled": False, "phone_number": None}
    },
    "backup_codes_remaining": 7,
    "last_used": "2024-08-19T10:30:00Z"
}
```

**MFA Flow Management:**
```python
# Start MFA challenge
session = mfa_service.start_mfa_session(user, available_methods=["totp", "webauthn"])

# Verify MFA response
result = mfa_service.verify_mfa_challenge(
    session_id=session.id,
    method="totp",
    code="123456",
    request_info=request_info
)

# Complete MFA flow
if result.success:
    mfa_service.complete_mfa_session(session.id)
    # User is now authenticated with MFA
```

## TOTP (Time-based One-Time Passwords)

### Current Implementation
**Location:** `app/Services/TOTPService.py`

**Features:**
- RFC 6238 compliant TOTP generation
- QR code generation for easy setup
- Multiple backup codes
- Time window tolerance
- Replay attack prevention

### TOTP Setup Process

**Initial Setup:**
```python
from app.Services.TOTPService import TOTPService

totp_service = TOTPService(db)

# Generate TOTP secret for user
setup_result = totp_service.setup_totp(user)

# Response includes
{
    "secret": "JBSWY3DPEHPK3PXP",  # Base32 encoded secret
    "qr_code_url": "data:image/png;base64,iVBORw0KGgoAAAAN...",
    "manual_entry_key": "jbsw-y3dp-ehpk-3pxp",  # Formatted for manual entry
    "backup_codes": ["12345678", "87654321", ...],  # 10 backup codes
    "issuer": "FastAPI Laravel",
    "account_name": "user@example.com"
}
```

**QR Code Generation:**
```python
# Generate styled QR code
qr_code = totp_service.generate_qr_code(
    user=user,
    secret=secret,
    style="modern",  # modern, classic, minimal
    logo_path="/path/to/logo.png",  # Optional logo
    color_scheme="blue"  # blue, green, red, custom
)

# Returns SVG or PNG based on configuration
```

**TOTP Verification:**
```python
# Verify TOTP code
verification_result = totp_service.verify_totp(
    user=user,
    code="123456",
    client_ip="192.168.1.1",
    user_agent="Mozilla/5.0..."
)

# Result structure
{
    "valid": True,
    "used_backup_code": False,
    "remaining_backup_codes": 7,
    "rate_limited": False,
    "attempt_id": "mfa_attempt_123"
}
```

### Advanced TOTP Features

**Time Tolerance & Security:**
```python
# TOTP Service Configuration
{
    "secret_length": 32,      # 160 bits of entropy
    "interval": 30,           # 30 second time steps
    "digits": 6,              # 6 digit codes
    "algorithm": "SHA1",      # SHA1 (most compatible)
    "window": 2,              # ±60 seconds tolerance
    "rate_limit": "5/hour",   # Max 5 attempts per hour
    "replay_prevention": True  # Prevent code reuse
}
```

**Backup Code Management:**
```python
# Generate new backup codes
new_codes = totp_service.regenerate_backup_codes(user)

# Use backup code
backup_result = totp_service.use_backup_code(user, "12345678")

# Check remaining codes
remaining = totp_service.get_remaining_backup_codes(user)
```

## WebAuthn/FIDO2 Authentication

### Current Implementation
**Location:** `app/Services/WebAuthnService.py`

**Features:**
- FIDO2/WebAuthn standard compliance
- Hardware security key support
- Biometric authentication (Touch ID, Face ID, Windows Hello)
- Attestation verification
- Device management and naming

### WebAuthn Registration Process

**Registration Flow:**
```python
from app.Services.WebAuthnService import WebAuthnService

webauthn_service = WebAuthnService(db)

# 1. Generate registration options
registration_options = webauthn_service.generate_registration_options(
    user=user,
    authenticator_selection={
        "authenticator_attachment": "any",  # "platform", "cross-platform", "any"
        "resident_key": "preferred",        # "required", "preferred", "discouraged"
        "user_verification": "preferred"    # "required", "preferred", "discouraged"
    },
    attestation="none"  # "none", "indirect", "direct"
)

# 2. Client performs registration (frontend JavaScript)
# navigator.credentials.create({publicKey: registration_options})

# 3. Verify registration response
verification_result = webauthn_service.verify_registration_response(
    user=user,
    credential=credential_from_client,
    challenge=stored_challenge,
    device_name="iPhone Touch ID"  # User-friendly name
)
```

**Registration Options:**
```python
# Advanced registration options
registration_options = webauthn_service.generate_registration_options(
    user=user,
    authenticator_selection={
        "authenticator_attachment": "platform",  # Platform authenticators only
        "resident_key": "required",              # Require resident keys
        "user_verification": "required"          # Require user verification
    },
    attestation="direct",  # Request direct attestation
    exclude_credentials=user.existing_webauthn_credentials,  # Prevent re-registration
    timeout=60000,  # 60 seconds
    extensions={
        "credProps": True,  # Get credential properties
        "hmacCreateSecret": True  # Enable HMAC extension
    }
)
```

### WebAuthn Authentication Process

**Authentication Flow:**
```python
# 1. Generate authentication options
auth_options = webauthn_service.generate_authentication_options(
    user=user,
    user_verification="preferred"
)

# 2. Client performs authentication (frontend)
# navigator.credentials.get({publicKey: auth_options})

# 3. Verify authentication response
auth_result = webauthn_service.verify_authentication_response(
    user=user,
    credential=credential_from_client,
    challenge=stored_challenge
)

# Result includes
{
    "verified": True,
    "credential_id": "credential_123",
    "sign_count": 42,
    "device_name": "YubiKey 5C",
    "last_used": "2024-08-19T10:30:00Z"
}
```

### Credential Management

**Device Management:**
```python
# List user's WebAuthn credentials
credentials = webauthn_service.get_user_credentials(user)

# Example credential info
{
    "id": "credential_123",
    "name": "YubiKey 5C",  # User-assigned name
    "created_at": "2024-01-15T09:00:00Z",
    "last_used": "2024-08-19T10:30:00Z",
    "sign_count": 42,
    "aaguid": "2fc0579f-8113-47ea-b116-bb5a8db9202a",
    "device_type": "cross-platform",
    "transport": ["usb", "nfc"],
    "backed_up": False,
    "attestation_type": "basic"
}

# Rename credential
webauthn_service.rename_credential(credential_id, "My Primary Key")

# Delete credential
webauthn_service.delete_credential(user, credential_id)
```

**Attestation Verification:**
```python
# Enable strict attestation checking
webauthn_service.set_attestation_policy(
    require_attestation=True,
    trusted_attestation_roots=[
        "/path/to/yubico_root_ca.pem",
        "/path/to/google_titan_ca.pem"
    ],
    allow_self_attestation=False
)
```

## SMS Authentication

### Current Implementation
**Location:** `app/Services/SMSService.py`

**Features:**
- Multiple SMS providers (Twilio, AWS SNS, etc.)
- Rate limiting and fraud prevention
- International phone number support
- Message customization

**SMS Setup and Verification:**
```python
from app.Services.SMSService import SMSService

sms_service = SMSService(db)

# Setup SMS for user
setup_result = sms_service.setup_sms_mfa(
    user=user,
    phone_number="+1234567890"
)

# Send verification code
send_result = sms_service.send_verification_code(
    user=user,
    message_template="Your verification code is: {code}",
    expiry_minutes=10
)

# Verify SMS code
verification_result = sms_service.verify_sms_code(
    user=user,
    code="123456"
)
```

## MFA Policy Management

### Current Implementation
**Location:** `app/Services/MFAPolicyService.py`

**Policy Features:**
- Role-based MFA requirements
- IP-based exemptions
- Device trust management
- Grace periods for new users

**Policy Configuration:**
```python
from app.Services.MFAPolicyService import MFAPolicyService

policy_service = MFAPolicyService(db)

# Define MFA policy
policy = policy_service.create_policy({
    "name": "Admin MFA Policy",
    "description": "Require MFA for all admin users",
    "rules": [
        {
            "condition": {"user.role": "admin"},
            "require_mfa": True,
            "allowed_methods": ["totp", "webauthn"],
            "grace_period_hours": 0
        },
        {
            "condition": {"user.department": "finance"},
            "require_mfa": True,
            "allowed_methods": ["totp", "webauthn", "sms"],
            "grace_period_hours": 24
        }
    ],
    "exemptions": [
        {"ip_range": "192.168.1.0/24", "reason": "Office network"},
        {"user_ids": ["admin_user_123"], "reason": "Emergency access"}
    ]
})

# Apply policy
policy_service.apply_policy(policy_id, user)
```

## MFA Analytics & Monitoring

### Analytics Service
**Location:** `app/Services/MFAAnalyticsService.py`

**Metrics Tracked:**
- MFA adoption rates
- Method usage patterns
- Failed attempt analysis
- Device and browser analytics

**Analytics Examples:**
```python
from app.Services.MFAAnalyticsService import MFAAnalyticsService

analytics = MFAAnalyticsService(db)

# Get MFA adoption metrics
adoption_stats = analytics.get_adoption_metrics()
{
    "total_users": 1000,
    "mfa_enabled_users": 750,
    "adoption_rate": 0.75,
    "methods": {
        "totp": 500,
        "webauthn": 300,
        "sms": 200
    }
}

# Get security incident analysis
incidents = analytics.get_security_incidents(days=30)
{
    "failed_attempts": 145,
    "blocked_ips": 12,
    "suspicious_patterns": 3,
    "compromised_accounts": 0
}
```

### Audit Service
**Location:** `app/Services/MFAAuditService.py`

**Audit Events:**
- MFA setup/removal
- Authentication attempts
- Policy changes
- Security incidents

**Audit Logging:**
```python
from app.Services.MFAAuditService import MFAAuditService

audit = MFAAuditService(db)

# Log MFA events automatically
audit.log_mfa_attempt(
    user=user,
    method="totp",
    result="success",
    ip_address="192.168.1.100",
    user_agent="Chrome/91.0"
)

# Query audit logs
recent_events = audit.get_user_audit_log(user, days=30)
```

## API Endpoints

### MFA Management API
```python
# Get MFA status
@app.get("/api/mfa/status")
async def get_mfa_status(user: User = Depends(get_current_user)):
    mfa_service = MFAService(db)
    return mfa_service.get_mfa_status(user)

# Setup TOTP
@app.post("/api/mfa/totp/setup")
async def setup_totp(user: User = Depends(get_current_user)):
    totp_service = TOTPService(db)
    return totp_service.setup_totp(user)

# Verify TOTP setup
@app.post("/api/mfa/totp/verify-setup")
async def verify_totp_setup(
    code: str,
    user: User = Depends(get_current_user)
):
    totp_service = TOTPService(db)
    return totp_service.complete_totp_setup(user, code)

# Start WebAuthn registration
@app.post("/api/mfa/webauthn/register-begin")
async def webauthn_register_begin(user: User = Depends(get_current_user)):
    webauthn_service = WebAuthnService(db)
    return webauthn_service.generate_registration_options(user)

# Complete WebAuthn registration  
@app.post("/api/mfa/webauthn/register-complete")
async def webauthn_register_complete(
    credential: dict,
    device_name: str,
    user: User = Depends(get_current_user)
):
    webauthn_service = WebAuthnService(db)
    return webauthn_service.verify_registration_response(
        user, credential, device_name
    )
```

### MFA Challenge API
```python
# Start MFA challenge
@app.post("/api/auth/mfa/challenge")
async def start_mfa_challenge(
    user: User = Depends(get_partially_authenticated_user)
):
    mfa_service = MFAService(db)
    session = mfa_service.start_mfa_session(user)
    
    return {
        "session_id": session.id,
        "available_methods": session.available_methods,
        "expires_at": session.expires_at
    }

# Submit MFA response
@app.post("/api/auth/mfa/verify")
async def verify_mfa(
    session_id: str,
    method: str,
    code: Optional[str] = None,
    credential: Optional[dict] = None
):
    mfa_service = MFAService(db)
    
    if method == "totp":
        result = mfa_service.verify_totp(session_id, code)
    elif method == "webauthn":
        result = mfa_service.verify_webauthn(session_id, credential)
    elif method == "sms":
        result = mfa_service.verify_sms(session_id, code)
    
    if result.success:
        # Complete authentication
        token = create_access_token(result.user)
        return {"access_token": token, "token_type": "bearer"}
    
    return {"error": "Invalid MFA code", "attempts_remaining": result.attempts_remaining}
```

## Frontend Integration

### JavaScript WebAuthn Helper
```javascript
class WebAuthnHelper {
    static async registerCredential(options) {
        try {
            // Convert base64 strings to ArrayBuffer
            options.user.id = this.base64ToArrayBuffer(options.user.id);
            options.challenge = this.base64ToArrayBuffer(options.challenge);
            
            // Create credential
            const credential = await navigator.credentials.create({
                publicKey: options
            });
            
            // Convert ArrayBuffer to base64 for transmission
            return {
                id: credential.id,
                rawId: this.arrayBufferToBase64(credential.rawId),
                response: {
                    clientDataJSON: this.arrayBufferToBase64(credential.response.clientDataJSON),
                    attestationObject: this.arrayBufferToBase64(credential.response.attestationObject)
                },
                type: credential.type
            };
        } catch (error) {
            throw new Error(`WebAuthn registration failed: ${error.message}`);
        }
    }
    
    static async authenticateCredential(options) {
        try {
            options.challenge = this.base64ToArrayBuffer(options.challenge);
            options.allowCredentials = options.allowCredentials.map(cred => ({
                ...cred,
                id: this.base64ToArrayBuffer(cred.id)
            }));
            
            const credential = await navigator.credentials.get({
                publicKey: options
            });
            
            return {
                id: credential.id,
                rawId: this.arrayBufferToBase64(credential.rawId),
                response: {
                    clientDataJSON: this.arrayBufferToBase64(credential.response.clientDataJSON),
                    authenticatorData: this.arrayBufferToBase64(credential.response.authenticatorData),
                    signature: this.arrayBufferToBase64(credential.response.signature),
                    userHandle: credential.response.userHandle ? 
                        this.arrayBufferToBase64(credential.response.userHandle) : null
                },
                type: credential.type
            };
        } catch (error) {
            throw new Error(`WebAuthn authentication failed: ${error.message}`);
        }
    }
}
```

## Security Features

### Rate Limiting
**Location:** `app/Services/MFARateLimitService.py`

**Features:**
- Per-user rate limiting
- IP-based rate limiting
- Progressive delays
- Account lockout protection

### Fraud Detection
**Features:**
- Suspicious pattern detection
- Geolocation analysis
- Device fingerprinting
- Behavioral analytics

### Recovery Options
**Features:**
- Account recovery codes
- Admin override capabilities
- Emergency access procedures
- Temporary disable options

## Testing

### MFA Testing Utilities
```python
from app.Testing.MFATesting import MFATestHelper

def test_totp_flow():
    helper = MFATestHelper()
    
    # Setup TOTP for test user
    user = helper.create_test_user()
    secret = helper.setup_totp(user)
    
    # Generate valid TOTP code
    code = helper.generate_totp_code(secret)
    
    # Verify authentication
    result = helper.verify_totp(user, code)
    assert result.success == True

def test_webauthn_flow():
    helper = MFATestHelper()
    
    # Mock WebAuthn registration
    user = helper.create_test_user()
    credential = helper.mock_webauthn_registration(user)
    
    # Mock authentication
    auth_result = helper.mock_webauthn_authentication(user, credential)
    assert auth_result.verified == True
```

## Improvements

### Performance Optimizations
1. **Credential caching**: Cache WebAuthn credentials for faster lookup
2. **Batch operations**: Efficient batch processing of MFA operations
3. **Connection pooling**: Optimize database connections for MFA services
4. **Async processing**: Background processing of audit logs and analytics

### Advanced Security Features
1. **Risk-based authentication**: Dynamic MFA requirements based on risk score
2. **Device trust management**: Trust known devices to reduce MFA friction
3. **Contextual authentication**: Location and behavior-based authentication
4. **Zero-trust integration**: Integration with zero-trust architecture

### User Experience Improvements
1. **Progressive setup**: Gradual MFA onboarding process
2. **Smart suggestions**: Recommend optimal MFA methods for users
3. **Unified management**: Single interface for all MFA methods
4. **Mobile app integration**: Dedicated mobile app for MFA

### Enterprise Features
1. **SSO integration**: Integration with enterprise SSO providers
2. **Compliance reporting**: SOC2, FIDO Alliance compliance reports
3. **Bulk management**: Administrative bulk operations for MFA
4. **Multi-tenancy**: Tenant-specific MFA policies and settings