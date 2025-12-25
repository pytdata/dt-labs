"""Add dynamic analyzer connectivity fields

Revision ID: 0003_analyzer_connectivity
Revises: 0002_billing_and_lab_workflow
Create Date: 2025-12-24
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_analyzer_connectivity'
down_revision = '0002_billing_and_lab_workflow'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns
    op.add_column('analyzers', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')))
    op.add_column('analyzers', sa.Column('result_format', sa.String(length=20), nullable=False, server_default='ASTM'))

    op.add_column('analyzers', sa.Column('tcp_ip', sa.String(length=255), nullable=True))
    op.add_column('analyzers', sa.Column('tcp_port', sa.Integer(), nullable=True))

    op.add_column('analyzers', sa.Column('serial_port', sa.String(length=50), nullable=True))
    op.add_column('analyzers', sa.Column('baud_rate', sa.Integer(), nullable=True))
    op.add_column('analyzers', sa.Column('parity', sa.String(length=10), nullable=True))
    op.add_column('analyzers', sa.Column('stop_bits', sa.Integer(), nullable=True))
    op.add_column('analyzers', sa.Column('data_bits', sa.Integer(), nullable=True))
    op.add_column('analyzers', sa.Column('flow_control', sa.String(length=20), nullable=True))

    op.add_column('analyzers', sa.Column('manufacturer', sa.String(length=120), nullable=True))
    op.add_column('analyzers', sa.Column('model', sa.String(length=120), nullable=True))
    op.add_column('analyzers', sa.Column('notes', sa.Text(), nullable=True))

    # Migrate existing host/port into tcp fields where possible
    with op.batch_alter_table('analyzers') as batch:
        # Ensure connection_type is not null
        batch.alter_column('connection_type', existing_type=sa.String(length=30), nullable=False, server_default='tcp')

    op.execute("UPDATE analyzers SET tcp_ip = COALESCE(tcp_ip, host) WHERE host IS NOT NULL")
    # port was previously string; best-effort cast
    op.execute("UPDATE analyzers SET tcp_port = COALESCE(tcp_port, NULLIF(regexp_replace(port, '[^0-9]', '', 'g'), '')::int) WHERE port IS NOT NULL")

    # Drop legacy columns if present
    with op.batch_alter_table('analyzers') as batch:
        if _has_column('analyzers', 'host'):
            batch.drop_column('host')
        if _has_column('analyzers', 'port'):
            batch.drop_column('port')

    # Remove server defaults we don't want persisted
    with op.batch_alter_table('analyzers') as batch:
        batch.alter_column('is_active', server_default=None)
        batch.alter_column('result_format', server_default=None)
        batch.alter_column('connection_type', server_default=None)


def downgrade() -> None:
    # Re-add legacy columns
    op.add_column('analyzers', sa.Column('host', sa.String(length=255), nullable=True))
    op.add_column('analyzers', sa.Column('port', sa.String(length=50), nullable=True))

    # Best-effort move back
    op.execute("UPDATE analyzers SET host = COALESCE(host, tcp_ip) WHERE tcp_ip IS NOT NULL")
    op.execute("UPDATE analyzers SET port = COALESCE(port, tcp_port::text) WHERE tcp_port IS NOT NULL")

    # Drop new columns
    with op.batch_alter_table('analyzers') as batch:
        batch.drop_column('notes')
        batch.drop_column('model')
        batch.drop_column('manufacturer')
        batch.drop_column('flow_control')
        batch.drop_column('data_bits')
        batch.drop_column('stop_bits')
        batch.drop_column('parity')
        batch.drop_column('baud_rate')
        batch.drop_column('serial_port')
        batch.drop_column('tcp_port')
        batch.drop_column('tcp_ip')
        batch.drop_column('result_format')
        batch.drop_column('is_active')

        # allow null again
        batch.alter_column('connection_type', nullable=True)


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c['name'] for c in insp.get_columns(table_name)]
    return column_name in cols
