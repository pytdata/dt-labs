let transactionURL = "/api/v1/payments/";
let paymentTableEL = document.querySelector(".payment__table");
let totalTransactionEl = document.querySelector(".total__amount");
let paymentDataTable = null;

// Track current filter state globally
let currentFilters = {
    start: moment().subtract(29, 'days').format('YYYY-MM-DD'),
    end: moment().format('YYYY-MM-DD'),
    search: ''
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
            setupSearchFilter(); // Fixed the "null" error here
            
            // Initial load with default 30 days
            fetchAndRender(currentFilters.start, currentFilters.end);
        }
    }, 100);
})();

/**
 * 1. DATE FILTER SETUP
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

/**
 * 2. PAYMENT TYPE FILTERS
 */
function setupTypeFilters() {
    $('.payment__type').on('change', function() {
        // Always pass current dates when a checkbox is toggled
        fetchAndRender(currentFilters.start, currentFilters.end);
    });
}

/**
 * 3. SEARCH FILTER (Fixed "addEventListener" error)
 */
function setupSearchFilter() {
    // Check multiple possible selectors based on common naming patterns
    const searchInput = document.querySelector(".search__transaction__patient") || 
                        document.querySelector(".search-input input") ||
                        document.querySelector(".btn-searchset").closest('.search-input')?.querySelector('input');

    if (!searchInput) {
        console.warn("Search input element not found. Skipping search listener.");
        return;
    }

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
        
        if (startDate && endDate) {
            url.searchParams.set('start_date', startDate);
            url.searchParams.set('end_date', endDate);
        }

        if (currentFilters.search) {
            url.searchParams.set('search', currentFilters.search);
        }

        // Add selected payment methods (handles multi-select)
        $('.payment__type:checked').each(function() {
            url.searchParams.append('method', $(this).data('payment-type'));
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
    
    totalTransactionEl.textContent = transactionList.length;

    if ($.fn.DataTable.isDataTable('.datatable')) {
        $('.datatable').DataTable().clear().destroy();
    }

    paymentTableEL.innerHTML = transactionList.map(item => renderData(item)).join("");

    paymentDataTable = $('.datatable').DataTable({
        columnDefs: [{ targets: 'no-sort', orderable: false }],
        dom: 'tpr',
        pageLength: 20,
        buttons: [
            { extend: 'excelHtml5', title: 'Transactions_' + moment().format('YYYY-MM-DD') },
            { extend: 'pdfHtml5', title: 'Transaction Report' }
        ]
    });

    $('.export-excel').off('click').on('click', () => paymentDataTable.button(0).trigger());
    $('.export-pdf').off('click').on('click', () => paymentDataTable.button(1).trigger());
}

function renderData(transaction) {
    const statusClass = (transaction.invoice?.status || "").toLowerCase() === "paid" 
        ? "badge-soft-success text-success border-success" 
        : "badge-soft-warning text-warning border-warning";

    return `
    <tr>
        <td><div class="form-check form-check-md"><input class="form-check-input" type="checkbox"></div></td>
        <td class="fw-bold">${transaction.display_id}</td>
        <td>
            <div class="d-flex align-items-center">
                <img src="${transaction.invoice?.patient?.profile_image || '/static/img/profiles/avatar-01.jpg'}" class="avatar avatar-xs me-2 rounded">
                <h6 class="fs-14 mb-0 fw-medium">${transaction.invoice?.patient?.full_name || 'Unknown'}</h6>
            </div>
        </td>
        <td>${formatDate(transaction.received_at || transaction.transaction_date)}</td>
        <td><p class="text-truncate mb-0" style="max-width: 150px;">${transaction.description || 'N/A'}</p></td>
        <td class="fw-bold text-dark">${transaction.amount || transaction.invoice?.amount_paid || '0.00'}</td>
        <td><span class="text-uppercase small fw-bold">${transaction.method}</span></td>
        <td><span class="badge badge-md ${statusClass}">${transaction.invoice?.status || 'unpaid'}</span></td>
        <td class="text-end">
            <div class="dropdown">
                <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown"><i class="ti ti-dots-vertical"></i></a>
                <ul class="dropdown-menu p-2">
                    <li><a href="#" class="dropdown-item"><i class="ti ti-eye me-1"></i>Details</a></li>
                </ul>
            </div>
        </td>
    </tr>`;
}

function formatDate(dateStr) {
    if (!dateStr) return "N/A";
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}