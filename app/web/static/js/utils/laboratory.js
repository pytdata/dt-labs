/**
 * 0. GLOBAL STATE & CONFIG
 */
const fillQueueURL = "/api/v1/lab/phlebotomy-queue/"; 
let labDataTable = null;

// Default filter: Last 30 days
let currentFilters = {
    start: moment().subtract(30, 'days').format('YYYY-MM-DD'),
    end: moment().format('YYYY-MM-DD'),
    search: ''
};

/**
 * 1. INITIALIZATION
 */
$(document).ready(function() {
    setupDatePicker();
    setupSearchFilter();
    init(); // Initial fetch

    // Master Checkbox Logic
    $(document).on('change', '#selectAllTests', function() {
        const isChecked = $(this).is(':checked');
        $('.labtest__container .row-checkbox').prop('checked', isChecked);
    });
});

/**
 * 2. FILTERS (Date & Search)
 */
function setupDatePicker() {
    const $picker = $('#reportrange');
    if (!$picker.length) return;

    $picker.daterangepicker({
        startDate: moment(currentFilters.start),
        endDate: moment(currentFilters.end),
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
        
        const displayText = (label === 'Custom Range') 
            ? start.format('DD MMM YY') + ' - ' + end.format('DD MMM YY')
            : label;

        $('.reportrange-picker-field').html(displayText);
        init();
    });

    $('.reportrange-picker-field').html(
        moment(currentFilters.start).format('DD MMM YY') + ' - ' + moment(currentFilters.end).format('DD MMM YY')
    );
}


function setupSearchFilter() {
    // Listen for both 'input' (typing) and 'search' (the 'x' button in some browsers)
    $('body').on('input search', '.search__laboratory', function() {
        const query = $(this).val().trim();
        
        clearTimeout(this.delay);
        this.delay = setTimeout(() => {
            // Update the global filter state
            currentFilters.search = query;
            
            // If the query is empty, we are essentially "resetting" the view
            if (query === "") {
                console.log("Search cleared, reloading full list...");
            }
            
            init(); 
        }, 400); // Slightly faster response time for clearing
    });
}

/**
 * 3. CORE FETCH & RENDER
 */
async function init() {
    try {
        const url = new URL(fillQueueURL, window.location.origin);
        url.searchParams.set('start_date', currentFilters.start);
        url.searchParams.set('end_date', currentFilters.end);
        
        // Only attach search if it has a value
        if (currentFilters.search) {
            url.searchParams.set('search', currentFilters.search);
        }

        const data = await getRemoteData(url.toString());
        const container = document.querySelector(".labtest__container");

        // IMPORTANT: Clear the container first
        container.innerHTML = "";

        if (data && data.length > 0) {
            renderQueue(data);
            initDataTable(); // This re-binds the "Smart" table features to the new data
        } else {
            // No results found
            container.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-muted">No results matching "${currentFilters.search}"</td></tr>`;
            
            // If the table was initialized, kill it so it doesn't show old data
            if ($.fn.DataTable.isDataTable('.datatable')) {
                $('.datatable').DataTable().clear().destroy();
            }
        }
        
        // Update the count badge
        const countEl = document.querySelector("#total__test__count");
        if (countEl) countEl.textContent = data ? data.length : 0;

    } catch (err) {
        console.error("Fetch error:", err);
    }
}


function renderQueue(list) {
    const container = document.querySelector(".labtest__container");
    container.innerHTML = list.map(item => {
        const patient = item.order.patient;
        const fullName = patient.full_name;
        const testName = item.test.name;
        const appointmentDate = item.order.appointment ? item.order.appointment.appointment_at : null;

        // Logic for Provisional vs Awaiting
        const isProvisional = item.lab_result && item.lab_result.status === 'pending';
        const statusBadge = isProvisional 
            ? `<span class="badge bg-soft-info text-info border-info"><i class="ti ti-clock-edit me-1"></i>Provisional</span>`
            : `<span class="badge bg-soft-warning text-warning border-warning">Awaiting Results</span>`;

        return `
        <tr class="align-middle">
            <td><div class="form-check"><input class="form-check-input row-checkbox" type="checkbox"></div></td>
            <td class="fw-bold text-primary">${item.display_id}</td>
            <td>
                <div class="d-flex flex-column">
                    <span class="fw-bold text-dark">${fullName}</span>
                    <small class="text-muted">${patient.patient_no}</small>
                </div>
            </td>
            <td>${testName}</td>
            <td><span class="badge bg-outline-info text-info border-info">${item.test.test_category.category_name}</span></td>
            <td>${formatDate(appointmentDate)}</td>
            <td>${statusBadge}</td>
            <td class="text-end">
                <button class="btn btn-sm ${isProvisional ? 'btn-outline-primary' : 'btn-primary'} shadow-sm" 
                    onclick="openFillModal(${item.id}, '${testName.replace(/'/g, "\\'")}', '${fullName.replace(/'/g, "\\'")}', '${item.display_id}')">
                    <i class="ti ti-edit me-1"></i> ${isProvisional ? 'Edit Draft' : 'Enter Results'}
                </button>
            </td>
        </tr>`;
    }).join('');
}


