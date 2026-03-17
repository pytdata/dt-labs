from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from app.models.billing import Billing, BillingItem, Invoice, Payment, InvoiceItem
from app.models.lab import LabOrderItem
from app.models.enums import LabStage, LabStatus
from app.schemas.billing import PaymentCreate

from decimal import Decimal
from sqlalchemy import update, select
from sqlalchemy.orm import selectinload, joinedload


async def process_bill_payment(
    db: AsyncSession,
    invoice_id: int,
    payment_data: PaymentCreate,
    user_id: int | None = None,
):
    # 1. Fetch Invoice with its Items, Tests, and the linked Billing record
    result = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(selectinload(Invoice.items).joinedload(InvoiceItem.test))
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # 2. Create Payment Record
    new_payment = Payment(
        invoice_id=invoice_id,
        amount=payment_data.amount,
        method=payment_data.method,
        reference=payment_data.reference,
        verified_by_user_id=user_id,
        description=payment_data.description,
    )
    db.add(new_payment)

    # 3. Enhanced Helper to unlock items AND update Master Billing Record
    async def unlock_item(inv_item: InvoiceItem):
        if inv_item.is_paid:
            return

        inv_item.is_paid = True

        # A. UPDATE MASTER BILLING RECORD (For your Modal Status)
        # We find the billing item associated with this appointment and this test
        await db.execute(
            update(BillingItem)
            .where(
                BillingItem.billing_id
                == (
                    select(Billing.id)
                    .where(Billing.appointment_id == invoice.appointment_id)
                    .scalar_subquery()
                ),
                BillingItem.test_id == inv_item.test_id,
            )
            .values(is_paid=True)
        )

        # B. UPDATE CLINICAL WORKFLOW
        if inv_item.lab_order_item_id:
            if inv_item.test.requires_phlebotomy:
                new_status, new_stage = LabStatus.AWAITING_SAMPLE, LabStage.SAMPLING
            else:
                new_status, new_stage = LabStatus.AWAITING_RESULTS, LabStage.RUNNING

            await db.execute(
                update(LabOrderItem)
                .where(LabOrderItem.id == inv_item.lab_order_item_id)
                .values(status=new_status, stage=new_stage)
            )

    # 4. Process selected items (Partial Payment)
    if payment_data.test_ids_to_clear:
        for item in invoice.items:
            if item.id in payment_data.test_ids_to_clear:
                await unlock_item(item)

    # 5. Update Invoice Totals
    invoice.amount_paid = Decimal(str(invoice.amount_paid)) + Decimal(
        str(payment_data.amount)
    )
    invoice.balance = Decimal(str(invoice.total_amount)) - invoice.amount_paid

    # 6. Global Status & Final Cleanup
    if invoice.balance <= 0:
        invoice.status = "paid"
        invoice.balance = 0
        for item in invoice.items:
            await unlock_item(item)
    elif invoice.amount_paid > 0:
        invoice.status = "partial"

    return invoice
