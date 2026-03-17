// 1. GLOBAL STATE
let allQueueItems = [];




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

const phlebotomyContainerEl = document.querySelector(".phlebotomy__container");
const phlebotomyURL = `/api/v1/lab/queue/phlebotomy`;

(async function init() {
    const res = await getRemoteData(phlebotomyURL);
    allQueueItems = res || []; // Store globally so modal can find data
    console.log("QUEUE: ", res);
    render(allQueueItems);
})();

async function getRemoteData(url) {
    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error("Failed to fetch queue data");
        return await res.json();
    } catch (error) {
        throw new Error(error)
    }
}

function render(queueList) {
    if (!queueList || queueList.length === 0) {
        phlebotomyContainerEl.innerHTML = `<tr><td colspan="7" class="text-center py-5 text-muted">No pending collections.</td></tr>`;
        return;
    }
    const renderedHTML = queueList.map(item => renderQueueRow(item)).join("");
    phlebotomyContainerEl.innerHTML = renderedHTML;
}

function renderQueueRow(item) {
    const patient = item.order.appointment.patient;
    const test = item.test;
    const statusClass = item.status === 'awaiting_sample' ? 'bg-soft-warning text-warning' : 'bg-soft-info text-info';

    return ` 
    <tr class="align-middle">
        <td><div class="form-check"><input class="form-check-input" type="checkbox" value="${item.id}"></div></td>
        <td><span class="fw-bold text-dark">${patient.patient_no}</span></td>
        <td>
            <div class="d-flex flex-column">
                <span class="fw-medium text-dark">${patient.full_name}</span>
                <small class="text-muted">${patient.sex} | ${patient.age} yrs</small>
            </div>
        </td>
        <td>
            <div class="d-flex flex-column">
                <span class="text-dark">${test.name}</span>
                <small class="text-primary fw-bold">${test.sample_type || 'Blood'}</small>
            </div>
        </td>
        <td><span class="badge ${statusClass} border-0">${item.status.toUpperCase()}</span></td>
        <td>${item.priority || 'Normal'}</td>
        <td class="text-end">
            <div class="dropdown">
                <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown">
                    <i class="ti ti-dots-vertical"></i>
                </a>
                <ul class="dropdown-menu dropdown-menu-end p-2 shadow-sm">
                    <li>
                        <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center" 
                           onclick="openSampleModal(${item.id}, ${item.order.appointment.id})">
                            <i class="ti ti-flask me-2 text-success"></i>Collect Sample
                        </a>
                    </li>
                    <li>
                        <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center" onclick="viewHistory(${patient.id})">
                            <i class="ti ti-history me-2 text-info"></i>Patient History
                        </a>
                    </li>
                    <li>
                        <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center" 
                        onclick="openManageSamplesModal(${item.order.appointment.id})">
                            <i class="ti ti-layers-subtract me-2 text-warning"></i>Manage Samples
                        </a>
                    </li>
                    <li><hr class="dropdown-divider"></li>
                    <li>
                        <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center text-danger">
                            <i class="ti ti-trash me-2"></i>Cancel Test
                        </a>
                    </li>
                </ul>
            </div>
        </td>
    </tr>`;
}

