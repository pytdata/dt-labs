from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.db.session import get_db
from app.models.billing import Invoice, InvoiceItem, Payment
from app.schemas import billing_service
from app.schemas.billing import PaymentCreate

router = APIRouter()


@router.post("/{invoice_id}/payments", response_model=None)
async def create_invoice_payment(
    invoice_id: int,
    payment_in: PaymentCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        # 1. Process the logic (updates Invoice, creates Payment, toggles items)
        updated_invoice = await billing_service.process_bill_payment(
            db=db, invoice_id=invoice_id, payment_data=payment_in, user_id=None
        )

        # 2. COMMIT the changes to the database
        await db.commit()

        # 3. Refresh to get the latest state from the DB
        await db.refresh(updated_invoice)

        return {
            "status": "success",
            "message": "Payment recorded successfully",
            "new_balance": float(updated_invoice.balance),
            "invoice_status": updated_invoice.status,
        }
    except HTTPException as e:
        await db.rollback()  # Rollback on known errors
        raise e
    except Exception as e:
        await db.rollback()  # Rollback on crashes
        print(f"Error processing payment: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}",
        )


@router.post("/invoices/{invoice_id}/pay")
async def mark_invoice_as_paid_full(
    invoice_id: int, db: AsyncSession = Depends(get_db)
):
    """Simple full-payment shortcut."""
    try:
        # Fetch invoice
        result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = result.scalar_one_or_none()

        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # Reuse the logic but for full amount
        payment_data = PaymentCreate(
            amount=invoice.total_amount,
            method=invoice.payment_mode or "cash",
            description="Full payment shortcut",
        )

        updated_invoice = await billing_service.process_bill_payment(
            db=db, invoice_id=invoice_id, payment_data=payment_data, user_id=None
        )

        return {"status": "success", "message": "Invoice fully paid"}
    except Exception as e:
        print(f"DEBUG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payments/{payment_id}/receipt")
async def get_payment_receipt(payment_id: int, db: AsyncSession = Depends(get_db)):
    # Fetch payment with all related details
    stmt = (
        select(Payment)
        .where(Payment.id == payment_id)
        .options(
            joinedload(Payment.invoice).joinedload(Invoice.patient),
            joinedload(Payment.invoice)
            .selectinload(Invoice.items)
            .joinedload(InvoiceItem.test),
        )
    )
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    return {
        "payment_ref": f"REC-{payment.id:04d}",
        "date": payment.created_at.strftime("%Y-%m-%d %H:%M"),
        "patient_name": f"{payment.invoice.patient.first_name} {payment.invoice.patient.last_name}",
        "patient_id": payment.invoice.patient.id,
        "amount_paid": float(payment.amount),
        "payment_method": payment.method,
        "invoice_no": payment.invoice.invoice_no,
        "balance_remaining": float(payment.invoice.balance),
        "items": [
            {"name": item.test.name, "price": float(item.unit_price)}
            for item in payment.invoice.items
            if item.is_paid
        ],
    }


@router.get("/payments/{payment_id}/print", response_class=HTMLResponse)
async def print_receipt_page(payment_id: int, db: AsyncSession = Depends(get_db)):
    # Fetch data (same logic as before)
    stmt = (
        select(Payment)
        .where(Payment.id == payment_id)
        .options(joinedload(Payment.invoice).joinedload(Invoice.patient))
    )
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()

    if not payment:
        return "<h1>Receipt Not Found</h1>"

    return f"""
    <html>
    <head>
        <style>
            body {{ font-family: sans-serif; padding: 20px; line-height: 1.4; color: #333; }}
            .receipt-header {{ text-align: center; border-bottom: 2px solid #000; margin-bottom: 20px; }}
            .info-row {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
            .totals {{ text-align: right; margin-top: 20px; }}
            .footer {{ text-align: center; margin-top: 40px; font-size: 0.8em; font-style: italic; }}
            @media print {{
                .no-print {{ display: none; }}
                body {{ padding: 0; }}
            }}
        </style>
    </head>
    <body>
        <div class="no-print" style="background: #fff3cd; padding: 10px; margin-bottom: 20px; text-align: center;">
            <button onclick="window.print()" style="padding: 10px 20px; cursor: pointer;">Click here to Print</button>
        </div>
        
        <div class="receipt-header">
            <h2>HOSPITAL NAME</h2>
            <p>Official Payment Receipt</p>
        </div>

        <div class="info-row">
            <span><strong>Receipt No:</strong> REC-{payment.id}</span>
            <span><strong>Date:</strong> {payment.created_at.strftime("%d %b %Y %H:%M")}</span>
        </div>
        
        <div class="info-row">
            <span><strong>Patient:</strong> {payment.invoice.patient.first_name} {payment.invoice.patient.last_name}</span>
            <span><strong>ID:</strong> {payment.invoice.patient.id}</span>
        </div>

        <table>
            <thead>
                <tr><th>Description</th><th>Amount</th></tr>
            </thead>
            <tbody>
                <tr>
                    <td>Payment for Medical Services (Invoice {payment.invoice.invoice_no})</td>
                    <td>GHS {payment.amount:,.2f}</td>
                </tr>
            </tbody>
        </table>

        <div class="totals">
            <p><strong>Amount Paid: GHS {payment.amount:,.2f}</strong></p>
            <p>Remaining Balance: GHS {payment.invoice.balance:,.2f}</p>
        </div>

        <div class="footer">
            <p>Thank you for choosing our facility.</p>
            <p>Payment Method: {payment.method} | Ref: {payment.reference or "N/A"}</p>
        </div>
    </body>
    </html>
    """
