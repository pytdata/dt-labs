async function loadBillingRecords() {
    const container = document.querySelector('.billing__container');
    
    try {
        const response = await fetch('/api/v1/billing/records');
        const records = await response.json();

        console.log(records, "====================")

        // 1. Check if there are no records
        if (!records || records.length === 0) {
            container.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center py-5">
                        <div class="no-data-found">
                            <i class="ti ti-receipt-off fs-1 text-muted mb-2"></i>
                            <h5 class="text-muted">No Billing Records Found</h5>
                            <p class="mb-0">All bills created during appointments will appear here.</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        // 2. Render records if they exist
        container.innerHTML = records.map(bill => `
            <tr>
                <td>
                    <div class="form-check form-check-md">
                        <input class="form-check-input" type="checkbox">
                    </div>
                </td>
                <td><span class="text-primary fw-bold">${bill.bill_no}</span></td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="avatar avatar-sm me-2">
                            <img src="${bill.patient.profile_image}" class="rounded-circle" alt="Patient">
                        </div>
                        <div>
                            <h6 class="mb-0">${bill.patient.first_name} ${bill.patient.surname}</h6>
                            <small>${bill.patient.patient_no}</small>
                        </div>
                    </div>
                </td>
                <td>${new Date(bill.appointment.appointment_at).toLocaleDateString()}</td>
                <td>GHS ${parseFloat(bill.total_billed).toFixed(2)}</td>
              <td><span class="badge bg-info-light text-info">${bill.items.length} Tests</span></td>
                <td>
                    <span class="badge ${getStatusClass(bill.appointment.invoice.status)} text-dark">
                        ${bill.appointment.invoice.status.toUpperCase()}
                    </span>
                </td>
                <td class="text-end">
                    <div class="dropdown">
                        <a href="javascript:void(0);" class="btn btn-icon btn-sm" data-bs-toggle="dropdown"><i class="ti ti-dots-vertical"></i></a>
                        <ul class="dropdown-menu dropdown-menu-end">
                            <li><a class="dropdown-item" href="javascript:void(0);" onclick="viewBillDetails(${bill.id})"><i class="ti ti-eye me-1"></i> View Details</a></li>
                        </ul>
                    </div>
                </td>
            </tr>
        `).join('');

    } catch (error) {
        console.error("Fetch Error:", error);
        container.innerHTML = `<tr><td colspan="8" class="text-center text-danger py-4">Error loading records. Please refresh.</td></tr>`;
    }
}

function getStatusClass(status) {
    console.log("status: =>", status)
    if (status === 'paid') return 'bg-success-light';
    if (status === 'partial') return 'bg-warning-light';
    return 'bg-danger-light';
}
async function viewBillDetails(billId) {
    try {
        const response = await fetch(`/api/v1/billing/records/${billId}`);
        if (!response.ok) throw new Error('Failed to fetch billing details');
        
        const bill = await response.json();
        const invoice = bill.appointment?.invoice;

        // 1. Calculate the paid amount and percentage for the progress bar
        const total = parseFloat(bill.total_billed || 0);
        const paid = parseFloat(invoice?.amount_paid || 0); // This will now pick up the 20.00
        const balance = parseFloat(invoice?.balance || 0);
        const paidPercentage = total > 0 ? (paid / total) * 100 : 0;

        const getPaidBadge = (isPaid) => {
            return isPaid 
                ? '<span class="badge bg-success-light text-success"><i class="ti ti-check me-1"></i>Paid</span>' 
                : '<span class="badge bg-danger-light text-danger"><i class="ti ti-clock me-1"></i>Unpaid</span>';
        };

        let itemsHtml = `
            <div class="mb-3 d-flex justify-content-between align-items-start">
                <div>
                    <h5 class="mb-1">${bill.patient.first_name} ${bill.patient.surname}</h5>
                    <p class="text-muted mb-0 small">Bill No: <strong class="text-primary">${bill.bill_no}</strong></p>
                </div>
                <div class="text-end">
                    <span class="badge ${invoice?.status === 'paid' ? 'bg-success' : 'bg-warning'} mb-1">
                        ${(invoice?.status || 'Unpaid').toUpperCase()}
                    </span>
                    <span class="text-muted d-block small">Date: ${new Date(bill.created_at).toLocaleDateString()}</span>
                </div>
            </div>

            <div class="mb-4">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="small text-muted">Payment Progress</span>
                    <span class="small fw-bold">${paidPercentage.toFixed(0)}%</span>
                </div>
                <div class="progress" style="height: 8px;">
                    <div class="progress-bar bg-success" role="progressbar" style="width: ${paidPercentage}%" aria-valuenow="${paidPercentage}" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
            </div>
            
            <div class="table-responsive border rounded mb-3">
                <table class="table table-nowrap custom-table mb-0">
                    <thead class="thead-light">
                        <tr>
                            <th>Test Description</th>
                            <th class="text-center">Status</th>
                            <th class="text-end">Price</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${bill.items.map(item => `
                            <tr>
                                <td class="text-wrap">${item.test_name}</td>
                                <td class="text-center">${getPaidBadge(item.is_paid)}</td>
                                <td class="text-end fw-bold">GHS ${parseFloat(item.price_at_booking || 0).toFixed(2)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                    <tfoot class="bg-light">
                        <tr>
                            <td colspan="2" class="text-end text-muted small">Subtotal:</td>
                            <td class="text-end small">GHS ${total.toFixed(2)}</td>
                        </tr>
                        <tr>
                            <td colspan="2" class="text-end text-success small">Amount Paid:</td>
                            <td class="text-end text-success small">- GHS ${paid.toFixed(2)}</td>
                        </tr>
                        <tr class="border-top">
                            <td colspan="2" class="text-end fw-bold">Remaining Balance:</td>
                            <td class="text-end"><h5 class="mb-0 text-danger fw-bold">GHS ${balance.toFixed(2)}</h5></td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        `;
        
        document.getElementById('bill_details_content').innerHTML = itemsHtml;
        
        const modalElement = document.getElementById('view_bill_modal');
        if (typeof bootstrap !== 'undefined') {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
        } else {
            $(modalElement).modal('show');
        }

    } catch (error) {
        console.error("Error loading bill details:", error);
        alert("Could not load billing details.");
    }
}


loadBillingRecords();


