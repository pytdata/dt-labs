/**
 * TRANSACTION MANAGEMENT MODULE
 */
let transactionURL = "/api/v1/payments/";
let statsURL = "/api/v1/payments/stats";
let paymentTableEL = document.querySelector(".payment__table");
let totalTransactionEl = document.querySelector(".total__amount");
let paymentDataTable = null;

// 1. GLOBAL FILTER STATE
let currentFilters = {
    start: moment().subtract(29, 'days').format('YYYY-MM-DD'),
    end: moment().format('YYYY-MM-DD'),
    search: '',
    status: [] // Track paid/unpaid filters
};

/**
 * INITIALIZATION
 */
(function init() {
    const checkDeps = setInterval(() => {
        if (window.jQuery && window.moment && jQuery.fn.DataTable && jQuery.fn.daterangepicker) {
            clearInterval(checkDeps);
            
            setupDateFilter();
            setupTypeFilters();
            setupSearchFilter();
            
            // Initial load
            fetchAndRender(currentFilters.start, currentFilters.end);
            fetchStats();
        }
    }, 100);
})();

/**
 * 2. DASHBOARD STATS FETCHING
 */
async function fetchStats() {
    try {
        const res = await fetch(statsURL);
        const stats = await res.json();
        
        const currency = "GH₵";
        const updateText = (cls, val) => {
            const el = document.querySelector(cls);
            if (el) el.innerText = `${currency}${parseFloat(val || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
        };

        updateText(".total-transactions-val", stats.total_all_time);
        updateText(".last-month-val", stats.last_month);
        updateText(".this-month-val", stats.this_month);
        updateText(".last-week-val", stats.last_week);
        updateText(".this-week-val", stats.this_week);
        updateText(".today-val", stats.today);

    } catch (error) {
        console.error("Stats fetch error:", error);
    }
}

/**
 * 3. FILTER SETUP (DATE, METHOD, STATUS, SEARCH)
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

    $('.reportrange-picker-field').html(moment(currentFilters.start).format('MMMM D, YYYY') + ' - ' + moment(currentFilters.end).format('MMMM D, YYYY'));
}

function setupTypeFilters() {
    // Payment Method Checkboxes
    $('.payment__type').on('change', function() {
        fetchAndRender(currentFilters.start, currentFilters.end);
    });

    // Invoice Status Checkboxes (Paid/Unpaid)
    $('#status-filter-container input[type="checkbox"]').on('change', function() {
        currentFilters.status = [];
        $('#status-filter-container input:checked').each(function() {
            currentFilters.status.push($(this).val());
        });
        fetchAndRender(currentFilters.start, currentFilters.end);
    });
}

function setupSearchFilter() {
    const searchInput = document.querySelector(".search__transaction__patient") || 
                        document.querySelector(".search-input input");
    if (!searchInput) return;

    let searchTimeout = null;
    searchInput.addEventListener("input", (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            currentFilters.search = e.target.value;
            fetchAndRender(currentFilters.start, currentFilters.end);
        }, 500);
    });
}

/**
 * 4. DATA FETCHING
 */
async function fetchAndRender(startDate = '', endDate = '') {
    try {
        let url = new URL(transactionURL, window.location.origin);
        
        if (startDate) url.searchParams.set('start_date', startDate);
        if (endDate) url.searchParams.set('end_date', endDate);
        if (currentFilters.search) url.searchParams.set('search', currentFilters.search);

        // Methods
        $('.payment__type:checked').each(function() {
            url.searchParams.append('method', $(this).data('payment-type'));
        });

        // Statuses
        currentFilters.status.forEach(status => {
            url.searchParams.append('status', status);
        });

        const res = await fetch(url.toString());
        const data = await res.json();
        render(data);
    } catch (error) {
        console.error("Fetch error:", error);
    }
}

/**
 * 5. TABLE RENDERING
 */
function render(transactionList) {
    if (!transactionList || !paymentTableEL) return;
    
    if (totalTransactionEl) totalTransactionEl.textContent = transactionList.length;

    if ($.fn.DataTable.isDataTable('.datatable')) {
        $('.datatable').DataTable().clear().destroy();
    }

    paymentTableEL.innerHTML = transactionList.map(item => renderData(item)).join("");

    paymentDataTable = $('.datatable').DataTable({
        columnDefs: [{ targets: 'no-sort', orderable: false }],
        dom: 'tpr',
        pageLength: 20,
        language: {
            paginate: {
                next: 'Next <i class="ti ti-chevron-right ms-1"></i>',
                previous: '<i class="ti ti-chevron-left me-1"></i> Previous'
            }
        }
    });
}

function renderData(transaction) {
    const patient = transaction.invoice?.patient;
    const patientName = patient?.full_name || 'Walk-in';
    const patientAvatar = patient?.profile_image || '/static/img/defaults/default-user-icon.jpeg';
    
    const status = (transaction.invoice?.status || "unpaid").toLowerCase();
    const statusClass = status === "paid" 
        ? "badge-soft-success text-success border-success" 
        : "badge-soft-warning text-warning border-warning";

    return `
    <tr>
        <td><div class="form-check form-check-md"><input class="form-check-input" type="checkbox"></div></td>
        <td class="fw-bold">${transaction.invoice?.invoice_no || 'N/A'}</td>
        <td>
            <div class="d-flex align-items-center">
                <img src="${patientAvatar}" class="avatar avatar-xs me-2 rounded">
                <h6 class="fs-14 mb-0 fw-medium">${patientName}</h6>
            </div>
        </td>
        <td>${formatDate(transaction.received_at)}</td>
        <td><p class="text-truncate mb-0" style="max-width: 150px;">${transaction.description || 'Lab Services'}</p></td>
        <td class="fw-bold text-dark">GH₵${parseFloat(transaction.amount).toFixed(2)}</td>
        <td><span class="text-uppercase small fw-bold">${transaction.method}</span></td>
        <td><span class="badge badge-md ${statusClass}">${status}</span></td>
        <td class="text-end">
            <div class="dropdown">
                <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown"><i class="ti ti-dots-vertical"></i></a>
                <ul class="dropdown-menu p-2">
                    <li><a href="javascript:void(0);" onclick="viewInvoiceDetail(${transaction.invoice_id})" class="dropdown-item">
                        <i class="ti ti-file-text me-1"></i>View Invoice</a>
                    </li>
                </ul>
            </div>
        </td>
    </tr>`;
}

function formatDate(dateStr) {
    if (!dateStr) return "N/A";
    return moment(dateStr).format('DD MMM, YYYY');
}

/**
 * 6. MODAL & PRINTING
 */
window.viewInvoiceDetail = async function(invoiceId) {
    if (!invoiceId) {
        showToast("Invoice ID not found", "error");
        return;
    }

    try {
        const [invRes, compRes] = await Promise.all([
            fetch(`/api/v1/payments/invoices/${invoiceId}`),
            fetch(`/api/v1/company/`)
        ]);

        if (!invRes.ok) throw new Error("Invoice fetch failed");
        
        const invoice = await invRes.json();
        const company = compRes.ok ? await compRes.json() : null;

        // Safety setters
        const setText = (id, val) => { if(document.getElementById(id)) document.getElementById(id).innerText = val; };
        const setHTML = (id, val) => { if(document.getElementById(id)) document.getElementById(id).innerHTML = val; };

        // 1. Company Branding
        if (company) {
            setText('modal_from_name', company.name);
            setHTML('modal_from_details', `${company.address}<br>${company.phone}<br>${company.email}`);
            const logoImg = document.querySelector('#invoiceDetailModal img[alt="Logo"]');
            if (logoImg) logoImg.src = company.logo;
            const sig = document.querySelector('#invoiceDetailModal .signature-font');
            if (sig) sig.innerText = company.name;
        }

        // 2. Invoice Meta
        setText('modal_inv_number', invoice.invoice_no);
        const statusBadge = document.getElementById('modal_inv_status_badge');
        if (statusBadge) {
            const status = invoice.status.toLowerCase();
            statusBadge.className = `badge ${status === 'paid' ? 'bg-success' : 'bg-warning'} px-3`;
            statusBadge.innerText = status.toUpperCase();
        }

        // 3. Bill To
        setText('modal_to_name', invoice.patient?.full_name || 'N/A');
        setHTML('modal_to_details', `Patient ID: ${invoice.patient?.display_id || invoice.patient?.patient_no}<br>Tel: ${invoice.patient?.phone || 'N/A'}`);

        // 4. Items
        const itemsTable = document.getElementById('modal_invoice_items');
        if (itemsTable) {
            itemsTable.innerHTML = (invoice.items || []).map((item, index) => `
                <tr>
                    <td class="text-center">${index + 1}</td>
                    <td><h6 class="mb-0 fs-14 fw-bold text-dark">${item.test?.name || item.description}</h6></td>
                    <td class="text-center">${item.qty}</td>
                    <td class="text-end">${parseFloat(item.unit_price).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                    <td class="text-end fw-bold">${parseFloat(item.line_total).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                </tr>
            `).join('');
        }

        // 5. Totals
        const total = parseFloat(invoice.total_amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2});
        setText('modal_subtotal', `GH₵ ${total}`);
        setText('modal_total', `GH₵ ${total}`);

        // 6. QR Code
        const qrImg = document.querySelector('#modal_inv_qr img');
        if (qrImg) qrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=70x70&data=${invoice.invoice_no}`;

        bootstrap.Modal.getOrCreateInstance(document.getElementById('invoiceDetailModal')).show();

    } catch (err) {
        console.error("Modal Error:", err);
        showToast("Error loading invoice", "error");
    }
};

window.printInvoice = function() {
    const printArea = document.getElementById('invoice_print_area').innerHTML;
    const printWindow = window.open('', '_blank', 'width=900,height=800');
    printWindow.document.write(`
        <html>
            <head>
                <title>Print Invoice</title>
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
                <style>
                    body { padding: 40px; background: #fff !important; }
                    .table-dark { background-color: #212529 !important; color: white !important; -webkit-print-color-adjust: exact; }
                </style>
            </head>
            <body>${printArea}</body>
        </html>
    `);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => {
        printWindow.print();
        printWindow.close();
    }, 500);
};

/**
 * 7. UTILITIES (TOASTS & CHARTS)
 */
function showToast(message, type = 'success') {
    const toastEl = document.getElementById('appCustomToast');
    const toastText = document.getElementById('appCustomToastText');
    if (!toastEl) return;
    toastEl.classList.remove('bg-success', 'bg-danger');
    toastEl.classList.add(type === 'success' ? 'bg-success' : 'bg-danger');
    toastText.innerText = message;
    bootstrap.Toast.getOrCreateInstance(toastEl).show();
}

(function initTransactionChart() {
    let transactionChart = null;
    const chartContainer = document.querySelector("#chart-7");
    const yearPicker = document.querySelector(".yearpicker");
    if (!chartContainer) return;

    const options = {
        series: [{ name: 'Revenue', data: [] }],
        chart: { type: 'area', height: 300, toolbar: { show: false } },
        colors: ['#003366'],
        stroke: { curve: 'smooth', width: 2 },
        fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.1 } },
        xaxis: { categories: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"] }
    };

    async function updateChart() {
        const year = yearPicker ? yearPicker.value : new Date().getFullYear();
        try {
            const res = await fetch(`/api/v1/payments/stats/monthly?year=${year}`);
            const data = await res.json();
            if (!transactionChart) {
                transactionChart = new ApexCharts(chartContainer, options);
                transactionChart.render();
            }
            transactionChart.updateSeries([{ name: 'Revenue', data: data }]);
        } catch (err) { console.error("Chart Error:", err); }
    }

    if (yearPicker) yearPicker.addEventListener('change', updateChart);
    updateChart();
})();