"""init

Revision ID: 0001_init
Revises:
Create Date: 2025-12-24

"""

from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "company_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("slogan", sa.String(length=255), nullable=True),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "analyzers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("connection_type", sa.String(length=30), nullable=True),
        sa.Column("host", sa.String(length=255), nullable=True),
        sa.Column("port", sa.String(length=50), nullable=True),
        sa.Column("protocol", sa.String(length=30), nullable=True),
    )

    op.create_table(
        "tests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("default_analyzer_id", sa.Integer(), sa.ForeignKey("analyzers.id"), nullable=True),
        sa.Column("price_ghs", sa.Numeric(10,2), nullable=True),
    )

    op.create_table(
        "test_parameters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("test_id", sa.Integer(), sa.ForeignKey("tests.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("ref_range", sa.String(length=100), nullable=True),
        sa.UniqueConstraint("test_id","name", name="uq_test_param"),
    )
    op.create_index("ix_test_parameters_test_id", "test_parameters", ["test_id"])


    op.create_table(
        "insurance_companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False, server_default="private"),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.UniqueConstraint("name", name="uq_insurance_company_name"),
    )
    op.create_index("ix_insurance_companies_name", "insurance_companies", ["name"], unique=True)

    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_no", sa.String(length=50), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("surname", sa.String(length=100), nullable=False),
        sa.Column("other_names", sa.String(length=150), nullable=True),
        sa.Column("sex", sa.String(length=10), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("patient_type", sa.String(length=20), nullable=False, server_default="cash"),
        sa.Column("insurance_company_id", sa.Integer(), sa.ForeignKey("insurance_companies.id"), nullable=True),
        sa.Column("insurance_member_id", sa.String(length=100), nullable=True),
        sa.Column("guardian_name", sa.String(length=150), nullable=True),
        sa.Column("guardian_phone", sa.String(length=50), nullable=True),
        sa.Column("guardian_relation", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("patient_no", name="uq_patient_no"),
    )
    op.create_index("ix_patients_patient_no", "patients", ["patient_no"], unique=True)
    op.create_index("ix_patients_surname", "patients", ["surname"])
    op.create_index("ix_patients_first_name", "patients", ["first_name"])



    op.create_table(
        "visits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("visit_date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_visits_patient_id", "visits", ["patient_id"])

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("appointment_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="scheduled"),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"])
    op.create_index("ix_appointments_appointment_at", "appointments", ["appointment_at"])

    op.create_table(
        "lab_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("status", sa.String(length=30), nullable=False),
    )
    op.create_index("ix_lab_orders_patient_id", "lab_orders", ["patient_id"])

    op.create_table(
        "lab_order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("lab_orders.id"), nullable=False),
        sa.Column("test_id", sa.Integer(), sa.ForeignKey("tests.id"), nullable=False),
        sa.Column("analyzer_id", sa.Integer(), sa.ForeignKey("analyzers.id"), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("external_sample_id", sa.String(length=100), nullable=True),
    )
    op.create_index("ix_lab_order_items_order_id", "lab_order_items", ["order_id"])
    op.create_index("ix_lab_order_items_test_id", "lab_order_items", ["test_id"])

    op.create_table(
        "analyzer_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("analyzer_id", sa.Integer(), sa.ForeignKey("analyzers.id"), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("raw", sa.Text(), nullable=False),
    )

def downgrade():
    op.drop_table("analyzer_messages")
    op.drop_index("ix_lab_order_items_test_id", table_name="lab_order_items")
    op.drop_index("ix_lab_order_items_order_id", table_name="lab_order_items")
    op.drop_table("lab_order_items")
    op.drop_index("ix_lab_orders_patient_id", table_name="lab_orders")
    op.drop_table("lab_orders")
    op.drop_index("ix_patients_patient_no", table_name="patients")
    op.drop_table("appointments")
    op.drop_table("visits")
    op.drop_table("patients")
    op.drop_table("insurance_companies")
    op.drop_index("ix_test_parameters_test_id", table_name="test_parameters")
    op.drop_table("test_parameters")
    op.drop_table("tests")
    op.drop_table("analyzers")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("company_profile")