/**
 * 4. DATATABLE & EXPORT
 */
function initDataTable() {
    if ($.fn.DataTable.isDataTable('.datatable')) {
        $('.datatable').DataTable().clear().destroy();
    }

    labDataTable = $('.datatable').DataTable({
        "bFilter": true,
        "sDom": 'tpr', 
        "ordering": true,
        "columnDefs": [{ "targets": [0, 7], "orderable": false }],
        "buttons": [
            {
                extend: 'excelHtml5',
                title: 'Lab_Phlebotomy_Queue_' + moment().format('YYYYMMDD'),
                exportOptions: { 
                    columns: [1, 2, 3, 4, 5, 6],
                    rows: function (idx, data, node) {
                        const anyChecked = $('.row-checkbox:checked').length > 0;
                        return anyChecked ? $(node).find('.row-checkbox').prop('checked') : true;
                    }
                }
            },
            {
                extend: 'pdfHtml5',
                title: 'Lab_Phlebotomy_Queue_' + moment().format('YYYYMMDD'),
                orientation: 'landscape',
                exportOptions: { 
                    columns: [1, 2, 3, 4, 5, 6],
                    rows: function (idx, data, node) {
                        const anyChecked = $('.row-checkbox:checked').length > 0;
                        return anyChecked ? $(node).find('.row-checkbox').prop('checked') : true;
                    }
                }
            }
        ]
    });

    // Re-bind custom dropdown triggers
    $('.export-excel').off('click').on('click', function() {
        showToast("Preparing Excel download...");
        labDataTable.button(0).trigger();
    });
    $('.export-pdf').off('click').on('click', function() {
        showToast("Preparing PDF download...");
        labDataTable.button(1).trigger();
    });
}

/**
 * 5. MODAL LOGIC
 */
window.openFillModal = async function(itemId, testName, patientName, displayId) {
    document.getElementById('display_test_name').innerText = testName;
    document.getElementById('display_patient_name').innerText = patientName;
    document.getElementById('display_order_id').innerText = `${displayId}`;
    document.getElementById('fill_order_item_id').value = itemId;
    
    // Reset the finalize toggle every time the modal opens
    const finalizeCheck = document.getElementById('finalize_check');
    if (finalizeCheck) finalizeCheck.checked = false;

    const container = document.getElementById('dynamic_template_container');
    container.innerHTML = `<div class="text-center py-5"><div class="spinner-border text-primary"></div></div>`;
    
    new bootstrap.Modal(document.getElementById('fillResultModal')).show();

    try {
        // We fetch the template AND check for existing lab results
        const [templateRes, resultRes] = await Promise.all([
            fetch(`/api/v1/tests-templates/by-item/${itemId}`),
            fetch(`/api/v1/lab/results/by-item/${itemId}`) // Ensure this route exists on backend
        ]);

        const templates = await templateRes.json();
        const existingData = resultRes.ok ? await resultRes.json() : null;
        const savedResults = existingData ? existingData.results : {};

        if (!templates.length) {
            container.innerHTML = `<div class="alert alert-warning">No Template Found.</div>`;
            return;
        }

        container.innerHTML = templates.map(t => {
            // Check if we have a saved value for this specific parameter
            const savedValue = savedResults[t.test_name] ? savedResults[t.test_name].value : '';

            return `
            <div class="row mx-0 align-items-center test-row py-3 border-bottom bg-white">
                <div class="col-md-3"><strong>${t.test_name}</strong></div>
                <div class="col-md-4">
                    <div class="input-group">
                        <input type="number" step="any" class="form-control result-input" 
                               value="${savedValue}"
                               data-name="${t.test_name}" data-min="${t.min_reference_range ?? ''}" 
                               data-max="${t.max_reference_range ?? ''}" data-unit="${t.unit ?? ''}"
                               oninput="validateFlag(this)">
                        <span class="input-group-text">${t.unit ?? '-'}</span>
                    </div>
                </div>
                <div class="col-md-1 text-center"><span class="badge flag-badge bg-light text-dark">-</span></div>
                <div class="col-md-4 text-center bg-light rounded py-2 border">
                    <small class="d-block text-muted" style="font-size:0.7rem">REF RANGE</small>
                    <span class="fw-bold">${t.min_reference_range ?? '0'} — ${t.max_reference_range ?? 'N/A'}</span>
                </div>
            </div>`;
        }).join('');

        // Trigger validation for pre-filled data so flags (H/L) show immediately
        container.querySelectorAll('.result-input').forEach(input => {
            if (input.value !== "") validateFlag(input);
        });

    } catch (err) {
        console.error("Modal Load Error:", err);
        container.innerHTML = `<div class="alert alert-danger">Error loading template or existing results.</div>`;
    }
};

