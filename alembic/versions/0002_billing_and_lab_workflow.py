"""billing and lab workflow

Revision ID: 0002_billing_and_lab_workflow
Revises: 0001_init
Create Date: 2025-12-24

"""

from alembic import op
import sqlalchemy as sa


revision = "0002_billing_and_lab_workflow"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade():
    # --- Lab workflow fields ---
    with op.batch_alter_table("lab_order_items") as batch:
        batch.add_column(sa.Column("stage", sa.String(length=40), nullable=False, server_default="booking"))
        batch.add_column(sa.Column("assigned_to_user_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("entered_by_user_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_lab_order_items_assigned_to", "users", ["assigned_to_user_id"], ["id"])
        batch.create_foreign_key("fk_lab_order_items_entered_by", "users", ["entered_by_user_id"], ["id"])

    op.create_table(
        "lab_status_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_item_id", sa.Integer(), nullable=False),
        sa.Column("from_stage", sa.String(length=40), nullable=True),
        sa.Column("to_stage", sa.String(length=40), nullable=False),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_item_id"], ["lab_order_items.id"], name="fk_lab_status_logs_item"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], name="fk_lab_status_logs_user"),
    )
    op.create_index("ix_lab_status_logs_order_item_id", "lab_status_logs", ["order_item_id"])

    # --- Billing (Invoices + partial payments) ---
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_no", sa.String(length=50), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("amount_paid", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("balance", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="unpaid"),
        sa.Column("payment_mode", sa.String(length=30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name="fk_invoices_patient"),
        sa.ForeignKeyConstraint(["order_id"], ["lab_orders.id"], name="fk_invoices_order"),
    )
    op.create_index("ix_invoices_invoice_no", "invoices", ["invoice_no"], unique=True)
    op.create_index("ix_invoices_patient_id", "invoices", ["patient_id"])
    op.create_index("ix_invoices_order_id", "invoices", ["order_id"])

    op.create_table(
        "invoice_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], name="fk_invoice_items_invoice"),
        sa.ForeignKeyConstraint(["test_id"], ["tests.id"], name="fk_invoice_items_test"),
    )
    op.create_index("ix_invoice_items_invoice_id", "invoice_items", ["invoice_id"])
    op.create_index("ix_invoice_items_test_id", "invoice_items", ["test_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("method", sa.String(length=30), nullable=False, server_default="cash"),
        sa.Column("verified_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reference", sa.String(length=100), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], name="fk_payments_invoice"),
        sa.ForeignKeyConstraint(["verified_by_user_id"], ["users.id"], name="fk_payments_user"),
    )
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"])


def downgrade():
    op.drop_index("ix_payments_invoice_id", table_name="payments")
    op.drop_table("payments")

    op.drop_index("ix_invoice_items_test_id", table_name="invoice_items")
    op.drop_index("ix_invoice_items_invoice_id", table_name="invoice_items")
    op.drop_table("invoice_items")

    op.drop_index("ix_invoices_order_id", table_name="invoices")
    op.drop_index("ix_invoices_patient_id", table_name="invoices")
    op.drop_index("ix_invoices_invoice_no", table_name="invoices")
    op.drop_table("invoices")

    op.drop_index("ix_lab_status_logs_order_item_id", table_name="lab_status_logs")
    op.drop_table("lab_status_logs")

    with op.batch_alter_table("lab_order_items") as batch:
        batch.drop_constraint("fk_lab_order_items_entered_by", type_="foreignkey")
        batch.drop_constraint("fk_lab_order_items_assigned_to", type_="foreignkey")
        batch.drop_column("entered_by_user_id")
        batch.drop_column("assigned_to_user_id")
        batch.drop_column("stage")
