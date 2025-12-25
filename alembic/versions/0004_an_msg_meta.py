"""Add analyzer message meta JSON

Revision ID: 0004_analyzer_message_meta
Revises: 0003_analyzer_connectivity
Create Date: 2025-12-24
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_an_msg_meta" #0004_analyzer_message_meta
down_revision = "0003_analyzer_connectivity"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("analyzer_messages", sa.Column("meta", sa.JSON(), nullable=True))

def downgrade() -> None:
    op.drop_column("analyzer_messages", "meta")
