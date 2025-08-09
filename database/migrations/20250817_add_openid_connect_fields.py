"""Add OpenID Connect fields to OAuth2 models and User model

Revision ID: 20250817_add_openid_connect_fields
Revises: previous
Create Date: 2025-08-17

"""

from __future__ import annotations

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers
revision: str = '20250817_add_openid_connect_fields'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add OpenID Connect fields to support Google IDP-style OAuth."""
    
    # Add OpenID Connect fields to oauth_clients table
    with op.batch_alter_table('oauth_clients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('logo_uri', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('client_uri', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('policy_uri', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('tos_uri', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('jwks_uri', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('sector_identifier_uri', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('subject_type', sa.String(), nullable=False, server_default='public'))
        batch_op.add_column(sa.Column('id_token_signed_response_alg', sa.String(), nullable=False, server_default='RS256'))
        batch_op.add_column(sa.Column('token_endpoint_auth_method', sa.String(), nullable=False, server_default='client_secret_basic'))
        batch_op.add_column(sa.Column('require_auth_time', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('default_max_age', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('require_pushed_authorization_requests', sa.Boolean(), nullable=False, server_default='0'))
    
    # Add OpenID Connect fields to oauth_access_tokens table
    with op.batch_alter_table('oauth_access_tokens', schema=None) as batch_op:
        batch_op.add_column(sa.Column('id_token', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('nonce', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('auth_time', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('acr', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('amr', sa.String(), nullable=True))
    
    # Add OpenID Connect fields to oauth_authorization_codes table
    with op.batch_alter_table('oauth_authorization_codes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('nonce', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('oidc_params', sa.Text(), nullable=True))
    
    # Add OpenID Connect standard claims to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('given_name', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('family_name', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('middle_name', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('nickname', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('preferred_username', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('profile', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('picture', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('website', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('gender', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('birthdate', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('zoneinfo', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('phone_number', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('phone_number_verified', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('address', sa.Text(), nullable=True))
    
    # Update default scopes for existing clients to include OpenID Connect scopes
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE oauth_clients SET allowed_scopes = 'openid,profile,email' WHERE allowed_scopes = '' OR allowed_scopes IS NULL")
    )
    connection.execute(
        sa.text("UPDATE oauth_clients SET grant_types = 'authorization_code,refresh_token' WHERE grant_types = 'authorization_code'")
    )
    connection.execute(
        sa.text("UPDATE oauth_clients SET response_types = 'code,id_token,token' WHERE response_types = 'code'")
    )


def downgrade() -> None:
    """Remove OpenID Connect fields."""
    
    # Remove OpenID Connect fields from oauth_clients table
    with op.batch_alter_table('oauth_clients', schema=None) as batch_op:
        batch_op.drop_column('require_pushed_authorization_requests')
        batch_op.drop_column('default_max_age')
        batch_op.drop_column('require_auth_time')
        batch_op.drop_column('token_endpoint_auth_method')
        batch_op.drop_column('id_token_signed_response_alg')
        batch_op.drop_column('subject_type')
        batch_op.drop_column('sector_identifier_uri')
        batch_op.drop_column('jwks_uri')
        batch_op.drop_column('tos_uri')
        batch_op.drop_column('policy_uri')
        batch_op.drop_column('client_uri')
        batch_op.drop_column('logo_uri')
    
    # Remove OpenID Connect fields from oauth_access_tokens table
    with op.batch_alter_table('oauth_access_tokens', schema=None) as batch_op:
        batch_op.drop_column('amr')
        batch_op.drop_column('acr')
        batch_op.drop_column('auth_time')
        batch_op.drop_column('nonce')
        batch_op.drop_column('id_token')
    
    # Remove OpenID Connect fields from oauth_authorization_codes table
    with op.batch_alter_table('oauth_authorization_codes', schema=None) as batch_op:
        batch_op.drop_column('oidc_params')
        batch_op.drop_column('nonce')
    
    # Remove OpenID Connect fields from users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('address')
        batch_op.drop_column('phone_number_verified')
        batch_op.drop_column('phone_number')
        batch_op.drop_column('zoneinfo')
        batch_op.drop_column('birthdate')
        batch_op.drop_column('gender')
        batch_op.drop_column('website')
        batch_op.drop_column('picture')
        batch_op.drop_column('profile')
        batch_op.drop_column('preferred_username')
        batch_op.drop_column('nickname')
        batch_op.drop_column('middle_name')
        batch_op.drop_column('family_name')
        batch_op.drop_column('given_name')