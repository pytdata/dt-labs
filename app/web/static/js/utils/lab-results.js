const laboratoryURL = "/api/v1/lab/active-appointments/";

// DOM ELEMENTS
const labTestsContainerEl = document.querySelector(".labtest__container");
const totalLabTestsEl = document.querySelector("#total__test__count");



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



(async function init() {
  const res = await getRemoteData(laboratoryURL);
  render(res);
})();

function render(labList) {
  if (!labList) return;
  totalLabTestsEl.textContent = labList.length;
  const renderedHTML = labList.map((lab) => renderData(lab)).join("");
  labTestsContainerEl.innerHTML = renderedHTML;
  const tableEl = document.querySelector(".datatable");
  if (tableEl && window.simpleDatatables) {
      new simpleDatatables.DataTable(tableEl);
  }
}

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

window.viewFinalReport = async function(itemId) {
    try {
        const res = await fetch(`/api/v1/lab/item/${itemId}`);
        if (!res.ok) throw new Error("Could not fetch report details.");
        const data = await res.json();
        
        const modalEl = document.getElementById('viewReportModal');
        if (!modalEl) return console.error("viewReportModal missing from HTML");

        const safeSet = (selector, value) => {
            const el = document.querySelector(selector);
            if (el) el.innerText = value || "--";
        };

        safeSet("#view_test_name", data.test?.name);
        const patient = data.order?.appointment?.patient || data.order?.patient;
        if (patient) safeSet("#header_patient_name", `${patient.first_name} ${patient.surname}`);

        safeSet("#header_test_type", data.test?.test_category?.category_name);
        safeSet("#header_date", formatDate(data.order?.created_at));
        safeSet("#display_order_id", `#ORD-${data.id}`);

        const isRad = data.test?.test_category?.category_name === "Radiology";
        const labDisplay = document.getElementById('lab_result_display');
        const radDisplay = document.getElementById('rad_result_display');

        if (isRad) {
            if(labDisplay) labDisplay.style.display = 'none';
            if(radDisplay) radDisplay.style.display = 'block';
            safeSet("#view_rad_findings", data.radiology_result?.result_value);
            safeSet("#view_rad_impression", data.radiology_result?.comments);
        } else {
            if(labDisplay) labDisplay.style.display = 'block';
            if(radDisplay) radDisplay.style.display = 'none';
            const resultsJson = data.lab_result?.results; 
            if (resultsJson && Object.keys(resultsJson).length > 0) {
                let tableHtml = `<div class="table-responsive"><table class="table table-hover align-middle mb-0"><thead class="table-light text-uppercase small"><tr><th class="ps-4 py-3">Parameter</th><th class="text-center">Result</th><th class="text-center">Unit</th><th class="text-center">Flag</th><th class="pe-4 text-center">Reference Range</th></tr></thead><tbody>`;
                for (const [parameter, details] of Object.entries(resultsJson)) {
                    const isAbnormal = details.flag !== 'N' && details.flag !== '-';
                    const flagBadgeClass = isAbnormal ? 'bg-danger text-white' : 'bg-success-soft text-success';
                    tableHtml += `<tr class="${isAbnormal ? 'bg-danger-light' : ''}"><td class="ps-4 py-3 fw-bold text-dark">${parameter}</td><td class="text-center h6 mb-0 fw-bold">${details.value}</td><td class="text-center text-muted">${details.unit || '-'}</td><td class="text-center"><span class="badge ${flagBadgeClass} px-3 py-2">${details.flag || 'N'}</span></td><td class="pe-4 text-center text-muted small">${details.reference_range || '-'}</td></tr>`;
                }
                tableHtml += `</tbody></table></div>`;
                if(labDisplay) labDisplay.innerHTML = tableHtml;
            } else {
                if(labDisplay) labDisplay.innerHTML = `<div class="p-5 text-center text-muted">No lab data found.</div>`;
            }
        }
        safeSet("#view_remarks", data.lab_result?.comments || data.radiology_result?.comments);
        new bootstrap.Modal(modalEl).show();
    } catch (error) {
        console.error("View Report Error:", error);
    }
}; 

window.printFromModal = function() {
    const orderId = document.querySelector("#display_order_id").innerText.replace('#ORD-', '');
    window.open(`/api/v1/lab/report/print/${orderId}`, '_blank');
};

window.printResult = function(itemId) {
    window.open(`/api/v1/lab/report/print/${itemId}`, '_blank');
};

const cleanText = (val) => val && val !== "null" ? val : "--";

// --- UTILITIES ---
async function getRemoteData(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch data.");
    return await res.json();
  } catch (error) { console.error(error); }
}

function formatDate(dateStr) {
  if (!dateStr) return "N/A";
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}