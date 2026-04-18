/**
 * INVOICE MANAGEMENT SYSTEM - FULL MODULE
 */

let invoiceContainerEL = document.querySelector(".invoice__container");
let totalInvoiceEl = document.querySelector(".total__invoices");
let invoiceURL = "/api/v1/payments/invoices";
let invoiceDataTable = null;

// 1. GLOBAL FILTER STATE
let currentFilters = {
    start: moment().subtract(29, 'days').format('YYYY-MM-DD'),
    end: moment().format('YYYY-MM-DD'),
    status: ''
};

// 2. INITIALIZATION (Waits for all dependencies)
(function init() {
    const checkDeps = setInterval(() => {
        const hasDeps = window.jQuery && window.moment && jQuery.fn.DataTable && jQuery.fn.daterangepicker;
        if (hasDeps) {
            clearInterval(checkDeps);
            console.log("🚀 Invoice Module Initialized");
            
            setupDateFilter();
            setupStatusFilter();
            fetchAndRender(currentFilters.start, currentFilters.end);
        }
    }, 100);
})();

// 3. FILTER SETTINGS
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

    $('.reportrange-picker-field').html(moment(currentFilters.start).format('MMMM D, YYYY') + ' - ' + moment(currentFilters.end).format('MMMM D, YYYY'));
}

function setupStatusFilter() {
    // Selects status from the dropdown
    $('.dropdown-menu a.dropdown-item').on('click', function(e) {
        e.preventDefault();
        const selected = $(this).text().trim();
        
        // Update UI Text
        $(this).closest('.dropdown').find('.dropdown-toggle').text(selected);
        
        // Set Filter Logic
        currentFilters.status = (selected === "Select Status" || selected === "All") ? "" : selected;
        fetchAndRender(currentFilters.start, currentFilters.end);
    });
}

// 4. CORE DATA LOGIC
async function fetchAndRender(startDate = '', endDate = '') {
    try {
        let url = new URL(invoiceURL, window.location.origin);
        
        if (startDate && endDate) {
            url.searchParams.set('start_date', startDate);
            url.searchParams.set('end_date', endDate);
        }
        if (currentFilters.status) {
            url.searchParams.set('status', currentFilters.status);
        }

        const res = await fetch(url.toString());
        if (!res.ok) throw new Error("Failed to fetch invoices");
        const data = await res.json();
        
        renderTable(data);
    } catch (error) {
        console.error("Invoice fetch error:", error);
    }
}

function renderTable(invoiceList) {
    if (!invoiceList || !invoiceContainerEL) return;
    
    totalInvoiceEl.textContent = `${invoiceList.length} Invoices`;

    // Reset Table
    if ($.fn.DataTable.isDataTable('.table.border')) {
        $('.table.border').DataTable().clear().destroy();
    }

    // Map HTML
    invoiceContainerEL.innerHTML = invoiceList.map(item => renderRow(item)).join("");

    // Initialize DataTable with Export configuration
    invoiceDataTable = $('.table.border').DataTable({
        columnDefs: [{ targets: [0, 8], orderable: false }],
        dom: 'tpr',
        pageLength: 15,
        buttons: [
            { 
                extend: 'excelHtml5', 
                title: 'Invoice_Export_' + moment().format('YYYY-MM-DD'),
                exportOptions: { columns: [1, 2, 3, 4, 5, 6, 7] } 
            },
            { 
                extend: 'pdfHtml5', 
                title: 'Invoice_Report_' + moment().format('YYYY-MM-DD'),
                orientation: 'landscape',
                exportOptions: { columns: [1, 2, 3, 4, 5, 6, 7] }
            }
        ]
    });

    // Proxy Click Events for Custom Export Buttons
    $('.export-excel').off('click').on('click', () => invoiceDataTable.button(0).trigger());
    $('.export-pdf').off('click').on('click', () => invoiceDataTable.button(1).trigger());
}


