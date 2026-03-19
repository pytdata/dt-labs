/**
 * RADIOLOGY QUEUE MANAGEMENT - INTEGRATED WITH DATATABLES & EXPORT
 */

// 1. SAFE GLOBAL DECLARATIONS
if (typeof window.radiologyDataTable === 'undefined') {
    var radiologyDataTable = null;
}
if (typeof window.radiologyQueueURL === 'undefined') {
    var radiologyQueueURL = "/api/v1/lab/queue/radiology";
}

// 2. TOAST NOTIFICATION UTILITY
window.showToast = window.showToast || function(message, type = 'success') {
    const toastEl = document.getElementById('appCustomToast');
    const toastText = document.getElementById('appCustomToastText');
    const toastIcon = document.getElementById('toastIcon');
    if (!toastEl) return;

    toastEl.classList.remove('bg-success', 'bg-danger');
    if (toastIcon) toastIcon.className = 'ti fs-4 me-2';
    toastText.innerText = message;

    if (type === 'success') {
        toastEl.classList.add('bg-success');
        if (toastIcon) toastIcon.classList.add('ti-circle-check');
    } else {
        toastEl.classList.add('bg-danger');
        if (toastIcon) toastIcon.classList.add('ti-alert-triangle');
    }

    const toast = bootstrap.Toast.getOrCreateInstance(toastEl);
    toast.show();
};

// 3. INITIALIZATION
(function initRadiologyModule() {
    const checkDeps = setInterval(() => {
        if (window.jQuery && window.moment && jQuery.fn.DataTable && jQuery.fn.daterangepicker) {
            clearInterval(checkDeps);
            setupFilters();
            fetchAndRender(); 
        }
    }, 200);
})();

// 4. DATE RANGE FILTER
// 4. DATE RANGE FILTER - UPDATED FOR VISIBILITY
function setupFilters() {
    const $picker = $('#reportrange');
    if (!$picker.length) return;

    const start = moment().subtract(29, 'days');
    const end = moment();

    $picker.daterangepicker({
        startDate: start,
        endDate: end,
        opens: 'left',
        drops: 'auto', // Automatically detect if it should drop up or down
        parentEl: "body", // Attaches the picker to the body so it isn't clipped by cards
        ranges: {
            'Today': [moment(), moment()],
            'Yesterday': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
            'Last 7 Days': [moment().subtract(6, 'days'), moment()],
            'Last 30 Days': [moment().subtract(29, 'days'), moment()],
            'This Month': [moment().startOf('month'), moment().endOf('month')],
            'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
        }
    }, function(start, end) {
        $('.reportrange-picker-field').html(start.format('MMMM D, YYYY') + ' - ' + end.format('MMMM D, YYYY'));
        fetchAndRender(start.format('YYYY-MM-DD'), end.format('YYYY-MM-DD'));
    });

    // Initialize the label
    $('.reportrange-picker-field').html(start.format('MMMM D, YYYY') + ' - ' + end.format('MMMM D, YYYY'));
}

// 5. DATA FETCHING
window.fetchAndRender = async function(startDate, endDate) {
    const containerEl = document.querySelector(".lab__container");
    if (!containerEl) return;

    containerEl.innerHTML = `<tr><td colspan="9" class="text-center py-5"><div class="spinner-border spinner-border-sm text-primary"></div></td></tr>`;

    try {
        let url = window.radiologyQueueURL;
        if (startDate && endDate) url += `?start_date=${startDate}&end_date=${endDate}`;

        const response = await fetch(url);
        const data = await response.json();
        renderRadiologyTable(data);
    } catch (error) {
        console.error("Fetch error:", error);
        containerEl.innerHTML = `<tr><td colspan="9" class="text-center text-danger">Failed to load queue.</td></tr>`;
    }
};