window.openSampleModal = async function(itemId, appointmentId) {
    const sampleTypeSelect = document.getElementById("sample_type");
    const testSelect = document.getElementById("test_ids");
    const patientNameSpan = document.getElementById("modal_patient_name");
    const phlebInput = document.getElementById("target_phlebotomy_id");
    
    // 1. Reset UI & Show Loading State
    sampleTypeSelect.innerHTML = '<option>Loading categories...</option>';
    testSelect.innerHTML = '<option>Loading tests...</option>';
    
    // Find the item in your local queue array
    const item = allQueueItems.find(i => i.id === itemId);
    
    if (item) {
        document.getElementById("modal_patient_name").textContent = item.order.appointment.patient.full_name;
        document.getElementById("modal_appointment_id").textContent = `#${appointmentId}`;
        
        // HIDDEN FIELDS for the /collect payload
        document.getElementById("target_appointment_id").value = appointmentId;
        document.getElementById("target_patient_id").value = item.order.appointment.patient.id;
        
        const phlebId = item.order.appointment.phlebotomy?.id || "";
        phlebInput.value = phlebId; 
    }

    try {
        // 2. Parallel Fetch: Categories and NESTED Pending Items
        const [catRes, testRes] = await Promise.all([
            fetch('/api/v1/samples/sample-categories'),
            // Updated URL to match your corrected route
            fetch(`/api/v1/lab/appointments/${appointmentId}/pending-items`)
        ]);

        if (!catRes.ok || !testRes.ok) throw new Error("API Fetch failed");

        const categories = await catRes.json();
        const pendingItems = await testRes.json();

        // 3. Populate Sample Categories
        sampleTypeSelect.innerHTML = '<option value="">Select Category...</option>';
        categories.forEach(cat => {
            const opt = document.createElement("option");
            opt.value = cat.id; 
            opt.textContent = cat.category_name.toUpperCase();
            sampleTypeSelect.appendChild(opt);
        });

        // 4. Populate Pending Tests (Using the LabOrderItem ID and Nested Test Name)
        testSelect.innerHTML = "";
        pendingItems.forEach(item => {
            const opt = document.createElement("option");
            
            // This is the LabOrderItem.id (e.g., 101)
            opt.value = item.id; 
            
            // Access the nested test name from the TestResponse schema
            opt.textContent = item.test.name; 
            
            // Auto-select if it matches the row the scientist clicked
            if (item.id === itemId) opt.selected = true;
            
            testSelect.appendChild(opt);
        });

        // 5. Open Modal
        const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById("addSamplesModal"));
        modal.show();

    } catch (error) {
        console.error("Modal Data Load Error:", error);
        showToast("Failed to load sample data. Try again")
        
    }
};