function renderRow(invoice) {
    const status = (invoice.status || "").toLowerCase();
    const statusClass = status === "paid" ? "badge-soft-success" : (status === "overdue" ? "badge-soft-danger" : "badge-soft-warning");
    
    // Parse values safely to prevent NaN
    const totalAmount = parseFloat(invoice.total_amount) || 0;
    const balance = parseFloat(invoice.balance) || 0;

    return `
    <tr>
        <td><div class="form-check form-check-md"><input class="form-check-input" type="checkbox"></div></td>
        <td><a href="javascript:void(0);" onclick="viewInvoiceDetail(${invoice.id})" class="fw-bold text-primary">${invoice.display_id}</a></td>
        <td>
            <div class="d-flex align-items-center">
                <img src="${invoice.patient?.profile_image || '/static/img/default-user.png'}" class="avatar avatar-md rounded-circle me-2">
                <div>
                    <h6 class="fw-medium mb-0 fs-14">${invoice.patient?.full_name || 'N/A'}</h6>
                    <small class="text-muted">${invoice.patient?.display_id || '--'}</small>
                </div>
            </div>
        </td>
        <td>${formatDate(invoice.created_at)}</td>
        <td class="fw-bold text-dark">${totalAmount.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
        <td class="text-danger">${balance.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
        <td>${formatDate(invoice.updated_at || invoice.created_at)}</td>
        <td>
            <span class="badge ${statusClass} d-inline-flex align-items-center">
                <i class="ti ti-point-filled me-1"></i>${invoice.status.toUpperCase()}
            </span>
        </td>
        <td class="text-end">
            <button class="btn btn-sm btn-light" onclick="viewInvoiceDetail(${invoice.id})"><i class="ti ti-eye"></i></button>
        </td>
    </tr>`;
}


// 5. UTILITIES
function formatDate(dateStr) {
    if (!dateStr) return "N/A";
    return moment(dateStr).format('DD MMM, YYYY');
}