// 6. TABLE RENDERING
function renderRadiologyTable(items) {
    const containerEl = document.querySelector('.lab__container');
    const tableSelector = '#radiologyMainTable'; // Targets the unique ID
    const $table = $(tableSelector);

    // Destroy existing instance to prevent double-initialization
    if ($.fn.DataTable.isDataTable(tableSelector)) {
        $table.DataTable().clear().destroy();
    }

    if (window.pdfMake && window.pdfMake.vfs) {
        pdfMake.vfs = window.pdfMake.vfs;
    }

    containerEl.innerHTML = items.map(item => {
        const patient = item.order?.appointment?.patient || {};
        const doctor = item.order?.appointment?.doctor || {};
        const testName = item.test.name.replace(/'/g, "\\'");
        const displayDate = moment(item.order?.appointment?.appointment_at || item.entered_at).format('DD MMM YYYY');

        const stage = item.stage.toLowerCase();
        let badge = 'badge-soft-warning';
        let statusText = 'PENDING SCAN';
        let action = `<button class="btn btn-sm btn-primary me-2" onclick="openReportModal(${item.id}, '${testName}')">Findings</button>`;

        if (stage === 'review') {
            badge = 'badge-soft-info';
            statusText = 'AWAITING APPROVAL';
            action = `<button class="btn btn-sm btn-info text-white me-2" onclick="reviewReport(${item.id}, '${testName}')">Review</button>`;
        } else if (stage === 'complete') {
            badge = 'badge-soft-success';
            statusText = 'FINALIZED';
            action = `<button class="btn btn-sm btn-outline-success me-2" onclick="viewFinalReport(${item.id})">View</button>`;
        }

        return `
        <tr>
            <td><div class="form-check"><input class="form-check-input" type="checkbox" value="${item.id}"></div></td>
            <td><span class="text-muted fw-bold">#RAD-${item.id}</span></td>
            <td><h6 class="fs-14 mb-0 fw-medium">${patient.full_name || 'N/A'}</h6></td>
            <td>${patient.gender || 'N/A'}</td>
            <td>${displayDate}</td>
            <td>Dr. ${doctor.full_name || 'Referral'}</td>
            <td><span class="text-dark fw-medium">${item.test.name}</span></td>
            <td><span class="badge ${badge} border">${statusText}</span></td>
            <td class="text-end">
                <div class="d-flex align-items-center justify-content-end">
                    ${action}
                    <div class="dropdown">
                        <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown"><i class="ti ti-dots-vertical"></i></a>
                        <ul class="dropdown-menu dropdown-menu-end p-2 shadow-sm">
                             <li><a href="javascript:void(0);" class="dropdown-item" onclick="viewFinalReport(${item.id})">View History</a></li>
                        </ul>
                    </div>
                </div>
            </td>
        </tr>`;
    }).join('');

    /**
     * INITIALIZE DATATABLE
     * dom: 'tpr' removes the 'B' (Buttons) element entirely from the DOM layout.
     * We define the buttons in the configuration but they won't be rendered.
     */
    window.radiologyDataTable = $table.DataTable({
        dom: 'tpr', 
        pageLength: 20,
        responsive: true,
        buttons: [
            { 
                extend: 'csvHtml5', 
                title: 'Radiology_Export_' + moment().format('YYYY-MM-DD'),
                exportOptions: { columns: ':not(:first-child):not(:last-child)' } 
            },
            { 
                extend: 'excelHtml5', 
                title: 'Radiology_Export_' + moment().format('YYYY-MM-DD'),
                exportOptions: { columns: ':not(:first-child):not(:last-child)' } 
            },
            { 
                extend: 'pdfHtml5', 
                title: 'Radiology Report', 
                orientation: 'landscape', 
                exportOptions: { columns: ':not(:first-child):not(:last-child)' },
                customize: (doc) => { 
                    if (doc.defaultStyle) doc.defaultStyle.font = 'Roboto'; 
                } 
            },
            { 
                extend: 'print', 
                title: 'Radiology Queue', 
                exportOptions: { columns: ':not(:first-child):not(:last-child)' } 
            }
        ]
    });

    /**
     * PROXY CLICK EVENTS
     * We manually trigger the button actions by index.
     */
    $(document).off('click', '.export-csv').on('click', '.export-csv', function(e) {
        e.preventDefault();
        window.radiologyDataTable.button('.buttons-csv').trigger();
    });
    $(document).off('click', '.export-excel').on('click', '.export-excel', function(e) {
        e.preventDefault();
        window.radiologyDataTable.button('.buttons-excel').trigger();
    });
    $(document).off('click', '.export-pdf').on('click', '.export-pdf', function(e) {
        e.preventDefault();
        window.radiologyDataTable.button('.buttons-pdf').trigger();
    });
    $(document).off('click', '.export-print').on('click', '.export-print', function(e) {
        e.preventDefault();
        window.radiologyDataTable.button('.buttons-print').trigger();
    });
}

// 7. MODAL & API HANDLERS
window.saveRadiologyResult = async function() {
    const findings = document.getElementById('rad_findings').value;
    const conclusion = document.getElementById('rad_conclusion').value;
    const itemId = document.getElementById('rad_order_item_id').value;

    if (!findings.trim()) {
        showToast("Please enter clinical findings.", "error");
        return;
    }

    const submitBtn = document.getElementById('btn_save_result');
    submitBtn.disabled = true;

    try {
        const response = await fetch('/api/v1/radiology/submit-result', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order_item_id: parseInt(itemId), findings, conclusion })
        });

        if (response.ok) {
            const modal = bootstrap.Modal.getInstance(document.getElementById('radiologyResultModal'));
            if (modal) modal.hide();
            showToast("Findings submitted for approval.");
            fetchAndRender(); 
        } else {
            showToast("Failed to save results.", "error");
        }
    } catch (error) {
        showToast("Network error occurred.", "error");
    } finally {
        submitBtn.disabled = false;
    }
};