document.getElementById("sampleForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    
    // 1. DEFINE THE BUTTON (Missing in your snippet)
    const saveBtn = document.getElementById("saveSampleBtn");
    const formData = new FormData(e.target);
    
    // 2. DATA PARSING
    // Convert hidden field to integer or null for the Pydantic Optional[int]
    const rawPhlebId = formData.get("phlebotomy_id");
    const phlebotomyId = (rawPhlebId && rawPhlebId !== "") ? parseInt(rawPhlebId) : null;

    // 3. PAYLOAD CONSTRUCTION
    const payload = {
        patient_id: parseInt(formData.get("patient_id")),
        appointment_id: parseInt(formData.get("appointment_id")),
        phlebotomy_id: phlebotomyId, 
        sample_category_id: parseInt(formData.get("sample_category_id")),
        priority: formData.get("priority") || "routine",
        collection_site: formData.get("collection_site") || "clinic",
        storage_location: formData.get("storage_location") || "ambient",
        sample_condition: formData.get("sample_condition") || "good",
        test_item_ids: Array.from(document.getElementById("test_ids").selectedOptions)
                             .map(opt => parseInt(opt.value))
    };

    // Validation check before fetching
    if (payload.test_item_ids.length === 0) {
        // alert("Please select at least one test item.");
        showToast("Please select at least one test item", "error")
        return;
    }

    try {
        // 4. UI FEEDBACK
        saveBtn.disabled = true;
        saveBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> Saving...`;

        const response = await fetch('/api/v1/samples/collect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const err = await response.json();
            // Handles both FastAPI string details and Pydantic list errors
            throw new Error(Array.isArray(err.detail) ? err.detail[0].msg : err.detail);
        }

        // 5. SUCCESS HANDLING
        const modalElement = document.getElementById("addSamplesModal");
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) modal.hide();
        
        window.location.reload(); 

    } catch (error) {
        console.error("Submission Error:", error);
        // alert("Error: " + error.message);
        showToast(error.message, "error")
    } finally {
        // 6. RESET BUTTON STATE
        saveBtn.disabled = false;
        saveBtn.innerHTML = `<i class="ti ti-check me-1"></i> Confirm & Save`;
    }
});

// Variable to store the phlebotomy ID for the finalize action
let currentPhlebId = null;

window.openManageSamplesModal = async function(appointmentId) {
    const body = document.getElementById("manageSamplesBody");
    const loader = document.getElementById("manageSamplesLoading");
    const statusSummary = document.getElementById("modalStatusSummary");
    const finalizeBtn = document.getElementById("btnFinalizePhleb");
    
    // 1. Initial State
    body.innerHTML = "";
    statusSummary.innerHTML = "";
    loader.classList.remove("d-none");
    finalizeBtn.disabled = true; // Disabled until we verify all samples are in
    
    const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById("manageSamplesModal"));
    modal.show();

    try {
        // Fetch samples and pending items in parallel to compare progress
        const [samplesRes, pendingRes] = await Promise.all([
            fetch(`/api/v1/samples/appointment/${appointmentId}`),
            fetch(`/api/v1/lab/appointments/${appointmentId}/pending-items`)
        ]);

        const samples = await samplesRes.json();
        const pendingItems = await pendingRes.json();
        console.log("SAMPLES HERE IS >>>>", samples)

                // CAPTURE THE ID HERE
            if (samples && samples.length > 0) {
                currentPhlebId = samples[0].phlebotomy_id;
            } else {
                currentPhlebId = null;
                console.log("phleb id: ", currentPhlebId)
            }
        
        loader.classList.add("d-none");
        currentPhlebId = samples.length > 0 ? samples[0].phlebotomy_id : null;

        // 2. UI ENHANCEMENT: Status Summary
        const collectedCount = samples.reduce((acc, s) => acc + s.items.length, 0);
        const pendingCount = pendingItems.length; // Items still awaiting_sample
        const totalNeeded = collectedCount + pendingCount;

        if (totalNeeded === 0) {
            statusSummary.innerHTML = `<div class="alert alert-info py-2 small mb-0"><i class="ti ti-info-circle me-1"></i> No tests requiring phlebotomy found for this appointment.</div>`;
        } else if (pendingCount > 0) {
            statusSummary.innerHTML = `
                <div class="alert alert-warning py-2 mb-0 d-flex justify-content-between align-items-center">
                    <span class="small"><i class="ti ti-alert-triangle me-1"></i> <strong>Incomplete:</strong> ${pendingCount} test(s) still require sample collection.</span>
                    <span class="badge bg-warning text-dark">${collectedCount}/${totalNeeded} Collected</span>
                </div>`;
            finalizeBtn.disabled = true;
        } else {
            statusSummary.innerHTML = `
                <div class="alert alert-success py-2 mb-0 d-flex justify-content-between align-items-center">
                    <span class="small"><i class="ti ti-check me-1"></i> <strong>Ready:</strong> All samples have been collected.</span>
                    <span class="badge bg-success text-white">Complete</span>
                </div>`;
            finalizeBtn.disabled = false;
        }

        // 3. Render Empty State
        if (!samples || samples.length === 0) {
            body.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center py-5">
                        <div class="d-flex flex-column align-items-center text-muted">
                            <i class="ti ti-flask-off mb-2" style="font-size: 3rem;"></i>
                            <h6 class="fw-bold">No Samples Added Yet</h6>
                            <p class="small mb-0">Collect a sample to see it listed here.</p>
                        </div>
                    </td>
                </tr>`;
            return;
        }

        // 4. Render Table Rows
        samples.forEach(sample => {
            const tubeInfo = sample.category ? sample.category.category_name : `Tube #${sample.id}`;
            const collectDate = new Date(sample.collection_date).toLocaleString([], {
                month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
            });

            sample.items.forEach(item => {
                const tr = document.createElement("tr");
                tr.className = "align-middle";
                tr.innerHTML = `
                    <td>
                        <div class="d-flex flex-column">
                            <span class="fw-bold text-dark">${item.test.name}</span>
                            <small class="text-muted" style="font-size: 0.7rem;">ID: ${item.id}</small>
                        </div>
                    </td>
                    <td>
                        <span class="badge bg-soft-primary text-primary border border-primary-subtle">
                            <i class="ti ti-test-pipe me-1"></i>${tubeInfo}
                        </span>
                    </td>
                    <td><small class="text-muted">${collectDate}</small></td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-outline-danger border-0" 
                                onclick="deleteSample(${sample.id}, ${appointmentId})">
                            <i class="ti ti-trash"></i>
                        </button>
                    </td>
                `;
                body.appendChild(tr);
            });
        });

    } catch (error) {
        console.error("Error fetching samples:", error);
        body.innerHTML = `<tr><td colspan="4" class="text-center py-4 text-danger">Error loading data.</td></tr>`;
    }
};

