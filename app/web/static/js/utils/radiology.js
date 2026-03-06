/**
 * RADIOLOGY QUEUE MANAGEMENT - MATCHED TO API RESPONSE
 */

const radiologyQueueURL = "/api/v1/lab/queue/radiology";
const containerEl = document.querySelector(".lab__container");

(async function init() {
    const data = await fetchData(radiologyQueueURL);
    if (data) renderRadiologyTable(data);
})();

async function fetchData(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error("Network response was not ok");
        return await response.json();
    } catch (error) {
        console.error("Fetch error:", error);
        return null;
    }
}

function renderRadiologyTable(items) {
    const containerEl = document.getElementById('radiology_queue_container'); // Ensure this ID matches your HTML
    if (!containerEl) return;
    
    if (!items || items.length === 0) {
        containerEl.innerHTML = `<tr><td colspan="9" class="text-center p-4">No pending radiology requests found.</td></tr>`;
        return;
    }

    containerEl.innerHTML = items.map(item => {
        const appointment = item.order?.appointment || {};
        const patient = appointment.patient || {};
        const doctor = appointment.doctor || {};
        const testNameEscaped = item.test.name.replace(/'/g, "\\'"); // Escaping for JS onclick
        
        const dateSource = appointment.appointment_at || item.entered_at;
        const displayDate = dateSource 
            ? new Date(dateSource).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
            : 'Pending';

        // --- DYNAMIC STATUS & ACTION LOGIC ---
        let statusLabel = item.status.replace('_', ' ').toUpperCase();
        let badgeClass = 'badge-soft-warning border-warning text-warning'; // Default: Awaiting Results
        let actionHtml = '';

        // Case 1: Result entered, needs Senior approval
        if (item.status === 'awaiting_approval' || item.stage === 'analyzing') {
            badgeClass = 'badge-soft-info border-info text-info';
            statusLabel = 'AWAITING APPROVAL';
            actionHtml = `
                <li>
                    <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center text-info" 
                       onclick="reviewReport(${item.id}, '${testNameEscaped}')">
                        <i class="ti ti-checklist me-2"></i>Review Report
                    </a>
                </li>`;
        } 
        // Case 2: New request, needs findings
        else if (item.status === 'awaiting_results' || item.stage === 'running') {
            badgeClass = 'badge-soft-warning border-warning text-warning';
            statusLabel = 'PENDING SCAN';
            actionHtml = `
                <li>
                    <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center text-primary" 
                       onclick="openReportModal(${item.id}, '${testNameEscaped}')">
                        <i class="ti ti-report-medical me-2"></i>Enter Findings
                    </a>
                </li>`;
        } 
        // Case 3: Fully verified
        else if (item.status === 'completed' || item.stage === 'complete') {
            badgeClass = 'badge-soft-success border-success text-success';
            statusLabel = 'FINALIZED';
            actionHtml = `
                <li>
                    <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center" onclick="viewFinalReport(${item.id})">
                        <i class="ti ti-file-certificate me-2"></i>View Final Report
                    </a>
                </li>`;
        }

        return `
        <tr>
            <td>
                <div class="form-check form-check-md">
                    <input class="form-check-input" type="checkbox" value="${item.id}">
                </div>
            </td>
            <td><span class="text-muted fw-bold">#RAD-${item.id}</span></td>
            <td>
                <div class="d-flex align-items-center">
                    <div class="avatar avatar-xs me-2 bg-light rounded-circle d-flex align-items-center justify-content-center">
                        <i class="ti ti-user fs-12 text-muted"></i>
                    </div>
                    <div>
                        <h6 class="fs-14 mb-0 fw-medium">${patient.full_name || 'Unknown Patient'}</h6>
                    </div>
                </div>
            </td>
            <td>${patient.gender || 'N/A'}</td>
            <td>${displayDate}</td>
            <td>
                <div class="d-flex align-items-center">
                    <h6 class="fs-13 mb-0 text-muted">${doctor.full_name ? 'Dr. ' + doctor.full_name : 'Self-Referral'}</h6>
                </div>
            </td>
            <td>
                <div class="d-flex flex-column">
                    <span class="text-dark fw-medium">${item.test.name}</span>
                </div>
            </td>
            <td><span class="badge badge-md ${badgeClass} border">${statusLabel}</span></td>
            <td class="text-end">
                <div class="dropdown">
                    <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown">
                        <i class="ti ti-dots-vertical"></i>
                    </a>
                    <ul class="dropdown-menu dropdown-menu-end p-2 shadow-sm">
                        ${actionHtml}
                        <li><hr class="dropdown-divider"></li>
                        <li>
                            <a href="javascript:void(0);" class="dropdown-item text-danger d-flex align-items-center">
                                <i class="ti ti-trash me-2"></i>Cancel Request
                            </a>
                        </li>
                    </ul>
                </div>
            </td>
        </tr>`;
    }).join('');
}

// 5. MODAL CONTROL - FOR NEW ENTRIES
window.openReportModal = function(itemId, testName) {
    const modalEl = document.getElementById('radiologyResultModal');
    if (!modalEl) return;

    // Reset Modal Fields
    document.getElementById('rad_order_item_id').value = itemId;
    document.getElementById('rad_test_name_display').innerText = testName;
    document.getElementById('rad_findings').value = ''; 
    document.getElementById('rad_conclusion').value = '';

    // Show 'Submit for Approval', Hide 'Approve & Finalize'
    document.getElementById('btn_save_result').style.display = 'block';
    document.getElementById('btn_finalize_result').style.display = 'none';
    
    // Set fields to editable (just in case they were disabled)
    document.getElementById('rad_findings').readOnly = false;
    document.getElementById('rad_conclusion').readOnly = false;

    const modal = new bootstrap.Modal(modalEl);
    modal.show();
};


// 6. SUBMISSION

async function saveRadiologyResult() {
    const findings = document.getElementById('rad_findings').value;
    const conclusion = document.getElementById('rad_conclusion').value;
    const itemId = document.getElementById('rad_order_item_id').value;

    if (!findings.trim()) {
        alert("Please enter clinical findings.");
        return;
    }

    try {
        const response = await fetch('/api/v1/radiology/submit-result', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                order_item_id: parseInt(itemId),
                findings: findings,
                conclusion: conclusion
            })
        });

        if (response.ok) {
            // 1. Hide the modal using the Bootstrap instance
            const modalInstance = bootstrap.Modal.getInstance(document.getElementById('radiologyResultModal'));
            modalInstance.hide();

            // 2. Refresh the table data (This removes the completed item from the list)
            const data = await fetchData(radiologyQueueURL);
            renderRadiologyTable(data);

            // 3. Clear the modal inputs for the next patient
            document.getElementById('rad_findings').value = '';
            document.getElementById('rad_conclusion').value = '';
        }
    } catch (error) {
        console.error("Save error:", error);
    }
}

