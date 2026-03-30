/**
 * BILLING MANAGEMENT MODULE
 */

let billingContainerEL = document.querySelector(".billing__container");
let totalBillingEl = document.querySelector(".total__billings");
let billingURL = "/api/v1/billing/records";
let billingDataTable = null;

// 1. GLOBAL FILTER STATE
let currentFilters = {
    start: moment().subtract(29, 'days').format('YYYY-MM-DD'),
    end: moment().format('YYYY-MM-DD'),
    status: ''
};

/**
 * INITIALIZATION
 */
(function init() {
    const checkDeps = setInterval(() => {
        // Ensure all plugins are loaded (especially important with rocket-loader)
        const hasDeps = window.jQuery && window.moment && jQuery.fn.DataTable && jQuery.fn.daterangepicker;
        if (hasDeps) {
            clearInterval(checkDeps);
            console.log("💳 Billing Module Initialized");
            
            setupDateFilter();
            setupStatusFilter();
            fetchAndRender(currentFilters.start, currentFilters.end);
        }
    }, 100);
})();

/**
 * 2. FILTER SETUP FUNCTIONS
 */
function setupDateFilter() {
    const $picker = $('#reportrange');
    if (!$picker.length) return;

    $picker.daterangepicker({
        startDate: moment(currentFilters.start),
        endDate: moment(currentFilters.end),
        ranges: {
            'Today': [moment(), moment()],
            'Yesterday': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
            'Last 7 Days': [moment().subtract(6, 'days'), moment()],
            'Last 30 Days': [moment().subtract(29, 'days'), moment()],
            'This Month': [moment().startOf('month'), moment().endOf('month')],
            'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
        }
    }, function(start, end) {
        currentFilters.start = start.format('YYYY-MM-DD');
        currentFilters.end = end.format('YYYY-MM-DD');
        
        $('.reportrange-picker-field').html(start.format('MMMM D, YYYY') + ' - ' + end.format('MMMM D, YYYY'));
        fetchAndRender(currentFilters.start, currentFilters.end);
    });

    // Set initial text
    $('.reportrange-picker-field').html(moment(currentFilters.start).format('MMMM D, YYYY') + ' - ' + moment(currentFilters.end).format('MMMM D, YYYY'));
}

function setupStatusFilter() {
    $('.dropdown-menu .dropdown-item').on('click', function(e) {
        e.preventDefault();
        const selected = $(this).text().trim();
        
        // Update Button Text UI
        $(this).closest('.dropdown').find('.dropdown-toggle').text(selected);
        
        // Set Filter Logic
        currentFilters.status = (selected === "Select Status" || selected === "All") ? "" : selected;
        fetchAndRender(currentFilters.start, currentFilters.end);
    });
}

/**
 * 3. DATA FETCHING
 */
async function fetchAndRender(startDate = '', endDate = '') {
    try {
        let url = new URL(billingURL, window.location.origin);
        
        if (startDate && endDate) {
            url.searchParams.set('start_date', startDate);
            url.searchParams.set('end_date', endDate);
        }
        if (currentFilters.status) {
            url.searchParams.set('status', currentFilters.status);
        }

        const res = await fetch(url.toString());
        if (!res.ok) throw new Error("Failed to fetch billing records");
        const data = await res.json();
        
        renderTable(data);
    } catch (error) {
        console.error("Billing fetch error:", error);
        if (billingContainerEL) {
            billingContainerEL.innerHTML = `<tr><td colspan="8" class="text-center text-danger py-4">Error loading records.</td></tr>`;
        }
    }
}

/**
 * 4. TABLE RENDERING & DATATABLE CONFIG
 */
