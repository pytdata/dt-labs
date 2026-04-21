/**
 * RADIOLOGY QUEUE MANAGEMENT - INTEGRATED WITH DATATABLES & INLINE CONFIRMATION
 */

/**
 * RADIOLOGY QUEUE MANAGEMENT - FIXED & INTEGRATED
 */

// SAFE GLOBAL DECLARATIONS
if (typeof window.radiologyDataTable === 'undefined') { var radiologyDataTable = null; }
if (typeof window.radiologyQueueURL === 'undefined') { var radiologyQueueURL = "/api/v1/lab/queue/radiology"; }

// 2. TOAST UTILITY
window.showToast = window.showToast || function(message, type = 'success') {
    const toastEl = document.getElementById('appCustomToast');
    const toastText = document.getElementById('appCustomToastText');
    if (!toastEl) return;
    toastEl.classList.remove('bg-success', 'bg-danger');
    toastEl.classList.add(type === 'success' ? 'bg-success' : 'bg-danger');
    toastText.innerText = message;
    bootstrap.Toast.getOrCreateInstance(toastEl).show();
};

// 3. INITIALIZATION
(function initRadiologyModule() {
    const checkDeps = setInterval(() => {
        if (window.jQuery && window.moment && jQuery.fn.DataTable && jQuery.fn.daterangepicker) {
            clearInterval(checkDeps);
            setupFilters();
            setupSearch(); // Added call
            window.fetchAndRender(); 
        }
    }, 200);
})();

function setupSearch() {
    $('body').on('input', '.search__radiology', function() {
        const query = $(this).val().trim();
        const drp = $('#reportrange').data('daterangepicker');
        const start = drp ? drp.startDate.format('YYYY-MM-DD') : null;
        const end = drp ? drp.endDate.format('YYYY-MM-DD') : null;

        clearTimeout(this.delay);
        this.delay = setTimeout(() => {
            window.fetchAndRender(start, end, query);
        }, 500);
    });
}

function setupFilters() {
    const $picker = $('#reportrange');
    if (!$picker.length) return;
    const start = moment().subtract(29, 'days');
    const end = moment();

    $picker.daterangepicker({
        startDate: start, endDate: end, opens: 'left',
        ranges: {
            'Today': [moment(), moment()],
            'Last 30 Days': [moment().subtract(29, 'days'), moment()],
            'This Month': [moment().startOf('month'), moment().endOf('month')]
        }
    }, function(start, end) {
        $('.reportrange-picker-field').html(start.format('MMMM D, YYYY') + ' - ' + end.format('MMMM D, YYYY'));
        window.fetchAndRender(start.format('YYYY-MM-DD'), end.format('YYYY-MM-DD'), $('.search__radiology').val());
    });
    $('.reportrange-picker-field').html(start.format('MMMM D, YYYY') + ' - ' + end.format('MMMM D, YYYY'));
}

// DATA FETCHING

window.fetchAndRender = async function(startDate, endDate, search) {
    const containerEl = document.querySelector(".lab__container");
    if (!containerEl) return;

    containerEl.innerHTML = `<tr><td colspan="9" class="text-center py-5"><div class="spinner-border spinner-border-sm text-primary"></div></td></tr>`;

    try {
        const url = new URL(window.radiologyQueueURL, window.location.origin);
        if (startDate) url.searchParams.set('start_date', startDate);
        if (endDate) url.searchParams.set('end_date', endDate);
        if (search) url.searchParams.set('search', search);

        const response = await fetch(url.toString());
        const data = await response.json();
        renderRadiologyTable(data);
    } catch (error) {
        console.error("Fetch error:", error);
        containerEl.innerHTML = `<tr><td colspan="9" class="text-center text-danger">Failed to load queue.</td></tr>`;
    }
};


