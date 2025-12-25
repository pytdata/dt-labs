"""lab stage enum

Revision ID: 0008_lab_stage_enum
Revises: 0007_lab_results_and_sample_id
Create Date: 2025-12-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
# from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "0008_lab_stage_enum"
down_revision = "0007_lab_results"
branch_labels = None
depends_on = None


def upgrade() -> None:
    lab_stage = postgresql.ENUM(
        "booking", "sampling", "running", "complete", "analyzing", "printing", "ended",
        name="lab_stage"
    )
    lab_stage.create(op.get_bind(), checkfirst=True)

    # Convert existing string values to enum safely
    # Step 1: Drop the default
    op.alter_column(
        "lab_order_items",
        "stage",
        server_default=None,
        existing_type=sa.String(length=40),
        existing_nullable=False,
    )

    # Step 2: Cast to ENUM
    op.alter_column(
        "lab_order_items",
        "stage",
        type_=lab_stage,
        postgresql_using="stage::lab_stage",
        existing_type=sa.String(length=40),
        existing_nullable=False,
    )

    # Step 3: Reapply default
    op.alter_column(
        "lab_order_items",
        "stage",
        server_default=sa.text("'booking'"),
        existing_type=lab_stage,
        existing_nullable=False,
    )


    # op.alter_column(
    #     "lab_order_items",
    #     "stage",
    #     type_=lab_stage,
    #     postgresql_using="stage::lab_stage",
    #     existing_type=sa.String(length=40),
    #     existing_nullable=False,
    #     server_default="booking",
    # )


def downgrade() -> None:
    # op.alter_column(
    #     "lab_order_items",
    #     "stage",
    #     type_=sa.String(length=40),
    #     existing_type=postgresql.ENUM(name="lab_stage"),
    #     existing_nullable=False,
    #     server_default="booking",
    # )
    # op.execute("DROP TYPE IF EXISTS lab_stage")
    # Drop ENUM default
    op.alter_column(
        "lab_order_items",
        "stage",
        server_default=None,
        existing_type=postgresql.ENUM(name="lab_stage"),
        existing_nullable=False,
    )

    # Revert to string
    op.alter_column(
        "lab_order_items",
        "stage",
        type_=sa.String(length=40),
        postgresql_using="stage::text",
        existing_type=postgresql.ENUM(name="lab_stage"),
        existing_nullable=False,
    )

    # Restore default
    op.alter_column(
        "lab_order_items",
        "stage",
        server_default=sa.text("'booking'"),
        existing_type=sa.String(length=40),
        existing_nullable=False,
    )

    op.execute("DROP TYPE IF EXISTS lab_stage")

