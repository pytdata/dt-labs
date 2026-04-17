/**
 * TRANSACTION MANAGEMENT MODULE
 */
let transactionURL = "/api/v1/payments/";
let statsURL = "/api/v1/payments/stats"; // New stats endpoint
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
            setupSearchFilter();
            
            // Initial load
            fetchAndRender(currentFilters.start, currentFilters.end);
            fetchStats(); // Load the dashboard summary cards
        }
    }, 100);
})();

/**
 * 1. DASHBOARD STATS FETCHING
 */
async function fetchStats() {
    try {
        const res = await fetch(statsURL);
        const stats = await res.json();
        
        const currency = "GH₵";
        // Mapping backend keys to UI classes
        const updateText = (cls, val) => {
            const el = document.querySelector(cls);
            if (el) el.innerText = `${currency}${parseFloat(val).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
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
 * 2. DATE FILTER SETUP
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
 * 3. PAYMENT TYPE & SEARCH FILTERS
 */
function setupTypeFilters() {
    $('.payment__type').on('change', function() {
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

// function renderData(transaction) {
//     // Handling the nested patient object and avatar property from your model
//     const patient = transaction.invoice?.patient;
//     const patientName = patient?.full_name || 'Walk-in';
//     const patientAvatar = patient?.avatar || '/static/img/defaults/default-user-icon.jpeg';
    
//     // Status Logic
//     const status = (transaction.invoice?.status || "unpaid").toLowerCase();
//     const statusClass = status === "paid" 
//         ? "badge-soft-success text-success border-success" 
//         : "badge-soft-warning text-warning border-warning";

//     return `
//     <tr>
//         <td><div class="form-check form-check-md"><input class="form-check-input" type="checkbox"></div></td>
//         <td class="fw-bold">${transaction.invoice?.invoice_no || 'N/A'}</td>
//         <td>
//             <div class="d-flex align-items-center">
//                 <img src="${patientAvatar}" class="avatar avatar-xs me-2 rounded">
//                 <h6 class="fs-14 mb-0 fw-medium">${patientName}</h6>
//             </div>
//         </td>
//         <td>${formatDate(transaction.received_at)}</td>
//         <td><span class="text-uppercase small fw-bold">${transaction.method}</span></td>
//         <td class="fw-bold text-dark">GH₵${parseFloat(transaction.amount).toFixed(2)}</td>
//         <td><span class="badge badge-md ${statusClass}">${status}</span></td>
//         <td class="text-end">
//             <div class="dropdown">
//                 <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown"><i class="ti ti-dots-vertical"></i></a>
//                 <ul class="dropdown-menu p-2">
//                     <li><a href="/billing/invoices/${transaction.invoice_id}" class="dropdown-item"><i class="ti ti-file-text me-1"></i>View Invoice</a></li>
//                 </ul>
//             </div>
//         </td>
//     </tr>`;
// }


function renderData(transaction) {
    const patient = transaction.invoice?.patient;
    const patientName = patient?.full_name || 'Walk-in';
    const patientAvatar = patient?.avatar || '/static/img/defaults/default-user-icon.jpeg';
    
    const status = (transaction.invoice?.status || "unpaid").toLowerCase();
    const statusClass = status === "paid" 
        ? "badge-soft-success text-success border-success" 
        : "badge-soft-warning text-warning border-warning";

    // MATCHING THE 9 COLUMNS IN HTML
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
                    <li><a href="/billing/invoices/${transaction.invoice_id}" class="dropdown-item"><i class="ti ti-file-text me-1"></i>View Invoice</a></li>
                </ul>
            </div>
        </td>
    </tr>`;
}

function formatDate(dateStr) {
    if (!dateStr) return "N/A";
    return moment(dateStr).format('DD MMM, YYYY');
}


(function initTransactionChart() {
    let transactionChart = null;
    const chartContainer = document.querySelector("#chart-7");
    const yearPicker = document.querySelector(".yearpicker");

    if (!chartContainer) return;

    // 1. Chart Configuration
    const options = {
        series: [{ name: 'Revenue', data: [] }],
        chart: {
            type: 'area',
            height: 300,
            toolbar: { show: false },
            sparkline: { enabled: false }
        },
        colors: ['#003366'], // Brand Navy
        stroke: { curve: 'smooth', width: 2 },
        fill: {
            type: 'gradient',
            gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.1 }
        },
        xaxis: {
            categories: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            axisBorder: { show: false },
            axisTicks: { show: false }
        },
        yaxis: { labels: { show: true } },
        dataLabels: { enabled: false },
        grid: { borderColor: '#f1f1f1' }
    };

    // 2. Data Fetcher
    async function updateChart() {
        const year = yearPicker ? yearPicker.value : 2026;
        try {
            const response = await fetch(`/api/v1/payments/stats/monthly?year=${year}`);
            const data = await response.json();

            if (!transactionChart) {
                // First time render
                transactionChart = new ApexCharts(chartContainer, options);
                transactionChart.render();
            }
            
            // Update only the data
            transactionChart.updateSeries([{
                name: 'Revenue',
                data: data
            }]);
        } catch (error) {
            console.error("Chart Error:", error);
        }
    }

    // 3. Event Listeners
    if (yearPicker) {
        yearPicker.addEventListener('change', updateChart);
    }

    // Initial Load
    updateChart();
})();