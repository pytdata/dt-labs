"""A generic, single database configuration.

Revision ID: b15cbdb5306b
Revises: 13486b33af37
Create Date: 2026-03-11 23:56:41.666770

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b15cbdb5306b"
down_revision = "13486b33af37"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Manually create the ENUM types in PostgreSQL
    lab_status = postgresql.ENUM(
        "AWAITING_SAMPLE",
        "AWAITING_RESULTS",
        "IN_PROGRESS",
        "AWAITING_APPROVAL",
        "COMPLETED",
        "CANCELLED",
        name="labstatus",
    )
    lab_stage = postgresql.ENUM(
        "booking",
        "sampling",
        "analysis",
        "review",
        "complete",
        "printing",
        "ended",
        name="labstage",
    )

    lab_status.create(op.get_bind())
    lab_stage.create(op.get_bind())

    # 2. Alter 'status' column with explicit casting
    # We use a raw SQL execution because Alembic's alter_column doesn't support the 'USING' clause directly in all dialects
    op.execute(
        "ALTER TABLE lab_order_items ALTER COLUMN status TYPE labstatus USING status::text::labstatus"
    )

    # 3. Alter 'stage' column with explicit casting
    # We also remove the old server default first to avoid type conflicts
    op.execute("ALTER TABLE lab_order_items ALTER COLUMN stage DROP DEFAULT")
    op.execute(
        "ALTER TABLE lab_order_items ALTER COLUMN stage TYPE labstage USING stage::text::labstage"
    )
    op.execute(
        "ALTER TABLE lab_order_items ALTER COLUMN stage SET DEFAULT 'booking'::labstage"
    )


def downgrade():
    # 1. Convert columns back to VARCHAR
    op.execute("ALTER TABLE lab_order_items ALTER COLUMN stage DROP DEFAULT")
    op.execute(
        "ALTER TABLE lab_order_items ALTER COLUMN stage TYPE VARCHAR USING stage::text"
    )
    op.execute(
        "ALTER TABLE lab_order_items ALTER COLUMN status TYPE VARCHAR(30) USING status::text"
    )

    # 2. Drop the custom types
    op.execute("DROP TYPE labstatus")
    op.execute("DROP TYPE labstage")
