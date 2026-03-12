const laboratoryURL = "/api/v1/lab/active-appointments/";

// DOM ELEMENTS
const labTestsContainerEl = document.querySelector(".labtest__container");
const totalLabTestsEl = document.querySelector("#total__test__count");

(async function init() {
  const res = await getRemoteData(laboratoryURL);
  console.log(res, "data received");
  render(res);
})();

/**
 * Main Render Function
 */
function render(labList) {
  console.log(labList, "labList======================")
  console.log(totalLabTestsEl, labTestsContainerEl)
  if (!labList) return;
  totalLabTestsEl.textContent = labList.length;

  const renderedHTML = labList
    .map((lab) => renderData(lab))
    .join("");

  labTestsContainerEl.innerHTML = renderedHTML;
}

/**
 * Renders an individual Lab/Radiology item into a table row.
 */
function renderData(item) {
  // Mapping statuses to Bootstrap classes
  const statusColors = {
    "AWAITING_SAMPLE": "badge-soft-secondary text-secondary border-secondary",
    "AWAITING_RESULTS": "badge-soft-warning text-warning border-warning",
    "IN_PROGRESS": "badge-soft-primary text-primary border-primary",
    "COMPLETED": "badge-soft-success text-success border-success"
  };
  
  const statusClass = statusColors[item.status] || "badge-soft-dark";
  const statusText = item.status.replace("_", " ").toUpperCase();
  
  // LOGIC: Determine if it's Radiology based on the JSON category_name
  const categoryName = item.test.test_category?.category_name || "";
  const isRadiology = categoryName.toLowerCase().includes("radiology");

  const actionFunction = isRadiology ? 'openRadiologyResultModal' : 'openStandardResultModal';
  const actionIcon = isRadiology ? 'ti-scan' : 'ti-microscope';
  const actionLabel = isRadiology ? 'Findings' : 'Results';

  // Extract Patient Data
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
    <td>
        <div class="d-flex flex-column">
            <span class="text-dark">${item.test.name}</span>
            <small class="text-muted fs-11">${item.test.sample_type || ''}</small>
        </div>
    </td>
    <td>
        <span class="text-uppercase small fw-bold text-muted">
            <i class="ti ${isRadiology ? 'ti-photo' : 'ti-flask'} me-1"></i>
            ${categoryName}
        </span>
    </td>
    <td>${formatDate(item.created_at)}</td>
    <td><span class="badge badge-md ${statusClass}">${statusText}</span></td>
    <td class="text-end">
        <div class="d-flex align-items-center justify-content-end gap-2">
            <button class="btn btn-sm btn-outline-primary d-flex align-items-center" 
                    onclick="${actionFunction}(${item.id}, '${item.test.name.replace(/'/g, "\\'")}')">
                <i class="ti ${actionIcon} me-1"></i> ${actionLabel}
            </button>
            
            <div class="dropdown">
                <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown">
                    <i class="ti ti-dots-vertical"></i>
                </a>
                <ul class="dropdown-menu dropdown-menu-end p-2 shadow-sm">
                    <li><a class="dropdown-item d-flex align-items-center" href="#"><i class="ti ti-eye me-2"></i>Details</a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item text-danger d-flex align-items-center" href="#"><i class="ti ti-trash me-2"></i>Cancel</a></li>
                </ul>
            </div>
        </div>
    </td>
</tr>`;
}

// --- MODAL HELPERS ---

window.openStandardResultModal = function(itemId, testName) {
    const modalEl = document.getElementById('standardResultModal'); 
    if(!modalEl) return alert("Standard Result Modal not found in HTML");
    
    document.querySelector("#standard_order_item_id").value = itemId;
    document.querySelector("#standard_test_name_display").innerText = testName;
    
    new bootstrap.Modal(modalEl).show();
}

window.openRadiologyResultModal = function(itemId, testName) {
    const modalEl = document.getElementById('radiologyResultModal');
    if(!modalEl) return alert("Radiology Result Modal not found in HTML");
    
    document.getElementById('rad_order_item_id').value = itemId;
    document.getElementById('rad_test_name_display').innerText = testName;
    
    new bootstrap.Modal(modalEl).show();
}

// --- UTILITIES ---

async function getRemoteData(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch data.");
    return await res.json();
  } catch (error) {
    console.error(error);
    alert("Error loading laboratory queue.");
  }
}

function formatDate(dateStr) {
  if (!dateStr) return "N/A";
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}