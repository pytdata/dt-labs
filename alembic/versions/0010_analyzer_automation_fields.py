"""Add is_automated, transport_type, protocol_type to analyzers

Revision ID: 0010_analyzer_automation_fields
Revises: d443de9b7195 (add_created_by_id_field_to_invoice_)
Create Date: 2025-01-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "0010_analyzer_automation_fields"
down_revision = "d443de9b7195"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in cols


def upgrade() -> None:
    # Add is_automated flag - True for BC-5150 and BS-240, False for manual analyzers
    if not _has_column("analyzers", "is_automated"):
        op.add_column(
            "analyzers",
            sa.Column(
                "is_automated",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("FALSE"),
            ),
        )

    # Add transport_type: tcp_server | tcp_client | serial
    # tcp_server = LIS listens, analyzer connects (standard for Mindray)
    if not _has_column("analyzers", "transport_type"):
        op.add_column(
            "analyzers",
            sa.Column("transport_type", sa.String(length=30), nullable=True),
        )

    # Add protocol_type: hl7 | astm | auto
    if not _has_column("analyzers", "protocol_type"):
        op.add_column(
            "analyzers",
            sa.Column(
                "protocol_type",
                sa.String(length=30),
                nullable=True,
                server_default="hl7",
            ),
        )

    # Seed the two known automated analyzers if they already exist
    # BC-5150: HL7/MLLP over TCP, LIS is server on port 10001
    # BS-240:  HL7/MLLP over TCP, LIS is server on port 10002 (or ASTM on 10003)
    op.execute(
        """
        UPDATE analyzers
        SET
            is_automated   = TRUE,
            transport_type = 'tcp_server',
            protocol_type  = 'hl7'
        WHERE name ILIKE '%BC-5150%'
           OR name ILIKE '%BC5150%'
        """
    )

    op.execute(
        """
        UPDATE analyzers
        SET
            is_automated   = TRUE,
            transport_type = 'tcp_server',
            protocol_type  = 'hl7'
        WHERE name ILIKE '%BS-240%'
           OR name ILIKE '%BS240%'
        """
    )

    # Remove the server_default from is_automated so it stays explicit
    with op.batch_alter_table("analyzers") as batch:
        batch.alter_column("is_automated", server_default=None)
        batch.alter_column("protocol_type", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("analyzers") as batch:
        if _has_column("analyzers", "protocol_type"):
            batch.drop_column("protocol_type")
        if _has_column("analyzers", "transport_type"):
            batch.drop_column("transport_type")
        if _has_column("analyzers", "is_automated"):
            batch.drop_column("is_automated")