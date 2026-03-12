"""A generic, single database configuration.

Revision ID: 619053e92ff6
Revises: b15cbdb5306b
Create Date: 2026-03-12 00:13:19.275253

"""

from alembic import op
import sqlalchemy as sa

revision = "619053e92ff6"
down_revision = "b15cbdb5306b"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Convert columns to VARCHAR using explicit casting
    op.execute(
        "ALTER TABLE lab_order_items ALTER COLUMN status TYPE VARCHAR(50) USING status::text"
    )
    op.execute(
        "ALTER TABLE lab_order_items ALTER COLUMN stage TYPE VARCHAR(50) USING stage::text"
    )

    # 2. Remove the server default that references the old Enum type
    op.execute("ALTER TABLE lab_order_items ALTER COLUMN stage DROP DEFAULT")
    # Re-add a plain string default
    op.execute("ALTER TABLE lab_order_items ALTER COLUMN stage SET DEFAULT 'booking'")

    # 3. Drop the custom types to keep the database clean
    op.execute("DROP TYPE IF EXISTS labstatus")
    op.execute("DROP TYPE IF EXISTS labstage")


def downgrade():
    # Re-create types if reverting
    op.execute(
        "CREATE TYPE labstatus AS ENUM ('AWAITING_SAMPLE', 'AWAITING_RESULTS', 'IN_PROGRESS', 'AWAITING_APPROVAL', 'COMPLETED', 'CANCELLED')"
    )
    op.execute(
        "CREATE TYPE labstage AS ENUM ('booking', 'sampling', 'analysis', 'review', 'complete', 'printing', 'ended')"
    )

    # Convert back to ENUM
    op.execute(
        "ALTER TABLE lab_order_items ALTER COLUMN status TYPE labstatus USING status::labstatus"
    )
    op.execute(
        "ALTER TABLE lab_order_items ALTER COLUMN stage TYPE labstage USING stage::labstage"
    )
