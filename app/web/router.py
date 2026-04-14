from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from enum import Enum
from fastapi import (
    APIRouter,
    Request,
    HTTPException,
    Depends,
    Form,
    Query,
    BackgroundTasks,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, select, or_
from sqlalchemy.orm import joinedload, selectinload


from app.core import deps
from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.catalog import SampleCategory, TestCategory
from app.models.enums import LabStage
from app.models.permission import Permission, Role
from app.models.users import Department, User
from app.schemas.appointment import AppointmenCreate
from app.schemas.staff import StaffRole
from app.schemas.visit import PaymentMode, VisitStatus
from app.services.emailer import send_stage_email
from app.services.sample_service import generate_sample_id
from app.models import (
    Patient,
    InsuranceCompany,
    Test,
    Analyzer,
    LabOrder,
    LabOrderItem,
    Visit,
    Appointment,
    Invoice,
    InvoiceItem,
    Payment,
    LabStatusLog,
)

templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)
router = APIRouter()


def _render(
    request: Request,
    template_name: str,
    *,
    active_page: str | None = None,
    active_group: str | None = None,
    **extra,
):
    ctx = {
        "request": request,
        "active_page": active_page,
        "active_group": active_group,
        "unread_count": 0,
    }
    ctx.update(extra)
    return templates.TemplateResponse(template_name, ctx)


# Dashboard stays on "/"
@router.get("/", response_class=HTMLResponse, name="dashboard")
async def dashboard(
    request: Request,
    current_user: User = Depends(deps.get_current_user),  # Ensure logged in
):
    return _render(
        request, "index.html", active_page="dashboard", current_user=current_user
    )


@router.get("/login", response_class=HTMLResponse, name="login")
async def login(request: Request):
    return _render(request, "login.html")


@router.get("/billing", response_class=HTMLResponse, name="billing_list")
async def billing(request: Request):
    return _render(request, "all-billing.html")


