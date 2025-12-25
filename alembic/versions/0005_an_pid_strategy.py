"""Add analyzer patient id strategy

Revision ID: 0005_analyzer_patient_id_strategy
Revises: 0004_analyzer_message_meta
Create Date: 2025-12-24
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_an_pid_strategy"
down_revision = "0004_an_msg_meta"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("analyzers", sa.Column("patient_id_source", sa.String(length=30), nullable=False, server_default="patient_no"))
    op.add_column("analyzers", sa.Column("patient_id_fallbacks", sa.String(length=120), nullable=True))
    # remove server_default so future inserts use ORM default
    op.alter_column("analyzers", "patient_id_source", server_default=None)

def downgrade() -> None:
    op.drop_column("analyzers", "patient_id_fallbacks")
    op.drop_column("analyzers", "patient_id_source")
