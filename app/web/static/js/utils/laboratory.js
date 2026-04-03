const fillQueueURL = "/api/v1/lab/phlebotomy-queue/"; // Updated to your dedicated route



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



async function init() {
    const data = await getRemoteData(fillQueueURL);
    if (data) renderQueue(data);
}

function renderQueue(list) {
    const container = document.querySelector(".labtest__container");
    
    container.innerHTML = list.map(item => {
        console.log(item, "=========?????>>>>>>>")
        // Construct Full Name from JSON fields
        const patient = item.order.patient;
        const fullName = `${patient.full_name}`;
        const testName = item.test.name;
        const dateCreated = formatDate(item.order.created_at);

        return `
        <tr class="align-middle">
            <td><input class="form-check-input" type="checkbox"></td>
            <td class="fw-bold">${item.display_id}</td>
            <td>
                <div class="d-flex flex-column">
                    <span class="fw-bold text-dark">${fullName}</span>
                    <small class="text-muted">${patient.patient_no}</small>
                </div>
            </td>
            <td>${testName}</td>
            <td><span class="badge bg-outline-info text-info border-info">${item.test.test_category.category_name}</span></td>
            <td>${dateCreated}</td>
            <td><span class="badge bg-soft-warning text-warning border-warning">Awaiting Results</span></td>
            <td class="text-end">
                <button class="btn btn-sm btn-primary shadow-sm" 
                    onclick="openFillModal(${item.id}, '${testName.replace(/'/g, "\\'")}', '${fullName.replace(/'/g, "\\'")}', '${item.display_id}')">
                    <i class="ti ti-edit me-1"></i> Enter Results
                </button>
            </td>
        </tr>
    `}).join('');
}

// 1. OPEN MODAL & FETCH TEMPLATE
window.openFillModal = async function(itemId, testName, patientName, displayId) {
    // 1. UI Setup
    document.getElementById('display_test_name').innerText = testName;
    document.getElementById('display_patient_name').innerText = patientName;
    document.getElementById('display_order_id').innerText = `${displayId}`;
    document.getElementById('fill_order_item_id').value = itemId;
    
    const container = document.getElementById('dynamic_template_container');
    container.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status"></div>
            <p class="mt-2 text-muted">Loading ${testName} template...</p>
        </div>`;
    
    const modal = new bootstrap.Modal(document.getElementById('fillResultModal'));
    modal.show();

    try {
        // 2. Fetch using the specific "by-item" route we created above
        const response = await fetch(`/api/v1/tests-templates/by-item/${itemId}`);
        
        if (!response.ok) throw new Error("Template not found");
        
        const templates = await response.json();
        
        if (templates.length === 0) {
            container.innerHTML = `
                <div class="alert alert-warning border-0 shadow-sm d-flex align-items-center">
                    <i class="ti ti-alert-triangle fs-4 me-2"></i>
                    <div>
                        <strong>No Template Found:</strong> Please go to Settings and add parameters for "${testName}".
                    </div>
                </div>`;
            return;
        }

        // 3. Render the dynamic inputs
        container.innerHTML = templates.map(t => `
    <div class="row mx-0 align-items-center test-row py-3 border-bottom bg-white hover-bg-light">
        <div class="col-md-3 ps-3">
            <span class="fw-bold text-dark d-block">${t.test_name}</span>
            <small class="text-muted text-uppercase" style="font-size: 0.7rem;">${t.short_code || ''}</small>
        </div>

        <div class="col-md-4">
            <div class="input-group">
                <input type="number" step="any" class="form-control form-control-lg result-input border-primary-subtle text-center fw-bold" 
                       data-name="${t.test_name}" 
                       data-min="${t.min_reference_range ?? ''}" 
                       data-max="${t.max_reference_range ?? ''}"
                       data-unit="${t.unit ?? ''}"
                       oninput="validateFlag(this)"
                       placeholder="0.00">
                <span class="input-group-text bg-light small fw-medium" style="width: 80px; justify-content: center;">
                    ${t.unit ?? '-'}
                </span>
            </div>
        </div>

        <div class="col-md-1 text-center">
            <span class="badge flag-badge bg-light text-dark fs-6 p-2 w-100">-</span>
        </div>

        <div class="col-md-4 text-center">
            <div class="bg-light rounded py-2 border">
                <span class="small text-muted d-block" style="font-size: 0.65rem;">NORMAL RANGE</span>
                <span class="fw-bold px-2">${t.min_reference_range ?? '0'} — ${t.max_reference_range ?? 'N/A'}</span>
                <small class="text-muted ms-1">${t.unit ?? ''}</small>
            </div>
        </div>
    </div>
`).join('');


    } catch (err) {
        console.error("Modal Load Error:", err);
        container.innerHTML = `
            <div class="alert alert-danger shadow-sm">
                <i class="ti ti-circle-x me-2"></i> Error loading template. Please check your connection.
            </div>`;
    }
};

// 2. LIVE VALIDATION (High/Low)
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

    if (min && val < min) {
        badge.className = "badge flag-badge bg-danger";
        badge.innerText = "L";
    } else if (max && val > max) {
        badge.className = "badge flag-badge bg-danger text-white";
        badge.innerText = "H";
    } else {
        badge.className = "badge flag-badge bg-success";
        badge.innerText = "N";
    }
};

// 3. SUBMIT TO BACKEND (SAVE AS JSON)
document.getElementById('fill_results_form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const submitBtn = document.getElementById('save_results_btn');
    const itemId = document.getElementById('fill_order_item_id').value;
    const rows = document.querySelectorAll('.test-row');
    
    // We build the object that will be stored in the JSON column
    const resultsPayload = {};

    rows.forEach(row => {
        const input = row.querySelector('.result-input');
        const parameterName = input.dataset.name;
        const value = input.value;
        
        // Only save if a value was actually entered
        if (value !== "") {
            resultsPayload[parameterName] = {
                value: value,
                unit: input.dataset.unit,
                flag: row.querySelector('.flag-badge').innerText, // 'L', 'H', or 'N'
                reference_range: `${input.dataset.min} - ${input.dataset.max}`
            };
        }
    });

    if (Object.keys(resultsPayload).length === 0) {
        // return alert("Please enter at least one result value.");
        showToast("Please enter at least one result value.", "error");
        return;
    }

    // Disable button to prevent double-submission
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';

    try {
        const response = await fetch('/api/v1/lab/results/submit-phlebotomy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                order_item_id: parseInt(itemId),
                results: resultsPayload
            })
        });

        if (response.ok) {
            // alert("Results finalized and saved successfully!");
            showToast("Results finalized and saved successfully!")
            location.reload(); // Refresh the queue
        } else {
            const error = await response.json();
            throw new Error(error.detail || "Failed to save");
        }
    } catch (err) {
        // alert("Error: " + err.message);
        showToast(err.message, "error");
        submitBtn.disabled = false;
        submitBtn.innerText = "Save & Finalize Results";
    }
});


init();


function formatDate(dateStr) {
    if (!dateStr) return "N/A";
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit"
    });
}



// --- UTILS ---
async function getRemoteData(url) {
    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error("Fetch failed");
        return await res.json();
    } catch (error) { console.error("Data error:", error); }
}