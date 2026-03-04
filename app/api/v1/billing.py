from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.billing import Invoice, Payment
from decimal import Decimal

router = APIRouter()


@router.post("/invoices/{invoice_id}/pay")
async def mark_invoice_as_paid(invoice_id: int, db: AsyncSession = Depends(get_db)):
    try:
        async with db.begin():
            # 1. Fetch the invoice
            result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
            invoice = result.scalar_one_or_none()

            if not invoice:
                raise HTTPException(status_code=404, detail="Invoice not found")

            if invoice.status == "paid":
                return {"message": "Invoice is already paid"}

            # 2. Record the Payment entry for audit trails
            new_payment = Payment(
                invoice_id=invoice.id,
                amount=invoice.total_amount,
                method=invoice.payment_mode,
                description="Paid via Appt Edit",
            )
            db.add(new_payment)

            # 3. Update Invoice Status
            invoice.amount_paid = invoice.total_amount
            invoice.balance = 0
            invoice.status = "paid"

        return {"status": "success", "message": "Payment confirmed"}

    except Exception as e:
        print(f"DEBUG: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