function renderTable(records) {
    if (!billingContainerEL) return;
    
    totalBillingEl.textContent = `${records.length} Billing`;

    // Reset Existing DataTable
    if ($.fn.DataTable.isDataTable('.table.border')) {
        $('.table.border').DataTable().clear().destroy();
    }

    if (!records || records.length === 0) {
        billingContainerEL.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-5">
                    <div class="no-data-found">
                        <i class="ti ti-receipt-off fs-1 text-muted mb-2"></i>
                        <h5 class="text-muted">No Billing Records Found</h5>
                    </div>
                </td>
            </tr>`;
        return;
    }

    // Map rows
    billingContainerEL.innerHTML = records.map(bill => renderRow(bill)).join("");

    // Initialize DataTable with Export Buttons
    billingDataTable = $('.table.border').DataTable({
        columnDefs: [{ targets: [0, 7], orderable: false }],
        dom: 'tpr',
        pageLength: 15,
        buttons: [
            { 
                extend: 'excelHtml5', 
                title: 'Billing_Export_' + moment().format('YYYY-MM-DD'),
                exportOptions: { columns: [1, 2, 3, 4, 5, 6] } 
            },
            { 
                extend: 'pdfHtml5', 
                title: 'Billing_Report_' + moment().format('YYYY-MM-DD'),
                orientation: 'landscape',
                exportOptions: { columns: [1, 2, 3, 4, 5, 6] }
            }
        ]
    });

    // Handle External Export Button Clicks
    $('.export-excel').off('click').on('click', () => billingDataTable.button(0).trigger());
    $('.export-pdf').off('click').on('click', () => billingDataTable.button(1).trigger());
}

function renderRow(bill) {
    const status = bill.appointment?.invoice?.status || 'unpaid';
    
    return `
    <tr>
        <td><div class="form-check form-check-md"><input class="form-check-input" type="checkbox"></div></td>
        <td><span class="text-primary fw-bold">${bill.bill_no}</span></td>
        <td>
            <div class="d-flex align-items-center">
                <img src="${bill.patient?.profile_image || '/static/img/default-user.png'}" class="avatar avatar-sm rounded-circle me-2">
                <div>
                    <h6 class="mb-0 fs-14 fw-medium">${bill.patient?.first_name} ${bill.patient?.surname}</h6>
                    <small class="text-muted">${bill.patient?.patient_no}</small>
                </div>
            </div>
        </td>
        <td>${moment(bill.appointment?.appointment_at).format('DD MMM, YYYY')}</td>
        <td class="fw-bold text-dark">GHS ${parseFloat(bill.total_billed).toFixed(2)}</td>
        <td><span class="badge bg-info-light text-info">${bill.items?.length || 0} Tests</span></td>
        <td>
            <span class="badge ${getStatusClass(status)} text-dark">
                ${status.toUpperCase()}
            </span>
        </td>
        <td class="text-end">
            <button class="btn btn-sm btn-light" onclick="viewBillDetails(${bill.id})">
                <i class="ti ti-eye"></i>
            </button>
        </td>
    </tr>`;
}

function getStatusClass(status) {
    const s = status.toLowerCase();
    if (s === 'paid') return 'bg-success-light';
    if (s === 'partial') return 'bg-warning-light';
    return 'bg-danger-light';
}

/**
 * 5. MODAL DETAIL VIEW
 */
window.viewBillDetails = async function(billId) {
    try {
        const response = await fetch(`/api/v1/billing/records/${billId}`);
        if (!response.ok) throw new Error('Failed to fetch billing details');
        
        const bill = await response.json();
        const invoice = bill.appointment?.invoice;

        const total = parseFloat(bill.total_billed || 0);
        const paid = parseFloat(invoice?.amount_paid || 0);
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
                    <span class="text-muted d-block small">Date: ${moment(bill.created_at).format('DD/MM/YYYY')}</span>
                </div>
            </div>

            <div class="mb-4">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="small text-muted">Payment Progress</span>
                    <span class="small fw-bold">${paidPercentage.toFixed(0)}%</span>
                </div>
                <div class="progress" style="height: 8px;">
                    <div class="progress-bar bg-success" role="progressbar" style="width: ${paidPercentage}%"></div>
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
                        ${(bill.items || []).map(item => `
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
        bootstrap.Modal.getOrCreateInstance(modalElement).show();

    } catch (error) {
        console.error("Error loading bill details:", error);
    }
}