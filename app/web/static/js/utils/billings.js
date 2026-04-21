let billingContainerEL = document.querySelector(".billing__container");
let totalBillingEl = document.querySelector(".total__billings");
let billingURL = "/api/v1/billing/records";
let billingDataTable = null;

// 1. GLOBAL FILTER STATE
let currentFilters = {
    // Subtracting 30 instead of 29 makes it a "Custom Range" 
    start: moment().subtract(30, 'days').format('YYYY-MM-DD'), 
    end: moment().format('YYYY-MM-DD'),
    status: '',
    search: ''
};

/**
 * INITIALIZATION
 */
(function init() {
    const checkDeps = setInterval(() => {
        const hasDeps = window.jQuery && window.moment && jQuery.fn.DataTable && jQuery.fn.daterangepicker;
        if (hasDeps) {
            clearInterval(checkDeps);
            console.log("💳 Revenue Module Initialized");
            
            setupDateFilter();
            setupStatusFilter();
            setupSearchFilter(); // Call search setup
            
            fetchAndRender(); // Fetch with initial filters
            updateBillingStats();
        }
    }, 100);
})();


/**
 * 2. FILTER SETUP FUNCTIONS
 */
function setupSearchFilter() {
    // Listen for input on the search field (make sure the class matches your HTML)
    $('body').on('input', '.search__billing', function() {
        const query = $(this).val();
        
        clearTimeout(this.delay);
        this.delay = setTimeout(() => {
            currentFilters.search = query;
            console.log("🔍 Searching Revenue for:", query);
            fetchAndRender();
        }, 500); 
    });
}


function setupDateFilter() {
    const $picker = $('#reportrange');
    if (!$picker.length) return;

    $picker.daterangepicker({
        startDate: moment(currentFilters.start),
        endDate: moment(currentFilters.end),
        // This ensures the custom range calendars are always the focus
        alwaysShowCalendars: true, 
        ranges: {
            'Today': [moment(), moment()],
            'Yesterday': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
            'Last 7 Days': [moment().subtract(6, 'days'), moment()],
            'Last 30 Days': [moment().subtract(29, 'days'), moment()],
            'This Month': [moment().startOf('month'), moment().endOf('month')],
            'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
        }
    }, function(start, end, label) {
        currentFilters.start = start.format('YYYY-MM-DD');
        currentFilters.end = end.format('YYYY-MM-DD');
        
        // Logic to show either the Range Name or the Date String
        const text = (label === 'Custom Range') 
            ? start.format('MMMM D, YYYY') + ' - ' + end.format('MMMM D, YYYY') 
            : label;

        $('.reportrange-picker-field').html(text);
        fetchAndRender();
    });

    // Set initial field text to the actual date range
    $('.reportrange-picker-field').html(
        moment(currentFilters.start).format('MMMM D, YYYY') + ' - ' + moment(currentFilters.end).format('MMMM D, YYYY')
    );
}


function setupStatusFilter() {
    $('.dropdown-menu .dropdown-item').on('click', function(e) {
        e.preventDefault();
        const selected = $(this).text().trim();
        $(this).closest('.dropdown').find('.dropdown-toggle').text(selected);
        currentFilters.status = (selected === "Select Status" || selected === "All") ? "" : selected;
        fetchAndRender();
    });
}

/**
 * 3. DATA FETCHING
 */
async function fetchAndRender() {
    try {
        let url = new URL(billingURL, window.location.origin);
        
        url.searchParams.set('start_date', currentFilters.start);
        url.searchParams.set('end_date', currentFilters.end);
        
        if (currentFilters.status) url.searchParams.set('status', currentFilters.status);
        if (currentFilters.search) url.searchParams.set('search', currentFilters.search);

        console.log("🌐 Revenue Request URL:", url.toString());

        const res = await fetch(url.toString());
        if (!res.ok) throw new Error("Failed to fetch billing records");
        const data = await res.json();
        
        renderTable(data);
    } catch (error) {
        console.error("Billing fetch error:", error);
    }
}

/**
 * 4. TABLE RENDERING & SELECTIVE EXPORT
 */
