# migrations/versions/001_initial_migration.py

"""Initial migration with all tables

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Auth users table (расширенная)
    op.create_table('auth_users',
                    sa.Column('id', sa.String(), nullable=False),
                    sa.Column('telegram_id', sa.BigInteger(), nullable=False),
                    sa.Column('first_name', sa.String(), nullable=False),
                    sa.Column('last_name', sa.String(), nullable=True),
                    sa.Column('username', sa.String(), nullable=True),
                    sa.Column('language_code', sa.String(), server_default='en', nullable=False),
                    sa.Column('is_bot', sa.Boolean(), server_default='false', nullable=False),
                    sa.Column('allows_write_to_pm', sa.Boolean(), server_default='false', nullable=False),
                    sa.Column('rating', sa.Integer(), server_default='1000', nullable=False),
                    sa.Column('country', sa.String(), server_default='US', nullable=False),
                    sa.Column('spoken_languages', sa.JSON(), server_default='[]', nullable=False),
                    sa.Column('purchased_languages', sa.JSON(), server_default='[]', nullable=False),
                    sa.Column('games_played', sa.Integer(), server_default='0', nullable=False),
                    sa.Column('games_won', sa.Integer(), server_default='0', nullable=False),
                    sa.Column('win_rate', sa.Float(), server_default='0.0', nullable=False),
                    sa.Column('linguistic_rating', sa.JSON(), server_default='{}', nullable=False),
                    sa.Column('is_premium', sa.Boolean(), server_default='false', nullable=False),
                    sa.Column('skin_id', sa.String(), nullable=True),
                    sa.Column('banned_until', sa.DateTime(timezone=True), nullable=True),
                    sa.Column('muted_players', sa.JSON(), server_default='[]', nullable=False),
                    sa.Column('referrer_id', sa.String(), nullable=True),
                    sa.Column('referral_code', sa.String(), nullable=True),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                              nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('telegram_id'),
                    sa.UniqueConstraint('referral_code')
                    )
    op.create_index(op.f('ix_auth_users_telegram_id'), 'auth_users', ['telegram_id'])

    # Economy wallets
    op.create_table('economy_wallets',
                    sa.Column('id', sa.String(), nullable=False),
                    sa.Column('user_id', sa.String(), nullable=False),
                    sa.Column('address', sa.String(), nullable=True),
                    sa.Column('encrypted_key', sa.String(), nullable=True),
                    sa.Column('balance_cache', sa.Integer(), server_default='0', nullable=False),
                    sa.Column('total_earned', sa.Integer(), server_default='0', nullable=False),
                    sa.Column('total_spent', sa.Integer(), server_default='0', nullable=False),
                    sa.Column('last_claim_at', sa.DateTime(timezone=True), nullable=True),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                              nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('user_id')
                    )
    op.create_index(op.f('ix_economy_wallets_user_id'), 'economy_wallets', ['user_id'])

    # Economy transactions
    op.create_table('economy_transactions',
                    sa.Column('id', sa.String(), nullable=False),
                    sa.Column('user_id', sa.String(), nullable=False),
                    sa.Column('amount', sa.Integer(), nullable=False),
                    sa.Column('type', sa.String(), nullable=False),
                    sa.Column('reason', sa.String(), nullable=False),
                    sa.Column('metadata', sa.JSON(), nullable=True),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                              nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_economy_transactions_user_id'), 'economy_transactions', ['user_id'])

    # Game tables
    op.create_table('game_games',
                    sa.Column('id', sa.String(), nullable=False),
                    sa.Column('status', sa.String(), server_default='lobby', nullable=False),
                    sa.Column('settings', sa.JSON(), nullable=True),
                    sa.Column('phase', sa.String(), server_default='lobby', nullable=False),
                    sa.Column('day_count', sa.Integer(), server_default='0', nullable=False),
                    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
                    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
                    sa.Column('winner_team', sa.String(), nullable=True),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                              nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )

    op.create_table('game_players',
                    sa.Column('id', sa.String(), nullable=False),
                    sa.Column('game_id', sa.String(), nullable=False),
                    sa.Column('user_id', sa.String(), nullable=False),
                    sa.Column('role', sa.String(), server_default='citizen', nullable=False),
                    sa.Column('alive', sa.Boolean(), server_default='true', nullable=False),
                    sa.Column('death_reason', sa.String(), nullable=True),
                    sa.Column('death_day', sa.Integer(), nullable=True),
                    sa.Column('kicked_at', sa.DateTime(timezone=True), nullable=True),
                    sa.Column('stats', sa.JSON(), server_default='{}', nullable=False),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                              nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_game_players_game_id'), 'game_players', ['game_id'])
    op.create_index(op.f('ix_game_players_user_id'), 'game_players', ['user_id'])

    # Voice rooms
    op.create_table('voice_rooms',
                    sa.Column('id', sa.String(), nullable=False),
                    sa.Column('game_id', sa.String(), nullable=False),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                              nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_voice_rooms_game_id'), 'voice_rooms', ['game_id'])

    # Moderation tables
    op.create_table('moderation_bans',
                    sa.Column('id', sa.String(), nullable=False),
                    sa.Column('user_id', sa.String(), nullable=False),
                    sa.Column('type', sa.String(), nullable=False),
                    sa.Column('reason', sa.String(), nullable=False),
                    sa.Column('issued_by', sa.String(), nullable=False),
                    sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
                    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
                    sa.Column('evidence', sa.Text(), nullable=True),
                    sa.Column('appeal_status', sa.String(), server_default='none', nullable=False),
                    sa.Column('notes', sa.Text(), nullable=True),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                              nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_moderation_bans_user_id'), 'moderation_bans', ['user_id'])

    # Social interactions
    op.create_table('social_interactions',
                    sa.Column('id', sa.String(), nullable=False),
                    sa.Column('from_user', sa.String(), nullable=False),
                    sa.Column('to_user', sa.String(), nullable=False),
                    sa.Column('type', sa.String(), nullable=False),
                    sa.Column('game_id', sa.String(), nullable=True),
                    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
                    sa.Column('data', sa.JSON(), nullable=False),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                              nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_social_interactions_from_user'), 'social_interactions', ['from_user'])
    op.create_index(op.f('ix_social_interactions_to_user'), 'social_interactions', ['to_user'])
    op.create_index(op.f('ix_social_interactions_game_id'), 'social_interactions', ['game_id'])

    # Skins catalog
    op.create_table('skins_catalog',
                    sa.Column('id', sa.String(), nullable=False),
                    sa.Column('name', sa.String(), nullable=False),
                    sa.Column('description', sa.String(), nullable=False),
                    sa.Column('price_mafia', sa.Integer(), nullable=False),
                    sa.Column('image_url', sa.String(), nullable=False),
                    sa.Column('preview_url', sa.String(), nullable=False),
                    sa.Column('rarity', sa.String(), nullable=False),
                    sa.Column('is_limited', sa.Boolean(), server_default='false', nullable=False),
                    sa.Column('available_until', sa.DateTime(timezone=True), nullable=True),
                    sa.Column('requirements', sa.JSON(), nullable=True),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                              nullable=False),
                    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )


def downgrade() -> None:
    op.drop_table('skins_catalog')
    op.drop_table('social_interactions')
    op.drop_table('moderation_bans')
    op.drop_table('voice_rooms')
    op.drop_table('game_players')
    op.drop_table('game_games')
    op.drop_table('economy_transactions')
    op.drop_table('economy_wallets')
    op.drop_table('auth_users')
