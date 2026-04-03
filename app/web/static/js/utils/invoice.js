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
    
    return `
    <tr>
        <td><div class="form-check form-check-md"><input class="form-check-input" type="checkbox"></div></td>
        <td><a href="javascript:void(0);" onclick="viewInvoiceDetail(${invoice.id})" class="fw-bold text-primary">${invoice.display_id}</a></td>
        <td>
            <div class="d-flex align-items-center">
                <img src="${invoice.patient?.profile_image || '/static/img/default-user.png'}" class="avatar avatar-md rounded-circle me-2">
                <div>
                    <h6 class="fw-medium mb-0 fs-14">${invoice.patient?.full_name || 'N/A'}</h6>
                    <small class="text-muted">${invoice.patient?.patient_no || '--'}</small>
                </div>
            </div>
        </td>
        <td>${formatDate(invoice.created_at)}</td>
        <td class="fw-bold text-dark">${Number(invoice.total_amount).toLocaleString()}</td>
        <td class="text-danger">${Number(invoice.amount_due || 0).toLocaleString()}</td>
        <td>${formatDate(invoice.updated_at || invoice.created_at)}</td>
        <td>
            <span class="badge ${statusClass} d-inline-flex align-items-center">
                <i class="ti ti-point-filled me-1"></i>${invoice.status}
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
            fetch(`/api/v1/company`)
        ]);

        if (!invRes.ok) throw new Error("Invoice fetch failed");
        
        const invoice = await invRes.json();
        const company = compRes.ok ? await compRes.json() : { name: "YKG LAB & DIAGNOSTIC CENTER" };

        // Header Mapping
        document.getElementById('modal_from_name').innerText = company.name;
        document.getElementById('modal_from_details').innerHTML = `${company.address || ''}<br>${company.phone || ''}`;
        
        // Modal Patient Mapping
        document.getElementById('modal_inv_number').innerText = `#INV-${invoice.id}`;
        document.getElementById('modal_to_name').innerText = invoice.patient.full_name;
        document.getElementById('modal_to_details').innerHTML = `ID: ${invoice.patient.patient_no}<br>Tel: ${invoice.patient.phone || 'N/A'}`;
        
        const statusBadge = document.getElementById('modal_inv_status_badge');
        statusBadge.className = invoice.status.toLowerCase() === 'paid' ? 'badge bg-success px-3' : 'badge bg-danger px-3';
        statusBadge.innerText = invoice.status.toUpperCase();

        // Items Table
        const itemsTable = document.getElementById('modal_invoice_items');
        itemsTable.innerHTML = (invoice.items || []).map((item, index) => `
            <tr>
                <td class="text-center">${index + 1}</td>
                <td><h6 class="mb-0 fs-14 fw-bold text-dark">${item.test?.name || item.item_description || "Service"}</h6></td>
                <td class="text-center">${item.quantity || 1}</td>
                <td class="text-end">${Number(item.unit_price).toLocaleString()}</td>
                <td class="text-end fw-bold">${Number(item.total_price).toLocaleString()}</td>
            </tr>`).join('');

        const total = Number(invoice.total_amount).toLocaleString();
        document.getElementById('modal_subtotal').innerText = total;
        document.getElementById('modal_total').innerText = total;

        bootstrap.Modal.getOrCreateInstance(document.getElementById('invoiceDetailModal')).show();
    } catch (err) {
        console.error("Modal Error:", err);
    }
};