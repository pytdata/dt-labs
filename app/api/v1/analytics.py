from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import literal_column, select, func, and_, union_all
from datetime import datetime, timedelta
from typing import List, Dict

from sqlalchemy.orm import joinedload

from app.db.session import get_db
from app.models import Patient, Appointment
from app.models.billing import Payment
from app.models.lab import LabOrderItem, LabResult, RadiologyLabResult
from app.models.permission import Role
from app.models.users import User

router = APIRouter()


@router.get("/dashboard-stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """
    Returns data for the 4 top metric cards and Sparkline charts
    """
    # 1. Total Patients & Trend
    total_patients = await db.scalar(select(func.count(Patient.id)))
    # (Mocking trend logic - in real app, compare count from last 30 days vs previous 30)

    # 2. Appointments
    total_appointments = await db.scalar(select(func.count(Appointment.id)))

    # 3. Total Staff (Doctors/Technicians)
    total_staff = await db.scalar(select(func.count(User.id)))

    # 4. Total Revenue
    total_revenue = await db.scalar(select(func.sum(Payment.amount))) or 0

    return {
        "metrics": {
            "patients": {
                "total": total_patients,
                "change": "+12%",
                "trend": [30, 40, 35, 50, 49, 60, 70],
            },
            "appointments": {
                "total": total_appointments,
                "change": "-5%",
                "trend": [20, 15, 25, 10, 18, 12],
            },
            "staff": {
                "total": total_staff,
                "change": "+2%",
                "trend": [5, 5, 6, 6, 7, 8],
            },
            "revenue": {
                "total": f"₵{total_revenue:,.2f}",
                "change": "+18%",
                "trend": [400, 800, 600, 900, 1100],
            },
        }
    }


@router.get("/patient-statistics")
async def get_patient_stats(db: AsyncSession = Depends(get_db)):
    """
    Returns New vs Old patients for Chart-5 (Doughnut/Pie)
    """
    # Example logic: New = registered in last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    new_patients = await db.scalar(
        select(func.count(Patient.id)).where(Patient.created_at >= thirty_days_ago)
    )
    total_patients = await db.scalar(select(func.count(Patient.id)))
    old_patients = total_patients - new_patients

    return {
        "labels": ["New Patients", "Old Patients"],
        "series": [new_patients, old_patients],
    }


@router.get("/transaction-history")
async def get_transaction_history(db: AsyncSession = Depends(get_db)):
    """
    Returns data for Chart-6 (Transactions Area Chart)
    """
    # Grouping revenue by month
    result = await db.execute(
        select(
            func.to_char(Payment.created_at, "Mon").label("month"),
            func.sum(Payment.amount).label("total"),
        ).group_by("month")
    )

    data = result.all()
    return {
        "labels": [row.month for row in data],
        "values": [float(row.total) for row in data],
    }


@router.get("/top-metrics")
async def get_top_metrics(db: AsyncSession = Depends(get_db)):
    # Get current counts
    count_patients = await db.scalar(select(func.count(Patient.id)))
    count_appointments = await db.scalar(select(func.count(Appointment.id)))
    count_doctors = await db.scalar(
        select(func.count(User.id))
    )  # Assuming Staff table filtered by role if needed
    sum_transactions = await db.scalar(select(func.sum(Payment.amount))) or 0

    return {
        "patients": {
            "value": count_patients,
            "change": "+20%",  # Hardcoded for now, can be calculated later
            "trend": [10, 40, 30, 50, 45, 60, 55],  # Data for the sparkline
        },
        "appointments": {
            "value": count_appointments,
            "change": "-15%",
            "trend": [20, 15, 25, 10, 18, 12, 22],
        },
        "doctors": {
            "value": count_doctors,
            "change": "+18%",
            "trend": [2, 3, 3, 4, 4, 5, 5],
        },
        "transactions": {
            "value": f"₵{sum_transactions:,.2f}",
            "change": "+12%",
            "trend": [400, 800, 600, 900, 1100, 800, 1200],
        },
    }


@router.get("/recent-patient-records")
async def get_recent_patient_records(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Patient).order_by(Patient.created_at.desc()).limit(5)
    )
    patients = result.scalars().all()

    return [
        {
            "full_name": p.full_name,
            "patient_no": p.patient_no,
            "sex": p.sex or "N/A",
            "image": p.profile_image,  # This uses your @property logic
            "created_at": p.created_at.strftime("%d %b %Y"),
            "id": p.id,
        }
        for p in patients
    ]


@router.get("/dashboard-bottom-widgets")
async def get_bottom_widgets(db: AsyncSession = Depends(get_db)):
    # Lab Technicians
    tech_query = select(User).join(User.role).limit(5)
    technicians = (await db.execute(tech_query)).scalars().all()

    #  Total Earnings
    total_earnings = await db.scalar(select(func.sum(Payment.amount))) or 0

    #  Recent Lab Results (The Fixed Join Logic)
    # We must go: Result -> Item -> Order -> Patient
    from app.models import LabOrder  # Ensure this is imported

    lab_union = (
        select(
            literal_column("'Lab'").label("type"),
            LabResult.received_at.label("date"),
            func.concat(Patient.first_name, " ", Patient.surname).label("patient_name"),
            Patient.image_url.label("patient_img"),
            func.coalesce(LabResult.test_no, "Lab Test").label("test_name"),
        )
        .join(LabOrderItem, LabResult.order_item_id == LabOrderItem.id)
        .join(LabOrder, LabOrderItem.order_id == LabOrder.id)
        .join(Patient, LabOrder.patient_id == Patient.id)
    )

    rad_union = (
        select(
            literal_column("'Radiology'").label("type"),
            RadiologyLabResult.entered_at.label("date"),
            func.concat(Patient.first_name, " ", Patient.surname).label("patient_name"),
            Patient.image_url.label("patient_img"),
            literal_column("'Radiology Scan'").label("test_name"),
        )
        .join(LabOrderItem, RadiologyLabResult.order_item_id == LabOrderItem.id)
        .join(LabOrder, LabOrderItem.order_id == LabOrder.id)
        .join(Patient, LabOrder.patient_id == Patient.id)
    )

    # Combine, sort by date descending, and limit to the 5 most recent across both tables
    results_query = (
        union_all(lab_union, rad_union).order_by(literal_column("date").desc()).limit(5)
    )
    recent_results = (await db.execute(results_query)).all()

    return {
        "technicians": [
            {
                "name": t.full_name,
                "role": t.role.name if t.role else "Staff",
                "avatar": t.avatar,
                "status": "Available" if t.is_active else "Unavailable",
            }
            for t in technicians
        ],
        "earnings": {"total": f"₵{total_earnings:,.2f}", "change": "+18%"},
        "results": [
            {
                "test": r.test_name,
                "date": r.date.strftime("%d %b %Y") if r.date else "N/A",
                "patient": r.patient_name,
                "patient_img": r.patient_img
                or "/static/img/defaults/male-patient.jpeg",
                "type": r.type,
            }
            for r in recent_results
        ],
    }


@router.get("/recent-appointments")
async def get_recent_appointments(db: AsyncSession = Depends(get_db)):
    """
    Returns the latest 5 appointments with Patient and Doctor details
    """
    result = await db.execute(
        select(Appointment)
        .options(
            joinedload(Appointment.patient),
            joinedload(
                Appointment.doctor
            ),  # Assuming 'doctor' is the relationship name for the User model
        )
        .order_by(Appointment.appointment_at.desc())
        .limit(5)
    )
    appointments = result.scalars().all()

    return [
        {
            "id": appt.id,
            "patient_no": appt.patient.patient_no,
            "patient_name": appt.patient.full_name,
            "patient_img": appt.patient.profile_image,
            "session_type": "Consultation",  # Or use a field if you have one
            "doctor_name": appt.doctor.full_name if appt.doctor else "Unassigned",
            "doctor_img": appt.doctor.avatar
            if appt.doctor
            else "/static/img/defaults/male-patient.jpeg",
            "date_time": appt.appointment_at.strftime("%d %b %Y, %I:%M %p"),
            "status": appt.status.capitalize() if appt.status else "Pending",
        }
        for appt in appointments
    ]
