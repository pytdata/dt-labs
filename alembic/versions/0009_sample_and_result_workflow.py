"""sample + result workflow improvements

Revision ID: 0009_sample_and_result_workflow
Revises: 0008_lab_stage_enum
Create Date: 2025-12-26
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0009_sample_and_result_workflow"
down_revision = "0008_lab_stage_enum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Sample tracking on orders
    op.add_column("lab_orders", sa.Column("sample_collected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("lab_orders", sa.Column("collected_by_user_id", sa.Integer(), nullable=True))
    op.add_column("lab_orders", sa.Column("sample_notes", sa.Text(), nullable=True))

    # Result workflow
    op.add_column("lab_results", sa.Column("sample_id", sa.String(length=80), nullable=True))
    op.add_column("lab_results", sa.Column("verified_by_user_id", sa.Integer(), nullable=True))
    op.add_column("lab_results", sa.Column("merged_from", sa.JSON(), nullable=True))
    op.add_column("lab_results", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("lab_results", sa.Column("comments", sa.Text(), nullable=True))
    op.add_column("lab_results", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))

    op.create_index(op.f("ix_lab_results_sample_id"), "lab_results", ["sample_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_lab_results_sample_id"), table_name="lab_results")
    op.drop_column("lab_results", "updated_at")
    op.drop_column("lab_results", "comments")
    op.drop_column("lab_results", "verified_at")
    op.drop_column("lab_results", "merged_from")
    op.drop_column("lab_results", "verified_by_user_id")
    op.drop_column("lab_results", "sample_id")

    op.drop_column("lab_orders", "sample_notes")
    op.drop_column("lab_orders", "collected_by_user_id")
    op.drop_column("lab_orders", "sample_collected_at")
