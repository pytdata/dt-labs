/**
 * RADIOLOGY QUEUE MANAGEMENT - MATCHED TO API RESPONSE
 */

const radiologyQueueURL = "/api/v1/lab/queue/radiology";
const containerEl = document.querySelector(".lab__container");
const totalRadiology = document
.querySelector(".lab__results__total");

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
    const containerEl = document.querySelector('.lab__container'); 
    if (!containerEl) return;

    totalRadiology.textContent = items.length;
    
    if (!items || items.length === 0) {
        containerEl.innerHTML = `<tr><td colspan="9" class="text-center p-4">No pending radiology requests found.</td></tr>`;
        return;
    }

    containerEl.innerHTML = items.map(item => {
        const appointment = item.order?.appointment || {};
        const patient = appointment.patient || {};
        const doctor = appointment.doctor || {};
        const testNameEscaped = item.test.name.replace(/'/g, "\\'"); 
        
        const dateSource = appointment.appointment_at || item.entered_at;
        const displayDate = dateSource 
            ? new Date(dateSource).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
            : 'Pending';

        // --- DYNAMIC STATUS & ACTION LOGIC ---
        // Normalize status for comparison
        const currentStatus = item.status.toUpperCase();
        const currentStage = item.stage.toLowerCase();

        let statusLabel = item.status.replace('_', ' ').toUpperCase();
        let badgeClass = 'badge-soft-warning border-warning text-warning';
        let primaryActionBtn = ''; // Direct button in the row
        let dropdownActionHtml = ''; // Inside the three-dot menu

        // Case 1: Result entered, needs Senior approval
        if (currentStatus === 'AWAITING_APPROVAL' || currentStage === 'review' || currentStage === 'analyzing') {
            badgeClass = 'badge-soft-info border-info text-info';
            statusLabel = 'AWAITING APPROVAL';
            
            primaryActionBtn = `
                <button class="btn btn-sm btn-info text-white me-2 d-flex align-items-center" 
                        onclick="reviewReport(${item.id}, '${testNameEscaped}')">
                    <i class="ti ti-checklist me-1"></i> Review
                </button>`;
                
            dropdownActionHtml = `
                <li>
                    <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center text-info" 
                       onclick="reviewReport(${item.id}, '${testNameEscaped}')">
                        <i class="ti ti-checklist me-2"></i>Review Report
                    </a>
                </li>`;
        } 
        // Case 2: New request, needs findings
        else if (currentStatus === 'AWAITING_RESULTS' || currentStage === 'analysis' || currentStage === 'running') {
            badgeClass = 'badge-soft-warning border-warning text-warning';
            statusLabel = 'PENDING SCAN';
            
            primaryActionBtn = `
                <button class="btn btn-sm btn-primary me-2 d-flex align-items-center" 
                        onclick="openReportModal(${item.id}, '${testNameEscaped}')">
                    <i class="ti ti-report-medical me-1"></i> Findings
                </button>`;

            dropdownActionHtml = `
                <li>
                    <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center text-primary" 
                       onclick="openReportModal(${item.id}, '${testNameEscaped}')">
                        <i class="ti ti-report-medical me-2"></i>Enter Findings
                    </a>
                </li>`;
        } 
        // Case 3: Fully verified
        else if (currentStatus === 'COMPLETED' || currentStage === 'complete') {
            badgeClass = 'badge-soft-success border-success text-success';
            statusLabel = 'FINALIZED';
            
            primaryActionBtn = `
                <button class="btn btn-sm btn-outline-success me-2 d-flex align-items-center" 
                        onclick="viewFinalReport(${item.id})">
                    <i class="ti ti-file-certificate me-1"></i> View
                </button>`;

            dropdownActionHtml = `
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
                <div class="d-flex align-items-center justify-content-end">
                    ${primaryActionBtn}

                    <div class="dropdown">
                        <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown">
                            <i class="ti ti-dots-vertical"></i>
                        </a>
                        <ul class="dropdown-menu dropdown-menu-end p-2 shadow-sm">
                            ${dropdownActionHtml}
                            <li><hr class="dropdown-divider"></li>
                            <li>
                                <a href="javascript:void(0);" class="dropdown-item text-danger d-flex align-items-center">
                                    <i class="ti ti-trash me-2"></i>Cancel Request
                                </a>
                            </li>
                        </ul>
                    </div>
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

    // Validation
    if (!findings.trim()) {
        alert("Please enter clinical findings before submitting.");
        return;
    }

    // UI Feedback: Disable button to prevent double submission
    const submitBtn = document.getElementById('btn_save_result');
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> Submitting...`;

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

        const result = await response.json();

        if (response.ok) {
            // 1. Close Modal
            const modalEl = document.getElementById('radiologyResultModal');
            const modalInstance = bootstrap.Modal.getInstance(modalEl);
            if (modalInstance) modalInstance.hide();

            // 2. Refresh the Queue (The item will now have a different status/color)
            const data = await fetchData(radiologyQueueURL);
            renderRadiologyTable(data);

            // 3. Optional: Success Notification
            console.log("Success:", result.message);
        } else {
            alert("Error: " + (result.detail || "Failed to save results"));
        }
    } catch (error) {
        console.error("Network Error:", error);
        alert("A network error occurred. Please try again.");
    } finally {
        // Re-enable button
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}


window.reviewReport = async function(itemId, testName) {
    const modalEl = document.getElementById('radiologyResultModal');
    if (!modalEl) return;

    try {
        // 1. Fetch the existing result data from the backend
        const response = await fetch(`/api/v1/radiology/result-by-item/${itemId}`);
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
        const response = await fetch(`/api/v1/radiology/finalize-report/${itemId}`, {
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


window.viewFinalReport = async function(itemId) {
    try {
        const response = await fetch(`/api/v1/lab/report/${itemId}`);
        if (!response.ok) throw new Error("Could not fetch report data");
        
        const data = await response.json();
        const patient = data.patient;
        const doctor = data.doctor || { full_name: "Self-Referral" };

        // Open new window for printing
        const printWindow = window.open('', '_blank', 'width=900,height=800');
        
        const htmlContent = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Report - ${patient.first_name} ${patient.surname}</title>
                <style>
                    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 50px; color: #333; }
                    .report-header { text-align: center; border-bottom: 3px solid #2c3e50; padding-bottom: 10px; margin-bottom: 30px; }
                    .patient-box { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; background: #f9f9f9; padding: 15px; border-radius: 8px; margin-bottom: 30px; }
                    .section-title { font-weight: bold; font-size: 1.1rem; border-bottom: 1px solid #eee; margin-top: 20px; padding-bottom: 5px; color: #2c3e50; }
                    .content { padding: 10px 0; white-space: pre-line; line-height: 1.6; }
                    .footer { margin-top: 50px; border-top: 1px solid #eee; padding-top: 20px; font-size: 0.9rem; font-style: italic; }
                    @media print { .btn-print { display: none; } }
                    .btn-print { background: #2c3e50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; float: right; }
                </style>
            </head>
            <body>
                <button class="btn-print" onclick="window.print()">Print PDF</button>
                <div class="report-header">
                    <h2>DATA GLOW DIAGNOSTICS</h2>
                    <p>Accra, Ghana | Digital Health Excellence</p>
                </div>
                
                <div class="patient-box">
                    <div>
                        <strong>Patient:</strong> ${patient.first_name} ${patient.surname} <br>
                        <strong>ID:</strong> ${patient.patient_no} | <strong>Gender:</strong> ${patient.sex || patient.gender}
                    </div>
                    <div style="text-align: right;">
                        <strong>Date:</strong> ${new Date(data.finalized_at).toLocaleDateString('en-GB')} <br>
                        <strong>Referrer:</strong> Dr. ${doctor.full_name}
                    </div>
                </div>

                <div class="section-title">EXAMINATION</div>
                <div class="content"><strong>${data.test_name}</strong></div>

                <div class="section-title">FINDINGS / OBSERVATIONS</div>
                <div class="content">${data.findings}</div>

                <div class="section-title">IMPRESSION / CONCLUSION</div>
                <div class="content"><strong>${data.conclusion || 'No specific conclusion provided.'}</strong></div>

                <div class="footer">
                    This is a digitally verified report. No physical signature is required. <br>
                    Verified on: ${new Date(data.finalized_at).toLocaleString()}
                </div>
            </body>
            </html>
        `;

        printWindow.document.write(htmlContent);
        printWindow.document.close();

    } catch (error) {
        console.error("Print error:", error);
        alert("Failed to generate the report. Please ensure the item is finalized.");
    }
};