window.deleteSample = async function(sampleId, appointmentId) {
    if (!confirm("Are you sure? This will unlink all associated tests and set them back to 'Awaiting Sample'.")) return;

    try {
        const response = await fetch(`/api/v1/samples/${sampleId}`, { method: 'DELETE' });
        if (!response.ok) throw new Error("Failed to delete sample");
        
        // Refresh the list inside the modal
        openManageSamplesModal(appointmentId);
        // Also refresh the background queue if needed
        if (typeof fetchQueue === 'function') fetchQueue(); 
    } catch (error) {
        // alert(error.message);
        showToast(error.message || "Failed to delete sample. Trya again", "error")
    }

};


// mark samples collection as complete
// Add this to your main script file
window.finalizeCollection = async function() {
    console.log("Finalize triggered for Phleb ID:", currentPhlebId); // Debugging line

    if (!currentPhlebId) {
        // alert("No active collection session found to finalize.");
        showToast("No active collection session found to finalize.", "error")
        return;
    }

    const confirmAction = confirm("Are you sure you want to finalize? This moves tests to the Laboratory and clears this patient from your queue.");
    if (!confirmAction) return;

    try {
        const res = await fetch(`/api/v1/samples/phlebotomy/${currentPhlebId}/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await res.json();

        if (res.ok) {
            // 1. Hide the modal
            const modalEl = document.getElementById("manageSamplesModal");
            const modalInstance = bootstrap.Modal.getInstance(modalEl);
            if (modalInstance) modalInstance.hide();

            // 2. Refresh your main queue
            if (typeof fetchQueue === 'function') {
                await fetchQueue();
            } else {
                window.location.reload(); // Fallback
            }
            
            // alert("Success: Samples sent to Laboratory.");
            showToast("Samples sent to Laboratory", "success");
        } else {
            // Handle the "missing samples" error from FastAPI
            // alert(`⚠️ Error: ${data.detail || "Unable to finalize"}`);
            showToast("Unable to finalize.", "error")
        }
    } catch (err) {
        // console.error("Finalize Error:", err);
        // alert("A network error occurred. Check the console.");
        showToast(err.message, "error")
    }
};


// // DOM ELEMENTS
// const phlebotomyContainerEl = document.querySelector(".phlebotomy__container");


// let phlebotomyURL = `/api/v1/phlebotomy/pending`;

// (async function init() {
//   const res = await getRemoteData(phlebotomyURL);
//   console.log(res)
// //   totalNumOfAppointments = res.length;
//   render(res);
// })();

// /**
//  * Fetch all data
//  * @returns Array[objects]
//  */
// async function getRemoteData(url) {
//   try {
//     const res = await fetch(url);
//     if (!res.ok) throw new Error("Failed to fetch data");
//     const data = await res.json();
//     return data;
//   } catch (error) {
//     alert(error);
//   }
// }



// /**
//  * Render a lsit of object as html elements and display in DOM
//  * @param {Array[Object]} phlebotomy
//  */
// function render(phlebotomyList) {
//   // render patients data into html and join the results into an html string
//   const renderedHTML = phlebotomyList
//     .map((phlebotomy) => {
//       return renderData(phlebotomy);
//     })
//     .join("");

//   // insert data into DOM
//   phlebotomyContainerEl.innerHTML = renderedHTML;
// }



// /**
//  * Renders the patient data into html.
//  * @param {Map} patient
//  * @returns htmlement
//  */
// function renderData(phlebotomy) {
//   const htmlElement = ` 
//   <tr>
//         <td>
//             <div class="form-check form-check-md">
//                 <input class="form-check-input" type="checkbox">
//           </div>
//       </td>
//         <td><a href="javascript:void(0);" data-bs-toggle="modal" data-bs-target="#view_modal">${phlebotomy.appointment.patient.patient_no}</a></td>
//         <td>${phlebotomy.appointment.patient.first_name} ${phlebotomy.appointment.patient.surname}</td>
//         <td>${formatDate(phlebotomy.created_at)}</td>
//         <td>${phlebotomy.collection_site}</td>
//         <td><span class="badge badge-md badge-soft-success border border-success text-success">${phlebotomy.status}</span></td>
//         <td class="text-end">
//             <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown"><i class="ti ti-dots-vertical"></i></a>
//             <ul class="dropdown-menu p-2">
//                 <li>
//                     <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center" data-bs-toggle="modal" data-bs-target="#view_modal" onclick="openDetailSamplesModal(${phlebotomy.id})"><i class="ti ti-eye me-1"></i>View Details</a>
//               </li>
//                 <li>
//                     <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center" data-bs-toggle="modal" data-bs-target="#addSamplesModal" onclick="openSampleModal(${phlebotomy.id}, ${phlebotomy.appointment.id}, ${phlebotomy.appointment.patient.id})"><i class="ti ti-edit me-1"></i>Add Sample</a>
//               </li>
//                 <li>
//                     <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center" data-bs-toggle="modal" data-bs-target="#delete_modal"><i class="ti ti-trash me-1"></i>Delete</a>
//               </li>
//           </ul>
//       </td>
//   </tr>
    
//   `;

//   return htmlElement;
// }



// function formatDate(dateStr) {
//   // "2026-01-13" → "13 Jan, 2026"
//   const date = new Date(dateStr);
//   return date.toLocaleDateString("en-GB", {
//     day: "2-digit",
//     month: "short",
//     year: "numeric",
//   });
// }




// async function openDetailSamplesModal(phlebotomyId) {

//     const container = document.getElementById("samplesContainer");

//     container.innerHTML = `
//         <div class="text-center py-4">
//             <span class="text-muted">Loading samples...</span>
//         </div>
//     `;

//     const modal = new bootstrap.Modal(
//         document.getElementById("viewSamplesModal")
//     );

//     modal.show();

//     try {
//         const response = await fetch(
//             `/api/v1/phlebotomy/${phlebotomyId}/samples/`
//         );

//         if (!response.ok) {
//             throw new Error("Failed to fetch samples");
//         }

//         const samples = await response.json();

//         if (samples.length === 0) {
//             container.innerHTML = `
//                 <div class="text-center py-4 text-muted">
//                     No samples added yet.
//                 </div>
//             `;
//             return;
//         }

//         let tableHTML = `
//             <table class="table table-bordered table-sm align-middle">
//                 <thead class="table-light">
//                     <tr>
//                         <th>Sample Type</th>
//                         <th>Test</th>
//                         <th>Priority</th>
//                         <th>Storage</th>
//                         <th>Condition</th>
//                         <th>Action</th>
//                     </tr>
//                 </thead>
//                 <tbody>
//         `;

//         samples.forEach(sample => {

//             if (!sample.tests || sample.tests.length === 0) {

//                 // tableHTML += `
//                 //     <tr>
//                 //         <td>${sample.sample_type}</td>
//                 //         <td class="text-muted">No tests</td>
//                 //         <td>${sample.priority ?? '-'}</td>
//                 //         <td>${sample.storage_location ?? '-'}</td>
//                 //         <td>${sample.sample_condition ?? '-'}</td>
//                 //         <td>-</td>
//                 //     </tr>
//                 // `;

//                 // continue

//             } else {

//                 sample.tests.forEach(test => {
//                     tableHTML += `
//                         <tr>
//                             <td>${sample.sample_type}</td>
//                             <td>${test.name}</td>
//                             <td>${sample.priority ?? '-'}</td>
//                             <td>${sample.storage_location ?? '-'}</td>
//                             <td>${sample.sample_condition ?? '-'}</td>
//                             <td>
//                                 <button class="btn btn-sm btn-danger"
//                                     onclick="deleteSampleTest(${test.sample_test_id}, ${phlebotomyId})">
//                                     Remove
//                                 </button>
//                             </td>
//                         </tr>
//                     `;
//                 });

//             }
//         });

//         tableHTML += `</tbody></table>`;
//         container.innerHTML = tableHTML;

//     } catch (error) {
//         container.innerHTML = `
//             <div class="text-danger text-center py-4">
//                 Error loading samples.
//             </div>
//         `;
//         console.error(error);
//     }
// }





// async function deleteSampleTest(sampleTestId, phlebotomyId) {

//     if (!confirm("Are you sure you want to remove this test from the sample?")) {
//         return;
//     }

//     try {
//         const response = await fetch(
//             `/api/v1/phlebotomy/sample-tests/${sampleTestId}`,
//             {
//                 method: "DELETE"
//             }
//         );

//         if (!response.ok) {
//             alert("Failed to remove test");
//             return;
//         }

//         // Reload modal content correctly
//         openDetailSamplesModal(phlebotomyId);

//     } catch (error) {
//         console.error(error);
//         alert("Error removing test");
//     }
// }