// DOM Elements
const testsDropDownEl = document.getElementById("test_id_select");
const addTemplateBtn = document.getElementById("add__template__btn");
const addFieldBtn = document.getElementById("add-new-parameter-row"); // Use the specific ID
const dynamicFieldsContainer = document.querySelector("#dynamic-fields-container");
const submitBtn = document.querySelector("#submitForm");
const testTemplatesViewContainerEL = document.querySelector(".view__test__templates");

let currentMode = "create"; // "create" | "edit"
let currentEditTestId = null;

// URL Constants
const testURL = "/api/v1/tests/tests/";
const testTemplatesURL = "/api/v1/tests-templates/";

// --- INITIALIZATION ---
(async function init() {
    const res = await getRemoteData(testTemplatesURL + "grouped");
    if (res) renderTemplates(res);
})();

// --- CORE FUNCTIONS ---

/**
 * Enhanced addField function: Adds a parameter row to the modal
 */
function addField(existingData = null) {
    const fieldHTML = `
    <div class="card mb-3 field-block p-3 border-start border-4 border-primary shadow-sm">
      <div class="row g-2 mb-2">
        <div class="col-md-6">
          <label class="form-label small fw-bold">Parameter Name</label>
          <input type="text" class="form-control test_name" value="${existingData?.test_name || ""}" placeholder="e.g., Hemoglobin" required>
        </div>
        <div class="col-md-6">
          <label class="form-label small fw-bold">Short Code</label>
          <input type="text" class="form-control short_code" value="${existingData?.short_code || ""}" placeholder="HGB">
        </div>
      </div>
      <div class="row g-2 mb-2">
        <div class="col-md-4">
          <label class="form-label small">Unit</label>
          <input type="text" class="form-control unit" value="${existingData?.unit || ""}" placeholder="g/dL">
        </div>
        <div class="col-md-4">
          <label class="form-label small">Min Range</label>
          <input type="number" step="any" class="form-control min_range" value="${existingData?.min_reference_range ?? ""}">
        </div>
        <div class="col-md-4">
          <label class="form-label small">Max Range</label>
          <input type="number" step="any" class="form-control max_range" value="${existingData?.max_reference_range ?? ""}">
        </div>
      </div>
      <div class="text-end mt-2">
        <button type="button" class="btn btn-sm btn-outline-danger remove-field">
          <i class="ti ti-trash"></i> Remove
        </button>
      </div>
    </div>`;

    dynamicFieldsContainer.insertAdjacentHTML("beforeend", fieldHTML);
}

/**
 * Renders the main table listing all created templates
 */
function renderTemplates(data) {
    const renderedHTML = data
        .map((e) => `
      <tr>
        <th scope="row">${formatDate(e.created_on)}</th>
        <td>
            <div class="fw-bold text-dark">${e.test_name}</div>
            <small class="text-muted">${e.parameter_count} Parameters configured</small>
        </td>
        <td>
          <span class="mx-1">
            <button class="btn btn-sm btn-info edit-template-btn" 
                    data-test-id="${e.test_id}" 
                    data-test-name="${e.test_name}">
              <i class="ti ti-edit"></i> Edit Full Template
            </button>
          </span>
          <span>
            <button class="btn btn-sm btn-outline-danger delete-test-template-btn" 
                    data-test-id="${e.test_id}">
              <i class="ti ti-trash"></i>
            </button>
          </span>
        </td>
        <td>#${e.test_id}</td>
      </tr>
    `).join("");

    testTemplatesViewContainerEL.innerHTML = renderedHTML || '<tr><td colspan="4" class="text-center">No templates found</td></tr>';
}

/**
 * Fetches phlebotomy tests only for the dropdown
 */
async function renderTestOptions() {
    testsDropDownEl.innerHTML = '<option value="">Loading tests...</option>';
    const phlebotomyURL = "/api/v1/tests/phlebotomy-only"; 
    const data = await getRemoteData(phlebotomyURL);

    if (data && data.length > 0) {
        const optionsHTML = data.map(test => `<option value="${test.id}">${test.name}</option>`).join("");
        testsDropDownEl.innerHTML = `<option value="" selected disabled>-- Select Phlebotomy Test --</option>${optionsHTML}`;
    } else {
        testsDropDownEl.innerHTML = '<option value="">No Phlebotomy tests found.</option>';
    }
}