window.reviewReport = async function(itemId, testName) {
    const modalEl = document.getElementById('radiologyResultModal');
    if (!modalEl) return;

    try {
        // 1. Fetch the existing result data from the backend
        const response = await fetch(`/api/v1/lab/radiology/result-by-item/${itemId}`);
        if (!response.ok) throw new Error("Failed to fetch report data");
        
        const resultData = await response.json();

        // 2. Populate the modal
        document.getElementById('rad_order_item_id').value = itemId;
        document.getElementById('rad_test_name_display').innerText = testName;
        document.getElementById('rad_findings').value = resultData.result_value || '';
        document.getElementById('rad_conclusion').value = resultData.comments || '';

        // 3. UI Toggle: Hide 'Save', Show 'Finalize'
        document.getElementById('btn_save_result').style.display = 'none';
        document.getElementById('btn_finalize_result').style.display = 'block';

        // 4. Show Modal
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    } catch (err) {
        console.error("Error loading report for review:", err);
        alert("Could not load the report findings. Please try again.");
    }
};


window.finalizeReport = async function() {
    const itemId = document.getElementById('rad_order_item_id').value;
    
    if (!itemId) return;

    // Optional: Add a confirmation dialog
    if (!confirm("Are you sure you want to finalize this report? This will sign off the results.")) {
        return;
    }

    try {
        const response = await fetch(`/api/v1/lab/finalize-report/${itemId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            // 1. Hide the modal
            const modalInstance = bootstrap.Modal.getInstance(document.getElementById('radiologyResultModal'));
            if (modalInstance) modalInstance.hide();

            // 2. Refresh the table data (Item will now disappear from the queue)
            const data = await fetchData(radiologyQueueURL);
            if (data) renderRadiologyTable(data);
            
            // 3. Success notification (if you have a toast library)
            console.log("Report finalized successfully");
        } else {
            const errorData = await response.json();
            alert("Error: " + (errorData.detail || "Could not finalize report"));
        }
    } catch (error) {
        console.error("Finalization error:", error);
        alert("A network error occurred.");
    }
};