// 6. TABLE RENDERING
window.fetchAndRender = async function(startDate, endDate, search) {
    const containerEl = document.querySelector(".lab__container");
    if (!containerEl) return;
    containerEl.innerHTML = `<tr><td colspan="9" class="text-center py-5"><div class="spinner-border spinner-border-sm text-primary"></div></td></tr>`;

    try {
        const url = new URL(window.radiologyQueueURL, window.location.origin);
        if (startDate) url.searchParams.set('start_date', startDate);
        if (endDate) url.searchParams.set('end_date', endDate);
        if (search) url.searchParams.set('search', search);

        const response = await fetch(url.toString());
        const data = await response.json();
        renderRadiologyTable(data);
    } catch (error) {
        containerEl.innerHTML = `<tr><td colspan="9" class="text-center text-danger">Failed to load queue.</td></tr>`;
    }
};

function renderRadiologyTable(items) {
    const containerEl = document.querySelector('.lab__container');
    const tableSelector = '#radiologyMainTable';
    document.querySelector(".lab__results__total").textContent = items.length;
    
    if ($.fn.DataTable.isDataTable(tableSelector)) {
        $(tableSelector).DataTable().clear().destroy();
    }

    containerEl.innerHTML = items.map(item => {
    // 1. Correctly point to item.order.patient for the robust data
    const patient = item.order?.patient || {}; 
    const doctor = item.order?.appointment?.doctor || {};
    
    const testName = item.test.name.replace(/'/g, "\\'");
    
    // 2. Use patient.sex directly from the order object
    const gender = patient.sex || 'N/A'; 
    
    const displayDate = moment(item.order?.appointment?.appointment_at || item.entered_at).format('DD MMM YYYY');

        const stage = item.stage.toLowerCase();
        
        let badge = 'badge-soft-warning', statusText = 'PENDING SCAN';
        let action = `<button class="btn btn-sm btn-primary me-2" onclick="openReportModal(${item.id}, '${testName}')">Findings</button>`;

        if (stage === 'review' || item.status === 'AWAITING_APPROVAL') {
            badge = 'badge-soft-info'; statusText = 'AWAITING APPROVAL';
            action = `<button class="btn btn-sm btn-info text-white me-2" onclick="reviewReport(${item.id}, '${testName}')">Review</button>`;
        } else if (stage === 'complete' || item.status === 'COMPLETED') {
            badge = 'badge-soft-success'; statusText = 'FINALIZED';
            action = `<button class="btn btn-sm btn-outline-success me-2" onclick="viewFinalReport(${item.id})">View</button>`;
        }

        return `
    <tr>
        <td><div class="form-check"><input class="form-check-input" type="checkbox" value="${item.id}"></div></td>
        <td><span class="text-muted fw-bold">${item.display_id}</span></td>
        <td><h6 class="fs-14 mb-0 fw-medium">${patient.full_name || 'N/A'}</h6></td>
        <td>${gender}</td> <td>${displayDate}</td>
        <td>Dr. ${doctor.full_name || 'Referral'}</td>
        <td><span class="text-dark fw-medium">${item.test.name}</span></td>
        <td><span class="badge ${badge} border">${statusText}</span></td>
        <td class="text-end">
            <div class="d-flex align-items-center justify-content-end">
                ${action}
            </div>
        </td>
    </tr>`;
}).join('');

    window.radiologyDataTable = $(tableSelector).DataTable({
        dom: 't<"row mt-3 align-items-center"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7 d-flex justify-content-end"p>>',
        pageLength: 20,
        columnDefs: [{ "targets": [0, 8], "orderable": false }],
        buttons: [
    { 
        extend: 'excelHtml5', 
        title: 'Radiology_Report_' + moment().format('YYYYMMDD'), 
        exportOptions: { 
            columns: [1,2,3,4,5,6,7],
            rows: function (idx, data, node) {
                // Find all checked checkboxes in the table
                const anyChecked = $('.lab__container .form-check-input:checked').length > 0;
                // If something is checked, only return true for rows where the checkbox is checked
                return anyChecked ? $(node).find('.form-check-input').prop('checked') : true;
            }
        } 
    },
    { 
        extend: 'pdfHtml5', 
        title: 'Radiology_Report_' + moment().format('YYYYMMDD'), 
        orientation: 'landscape', 
        exportOptions: { 
            columns: [1,2,3,4,5,6,7],
            rows: function (idx, data, node) {
                const anyChecked = $('.lab__container .form-check-input:checked').length > 0;
                return anyChecked ? $(node).find('.form-check-input').prop('checked') : true;
            }
        } 
    }
]
    });

    $('.export-excel').off('click').on('click', () => window.radiologyDataTable.button(0).trigger());
    $('.export-pdf').off('click').on('click', () => window.radiologyDataTable.button(1).trigger());
}

// MODAL HANDLERS (Now outside the render function)
window.openReportModal = function(itemId, testName) {
    $('#rad_order_item_id').val(itemId);
    $('#rad_test_name_display').text(testName);
    $('#rad_findings, #rad_conclusion').val('');
    $('#btn_save_result').show();
    $('#btn_finalize_init, #inline_confirm_wrapper').hide();
    bootstrap.Modal.getOrCreateInstance(document.getElementById('radiologyResultModal')).show();
};

window.reviewReport = async function(itemId, testName) {
    try {
        const response = await fetch(`/api/v1/radiology/result-by-item/${itemId}`);
        const resultData = await response.json();
        $('#rad_order_item_id').val(itemId);
        $('#rad_test_name_display').text(testName);
        $('#rad_findings').val(resultData.result_value || '');
        $('#rad_conclusion').val(resultData.comments || '');
        $('#btn_save_result').hide();
        $('#btn_finalize_init').show();
        $('#inline_confirm_wrapper').hide();
        bootstrap.Modal.getOrCreateInstance(document.getElementById('radiologyResultModal')).show();
    } catch (err) { showToast("Could not load findings.", "error"); }
};

/**
 * Save Draft Results
 */
window.saveRadiologyResult = async function() {
    const findings = document.getElementById('rad_findings').value;
    const conclusion = document.getElementById('rad_conclusion').value;
    const itemId = document.getElementById('rad_order_item_id').value;

    if (!findings.trim()) return showToast("Please enter clinical findings.", "error");

    const submitBtn = document.getElementById('btn_save_result');
    submitBtn.disabled = true;

    try {
        const response = await fetch('/api/v1/radiology/submit-result', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order_item_id: parseInt(itemId), findings, conclusion })
        });

        if (response.ok) {
            bootstrap.Modal.getInstance(document.getElementById('radiologyResultModal')).hide();
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

/**
 * Inline Confirmation Toggles
 */
window.showInlineConfirm = function() {
    document.getElementById('btn_finalize_init').style.display = 'none';
    document.getElementById('inline_confirm_wrapper').style.display = 'inline-flex';
};

window.cancelInlineConfirm = function() {
    document.getElementById('inline_confirm_wrapper').style.display = 'none';
    document.getElementById('btn_finalize_init').style.display = 'inline-block';
};

/**
 * Final Sign-off and API Call
 */
window.executeFinalizeNow = async function() {
    const itemId = document.getElementById('rad_order_item_id').value;
    const wrapper = document.getElementById('inline_confirm_wrapper');
    
    if (!itemId) return showToast("Order ID missing", "error");

    wrapper.style.pointerEvents = 'none';
    wrapper.style.opacity = '0.7';

    try {
        const response = await fetch(`/api/v1/radiology/finalize-report/${itemId}`, { 
            method: 'POST' 
        });

        if (response.ok) {
            bootstrap.Modal.getInstance(document.getElementById('radiologyResultModal')).hide();
            showToast("Report finalized and signed successfully.");
            fetchAndRender();
        } else {
            const error = await response.json();
            showToast(error.detail || "Finalization failed.", "error");
            cancelInlineConfirm();
        }
    } catch (error) {
        showToast("Network error occurred.", "error");
        cancelInlineConfirm();
    } finally {
        wrapper.style.pointerEvents = 'auto';
        wrapper.style.opacity = '1';
    }
};

/**
 * View Final Report PDF-style
 */
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