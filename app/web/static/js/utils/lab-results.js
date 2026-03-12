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
 if (!labList) return;
  totalLabTestsEl.textContent = labList.length;

  // 1. Generate the HTML string
  const renderedHTML = labList
    .map((lab) => renderData(lab))
    .join("");

  // 2. Insert into the DOM
  labTestsContainerEl.innerHTML = renderedHTML;

  // 3. Re-initialize the Table (Vanilla JS approach)
  // We check if a DataTable instance already exists and refresh it
  const tableEl = document.querySelector(".datatable");
  
  if (tableEl) {
    // If you are using simple-datatables:
    if (window.simpleDatatables) {
        new simpleDatatables.DataTable(tableEl);
    } 
    // If you ARE using jQuery but it's just not loaded yet, 
    // you'd need to add the <script src="..."> for jQuery in your HTML.
  }
}

/**
 * Renders an individual Lab/Radiology item into a table row.
 */
function renderData(item) {
  const statusColors = {
    "COMPLETED": "badge-soft-success text-success border-success",
    "APPROVED": "badge-soft-info text-info border-info"
  };
  
  const statusClass = statusColors[item.status] || "badge-soft-success";
  const statusText = "FINALIZED";

  // Mapping data from your JSON structure
  const patient = item.order.appointment.patient;
  const appointmentDate = item.order.appointment.appointment_at;

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

    <td>${formatDate(appointmentDate)}</td>

    <td>Dr. ${item.order.appointment.doctor?.full_name || 'System'}</td>

    <td>${item.test.name}</td>

    <td><span class="badge badge-md ${statusClass}">${statusText}</span></td>

    <td class="text-end">
        <div class="d-flex align-items-center justify-content-end gap-2">
            <button class="btn btn-sm btn-light" onclick="viewFinalReport(${item.id})">
                <i class="ti ti-eye me-1"></i> View
            </button>
            <button class="btn btn-sm btn-outline-secondary" onclick="printResult(${item.id})">
                <i class="ti ti-printer"></i>
            </button>
        </div>
    </td>
</tr>`;
}
// --- MODAL HELPERS ---

window.openStandardResultModal = function(itemId, testName) {
    const modalEl = document.getElementById('standardResultModal'); 
    console.log(modalEl)
    
    // Debugging: This will print 'null' in the console if it's still missing
    console.log("Looking for modal... found:", modalEl);

    if(!modalEl) {
        return alert("Error: The modal with ID 'standardResultModal' is missing from this HTML page.");
    }
    
    // Set values
    const idInput = document.querySelector("#standard_order_item_id");
    const nameDisplay = document.querySelector("#standard_test_name_display");

    if(idInput) idInput.value = itemId;
    if(nameDisplay) nameDisplay.innerText = testName;
    
    // Open modal
    const myModal = new bootstrap.Modal(modalEl);
    myModal.show();
}


window.openRadiologyResultModal = function(itemId, testName) {
    const modalEl = document.getElementById('radiologyResultModal');
    if(!modalEl) return alert("Radiology Result Modal not found in HTML");
    
    document.getElementById('rad_order_item_id').value = itemId;
    document.getElementById('rad_test_name_display').innerText = testName;
    
    new bootstrap.Modal(modalEl).show();
}

window.viewFinalReport = async function(itemId) {
    try {
        const res = await fetch(`/api/v1/lab/item/${itemId}`);
        if (!res.ok) throw new Error("Could not fetch report details.");
        const data = await res.json();
        
        const modalEl = document.getElementById('viewReportModal');
        if (!modalEl) return console.error("viewReportModal missing");

        // Set Header
        document.querySelector("#view_test_name").innerText = data.test.name;
        
        // Toggle Display based on Category
        const isRad = data.test.test_category?.category_name === "Radiology";
        document.getElementById('lab_result_display').style.display = isRad ? 'none' : 'block';
        document.getElementById('rad_result_display').style.display = isRad ? 'block' : 'none';

        if (isRad) {
            // Populate Radiology fields
            document.querySelector("#view_rad_findings").innerText = data.radiology_result?.result_value || "No findings recorded.";
            document.querySelector("#view_rad_impression").innerText = data.radiology_result?.comments || "N/A";
        } else {
            // Populate Lab fields
            document.querySelector("#view_result_value").innerText = `${data.lab_result?.result_value || '--'} ${data.lab_result?.unit || ''}`;
            document.querySelector("#view_ref_range").innerText = data.lab_result?.reference_range || 'Normal';
        }

        document.querySelector("#view_remarks").innerText = data.lab_result?.remarks || data.radiology_result?.comments || "No additional remarks.";

        // Show Modal
        new bootstrap.Modal(modalEl).show();

    } catch (error) {
        console.error(error);
        alert("Error loading report: " + error.message);
    }
}


window.printResult = function(itemId) {
    // Usually, you'd want to open a dedicated print-friendly URL
    const printUrl = `/api/v1/lab/report/print/${itemId}`;
    const printWindow = window.open(printUrl, '_blank');
    printWindow.focus();
};


// A simple helper to handle empty data
const cleanText = (val) => val && val !== "null" ? val : "--";

// Inside your viewFinalReport function:
document.querySelector("#view_rad_findings").innerText = cleanText(data.radiology_result?.result_value);

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