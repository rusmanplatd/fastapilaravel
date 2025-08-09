# Laravel Passport Commands Guide

This document provides a comprehensive guide to using the Laravel Passport-style OAuth2 management commands in this FastAPI application.

## Overview

The `passport` command provides complete OAuth2 client and server management functionality, similar to Laravel Passport but for FastAPI applications.

## Installation & Setup

### Quick Setup
```bash
# Complete setup wizard (recommended for first-time setup)
python artisan.py passport setup

# Manual installation
python artisan.py passport install
python artisan.py passport keys:generate
```

## Client Management

### Create Clients
```bash
# Create authorization code client (interactive)
python artisan.py passport create

# Create with specific options
python artisan.py passport create --name="My App" --redirect="https://myapp.com/callback"

# Create personal access client
python artisan.py passport create --personal --name="Personal Tokens"

# Create password grant client
python artisan.py passport create --password-client --name="Mobile App"

# Create client credentials client
python artisan.py passport create --type=client_credentials --name="Service Client"
```

### List and Show Clients
```bash
# List active clients
python artisan.py passport list

# List all clients (including revoked)
python artisan.py passport list --revoked

# Show specific client details
python artisan.py passport show --id=01H...
```

### Update and Manage Clients
```bash
# Update client details
python artisan.py passport update --id=01H... --name="New Name"

# Regenerate client secret
python artisan.py passport secret --id=01H...

# Revoke a client
python artisan.py passport revoke --id=01H...

# Restore a revoked client
python artisan.py passport restore --id=01H...

# Delete a client permanently
python artisan.py passport delete --id=01H...
```

## Key Management

### Generate Encryption Keys
```bash
# Generate RSA key pair for JWT signing
python artisan.py passport keys:generate

# Force regenerate (overwrite existing keys)
python artisan.py passport keys:generate --force

# Show current key status
python artisan.py passport keys
```

## Scope Management

### List and Manage Scopes
```bash
# List all supported scopes
python artisan.py passport scopes

# Create a new scope (configuration guidance)
python artisan.py passport scopes:create --scope=custom

# Delete a scope (configuration guidance)
python artisan.py passport scopes:delete --scope=old_scope
```

## Token Management

### Prune and Revoke Tokens
```bash
# Remove expired tokens
python artisan.py passport tokens:prune

# Force prune without confirmation
python artisan.py passport tokens:prune --force

# Revoke all tokens for a client
python artisan.py passport tokens:revoke --id=01H...

# Show detailed token statistics
python artisan.py passport tokens:stats

# Show tokens for a specific client
python artisan.py passport tokens --id=01H...
```

## Status and Diagnostics

### System Status
```bash
# Show overall Passport status
python artisan.py passport status

# Comprehensive health check
python artisan.py passport health

# Basic statistics
python artisan.py passport stats
```

## Maintenance Commands

### Setup and Reset
```bash
# Complete setup wizard
python artisan.py passport setup

# Install default clients only
python artisan.py passport install

# Purge all Passport data (destructive)
python artisan.py passport purge
```

## Legacy Compatibility

For Laravel developers familiar with the original syntax:
```bash
# These commands work for compatibility
python artisan.py passport:client create
python artisan.py oauth:client list
python artisan.py oauth2 status
```

## Configuration

### Environment Variables
```bash
# JWT Secret (required)
JWT_SECRET=your-super-secure-secret-key-here

# OAuth2 Settings
OAUTH2_ACCESS_TOKEN_EXPIRE_MINUTES=60
OAUTH2_REFRESH_TOKEN_EXPIRE_DAYS=30
OAUTH2_REQUIRE_PKCE=true
OAUTH2_ENFORCE_HTTPS=true  # Production only
```

### Storage Requirements
- Encryption keys are stored in `storage/oauth2/`
- Database tables for clients, tokens, and scopes
- Proper file permissions (600 for private key, 644 for public key)

## Security Best Practices

1. **Always use HTTPS in production**
2. **Store client secrets securely** - they're only shown during creation
3. **Regularly prune expired tokens** to maintain database performance
4. **Use PKCE for public clients** (enabled by default)
5. **Monitor token usage** with health checks and statistics
6. **Backup encryption keys** before rotating them

## Troubleshooting

### Common Issues

**Command not found:**
```bash
# Check if command is registered
python artisan.py list | grep passport
```

**Missing dependencies:**
```bash
# Install required packages
pip install cryptography webauthn redis
```

**Database errors:**
```bash
# Run migrations
python artisan.py migrate

# Seed OAuth2 data
python artisan.py db:seed oauth2
```

**Key generation fails:**
```bash
# Check storage directory permissions
mkdir -p storage/oauth2
chmod 755 storage/oauth2
```

## Examples

### Complete Setup Workflow
```bash
# 1. Install Passport
python artisan.py passport setup

# 2. Create a web application client
python artisan.py passport create \
  --name="MyApp Web" \
  --redirect="https://myapp.com/auth/callback"

# 3. Create a mobile app client
python artisan.py passport create \
  --name="MyApp Mobile" \
  --password-client

# 4. Check status
python artisan.py passport health

# 5. View all clients
python artisan.py passport list
```

### Production Maintenance
```bash
# Daily maintenance
python artisan.py passport tokens:prune

# Weekly health check
python artisan.py passport health

# Monthly statistics review
python artisan.py passport tokens:stats
```

## Integration with FastAPI

The passport command integrates seamlessly with your FastAPI OAuth2 implementation:

- **Clients** created here work with your OAuth2 endpoints
- **Scopes** defined in configuration are enforced
- **Tokens** are compatible with your authentication middleware
- **Keys** are used for JWT signing and verification

For more details on OAuth2 implementation, see the main documentation.