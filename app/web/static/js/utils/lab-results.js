const laboratoryURL = "/api/v1/lab/active-appointments/";
let currentActiveReportId = null;

// DOM ELEMENTS
const labTestsContainerEl = document.querySelector(".labtest__container");
const totalLabTestsEl = document.querySelector("#total__test__count");
let labDataTable = null;

/**
 * 1. INITIALIZATION & DEPENDENCY CHECK
 */
(function init() {
    // Wait for jQuery, moment, and daterangepicker to be ready
    const checkDeps = setInterval(() => {
        if (window.jQuery && window.moment && jQuery.fn.daterangepicker && jQuery.fn.DataTable) {
            clearInterval(checkDeps);
            setupDateFilter();
            fetchAndRender(); // Initial load
        }
    }, 100);
})();



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



/**
 * 2. DATE FILTER SETUP
 */
function setupDateFilter() {
    const $picker = $('#reportrange');
    if (!$picker.length) return;

    const start = moment().subtract(29, 'days');
    const end = moment();

    $picker.daterangepicker({
        startDate: start,
        endDate: end,
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

    $('.reportrange-picker-field').html(start.format('MMMM D, YYYY') + ' - ' + end.format('MMMM D, YYYY'));
}

/**
 * 3. FETCH AND RENDER LOGIC
 */
async function fetchAndRender(startDate = '', endDate = '') {
    try {
        let url = laboratoryURL;
        if (startDate && endDate) {
            url += `?start_date=${startDate}&end_date=${endDate}`;
        }
        
        const res = await getRemoteData(url);
        if (!res) return;

        // Update Counter
        if (totalLabTestsEl) totalLabTestsEl.textContent = res.length;

        // Destroy existing table if it exists
        if ($.fn.DataTable.isDataTable('.datatable')) {
            $('.datatable').DataTable().destroy();
        }

        // Render Rows
        const renderedHTML = res.map((lab) => renderData(lab)).join("");
        labTestsContainerEl.innerHTML = renderedHTML;

        // Re-initialize DataTable with Export Buttons
        initDataTable();

    } catch (error) {
        console.error("Fetch/Render Error:", error);
    }
}

function initDataTable() {
    labDataTable = $('.datatable').DataTable({
        "bFilter": true,
        "sDom": 'fBtlpi', 
        "ordering": true,
        "columnDefs": [
            { "targets": 'no-sort', "orderable": false }
        ],
        "language": {
            search: ' ',
            searchPlaceholder: "Search...",
            info: "_START_ - _END_ of _TOTAL_ items",
            paginate: {
                next: ' <i class=" ti ti-chevron-right"></i>',
                previous: '<i class=" ti ti-chevron-left"></i> '
            }
        },
        "buttons": [
            {
                extend: 'excelHtml5',
                className: 'd-none', // Hide default buttons
                exportOptions: { columns: ':not(:first-child):not(:last-child)' }
            },
            {
                extend: 'pdfHtml5',
                className: 'd-none',
                exportOptions: { columns: ':not(:first-child):not(:last-child)' }
            }
        ]
    });

    // Link Custom Export Dropdown to DataTable Buttons
    $('.export-excel').on('click', () => labDataTable.button('.buttons-excel').trigger());
    $('.export-pdf').on('click', () => labDataTable.button('.buttons-pdf').trigger());
}

/**
 * 4. ROW TEMPLATE
 */
function renderData(item) {
    const statusColors = { "COMPLETED": "badge-soft-success text-success border-success", "APPROVED": "badge-soft-info text-info border-info" };
    const statusClass = statusColors[item.status] || "badge-soft-success";
    const patient = item.order.appointment.patient;
    
    return `  
    <tr class="align-middle">
        <td><div class="form-check form-check-md"><input class="form-check-input" type="checkbox"></div></td>
        <td class="fw-bold text-dark">${item.display_id}</td>
        <td>
            <div class="d-flex flex-column">
                <span class="text-dark fw-medium">${patient.full_name}</span>
                <small class="text-muted">${patient.patient_no}</small>
            </div>
        </td>
        <td>${patient.sex || 'N/A'}</td>
        <td>${formatDate(item.order.appointment.appointment_at)}</td>
        <td>Dr. ${item.order.appointment.doctor?.full_name || 'System'}</td>
        <td>${item.test.name}</td>
        <td><span class="badge badge-md ${statusClass}">FINALIZED</span></td>
        <td class="text-end">
            <div class="d-flex align-items-center justify-content-end gap-2">
                <button class="btn btn-sm btn-light" onclick="viewFinalReport(${item.id})"><i class="ti ti-eye me-1"></i> View</button>
                <button class="btn btn-sm btn-outline-secondary" onclick="printResult(${item.id})"><i class="ti ti-printer"></i></button>
            </div>
        </td>
    </tr>`;
}

/**
 * 5. UTILITIES & MODAL LOGIC
 */
async function getRemoteData(url) {
    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error("Failed to fetch data.");
        return await res.json(); // Don't console.log(res.json()) here, it breaks the response
    } catch (error) { 
        console.error(error); 
        return null;
    }
}

function formatDate(dateStr) {
    if (!dateStr) return "N/A";
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

// Age calculator, Print, and viewFinalReport logic remains the same below
// window.viewFinalReport = async function(itemId) {
//     try {
//         const [reportRes, companyRes] = await Promise.all([
//             fetch(`/api/v1/lab/report/${itemId}`),
//             fetch(`/api/v1/company`)
//         ]);

//         if (!reportRes.ok) throw new Error("Could not fetch report details.");
        
//         const data = await reportRes.json();
//         const company = companyRes.ok ? await companyRes.json() : null;
        
//         const safeSet = (selector, value) => {
//             const el = document.querySelector(selector);
//             if (el) el.innerText = value || "--";
//         };

//         // 1. Set Company Info
//         if (company) {
//             const logoEl = document.querySelector("#report_company_logo");
//             if (logoEl) logoEl.src = company.logo || "/static/img/logo-small.png";
//             safeSet("#report_company_name", company.name);
//             const contactInfo = `${company.address || ''} ${company.phone ? '| Tel: ' + company.phone : ''}`;
//             safeSet("#report_company_contact", contactInfo);
//             safeSet("#report_signature_brand", company.name);
//         }

//         // 2. Set Patient & Header Info (Using your specific JSON keys)
//         const patient = data.patient;
//         safeSet("#header_test_type", data.test_name);
//         safeSet("#header_reported_on", formatDate(data.finalized_at));
        
//         // Handle Patient Name (Response has first_name and surname)
//         const fullName = patient.full_name || `${patient.first_name} ${patient.surname}`;
//         safeSet("#header_patient_name", fullName);
        
//         // Handle Age and Sex
//         const age = patient.age || "--";
//         safeSet("#header_patient_age_sex", `${age}Y / ${patient.sex || 'N/A'}`);
//         safeSet("#header_blood_group", patient.blood_group || "N/A");

//         // 3. Logic for Radiology vs Lab Results
//         // In your new response, you have 'findings' directly. 
//         // We can check if 'findings' is populated or based on a flag.
//         const labDisplay = document.getElementById('lab_result_display');
//         const radDisplay = document.getElementById('rad_result_display');

//         // Logic check: If findings exists and isn't the default "No findings recorded", show Rad
//         if (data.findings && data.findings !== "No findings recorded.") {
//             labDisplay.style.display = 'none';
//             radDisplay.style.display = 'block';
//             safeSet("#view_rad_findings", data.findings);
//             safeSet("#view_rad_impression", data.conclusion);
//         } else {
//             // Lab Result Logic: Access data.lab_result if it exists
//             labDisplay.style.display = 'block';
//             radDisplay.style.display = 'none';
            
//             if (data.results && Object.keys(data.results).length > 0) {
//                 let tableHtml = `<div class="table-responsive"><table class="table table-bordered">
//                     <thead><tr><th>Investigation</th><th>Result</th><th>Ref</th><th>Unit</th></tr></thead><tbody>`;
//                 for (const [parameter, details] of Object.entries(data.results)) {
//                     tableHtml += `<tr>
//                         <td>${parameter}</td>
//                         <td>${details.value}</td>
//                         <td>${details.reference_range || '-'}</td>
//                         <td>${details.unit || '-'}</td>
//                     </tr>`;
//                 }
//                 tableHtml += `</tbody></table></div>`;
//                 labDisplay.innerHTML = tableHtml;
//             } else {
//                 labDisplay.innerHTML = `<div class="p-3 text-center">No lab parameters found.</div>`;
//             }
//         }

//         // Show Modal
//         bootstrap.Modal.getOrCreateInstance(document.getElementById('viewReportModal')).show();
//     } catch (error) {
//         console.error(error);
//         showToast("Error loading report", "error");
//     }
// };


window.viewFinalReport = async function(itemId) {

    currentActiveReportId = itemId;

    try {
        const [reportRes, companyRes] = await Promise.all([
            fetch(`/api/v1/lab/report/${itemId}`),
            fetch(`/api/v1/company`)
        ]);

        if (!reportRes.ok) throw new Error("Could not fetch report details.");
        
        const data = await reportRes.json();
        const company = companyRes.ok ? await companyRes.json() : null;
        
        const safeSet = (selector, value) => {
            const el = document.querySelector(selector);
            if (el) el.innerText = value || "--";
        };

        // 1. Company Header
        if (company) {
            const logoEl = document.querySelector("#report_company_logo");
            if (logoEl) logoEl.src = company.logo || "/static/img/logo-small.png";
            safeSet("#report_company_name", company.name);
            const contact = `${company.address || ''} ${company.phone ? '| Tel: ' + company.phone : ''}`;
            safeSet("#report_company_contact", contact);
            safeSet("#report_signature_brand", company.name);
        }

        // 2. Patient & Meta Info
        const patient = data.patient || {};
        safeSet("#header_test_type", data.test_name);
        safeSet("#header_reported_on", formatDate(data.finalized_at));
        safeSet("#header_patient_name", patient.full_name);
        safeSet("#header_patient_age_sex", `${patient.age || '--'}Y / ${patient.sex || 'N/A'}`);
        safeSet("#header_blood_group", patient.blood_group);

        // 3. Result Display Logic
        const labDisplay = document.getElementById('lab_result_display');
        const radDisplay = document.getElementById('rad_result_display');

        if (data.category === "Radiology") {
            labDisplay.style.display = 'none';
            radDisplay.style.display = 'block';
            safeSet("#view_rad_findings", data.findings);
            safeSet("#view_rad_impression", data.conclusion);
        } else {
            labDisplay.style.display = 'block';
            radDisplay.style.display = 'none';
            
            if (data.results && Object.keys(data.results).length > 0) {
                let html = `
                <div class="table-responsive">
                    <table class="table table-sm table-bordered">
                        <thead class="bg-light">
                            <tr>
                                <th>Investigation</th>
                                <th>Result</th>
                                <th>Reference Range</th>
                                <th>Unit</th>
                            </tr>
                        </thead>
                        <tbody>`;
                
                for (const [param, details] of Object.entries(data.results)) {
                    html += `
                    <tr>
                        <td class="fw-medium">${param}</td>
                        <td class="text-dark fw-bold">${details.value}</td>
                        <td class="text-muted small">${details.reference_range || '-'}</td>
                        <td class="small">${details.unit || '-'}</td>
                    </tr>`;
                }
                html += `</tbody></table></div>`;
                labDisplay.innerHTML = html;
            } else {
                labDisplay.innerHTML = `<div class="alert alert-light text-center">No lab parameters found.</div>`;
            }
        }

        // 4. Open Modal
        const modalEl = document.getElementById('viewReportModal');
        modalEl.setAttribute('data-report-id', itemId);

        bootstrap.Modal.getOrCreateInstance(modalEl).show();

    } catch (error) {
        console.error("Modal Error:", error);
        if (typeof showToast === "function") showToast("Error loading report", "error");
    }
};


function calculateAge(dob) {
    const diff_ms = Date.now() - new Date(dob).getTime();
    return Math.abs(new Date(diff_ms).getUTCFullYear() - 1970) + "Y";
}

window.printResult = function(itemId) {
    window.open(`/api/v1/lab/report/print/${itemId}`, '_blank');
};


window.printFromModal = function() {
    if (currentActiveReportId) {
        window.open(`/api/v1/lab/report/print/${currentActiveReportId}`, '_blank');
    } else {
        // Fallback in case the global ID wasn't set correctly
        const modalEl = document.getElementById('viewReportModal');
        const backupId = modalEl.getAttribute('data-report-id');
        
        if (backupId) {
            window.open(`/api/v1/lab/report/print/${backupId}`, '_blank');
        } else {
            if (typeof showToast === "function") {
                showToast("Could not identify the report ID for printing.", "error");
            } else {
                alert("Error: Report ID not found.");
            }
        }
    }
};