@router.post("/login", name="login_post")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    user = await deps.authenticate_user(db, username, password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token(
        subject=user.email,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    response = RedirectResponse(url=request.url_for("dashboard"), status_code=303)
    response.set_cookie(
        "access_token",
        token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )
    return response


@router.get("/patients", response_class=HTMLResponse, name="patients")
async def patients_page(
    request: Request,
    q: str | None = Query(default=None, description="Filter by surname or first_name"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    # Check permission manually for Template routes
    if not current_user.has_permission("patients", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this module.",
        )

    stmt = select(Patient).order_by(Patient.id.desc())
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            (Patient.surname.ilike(like)) | (Patient.first_name.ilike(like))
        )
    patients = (await db.execute(stmt)).scalars().all()

    # Get all the staffs
    staff_stmt = select(User).order_by(User.id.desc())
    staffs = (await db.execute(staff_stmt)).scalars().all()

    # Get all tests
    test_stmt = select(Test).order_by(Test.id.desc())
    tests = (await db.execute(test_stmt)).scalars().all()

    tpl = (
        "all-patients-list.html"
        if (settings.TEMPLATES_PATH / "all-patients-list.html").exists()
        else "all-patients.html"
    )

    return _render(
        request,
        tpl,
        active_page="patients",
        patients=patients,
        staffs=staffs,
        tests=tests,
        q=q or "",
        user_perms=current_user.role.permissions if current_user.role else [],
    )


@router.get(
    "/patients/add",
    response_class=HTMLResponse,
    name="patient_add",
)
async def patient_add_get(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    if not current_user.has_permission("patients", "write"):
        raise HTTPException(status_code=403, detail="Access Denied")
    ins = (
        (
            await db.execute(
                select(InsuranceCompany).order_by(InsuranceCompany.name.asc())
            )
        )
        .scalars()
        .all()
    )
    return _render(
        request, "add-patient.html", active_page="patients", insurance_companies=ins
    )


@router.post("/patients/add", name="patient_add_post")
async def patient_add_post(
    request: Request,
    first_name: str = Form(...),
    surname: str = Form(...),
    other_names: str | None = Form(None),
    sex: str | None = Form(None),
    date_of_birth: date | None = Form(None),
    phone: str = Form(...),
    age: str = Form(...),
    email: str | None = Form(None),
    address: str | None = Form(None),
    patient_type: str = Form("cash"),
    insurance_company_id: int | None = Form(None),
    insurance_member_id: str | None = Form(None),
    guardian_name: str | None = Form(None),
    guardian_phone: str | None = Form(None),
    guardian_relation: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):

    if not current_user.has_permission("patients", "write"):
        # For a POST request, you might want to redirect back with an error message
        return RedirectResponse(url="/patients?error=unauthorized", status_code=303)

    # generate patient_no (same rule as API)
    from sqlalchemy import func

    max_id = (await db.execute(select(func.max(Patient.id)))).scalar() or 0
    nxt = int(max_id) + 1
    patient_no = f"YGK-PT-{nxt:06d}"

    patient = Patient(
        patient_no=patient_no,
        first_name=first_name.strip(),
        surname=surname.strip(),
        other_names=(other_names.strip() if other_names else None),
        sex=sex,
        date_of_birth=date_of_birth,
        age=age,
        phone=phone,
        email=email,
        address=address,
        patient_type=patient_type,
        insurance_company_id=insurance_company_id,
        insurance_member_id=insurance_member_id,
        guardian_name=guardian_name,
        guardian_phone=guardian_phone,
        guardian_relation=guardian_relation,
    )
    db.add(patient)
    await db.commit()

    return RedirectResponse(url=request.url_for("patients"), status_code=303)


@router.get(
    "/patients/{patient_id}", response_class=HTMLResponse, name="patient_detail"
)
async def patient_detail(
    request: Request,
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    # Ensure user is authenticated
    current_user: User = Depends(deps.get_current_user),
):
    # Permission Check
    if not current_user.has_permission("patients", "read"):
        # For UI routes, raise a 403 or redirect to a 'denied' page
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You do not have permission to view patient details.",
        )

    #  Fetch Patient
    result = await db.execute(
        select(Patient)
        .where(Patient.id == patient_id)
        # It's good practice to load the insurance details for the detail view
        .options(joinedload(Patient.insurance_company))
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    #  Template Selection
    tpl = (
        "patient-details.html"
        if (settings.TEMPLATES_PATH / "patient-details.html").exists()
        else "all-patients.html"
    )

    # Render with Context
    return _render(
        request,
        tpl,
        active_page="patients",
        patient=patient,
        # Pass current_user to allow the template to hide/show Edit or Delete buttons
        current_user=current_user,
    )


@router.get("/patients/{patient_id}/visit", name="patient_new_visit")
async def patient_new_visit_get(
    request: Request, patient_id: int, db: AsyncSession = Depends(get_db)
):
    patient = (
        await db.execute(select(Patient).where(Patient.id == patient_id))
    ).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = Visit(patient_id=patient_id, reason="Return visit")
    db.add(visit)
    await db.commit()
    return RedirectResponse(url=request.url_for("patients"), status_code=303)


@router.post("/patients/{patient_id}/visit", name="patient_new_visit_post")
async def patient_new_visit_post(
    request: Request,
    patient_id: int,
    reason: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    patient = (
        await db.execute(select(Patient).where(Patient.id == patient_id))
    ).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = Visit(patient_id=patient_id, reason=reason or "Return visit")
    db.add(visit)
    await db.commit()
    return RedirectResponse(url=request.url_for("patients"), status_code=303)


@router.get(
    "/patients/{patient_id}/appointments/add",
    response_class=HTMLResponse,
    name="appointment_add",
)
async def appointment_add_get(
    request: Request,
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    # Permission Check
    # Creating an appointment is a 'write' action
    if not current_user.has_permission("appointments", "write"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You do not have permission to book appointments.",
        )

    # Fetch Patient
    patient = (
        await db.execute(select(Patient).where(Patient.id == patient_id))
    ).scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Fetch Test Categories for the selection UI
    test_categories = (await db.execute(select(TestCategory))).scalars().all()

    # Fetch Staff (Filtering by Role Slugs)
    # Adjusted to use the relationship logic we established earlier
    staff_stmt = (
        select(User)
        .join(User.role)
        .join(Role.permissions)
        .where(
            Permission.resource == "appointments",
            Permission.action == "write",
            User.is_active == True,
        )
        .distinct()  # Prevent duplicate users if they have multiple matching perms
    )
    staff_results = (await db.execute(staff_stmt)).scalars().all()

    # Render
    return _render(
        request,
        "appointment-add.html",
        active_page="appointments",
        patient=patient,
        staffs=staff_results,
        test_categories=test_categories,
        current_user=current_user,
    )


@router.post("/patients/{patient_id}/appointments/add", name="appointment_add_post")
async def appointment_add_post(
    request: Request,
    patient_id: int,
    appointment_at: str = Form(...),
    notes: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    # Ensure user is authenticated
    current_user: User = Depends(deps.get_current_user),
):
    # Permission Check
    if not current_user.has_permission("appointments", "write"):
        # Redirect back with an error or show a 403
        return RedirectResponse(
            url=f"/patients/{patient_id}?error=unauthorized", status_code=303
        )

    #  Verify Patient Existence
    patient = (
        await db.execute(select(Patient).where(Patient.id == patient_id))
    ).scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Parse Datetime (Handling Flatpickr formats)
    try:
        dt = datetime.fromisoformat(appointment_at)
    except ValueError:
        try:
            dt = datetime.strptime(appointment_at, "%Y-%m-%d %H:%M")
        except ValueError:
            # Fallback/Error if format is totally unexpected
            raise HTTPException(
                status_code=400, detail="Invalid date format. Expected YYYY-MM-DD HH:mm"
            )

    # Create Appointment with Audit Data
    appt = Appointment(
        patient_id=patient_id,
        appointment_at=dt,
        notes=notes,
        # Track who performed the booking
        created_by_user_id=current_user.id,
    )

    try:
        db.add(appt)
        await db.commit()
    except Exception as e:
        await db.rollback()
        print(f"Booking Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save appointment.")

    # Success Redirect
    return RedirectResponse(url=request.url_for("appointments"), status_code=303)


@router.get(
    "/patients/{patient_id}/book-lab",
    response_class=HTMLResponse,
    name="patient_book_lab",
)
async def patient_book_lab_get(
    request: Request, patient_id: int, db: AsyncSession = Depends(get_db)
):
    patient = (
        await db.execute(select(Patient).where(Patient.id == patient_id))
    ).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    tests = (
        (
            await db.execute(
                select(Test)
                .options(selectinload(Test.default_analyzer))
                .order_by(Test.name.asc())
            )
        )
        .scalars()
        .all()
    )
    return _render(
        request,
        "book-lab.html",
        active_page="lab_main",
        active_group="lab",
        patient=patient,
        tests=tests,
    )


@router.post("/patients/{patient_id}/book-lab", name="patient_book_lab_post")
async def patient_book_lab_post(
    request: Request,
    patient_id: int,
    test_ids: list[int] = Form(...),
    db: AsyncSession = Depends(get_db),
):
    patient = (
        await db.execute(select(Patient).where(Patient.id == patient_id))
    ).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Record a visit (returning patient activity)
    db.add(Visit(patient_id=patient_id, reason="Lab service"))

    # Create order
    order = LabOrder(
        patient_id=patient_id, status="pending", sample_id=generate_sample_id()
    )
    db.add(order)
    await db.flush()  # get order.id

    # Load tests
    tests = (
        (await db.execute(select(Test).where(Test.id.in_(test_ids)))).scalars().all()
    )
    if not tests:
        raise HTTPException(status_code=400, detail="No tests selected")

    # Enforce analyzer mapping per test for automation
    missing = [t.name for t in tests if not t.default_analyzer_id]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=(
                "Missing analyzer mapping for: " + ", ".join(missing) + ". "
                "Go to Settings → Test Mapping and set a default analyzer for these tests."
            ),
        )

    total = 0.0
    for t in tests:
        price = float(t.price_ghs or 0)
        total += price
        item = LabOrderItem(
            order_id=order.id,
            test_id=t.id,
            analyzer_id=t.default_analyzer_id,
            status="pending",
            stage="booking",
            sample_id=order.sample_id,
        )
        db.add(item)

    # Create invoice
    from sqlalchemy import func

    max_id = (await db.execute(select(func.max(Invoice.id)))).scalar() or 0
    inv_no = f"YGK-INV-{int(max_id) + 1:06d}"

    invoice = Invoice(
        invoice_no=inv_no,
        patient_id=patient_id,
        order_id=order.id,
        total_amount=total,
        amount_paid=0,
        balance=total,
        status="unpaid",
    )
    db.add(invoice)
    await db.flush()

    for t in tests:
        price = float(t.price_ghs or 0)
        db.add(
            InvoiceItem(
                invoice_id=invoice.id,
                test_id=t.id,
                description=t.name,
                unit_price=price,
                qty=1,
                line_total=price,
            )
        )

    await db.commit()
    return RedirectResponse(
        url=request.url_for("invoice_detail", invoice_id=invoice.id), status_code=303
    )


@router.get("/invoice/{invoice_id}", response_class=HTMLResponse, name="invoice_detail")
async def invoice_detail(
    request: Request,
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    # Ensure user is authenticated
    current_user: User = Depends(deps.get_current_user),
):
    # Permission Check
    # We use 'billing' as the resource name to match your permission table
    if not current_user.has_permission("billing", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You do not have permission to view invoices.",
        )

    # Fetch Invoice with Comprehensive Loading
    stmt = (
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(
            selectinload(Invoice.items),
            selectinload(Invoice.payments),
            selectinload(Invoice.patient),
            # Load appointment so you can show the Doctor/Date on the invoice
            joinedload(Invoice.appointment).joinedload(Appointment.doctor),
        )
    )

    result = await db.execute(stmt)
    invoice = result.unique().scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Render
    return _render(
        request,
        "invoice-pay.html",
        active_page="billing",
        invoice=invoice,
        current_user=current_user,
    )


@router.post("/invoice/{invoice_id}/pay", name="invoice_pay")
async def invoice_pay(
    request: Request,
    invoice_id: int,
    amount: float = Form(...),
    method: str = Form("cash"),
    reference: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    # Ensure user is authenticated
    current_user: User = Depends(deps.get_current_user),
):
    # Permission Check
    if not current_user.has_permission("billing", "write"):
        return RedirectResponse(
            url=f"/invoice/{invoice_id}?error=unauthorized", status_code=303
        )

    # Use begin_nested to avoid "Transaction already begun" errors
    async with db.begin_nested():
        # Fetch Invoice
        invoice = (
            await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        ).scalar_one_or_none()

        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # Create Payment with Audit Trail
        pay = Payment(
            invoice_id=invoice.id,
            amount=amount,
            method=method,
            reference=reference,
            # Track who received the payment
            created_by_id=current_user.id,
        )
        db.add(pay)
        await db.flush()

        # Update Invoice Totals
        paid = float(invoice.amount_paid or 0) + float(amount)
        total = float(invoice.total_amount or 0)
        bal = max(total - paid, 0.0)

        invoice.amount_paid = paid
        invoice.balance = bal

        if bal <= 0.0001:
            invoice.status = "paid"
        elif paid > 0:
            invoice.status = "partial"
        else:
            invoice.status = "unpaid"

        invoice.payment_mode = method

        # Advance Lab Stages automatically
        if invoice.status == "paid" and invoice.order_id:
            items_res = await db.execute(
                select(LabOrderItem).where(LabOrderItem.order_id == invoice.order_id)
            )
            items = items_res.scalars().all()

            for it in items:
                # Use LabStage enum if available, otherwise strings match your current logic
                if it.stage == "booking":
                    db.add(
                        LabStatusLog(
                            order_item_id=it.id,
                            from_stage=it.stage,
                            to_stage="sampling",
                            note="Auto: payment confirmed",
                            # Log who triggered the stage change
                            created_by_id=current_user.id,
                        )
                    )
                    it.stage = "sampling"
                    # Also update item status if needed
                    it.status = "awaiting_sampling"

    # Commit the outer transaction
    await db.commit()

    return RedirectResponse(
        url=request.url_for("invoice_detail", invoice_id=invoice_id), status_code=303
    )


@router.get("/visits", response_class=HTMLResponse, name="visits")
async def visits(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    patients = await db.execute(select(Patient))
    department = await db.execute(select(Department))
    visits = await db.execute(select(Visit))
    doctors = await db.execute(
        select(User).where(User.role == "doctor", User.is_active == True)  # noqa: E712
    )

    patients_results = patients.scalars().all()
    doctors_results = doctors.scalars().all()
    department_results = department.scalars().all()
    visits_length = len(visits.scalars().all())

    return _render(
        request=request,
        template_name="visits.html",
        active_page="visits",
        departments=department_results,
        doctors=doctors_results,
        patients=patients_results,
        visits_length=visits_length,
    )


@router.post("/visits/add/")
async def create_visit(
    request: Request,
    patient_id: int = Form(...),
    department_id: int = Form(...),
    doctor_id: int = Form(...),
    visit_date: str = Form(...),
    visit_time: str = Form(...),
    reason: str | None = Form(None),
    patient_type: str = Form(...),
    payment_mode: PaymentMode | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    visit_date_obj = datetime.strptime(visit_date, "%d-%m-%Y").replace(
        tzinfo=timezone.utc
    )
    time_of_visit_obj = (
        datetime.strptime("14:30", "%H:%M").time().replace(tzinfo=timezone.utc)
    )

    visit = Visit(
        patient_id=patient_id,
        department_id=department_id,
        doctor_id=doctor_id,
        visit_date=visit_date_obj,
        reason=reason,
        status=VisitStatus.pending,
        mode_of_payment=payment_mode,
        time_of_visit=time_of_visit_obj,
    )

    db.add(visit)
    await db.commit()

    return RedirectResponse(
        url="/visits/",
        status_code=303,
    )


@router.get("/appointments", response_class=HTMLResponse, name="appointments")
async def appointments(
    request: Request,
    db: AsyncSession = Depends(get_db),
    # Ensure user is authenticated
    current_user: User = Depends(deps.get_current_user),
):
    # Permission Check
    if not current_user.has_permission("appointments", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You do not have permission to view the appointment list.",
        )

    # Fetch lookup data
    patients = await db.execute(select(Patient))
    departments = await db.execute(select(Department))
    sample_categories = await db.execute(select(SampleCategory))

    # Corrected to count Appointments instead of Visits
    appointments_count_res = await db.execute(select(func.count(Appointment.id)))

    # DYNAMIC STAFF FILTERING
    # Fetches staff authorized to handle appointments
    doctors_stmt = (
        select(User)
        .join(User.role)
        .join(Role.permissions)
        .where(
            and_(
                Permission.resource == "appointments",
                Permission.action.in_(["read", "write"]),
                User.is_active == True,
            )
        )
        .distinct()
    )
    doctors = await db.execute(doctors_stmt)

    # OPTIMIZED TEST CATEGORIES
    test_categories_stmt = (
        select(TestCategory)
        .options(selectinload(TestCategory.tests))
        .order_by(TestCategory.category_name.asc())
    )
    test_categories = await db.execute(test_categories_stmt)

    # Result Extraction
    patients_results = patients.scalars().all()
    department_results = departments.scalars().all()
    staff_results = doctors.scalars().all()
    test_categories_results = test_categories.scalars().all()
    sample_categories_results = sample_categories.scalars().all()
    total_appointments = appointments_count_res.scalar() or 0

    return _render(
        request,
        "all-appointments.html",
        active_page="appointments",
        departments=department_results,
        patients=patients_results,
        staffs=staff_results,
        test_categories=test_categories_results,
        total_appointments=total_appointments,
        sample_categories=sample_categories_results,
        current_user=current_user,
    )


@router.get(
    "/appointments/add",
    response_class=HTMLResponse,
    name="appointments_add_redirect",
)
async def create_appointments(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    # Permission Check
    if not current_user.has_permission("appointments", "write"):
        return RedirectResponse(url="/appointments?error=unauthorized", status_code=303)

    # Perform Redirect
    # Usually, a GET to /add would render a form, but if your flow
    # requires a redirect to the main list, we maintain that here.
    return RedirectResponse(
        url="/appointments/",
        status_code=303,
    )


@router.get("/lab", response_class=HTMLResponse, name="lab_main")
async def lab_main(
    request: Request, current_user: User = Depends(deps.get_current_user)
):
    # Permission: General lab access
    if not current_user.has_permission("lab", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You do not have permission to access the Laboratory module.",
        )

    return _render(
        request,
        "laboratory.html",
        active_page="lab_main",
        active_group="lab",
        current_user=current_user,
    )


@router.get("/lab/results", response_class=HTMLResponse, name="lab_results")
async def lab_results(
    request: Request, current_user: User = Depends(deps.get_current_user)
):
    # Permission: Specifically reading lab results
    if not current_user.has_permission("lab", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied."
        )

    tpl = (
        "lab-results.html"
        if (settings.TEMPLATES_PATH / "lab-results.html").exists()
        else "laboratory.html"
    )
    return _render(
        request,
        tpl,
        active_page="lab_results",
        active_group="lab",
        current_user=current_user,
    )


@router.get("/phlebotomy", response_class=HTMLResponse, name="phlebotomy")
async def phlebotomy(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    # Permission: Phlebotomy access (adjust resource name if yours is 'sampling')
    if not current_user.has_permission("phlebotomy", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You do not have permission for Phlebotomy.",
        )

    tpl = (
        "phlebotomy.html"
        if (settings.TEMPLATES_PATH / "phlebotomy.html").exists()
        else "phlebotomy.html"
    )

    # DYNAMIC STAFF: Fetch only active staff who can actually perform phlebotomy
    staff_stmt = (
        select(User)
        .join(User.role)
        .join(Role.permissions)
        .where(
            Permission.resource == "phlebotomy",
            Permission.action.in_(["read", "write"]),
            User.is_active == True,
        )
        .distinct()
    )

    phlebotomists = (await db.execute(staff_stmt)).scalars().all()

    return _render(
        request,
        tpl,
        phlebotomy=phlebotomists,
        active_page="phlebotomy",
        current_user=current_user,
    )


@router.get("/radiology", response_class=HTMLResponse, name="radiology")
async def radiology(
    request: Request,
    db: AsyncSession = Depends(get_db),
    # Ensure user is authenticated
    current_user: User = Depends(deps.get_current_user),
):
    # Permission Check
    # Resource: "radiology", Action: "read"
    if not current_user.has_permission("radiology", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You do not have permission to access the Radiology module.",
        )

    # Template Selection
    tpl = (
        "radiology.html"
        if (settings.TEMPLATES_PATH / "radiology.html").exists()
        else "radiology.html"
    )

    # Render with Context
    return _render(
        request,
        tpl,
        active_page="radiology",
        current_user=current_user,
    )


@router.get("/reports", response_class=HTMLResponse, name="reports")
async def reports(
    request: Request,
    db: AsyncSession = Depends(get_db),
    # Ensure user is authenticated
    current_user: User = Depends(deps.get_current_user),
):
    # Permission Check
    # Aggregated reports usually require high-level clearance
    if not current_user.has_permission("reports", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You do not have permission to view system reports.",
        )

    # Template Selection
    tpl = (
        "reports.html"
        if (settings.TEMPLATES_PATH / "reports.html").exists()
        else "transaction-report.html"
    )

    # Render with Context
    return _render(
        request,
        tpl,
        active_page="reports",
        current_user=current_user,  # Allows template to toggle specific report sections
    )


@router.get("/staff", response_class=HTMLResponse, name="staff_list")
async def staff_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    # Ensure user is authenticated and active
    current_user: User = Depends(deps.get_current_user),
):
    # Permission Check
    # Only users with 'staff:read' (or 'users:read') should see this list
    if not current_user.has_permission("staff", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You do not have permission to view the staff directory.",
        )

    # Template Selection
    tpl = (
        "staffs.html"
        if (settings.TEMPLATES_PATH / "staffs.html").exists()
        else "all-doctors-list.html"
    )

    # Fetch Staff with Role data
    # Added joinedload so the template can display staff roles without extra queries
    stmt = select(User).options(joinedload(User.role)).order_by(User.id.desc())
    result = await db.execute(stmt)
    staff_results = result.scalars().all()
    staff_counts = len(staff_results)

    # Render
    return _render(
        request,
        tpl,
        active_page="staff",
        staffs=staff_results,
        staff_counts=staff_counts,
        current_user=current_user,  # Pass for UI permission checks
    )


@router.get("/invoice", response_class=HTMLResponse, name="invoice_list")
async def invoice_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    if not current_user.has_permission("billing", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied"
        )

    tpl = (
        "invoice.html"
        if (settings.TEMPLATES_PATH / "invoice.html").exists()
        else "add-invoice.html"
    )
    return _render(request, tpl, active_page="invoice", current_user=current_user)


@router.get("/payments", response_class=HTMLResponse, name="payments")
async def payments(
    request: Request, current_user: User = Depends(deps.get_current_user)
):
    # Usually falls under billing or a specific 'accounting' permission
    if not current_user.has_permission("billing", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied"
        )

    tpl = (
        "transactions.html"
        if (settings.TEMPLATES_PATH / "transactions.html").exists()
        else "add-payment.html"
    )
    return _render(request, tpl, active_page="payments", current_user=current_user)


@router.get("/notifications", response_class=HTMLResponse, name="notifications")
async def notifications(
    request: Request, current_user: User = Depends(deps.get_current_user)
):
    # Everyone can usually read their own notifications,
    # but accessing the notification dashboard may require a general 'user' permission
    tpl = (
        "notifications.html"
        if (settings.TEMPLATES_PATH / "notifications.html").exists()
        else "notifications-settings.html"
    )
    return _render(request, tpl, active_page="notifications", current_user=current_user)


@router.get("/messages", response_class=HTMLResponse, name="messages")
async def messages(
    request: Request, current_user: User = Depends(deps.get_current_user)
):
    # Basic permission check for communication module
    if not current_user.has_permission("messages", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied"
        )

    tpl = (
        "messages.html"
        if (settings.TEMPLATES_PATH / "messages.html").exists()
        else "chat.html"
    )
    return _render(request, tpl, active_page="messages", current_user=current_user)


@router.get("/settings", response_class=HTMLResponse, name="settings")
async def settings_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    print(current_user.full_name, current_user.role.slug)
    # Settings should strictly be restricted to Admins
    if not current_user.has_permission("settings", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Only administrators can access system settings.",
        )

    return _render(
        request,
        "settings-general.html",
        active_page="settings",
        active_group="settings",
        settings=settings,
        current_user=current_user,
    )


@router.get(
    "/settings/tests-and-samples", response_class=HTMLResponse, name="tests_and_samples"
)
async def test_and_samples(
    request: Request,
    db: AsyncSession = Depends(get_db),
    # Ensure user is authenticated and has administrative/config rights
    current_user: User = Depends(deps.get_current_user),
):
    # Permission Check
    # Restrict to users who can manage system configurations
    if not current_user.has_permission("settings", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You do not have permission to manage test and sample settings.",
        )

    # Fetch Data for the Settings UI
    # Usually, this page needs the current list of tests and categories
    test_categories = (await db.execute(select(TestCategory))).scalars().all()
    sample_types = (await db.execute(select(SampleCategory))).scalars().all()

    # Render
    return _render(
        request,
        "tests-and-samples.html",
        active_page="tests_and_samples",
        active_group="settings",
        settings=settings,
        test_categories=test_categories,
        sample_types=sample_types,
        current_user=current_user,
    )


@router.get(
    "/settings/test-mapping", response_class=HTMLResponse, name="settings_test_mapping"
)
async def settings_test_mapping(
    request: Request,
    db: AsyncSession = Depends(get_db),
    # Ensure user is authenticated and has configuration permissions
    current_user: User = Depends(deps.get_current_user),
):
    # Permission Check
    if not current_user.has_permission("settings", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You do not have permission to modify analyzer mappings.",
        )

    # Fetch Active Analyzers
    analyzers_stmt = (
        select(Analyzer).where(Analyzer.is_active == True).order_by(Analyzer.name.asc())
    )
    analyzers = (await db.execute(analyzers_stmt)).scalars().all()

    # Fetch Tests with their current default analyzer mappings
    tests_stmt = (
        select(Test)
        .options(selectinload(Test.default_analyzer))
        .order_by(Test.department.asc().nulls_last(), Test.name.asc())
    )
    tests = (await db.execute(tests_stmt)).scalars().all()

    # Render with Context
    return _render(
        request,
        "settings-test-mapping.html",
        active_page="settings_test_mapping",
        active_group="settings",
        analyzers=analyzers,
        tests=tests,
        current_user=current_user,  # Added for template-level permission checks
    )


@router.post("/settings/test-mapping", name="settings_test_mapping_post")
async def settings_test_mapping_post(
    request: Request,
    test_id: list[int] = Form(...),
    default_analyzer_id: list[str] = Form(...),
    price_ghs: list[str] = Form(...),
    db: AsyncSession = Depends(get_db),
    # Ensure user is authenticated
    current_user: User = Depends(deps.get_current_user),
):
    #  Permission Check
    # Bulk updating configurations is strictly a 'write' action
    if not current_user.has_permission("settings", "write"):
        return RedirectResponse(
            url=f"{request.url_for('settings_test_mapping')}?error=unauthorized",
            status_code=303,
        )

    # Validation
    if not (len(test_id) == len(default_analyzer_id) == len(price_ghs)):
        raise HTTPException(status_code=400, detail="Form lists are misaligned.")

    try:
        # 3. Transactional Safety (Savepoint)
        async with db.begin_nested():
            # Fetch tests in one query for efficiency
            stmt = select(Test).where(Test.id.in_(test_id))
            tests = (await db.execute(stmt)).scalars().all()
            test_map = {t.id: t for t in tests}

            for i, tid in enumerate(test_id):
                t = test_map.get(tid)
                if not t:
                    continue

                # Update Analyzer Mapping
                raw_analyzer = (default_analyzer_id[i] or "").strip()
                t.default_analyzer_id = (
                    int(raw_analyzer) if raw_analyzer.isdigit() else None
                )

                # Update Price
                raw_price = (price_ghs[i] or "").strip()
                try:
                    t.price_ghs = float(raw_price) if raw_price else t.price_ghs
                except ValueError:
                    # Log invalid price but continue
                    pass

        # Finalize
        await db.commit()

    except Exception as e:
        await db.rollback()
        print(f"Mapping Update Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update test mappings.",
        )

    return RedirectResponse(
        url=request.url_for("settings_test_mapping"), status_code=303
    )


@router.get(
    "/settings/analyzers", response_class=HTMLResponse, name="settings_analyzers"
)
async def settings_analyzers(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    if not current_user.has_permission("settings", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied"
        )

    analyzers = (
        (await db.execute(select(Analyzer).order_by(Analyzer.name.asc())))
        .scalars()
        .all()
    )
    return _render(
        request,
        "settings-analyzers.html",
        active_page="settings_analyzers",
        active_group="settings",
        analyzers=analyzers,
        current_user=current_user,
    )


# --- ROLES & PERMISSIONS ---
@router.get("/settings/roles", response_class=HTMLResponse, name="settings_roles")
async def settings_roles(
    request: Request, current_user: User = Depends(deps.get_current_user)
):
    # This is the most sensitive route in the app
    if not current_user.has_permission("settings", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied"
        )

    return _render(
        request,
        "roles-and-permissions.html",
        active_page="settings_roles",
        active_group="settings",
        title="Roles & Permissions",
        message="Roles & permissions management UI coming soon.",
        current_user=current_user,
    )


# --- INSURANCE CONFIG ---
@router.get(
    "/settings/insurance", response_class=HTMLResponse, name="settings_insurance"
)
async def settings_insurance(
    request: Request, current_user: User = Depends(deps.get_current_user)
):
    if not current_user.has_permission("settings", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied"
        )

    return _render(
        request,
        "settings-placeholder.html",
        active_page="settings_insurance",
        active_group="settings",
        title="Insurance",
        message="Insurance configuration will live here.",
        current_user=current_user,
    )


# --- DOCUMENT TEMPLATES ---
@router.get(
    "/settings/templates", response_class=HTMLResponse, name="settings_templates"
)
async def settings_templates(
    request: Request, current_user: User = Depends(deps.get_current_user)
):
    if not current_user.has_permission("settings", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied"
        )

    return _render(
        request,
        "settings-placeholder.html",
        active_page="settings_templates",
        active_group="settings",
        title="Templates",
        message="Document and notification templates will be configurable here.",
        current_user=current_user,
    )


# --- PREFIXES & NUMBERING ---
@router.get("/settings/prefixes", response_class=HTMLResponse, name="settings_prefixes")
async def settings_prefixes(
    request: Request, current_user: User = Depends(deps.get_current_user)
):
    if not current_user.has_permission("settings", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied"
        )

    return _render(
        request,
        "settings-and-prefixes.html",
        active_page="settings_prefixes",
        active_group="settings",
        title="Prefixes",
        message="Prefix and numbering rules can be managed here.",
        current_user=current_user,
    )


# --- ADD ANALYZER FORM ---
@router.get("/settings/analyzers/add", response_class=HTMLResponse, name="analyzer_add")
async def analyzer_add_get(
    request: Request, current_user: User = Depends(deps.get_current_user)
):
    # This requires 'write' access conceptually, but 'read' to see the form
    if not current_user.has_permission("settings", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied"
        )

    return _render(
        request,
        "analyzer-form.html",
        active_page="settings_analyzers",
        active_group="settings",
        analyzer=None,
        current_user=current_user,
    )


@router.post("/settings/analyzers/add", name="analyzer_add_post")
async def analyzer_add_post(
    request: Request,
    name: str = Form(...),
    connection_type: str = Form("tcp"),
    result_format: str = Form("ASTM"),
    tcp_ip: str | None = Form(None),
    tcp_port: int | None = Form(None),
    serial_port: str | None = Form(None),
    baud_rate: int | None = Form(None),
    parity: str | None = Form(None),
    stop_bits: int | None = Form(None),
    data_bits: int | None = Form(None),
    flow_control: str | None = Form(None),
    manufacturer: str | None = Form(None),
    model: str | None = Form(None),
    notes: str | None = Form(None),
    is_active: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    # Ensure user is authenticated
    current_user: User = Depends(deps.get_current_user),
):
    # Permission Check
    if not current_user.has_permission("settings", "write"):
        return RedirectResponse(
            url=f"{request.url_for('settings_analyzers')}?error=unauthorized",
            status_code=303,
        )

    # Duplicate Check
    exists = (
        await db.execute(select(Analyzer).where(Analyzer.name == name.strip()))
    ).scalar_one_or_none()

    if exists:
        # If using HTMX, you might prefer a 200 with an error message,
        # but for standard forms, a 400 is appropriate.
        raise HTTPException(status_code=400, detail="Analyzer name already exists")

    # Create Instance
    analyzer = Analyzer(
        name=name.strip(),
        connection_type=connection_type,
        result_format=result_format,
        tcp_ip=(tcp_ip.strip() if tcp_ip else None),
        tcp_port=tcp_port,
        serial_port=(serial_port.strip() if serial_port else None),
        baud_rate=baud_rate,
        parity=(parity.strip().lower() if parity else None),
        stop_bits=stop_bits,
        data_bits=data_bits,
        flow_control=(flow_control.strip().lower() if flow_control else None),
        manufacturer=(manufacturer.strip() if manufacturer else None),
        model=(model.strip() if model else None),
        notes=notes,
        is_active=(is_active == "on"),
        # Recommended: Track who added the hardware
        # created_by_id=current_user.id
    )

    try:
        db.add(analyzer)
        await db.commit()
    except Exception as e:
        await db.rollback()
        # Log the error for debugging
        print(f"Error adding analyzer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while saving analyzer.",
        )

    # Success Redirect
    return RedirectResponse(url=request.url_for("settings_analyzers"), status_code=303)


@router.get(
    "/settings/analyzers/{analyzer_id}/edit",
    response_class=HTMLResponse,
    name="analyzer_edit",
)
async def analyzer_edit_get(
    request: Request,
    analyzer_id: int,
    db: AsyncSession = Depends(get_db),
    # Ensure user is authenticated and active
    current_user: User = Depends(deps.get_current_user),
):
    #  Permission Check
    # We check for 'read' permission to view the form;
    # the POST route will handle the 'write' permission check.
    if not current_user.has_permission("settings", "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You do not have permission to edit analyzer settings.",
        )

    #  Fetch Analyzer
    analyzer = (
        await db.execute(select(Analyzer).where(Analyzer.id == analyzer_id))
    ).scalar_one_or_none()

    if not analyzer:
        raise HTTPException(status_code=404, detail="Analyzer not found")

    #
    return _render(
        request,
        "analyzer-form.html",
        active_page="settings_analyzers",
        active_group="settings",
        analyzer=analyzer,
        current_user=current_user,
    )


@router.post("/settings/analyzers/{analyzer_id}/edit", name="analyzer_edit_post")
async def analyzer_edit_post(
    request: Request,
    analyzer_id: int,
    name: str = Form(...),
    connection_type: str = Form("tcp"),
    result_format: str = Form("ASTM"),
    tcp_ip: str | None = Form(None),
    tcp_port: int | None = Form(None),
    serial_port: str | None = Form(None),
    baud_rate: int | None = Form(None),
    parity: str | None = Form(None),
    stop_bits: int | None = Form(None),
    data_bits: int | None = Form(None),
    flow_control: str | None = Form(None),
    manufacturer: str | None = Form(None),
    model: str | None = Form(None),
    notes: str | None = Form(None),
    is_active: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    # Ensure user is authenticated
    current_user: User = Depends(deps.get_current_user),
):
    #  Permission Check
    if not current_user.has_permission("settings", "write"):
        return RedirectResponse(
            url=f"{request.url_for('settings_analyzers')}?error=unauthorized",
            status_code=303,
        )

    # Fetch Existing Analyzer
    analyzer = (
        await db.execute(select(Analyzer).where(Analyzer.id == analyzer_id))
    ).scalar_one_or_none()

    if not analyzer:
        raise HTTPException(status_code=404, detail="Analyzer not found")

    # Update Fields
    analyzer.name = name.strip()
    analyzer.connection_type = connection_type
    analyzer.result_format = result_format
    analyzer.tcp_ip = tcp_ip.strip() if tcp_ip else None
    analyzer.tcp_port = tcp_port
    analyzer.serial_port = serial_port.strip() if serial_port else None
    analyzer.baud_rate = baud_rate
    analyzer.parity = parity.strip().lower() if parity else None
    analyzer.stop_bits = stop_bits
    analyzer.data_bits = data_bits
    analyzer.flow_control = flow_control.strip().lower() if flow_control else None
    analyzer.manufacturer = manufacturer.strip() if manufacturer else None
    analyzer.model = model.strip() if model else None
    analyzer.notes = notes
    analyzer.is_active = is_active == "on"

    # Commit with Error Handling
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        # Log error for technical review
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save analyzer updates.",
        )

    # Success Redirect
    return RedirectResponse(url=request.url_for("settings_analyzers"), status_code=303)


@router.post("/settings/analyzers/{analyzer_id}/delete", name="analyzer_delete")
async def analyzer_delete(
    request: Request, analyzer_id: int, db: AsyncSession = Depends(get_db)
):
    analyzer = (
        await db.execute(select(Analyzer).where(Analyzer.id == analyzer_id))
    ).scalar_one_or_none()
    if analyzer:
        await db.delete(analyzer)
        await db.commit()
    return RedirectResponse(url=request.url_for("settings_analyzers"), status_code=303)


STAGE_ORDER = [
    ("booking", "Booking"),
    ("sampling", "Taking Samples"),
    ("running", "Running Test"),
    ("complete", "Complete Test"),
    ("analyzing", "Analyzing Test"),
    ("printing", "Printing & Interpreting"),
    ("ended", "Ended"),
]

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "booking": {"sampling"},
    "sampling": {"running"},
    "running": {"complete", "printing"},  # manual flexibility
    "complete": {"analyzing"},
    "analyzing": {"printing"},
    "printing": {"ended"},
    "ended": set(),
}


@router.get("/tasks", response_class=HTMLResponse, name="tasks")
async def tasks_board(
    request: Request,
    q: str | None = Query(default=None, description="Filter by patient name or test"),
    db: AsyncSession = Depends(get_db),
):
    """Kanban-style workflow board for LabOrderItems."""

    # Pull items with related data
    stmt = (
        select(LabOrderItem)
        .options(
            selectinload(LabOrderItem.order).selectinload(LabOrder.patient),
            selectinload(LabOrderItem.test),
            selectinload(LabOrderItem.analyzer),
        )
        .order_by(LabOrderItem.id.desc())
    )

    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.join(LabOrder, LabOrderItem.order_id == LabOrder.id).join(
            Patient, LabOrder.patient_id == Patient.id
        )
        stmt = stmt.join(Test, LabOrderItem.test_id == Test.id)
        stmt = stmt.where(
            or_(
                Patient.surname.ilike(like),
                Patient.first_name.ilike(like),
                Test.name.ilike(like),
            )
        )

    items = (await db.execute(stmt)).scalars().all()

    # Invoice status map (order_id -> invoice)
    order_ids = {it.order_id for it in items}
    invoices = {}
    if order_ids:
        invs = (
            (await db.execute(select(Invoice).where(Invoice.order_id.in_(order_ids))))
            .scalars()
            .all()
        )
        invoices = {inv.order_id: inv for inv in invs if inv.order_id}

    # Group items by stage
    grouped: dict[str, list] = {k: [] for k, _ in STAGE_ORDER}
    for it in items:
        grouped.setdefault(
            (it.stage.value if hasattr(it.stage, "value") else (it.stage or "booking")),
            [],
        ).append(it)

    # Counts
    counts = {k: len(grouped.get(k, [])) for k, _ in STAGE_ORDER}

    return _render(
        request,
        "tasks.html",
        active_page="tasks",
        q=q or "",
        stage_order=STAGE_ORDER,
        grouped=grouped,
        counts=counts,
        invoices=invoices,
        allowed_transitions=ALLOWED_TRANSITIONS,
    )


@router.post("/api/tasks/{item_id}/stage", name="task_update_stage_api")
async def task_update_stage_api(
    item_id: int,
    payload: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """AJAX endpoint used by Kanban drag-and-drop."""
    to_stage = (payload.get("to_stage") or "").strip().lower()
    note = payload.get("note")
    it = (
        await db.execute(select(LabOrderItem).where(LabOrderItem.id == item_id))
    ).scalar_one_or_none()
    if not it:
        raise HTTPException(status_code=404, detail="Task not found")

    valid_stages = {k for k, _ in STAGE_ORDER}
    if to_stage not in valid_stages:
        raise HTTPException(status_code=400, detail="Invalid stage")

    from_stage = (
        it.stage.value if hasattr(it.stage, "value") else (it.stage or "booking")
    )
    if to_stage == from_stage:
        return {"ok": True, "stage": from_stage}

    allowed = ALLOWED_TRANSITIONS.get(from_stage, set())
    if to_stage not in allowed:
        raise HTTPException(
            status_code=400, detail=f"Not allowed: {from_stage} -> {to_stage}"
        )

    # Payment gate: Booking -> Sampling requires paid invoice
    inv = None
    if from_stage == "booking" and to_stage == "sampling":
        inv = (
            await db.execute(select(Invoice).where(Invoice.order_id == it.order_id))
        ).scalar_one_or_none()
        if not inv or inv.status != "paid":
            raise HTTPException(
                status_code=400, detail="Invoice must be PAID before sampling"
            )

    # Update stage
    it.stage = LabStage(to_stage)
    await db.commit()
    await db.refresh(it)

    # Log status change
    db.add(
        LabStatusLog(
            order_item_id=it.id, from_stage=from_stage, to_stage=to_stage, note=note
        )
    )
    await db.commit()

    # Notify patient via email (if available)
    try:
        order = (
            await db.execute(
                select(LabOrder)
                .where(LabOrder.id == it.order_id)
                .options(selectinload(LabOrder.patient))
            )
        ).scalar_one_or_none()
        if order and order.patient and order.patient.email:
            background_tasks.add_task(
                send_stage_email,
                to_email=order.patient.email,
                patient_name=f"{order.patient.first_name} {order.patient.surname}",
                stage=to_stage,
                order_id=order.id,
                test_name=None,
            )
    except Exception:
        # Don't block stage updates on notification errors
        pass

    return {"ok": True, "stage": to_stage}


@router.post("/tasks/{item_id}/stage", name="task_update_stage")
async def task_update_stage(
    request: Request,
    item_id: int,
    to_stage: str = Form(...),
    note: str | None = Form(None),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    it = (
        await db.execute(select(LabOrderItem).where(LabOrderItem.id == item_id))
    ).scalar_one_or_none()
    if not it:
        raise HTTPException(status_code=404, detail="Task not found")

    to_stage = (to_stage or "").strip().lower()
    valid_stages = {k for k, _ in STAGE_ORDER}
    if to_stage not in valid_stages:
        raise HTTPException(status_code=400, detail="Invalid stage")

    from_stage = (
        it.stage.value if hasattr(it.stage, "value") else (it.stage or "booking")
    )
    if to_stage == from_stage:
        return RedirectResponse(url=request.url_for("tasks"), status_code=303)

    allowed = ALLOWED_TRANSITIONS.get(from_stage, set())
    if to_stage not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Stage transition not allowed: {from_stage} -> {to_stage}",
        )

    # Payment gate: cannot leave booking unless invoice is PAID
    inv = None
    if it.order_id:
        inv = (
            await db.execute(select(Invoice).where(Invoice.order_id == it.order_id))
        ).scalar_one_or_none()
    if from_stage == "booking" and (not inv or inv.status != "paid"):
        raise HTTPException(
            status_code=400,
            detail="Payment is required before proceeding to the next step",
        )

    db.add(
        LabStatusLog(
            order_item_id=it.id, from_stage=from_stage, to_stage=to_stage, note=note
        )
    )
    it.stage = LabStage(to_stage)
    await db.commit()
    return RedirectResponse(url=request.url_for("tasks"), status_code=303)


# Legacy support: keep existing template links like "all-patients.html" working.
@router.get("/{page}.html", response_class=HTMLResponse, name="legacy_page")
async def legacy_page(request: Request, page: str):
    if "/" in page or ".." in page:
        raise HTTPException(status_code=404)
    template_name = f"{page}.html"
    template_path = settings.TEMPLATES_PATH / template_name
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    return _render(request, template_name)
