"""add optional client nickname

Revision ID: b71f4c2a1d90
Revises: 70531ed7dd40
"""
from alembic import op
import sqlalchemy as sa

revision = 'b71f4c2a1d90'
down_revision = '70531ed7dd40'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('clients', sa.Column('nickname', sa.String(length=120), nullable=True))
    op.create_index(op.f('ix_clients_nickname'), 'clients', ['nickname'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_clients_nickname'), table_name='clients')
    op.drop_column('clients', 'nickname')
