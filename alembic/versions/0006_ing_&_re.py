"""ingestion and results tables

Revision ID: 0006_ingestion_and_results
Revises: 0005_analyzer_patient_id_strategy
Create Date: 2025-12-24
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0006_ing_&_re'
down_revision = '0005_an_pid_strategy'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('lab_order_items', sa.Column('sample_id', sa.String(length=80), nullable=True))
    op.create_index(op.f('ix_lab_order_items_sample_id'), 'lab_order_items', ['sample_id'], unique=False)

    op.create_table(
        'lab_results',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_item_id', sa.Integer(), sa.ForeignKey('lab_order_items.id'), nullable=False),
        sa.Column('analyzer_id', sa.Integer(), sa.ForeignKey('analyzers.id'), nullable=True),
        sa.Column('analyzer_message_id', sa.Integer(), sa.ForeignKey('analyzer_messages.id'), nullable=True),
        sa.Column('entered_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False, server_default='analyzer'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='received'),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('raw_format', sa.String(length=10), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_lab_results_order_item_id'), 'lab_results', ['order_item_id'], unique=False)
    op.create_index(op.f('ix_lab_results_analyzer_id'), 'lab_results', ['analyzer_id'], unique=False)
    op.create_index(op.f('ix_lab_results_analyzer_message_id'), 'lab_results', ['analyzer_message_id'], unique=False)

    op.create_table(
        'analyzer_ingestions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('analyzer_message_id', sa.Integer(), sa.ForeignKey('analyzer_messages.id'), nullable=False),
        sa.Column('analyzer_id', sa.Integer(), sa.ForeignKey('analyzers.id'), nullable=True),
        sa.Column('patient_id', sa.Integer(), sa.ForeignKey('patients.id'), nullable=True),
        sa.Column('order_item_id', sa.Integer(), sa.ForeignKey('lab_order_items.id'), nullable=True),
        sa.Column('match_method', sa.String(length=30), nullable=True),
        sa.Column('match_value', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='unmatched'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_analyzer_ingestions_analyzer_message_id'), 'analyzer_ingestions', ['analyzer_message_id'], unique=False)
    op.create_index(op.f('ix_analyzer_ingestions_analyzer_id'), 'analyzer_ingestions', ['analyzer_id'], unique=False)
    op.create_index(op.f('ix_analyzer_ingestions_patient_id'), 'analyzer_ingestions', ['patient_id'], unique=False)
    op.create_index(op.f('ix_analyzer_ingestions_order_item_id'), 'analyzer_ingestions', ['order_item_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_analyzer_ingestions_order_item_id'), table_name='analyzer_ingestions')
    op.drop_index(op.f('ix_analyzer_ingestions_patient_id'), table_name='analyzer_ingestions')
    op.drop_index(op.f('ix_analyzer_ingestions_analyzer_id'), table_name='analyzer_ingestions')
    op.drop_index(op.f('ix_analyzer_ingestions_analyzer_message_id'), table_name='analyzer_ingestions')
    op.drop_table('analyzer_ingestions')

    op.drop_index(op.f('ix_lab_results_analyzer_message_id'), table_name='lab_results')
    op.drop_index(op.f('ix_lab_results_analyzer_id'), table_name='lab_results')
    op.drop_index(op.f('ix_lab_results_order_item_id'), table_name='lab_results')
    op.drop_table('lab_results')

    op.drop_index(op.f('ix_lab_order_items_sample_id'), table_name='lab_order_items')
    op.drop_column('lab_order_items', 'sample_id')