window.validateFlag = function(input) {
    const val = parseFloat(input.value);
    const min = parseFloat(input.dataset.min);
    const max = parseFloat(input.dataset.max);
    const badge = input.closest('.test-row').querySelector('.flag-badge');

    if (isNaN(val)) {
        badge.className = "badge flag-badge bg-light text-dark";
        badge.innerText = "-";
        return;
    }

    if (min !== "" && val < min) {
        badge.className = "badge flag-badge bg-danger";
        badge.innerText = "L";
    } else if (max !== "" && val > max) {
        badge.className = "badge flag-badge bg-danger text-white";
        badge.innerText = "H";
    } else {
        badge.className = "badge flag-badge bg-success";
        badge.innerText = "N";
    }
};



document.getElementById('fill_results_form').addEventListener('submit', async function(e) {
    e.preventDefault();
    const submitBtn = document.getElementById('save_results_btn');
    const itemId = document.getElementById('fill_order_item_id').value;
    const isFinalized = document.getElementById('finalize_check').checked; // Capture the toggle
    
    const resultsPayload = {};
    document.querySelectorAll('.test-row').forEach(row => {
        const input = row.querySelector('.result-input');
        if (input.value !== "") {
            resultsPayload[input.dataset.name] = {
                value: input.value,
                unit: input.dataset.unit,
                flag: row.querySelector('.flag-badge').innerText,
                reference_range: `${input.dataset.min} - ${input.dataset.max}`
            };
        }
    });

    if (Object.keys(resultsPayload).length === 0) return showToast("Enter results before saving", "error");

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Saving...';

    try {
        const response = await fetch('/api/v1/lab/results/submit-phlebotomy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                order_item_id: parseInt(itemId), 
                results: resultsPayload,
                is_finalized: isFinalized 
            })
        });

        if (response.ok) {
            showToast(isFinalized ? "Results Finalized!" : "Provisional results saved successfully");
            bootstrap.Modal.getInstance(document.getElementById('fillResultModal')).hide();
            
            // Refresh the table via your init() function to show updated status
            if (typeof init === 'function') init(); 
        } else {
            throw new Error("Failed to save results");
        }
    } catch (err) {
        showToast(err.message, "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerText = "Save Results";
    }
});


/**
 * 6. UTILS
 */
function formatDate(dateStr) {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleDateString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

function showToast(message, type = 'success') {
    const toastEl = document.getElementById('appCustomToast');
    const toastText = document.getElementById('appCustomToastText');
    const toastIcon = document.getElementById('toastIcon');
    if (!toastEl) return;
    toastEl.classList.remove('bg-success', 'bg-danger');
    if (type === 'success') {
        toastEl.classList.add('bg-success');
        if (toastIcon) toastIcon.className = 'ti ti-circle-check fs-4 me-2';
    } else {
        toastEl.classList.add('bg-danger');
        if (toastIcon) toastIcon.className = 'ti ti-alert-triangle fs-4 me-2';
    }
    toastText.innerText = message;
    bootstrap.Toast.getOrCreateInstance(toastEl).show();
}

async function getRemoteData(url) {
    const res = await fetch(url);
    return res.ok ? await res.json() : null;
}

/**
 * Global bridge for legacy HTML onclick="exportData()"
 */
window.exportData = function(format) {
    if (format === 'excel') {
        $('.export-excel').trigger('click');
    } else if (format === 'pdf') {
        $('.export-pdf').trigger('click');
    }
};