window.openReportModal = function(itemId, testName) {
    document.getElementById('rad_order_item_id').value = itemId;
    document.getElementById('rad_test_name_display').innerText = testName;
    document.getElementById('rad_findings').value = '';
    document.getElementById('rad_conclusion').value = '';
    document.getElementById('btn_save_result').style.display = 'block';
    document.getElementById('btn_finalize_result').style.display = 'none';
    bootstrap.Modal.getOrCreateInstance(document.getElementById('radiologyResultModal')).show();
};

window.reviewReport = async function(itemId, testName) {
    const modalEl = document.getElementById('radiologyResultModal');
    try {
        const response = await fetch(`/api/v1/radiology/result-by-item/${itemId}`);
        const resultData = await response.json();
        document.getElementById('rad_order_item_id').value = itemId;
        document.getElementById('rad_test_name_display').innerText = testName;
        document.getElementById('rad_findings').value = resultData.result_value || '';
        document.getElementById('rad_conclusion').value = resultData.comments || '';
        document.getElementById('btn_save_result').style.display = 'none';
        document.getElementById('btn_finalize_result').style.display = 'block';
        bootstrap.Modal.getOrCreateInstance(modalEl).show();
    } catch (err) {
        showToast("Could not load report findings.", "error");
    }
};

window.finalizeReport = async function() {
    const itemId = document.getElementById('rad_order_item_id').value;
    if (!itemId || !confirm("Finalize and sign off this report?")) return;

    try {
        const response = await fetch(`/api/v1/radiology/finalize-report/${itemId}`, { method: 'POST' });
        if (response.ok) {
            const modal = bootstrap.Modal.getInstance(document.getElementById('radiologyResultModal'));
            if (modal) modal.hide();
            showToast("Report finalized and signed.");
            fetchAndRender();
        } else {
            showToast("Could not finalize report.", "error");
        }
    } catch (error) {
        showToast("Network error.", "error");
    }
};

window.viewFinalReport = async function(itemId) {
    try {
        const response = await fetch(`/api/v1/lab/report/${itemId}`);
        const data = await response.json();
        const patient = data.patient;
        const doctor = data.doctor || { full_name: "Self-Referral" };
        const printWindow = window.open('', '_blank', 'width=900,height=800');
        
        const htmlContent = `
            <html><head><title>Report - ${patient.first_name}</title>
            <style>body{font-family:sans-serif;padding:40px;} .header{text-align:center;border-bottom:2px solid #333;margin-bottom:20px;} .box{display:flex;justify-content:space-between;background:#f4f4f4;padding:15px;margin-bottom:20px;}</style>
            </head><body>
            <div class="header"><h2>DATA GLOW DIAGNOSTICS</h2><p>Radiology Department</p></div>
            <div class="box"><div><strong>Patient:</strong> ${patient.first_name} ${patient.surname}<br>ID: ${patient.patient_no}</div>
            <div><strong>Date:</strong> ${moment(data.finalized_at).format('DD/MM/YYYY')}<br>Referrer: Dr. ${doctor.full_name}</div></div>
            <h3>EXAMINATION: ${data.test_name}</h3>
            <h4>FINDINGS:</h4><p>${data.findings}</p>
            <h4>IMPRESSION:</h4><p><strong>${data.conclusion || 'Normal Study'}</strong></p>
            <p style="margin-top:40px; font-style:italic; border-top:1px solid #eee;">Digitally verified on ${moment(data.finalized_at).format('LLL')}</p>
            </body></html>`;

        printWindow.document.write(htmlContent);
        printWindow.document.close();
    } catch (error) {
        showToast("Failed to generate report.", "error");
    }
};