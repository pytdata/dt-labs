from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from app.models.billing import Invoice, Payment, InvoiceItem
from app.models.lab import LabOrderItem
from app.models.enums import LabStatus
from app.schemas.billing import PaymentCreate


async def process_bill_payment(
    db: AsyncSession,
    invoice_id: int,
    payment_data: PaymentCreate,
    user_id: int | None = None,
):
    # 1. Fetch Invoice AND its Items + Tests (needed for phlebotomy check)
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

    # 3. Helper function to unlock items correctly
    async def unlock_item(inv_item: InvoiceItem):
        inv_item.is_paid = True
        if inv_item.lab_order_item_id:
            # Check if it actually needs phlebotomy
            new_status = (
                LabStatus.AWAITING_SAMPLE
                if inv_item.test.requires_phlebotomy
                else LabStatus.AWAITING_RESULTS
            )
            await db.execute(
                update(LabOrderItem)
                .where(LabOrderItem.id == inv_item.lab_order_item_id)
                .values(status=new_status)
            )

    # 4. Process selected items
    if payment_data.test_ids_to_clear:
        for item in invoice.items:
            if item.id in payment_data.test_ids_to_clear:
                await unlock_item(item)

    # 5. Update Financials
    invoice.amount_paid = Decimal(str(invoice.amount_paid)) + Decimal(
        str(payment_data.amount)
    )
    invoice.balance = Decimal(str(invoice.total_amount)) - invoice.amount_paid

    # 6. Global Status & Final Cleanup
    if invoice.balance <= 0:
        invoice.status = "paid"
        # If fully paid, ensure EVERY item is unlocked
        for item in invoice.items:
            if not item.is_paid:
                await unlock_item(item)
    elif invoice.amount_paid > 0:
        invoice.status = "partial"

    return invoice
