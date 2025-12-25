"""lab results + sample_id on lab_orders

Revision ID: 0007_lab_results_and_sample_id
Revises: 0006_ingestion_and_results
Create Date: 2025-12-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0007_lab_results' #0007_lab_results_and_sample_id
down_revision = '0006_ing_&_re'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    op.add_column('lab_orders', sa.Column('sample_id', sa.String(length=80), nullable=True))
    op.create_index(op.f('ix_lab_orders_sample_id'), 'lab_orders', ['sample_id'], unique=False)

    if 'lab_results' not in inspector.get_table_names():
        op.create_table(
            'lab_results',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('order_item_id', sa.Integer(), sa.ForeignKey('lab_order_items.id'), nullable=False),
            sa.Column('analyzer_message_id', sa.Integer(), sa.ForeignKey('analyzer_messages.id'), nullable=True),
            sa.Column('analyte_code', sa.String(length=80), nullable=False),
            sa.Column('value', sa.String(length=120), nullable=True),
            sa.Column('unit', sa.String(length=40), nullable=True),
            sa.Column('flags', sa.String(length=40), nullable=True),
            sa.Column('ref_range', sa.String(length=80), nullable=True),
            sa.Column('raw_record', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            schema=None,
            if_not_exists=True

        )
        op.create_index(op.f('ix_lab_results_order_item_id'), 'lab_results', ['order_item_id'], unique=False)
        op.create_index(op.f('ix_lab_results_analyte_code'), 'lab_results', ['analyte_code'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_lab_results_analyte_code'), table_name='lab_results')
    op.drop_index(op.f('ix_lab_results_order_item_id'), table_name='lab_results')
    op.drop_table('lab_results')
    op.drop_index(op.f('ix_lab_orders_sample_id'), table_name='lab_orders')
    op.drop_column('lab_orders', 'sample_id')
