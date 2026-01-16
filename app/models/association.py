# Linking table for appointment to hold many test

from sqlalchemy import (
    Column,
    ForeignKey,
    Table,
)

from app.db.base import Base

appointment_tests = Table(
    "appointment_tests",
    Base.metadata,
    Column("appointment_id", ForeignKey("appointments.id"), primary_key=True),
    Column("test_id", ForeignKey("tests.id"), primary_key=True),
)