function renderTable(records) {
    if (!billingContainerEL) return;
    
    totalBillingEl.textContent = `${records.length} Revenue`;

    if ($.fn.DataTable.isDataTable('.table.border')) {
        $('.table.border').DataTable().clear().destroy();
    }

    billingContainerEL.innerHTML = records.map(bill => renderRow(bill)).join("");

    // Initialize DataTable
    billingDataTable = $('.table.border').DataTable({
        columnDefs: [{ targets: [0, 7], orderable: false }],
        dom: 'tprB', // Keep 'B' in dom for button functionality
        pageLength: 15,
        buttons: [
            { 
                extend: 'excelHtml5', 
                title: 'Revenue_Report',
                exportOptions: { 
                    columns: [1, 2, 3, 4, 5, 6],
                    rows: function (idx, data, node) {
                        const checked = $('.billing__container .form-check-input:checked');
                        // If nothing is checked, export all. Otherwise, export only checked.
                        return checked.length === 0 ? true : $(node).find('.form-check-input').prop('checked');
                    }
                } 
            },
            { 
                extend: 'pdfHtml5', 
                title: 'Revenue_Report',
                orientation: 'landscape',
                exportOptions: { 
                    columns: [1, 2, 3, 4, 5, 6],
                    rows: function (idx, data, node) {
                        const checked = $('.billing__container .form-check-input:checked');
                        return checked.length === 0 ? true : $(node).find('.form-check-input').prop('checked');
                    }
                }
            }
        ]
    });

    // Re-bind Export Buttons
    $('.export-excel').off('click').on('click', () => billingDataTable.button(0).trigger());
    $('.export-pdf').off('click').on('click', () => billingDataTable.button(1).trigger());
}

function renderRow(bill) {
    const status = bill.appointment?.invoice?.status || 'unpaid';
    
    return `
    <tr>
        <td><div class="form-check form-check-md"><input class="form-check-input" type="checkbox"></div></td>
        <td><span class="text-primary fw-bold">${bill.display_id}</span></td>
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
                    <p class="text-muted mb-0 small">Bill No: <strong class="text-primary">${bill.display_id}</strong></p>
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

async function updateBillingStats() {
    try {
        console.log("Fetching billing stats...");
        const response = await fetch('/api/v1/billing/stats/billing-summary');
        const data = await response.json();
        
        console.log("Stats Data Received:", data); // Check F12 console for this!

        // 1. Total Billed
        const totalBilled = parseFloat(data.current_month_total) || 0;
        const billedEl = document.getElementById('billing_total_display');
        if (billedEl) billedEl.innerText = `GH₵ ${totalBilled.toLocaleString(undefined, {minimumFractionDigits: 2})}`;

        // 2. Total Collected
        const totalCollected = parseFloat(data.total_collected) || 0;
        const collectedEl = document.getElementById('stat_total_collected');
        if (collectedEl) collectedEl.innerText = `GH₵ ${totalCollected.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
        
        // 3. Total Pending
        const totalPending = parseFloat(data.total_outstanding) || 0;
        const pendingEl = document.getElementById('stat_total_pending');
        if (pendingEl) pendingEl.innerText = `GH₵ ${totalPending.toLocaleString(undefined, {minimumFractionDigits: 2})}`;

        // 4. Progress Bars
        if (totalBilled > 0) {
            const collectRate = (totalCollected / totalBilled) * 100;
            const pendingRate = (totalPending / totalBilled) * 100;
            
            if (document.getElementById('collection_progress_bar')) {
                document.getElementById('collection_progress_bar').style.width = collectRate + '%';
            }
            if (document.getElementById('pending_progress_bar')) {
                document.getElementById('pending_progress_bar').style.width = pendingRate + '%';
            }
        }

        // 5. Percentage Trend
        const pctText = document.getElementById('billing_pct_text');
        if (pctText) {
            pctText.innerText = `${data.percentage_change}%`;
            const pctContainer = document.getElementById('billing_pct_color');
            pctContainer.className = data.is_improvement ? 'text-success fs-12 d-flex align-items-center me-1' : 'text-danger fs-12 d-flex align-items-center me-1';
        }

    } catch (error) {
        console.error("Error updating billing stats:", error);
    }
}

// Call on load
updateBillingStats();