// --- EVENT LISTENERS ---

// Listener for the "Add Parameter" button inside modal
if (addFieldBtn) {
    addFieldBtn.addEventListener("click", (e) => {
        e.preventDefault();
        addField();
    });
}

// Open Modal for a NEW Template
addTemplateBtn.addEventListener("click", async () => {
    currentMode = "create";
    currentEditTestId = null;
    document.getElementById("exampleModalLabel").innerText = "Add New Test Template";
    dynamicFieldsContainer.innerHTML = ""; 
    addField(); // Start with one field
    await renderTestOptions();
});

// Delegate Remove Field clicks
dynamicFieldsContainer.addEventListener("click", (e) => {
    const removeBtn = e.target.closest(".remove-field");
    if (removeBtn) {
        removeBtn.closest(".field-block").remove();
    }
});

// Edit Logic: Load existing templates for a specific test
testTemplatesViewContainerEL.addEventListener("click", async (e) => {
    const btn = e.target.closest(".edit-template-btn");
    console.log(btn, "======================")
    if (!btn) return;

    currentMode = "edit";
    currentEditTestId = +btn.dataset.testId;
    document.getElementById("exampleModalLabel").innerText = `Editing: ${btn.dataset.testName}`;

    await renderTestOptions();
    testsDropDownEl.value = currentEditTestId;

    const templates = await getRemoteData(`${testTemplatesURL}by-test/${currentEditTestId}`);
    dynamicFieldsContainer.innerHTML = ""; 

    if (templates && templates.length > 0) {
        templates.forEach(t => addField(t));
    } else {
        addField();
    }

    new bootstrap.Modal(document.getElementById("exampleModal")).show();
});

// Submit Logic
submitBtn.addEventListener("click", async () => {
    const testTypeId = testsDropDownEl.value;
    if (!testTypeId){
        showToast("Please select a test type", "error");
        return;
        // return alert("Please select a test type")};
    }

    const fieldBlocks = document.querySelectorAll(".field-block");
    if (fieldBlocks.length === 0) {
        showToast("Add at least one paramter", "error")
        // return alert("Add at least one parameter");
        return;
    }

    const payload = Array.from(fieldBlocks).map(block => ({
        test_id: parseInt(testTypeId),
        test_name: block.querySelector(".test_name").value.trim(),
        short_code: block.querySelector(".short_code").value.trim(),
        unit: block.querySelector(".unit").value.trim(),
        min_reference_range: block.querySelector(".min_range").value ? parseFloat(block.querySelector(".min_range").value) : null,
        max_reference_range: block.querySelector(".max_range").value ? parseFloat(block.querySelector(".max_range").value) : null,
    }));

    try {
        const url = currentMode === "create" ? `${testTemplatesURL}bulk` : `${testTemplatesURL}by-test/${currentEditTestId}`;
        const method = currentMode === "create" ? "POST" : "PATCH";

        const response = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!response.ok) throw new Error("Failed to save data");

        // alert(`Templates ${currentMode === "create" ? "created" : "updated"} successfully`);
        showToast(`Templates ${currentMode === "create" ?  "created" : "updated"}`)
        location.reload();
    } catch (err) {
        console.error(err);
        // alert("Error saving templates.");
        showToast("Error saving templates.")
    }
});

// Delete Logic
testTemplatesViewContainerEL.addEventListener("click", async (e) => {
    const btn = e.target.closest(".delete-template-btn");
    // if (!btn || !confirm("Delete this parameter?")) return;
    if (!btn) {
        return;
    }

    try {
        const res = await fetch(`${testTemplatesURL}${btn.dataset.templateId}/`, { method: "DELETE" });
        if (res.ok) location.reload();
    } catch (err) { showToast("Delete failed", "error")}
});

// --- UTILS ---
async function getRemoteData(url) {
    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error("Fetch failed");
        return await res.json();
    } catch (error) { console.error("Data error:", error); }
}

function formatDate(dateStr) {
    if (!dateStr) return "--";
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}



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