window.viewInvoiceDetail = async function(invoiceId) {
    try {
        const [invRes, compRes] = await Promise.all([
            fetch(`/api/v1/payments/invoices/${invoiceId}`),
            fetch(`/api/v1/company/`)
        ]);

        if (!invRes.ok) throw new Error("Invoice fetch failed");
        
        const invoice = await invRes.json();
        const company = compRes.ok ? await compRes.json() : null;

        // 1. DYNAMIC COMPANY BRANDING
        if (company) {
            document.getElementById('modal_from_name').innerText = company.name;
            document.getElementById('modal_from_details').innerHTML = 
                `${company.address || ''}<br>${company.phone || ''}<br>${company.email || ''}`;
            
            // Sync Logo
            const logoImg = document.querySelector('#invoiceDetailModal img[alt="Logo"]');
            if (logoImg && company.logo) logoImg.src = company.logo;
            
            // Sync Footer Signature
            const brandText = document.querySelector('#invoiceDetailModal .signature-font');
            if (brandText) brandText.innerText = company.name;
        }

        // 2. FIXED INVOICE NUMBER (Using invoice_no)
        // This targets the #INV-0000 header in your modal
        document.getElementById('modal_inv_number').innerText = invoice.invoice_no;
        
        // 3. PATIENT DETAILS
        document.getElementById('modal_to_name').innerText = invoice.patient?.full_name || "N/A";
        document.getElementById('modal_to_details').innerHTML = 
            `ID: ${invoice.patient?.display_id || invoice.patient?.patient_no}<br>Tel: ${invoice.patient?.phone || 'N/A'}`;
        
        const statusBadge = document.getElementById('modal_inv_status_badge');
        const status = (invoice.status || 'unpaid').toLowerCase();
        statusBadge.className = status === 'paid' ? 'badge bg-success px-3' : 'badge bg-warning px-3';
        statusBadge.innerText = status.toUpperCase();

        // 4. ITEMS TABLE (Mapping keys line_total and unit_price)
        const itemsTable = document.getElementById('modal_invoice_items');
        itemsTable.innerHTML = (invoice.items || []).map((item, index) => {
            const rate = parseFloat(item.unit_price) || 0;
            const lineTotal = parseFloat(item.line_total) || 0;
            
            return `
            <tr>
                <td class="text-center">${index + 1}</td>
                <td>
                    <h6 class="mb-0 fs-14 fw-bold text-dark">${item.test?.name || item.description}</h6>
                </td>
                <td class="text-center">${item.qty || 1}</td>
                <td class="text-end">${rate.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                <td class="text-end fw-bold">${lineTotal.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
            </tr>`;
        }).join('');

        // 5. TOTALS (Using total_amount)
        const totalVal = parseFloat(invoice.total_amount) || 0;
        const formattedTotal = totalVal.toLocaleString(undefined, {minimumFractionDigits: 2});
        
        document.getElementById('modal_subtotal').innerText = formattedTotal;
        document.getElementById('modal_total').innerText = formattedTotal;

        // 6. SYNC QR CODE (Using invoice_no for verification)
        const qrImg = document.querySelector('#modal_inv_qr img');
        if (qrImg) {
            qrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=70x70&data=${invoice.invoice_no}`;
        }

        bootstrap.Modal.getOrCreateInstance(document.getElementById('invoiceDetailModal')).show();
    } catch (err) {
        console.error("Modal Error:", err);
        showToast("Could not load invoice details", "error");
    }
};


/**
 * PRINT INVOICE FROM MODAL
 */
window.printInvoice = function() {
    const printContents = document.getElementById('invoice_print_area').innerHTML;
    const originalContents = document.body.innerHTML;

    // Create a temporary print window/frame to preserve styles
    const printWindow = window.open('', '_blank', 'width=900,height=800');
    
    printWindow.document.write(`
        <html>
            <head>
                <title>Print Invoice</title>
                <link rel="stylesheet" href="/static/css/bootstrap.min.css">
                <style>
                    body { padding: 30px; background: white !important; }
                    .table-dark { background-color: #212529 !important; color: white !important; -webkit-print-color-adjust: exact; }
                    #modal_inv_status_badge { -webkit-print-color-adjust: exact; }
                    @media print {
                        .btn-close, .modal-footer { display: none !important; }
                    }
                </style>
            </head>
            <body>
                ${printContents}
                <script>
                    // Wait for styles/images to load then print
                    window.onload = function() {
                        window.print();
                        window.onafterprint = function() { window.close(); };
                    };
                </script>
            </body>
        </html>
    `);

    printWindow.document.close();
};



async function loadInvoiceStats() {
    try {
        const res = await fetch('/api/v1/payments/summary');
        const stats = await res.json();

        // 1. Update Total
        document.getElementById('stat_total_invoice').innerText = 
            `GH₵ ${stats.this_month.toLocaleString(undefined, {minimumFractionDigits: 2})}`;

        // 2. Update Progress Bar (Example: Goal of 10,000 GH₵ per month)
        const goal = 10000;
        const progress = Math.min((stats.this_month / goal) * 100, 100);
        document.getElementById('stat_progress_bar').style.width = `${progress}%`;

        // 3. Update Percentage Trend
        const pctEl = document.getElementById('stat_pct_value');
        const icon = stats.is_up ? 'ti-arrow-wave-right-up' : 'ti-arrow-wave-right-down';
        const colorClass = stats.is_up ? 'text-success' : 'text-danger';
        
        pctEl.className = `${colorClass} fs-12 d-flex align-items-center me-1`;
        pctEl.innerHTML = `<i class="ti ${icon} me-1"></i>${stats.is_up ? '+' : ''}${stats.percentage_change}%`;

    } catch (error) {
        console.error("Error loading stats:", error);
    }
}

// Call this in your init function
loadInvoiceStats();



function showToast (message, type = 'success') {
    const toastEl = document.getElementById('appCustomToast');
    const toastText = document.getElementById('appCustomToastText');
    const toastIcon = document.getElementById('toastIcon');

    if (!toastEl) return;

    // CRITICAL: Move toast to body to escape any parent 'overflow:hidden'
    const container = toastEl.closest('.toast-container');
    if (container && container.parentElement !== document.body) {
        document.body.appendChild(container);
    }

    // Reset classes
    toastEl.classList.remove('bg-success', 'bg-danger');
    if (toastIcon) toastIcon.className = 'ti fs-4 me-2';

    // Set content
    toastText.innerText = message;
    if (type === 'success') {
        toastEl.classList.add('bg-success');
        if (toastIcon) toastIcon.classList.add('ti-circle-check');
    } else {
        toastEl.classList.add('bg-danger');
        if (toastIcon) toastIcon.classList.add('ti-alert-triangle');
    }

    // Show the toast
    const toast = bootstrap.Toast.getOrCreateInstance(toastEl, { 
        delay: 4000,
        autohide: true 
    });
    toast.show();
};
