const laboratoryURL = "/api/v1/lab/active-appointments/";

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
        <td class="fw-bold text-dark">#ORD-${item.id}</td>
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
window.viewFinalReport = async function(itemId) {
    try {
        const [reportRes, companyRes] = await Promise.all([
            fetch(`/api/v1/lab/item/${itemId}`),
            fetch(`/api/v1/company`)
        ]);
        if (!reportRes.ok) throw new Error("Could not fetch report details.");
        const data = await reportRes.json();
        const company = companyRes.ok ? await companyRes.json() : null;
        
        const safeSet = (selector, value) => {
            const el = document.querySelector(selector);
            if (el) el.innerText = value || "--";
        };

        if (company) {
            const logoEl = document.querySelector("#report_company_logo");
            if (logoEl) logoEl.src = company.logo || "/static/img/logo-small.png";
            safeSet("#report_company_name", company.name);
            const contactInfo = `${company.address || ''} ${company.phone ? '| Tel: ' + company.phone : ''}`;
            safeSet("#report_company_contact", contactInfo);
            safeSet("#report_signature_brand", company.name);
        }

        const patient = data.order?.appointment?.patient || data.order?.patient;
        safeSet("#header_test_type", data.test?.name);
        safeSet("#header_collected_on", formatDate(data.order?.created_at)); 
        safeSet("#header_reported_on", formatDate(data.updated_at));
        safeSet("#header_patient_name", patient?.full_name || `${patient?.first_name} ${patient?.surname}`);
        const age = patient?.dob ? calculateAge(patient.dob) : (patient?.age || "--");
        safeSet("#header_patient_age_sex", `${age}Y / ${patient?.sex || 'N/A'}`);
        safeSet("#header_blood_group", patient?.blood_group || "N/A");

        const isRad = data.test?.test_category?.category_name === "Radiology";
        const labDisplay = document.getElementById('lab_result_display');
        const radDisplay = document.getElementById('rad_result_display');

        if (isRad) {
            labDisplay.style.display = 'none';
            radDisplay.style.display = 'block';
            safeSet("#view_rad_findings", data.radiology_result?.result_value);
            safeSet("#view_rad_impression", data.radiology_result?.comments);
        } else {
            labDisplay.style.display = 'block';
            radDisplay.style.display = 'none';
            const resultsJson = data.lab_result?.results; 
            if (resultsJson && Object.keys(resultsJson).length > 0) {
                let tableHtml = `<div class="table-responsive"><table class="table table-bordered"><thead><tr><th>Investigation</th><th>Result</th><th>Ref</th><th>Unit</th></tr></thead><tbody>`;
                for (const [parameter, details] of Object.entries(resultsJson)) {
                    tableHtml += `<tr><td>${parameter}</td><td>${details.value}</td><td>${details.reference_range || '-'}</td><td>${details.unit || '-'}</td></tr>`;
                }
                tableHtml += `</tbody></table></div>`;
                labDisplay.innerHTML = tableHtml;
            } else {
                labDisplay.innerHTML = `<div class="p-3 text-center">No results found.</div>`;
            }
        }
        bootstrap.Modal.getOrCreateInstance(document.getElementById('viewReportModal')).show();
    } catch (error) {
        showToast("Error loading report", "error");
    }
};

function calculateAge(dob) {
    const diff_ms = Date.now() - new Date(dob).getTime();
    return Math.abs(new Date(diff_ms).getUTCFullYear() - 1970) + "Y";
}

window.printResult = function(itemId) {
    window.open(`/api/v1/lab/report/print/${itemId}`, '_blank');
};