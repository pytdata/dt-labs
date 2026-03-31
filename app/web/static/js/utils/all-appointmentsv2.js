// SEARCH INPUTS
const searchBacterialTestEl = document.querySelector(".search__bact");
const searchChemTestEl = document.querySelector(".search__chem");
const catSelectEl = document.querySelector(".test__cat__type");
const searchStaff = document.querySelector(".staff__search");
const patientSearch = document.querySelector(".search__patient");
const statusFilter = document.querySelectorAll(".filter__status");

// TABLES / VIEWS
const appointmentsTableEL = document.querySelector(".appointments__table");
const testTableVisibilityEl = document.querySelector(".is_cat_table_hidden");
const bacterialTestDivEl = document.querySelector("#bacteria-test");
const chemistryTestDivEl = document.querySelector("#chemistry-test");

// TOTAL PRICE
const totalPriceEL = document.querySelector(".total__price");
let totalSelectedPrice = 0;
// ACCORDION
const selectedTestAccordionListEl = document.querySelector(
  ".selected__accordion",
);

// SEARCH RESULTS
const bacteriaSearchResultsEl = document.querySelector(".bac__search__results");
const chemSearchResultsEl = document.querySelector(".chem__search__results");

// FORM
const appointmentForm = document.querySelector("#appointmentForm");
const addSampleForm = document.querySelector("#addSample");
const addSampleCategoryForm = document.querySelector("#sampleCategoryForm")

let totalNumOfAppointments = 0;
let searchTimeout = null;
let activeController = null;

let testCategoriesURL = "/api/v1/test-categories";
let appointmentsURL = "/api/v1/appointments/";

// Form data
const selectedTests = {
  bacteriology: [],
  chemistry: [],
};

// selected test data for required tests
let selectedTestForSample = [];
let selectedTestOrderList = [];


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



function showFeedback({ title, message, type = 'success', redirectUrl = null }) {
    // 1. COMPLETELY PURGE existing modal states
    // This stops the 'ghost' overlay by removing Bootstrap's internal tracking
    const existingModalEl = document.getElementById('feedbackModal');
    if (existingModalEl) {
        const existingInstance = bootstrap.Modal.getInstance(existingModalEl);
        if (existingInstance) {
            existingInstance.dispose(); // Properly destroy the JS instance
        }
    }

    // 2. FORCIBLY CLEANUP DOM artifacts
    document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
    
    const modalEl = document.getElementById('feedbackModal');
    if (!modalEl) {
        alert(`${title}: ${message}`);
        if (redirectUrl) window.location.href = redirectUrl;
        return;
    }

    // 3. Prepare content
    const titleEl = document.getElementById('feedbackTitle');
    const messageEl = document.getElementById('feedbackMessage');
    const iconContainer = document.getElementById('feedbackIconContainer');
    const closeBtn = document.getElementById('feedbackCloseBtn');

    if (titleEl) titleEl.innerText = title;
    if (messageEl) messageEl.innerText = message;

    if (iconContainer && closeBtn) {
        if (type === 'success') {
            iconContainer.innerHTML = `<div class="bg-light-success text-success rounded-circle d-inline-flex align-items-center justify-content-center" style="width: 70px; height: 70px; font-size: 2rem;"><i class="ti ti-circle-check"></i></div>`;
            closeBtn.className = 'btn btn-success w-100';
            closeBtn.innerText = 'Continue';
        } else {
            iconContainer.innerHTML = `<div class="bg-light-danger text-danger rounded-circle d-inline-flex align-items-center justify-content-center" style="width: 70px; height: 70px; font-size: 2rem;"><i class="ti ti-alert-circle"></i></div>`;
            closeBtn.className = 'btn btn-danger w-100';
            closeBtn.innerText = 'Dismiss';
        }
    }

    // 4. Initialize and show with a slight delay
    // The 10ms delay ensures the DOM cleanup above finishes before BS adds a new backdrop
    setTimeout(() => {
        const modal = new bootstrap.Modal(modalEl, {
            backdrop: 'static', // Prevents closing by clicking outside during feedback
            keyboard: false
        });
        
        modal.show();

        // Adjust z-index once shown
        modalEl.addEventListener('shown.bs.modal', () => {
            const backdrop = document.querySelector('.modal-backdrop:last-child');
            if (backdrop) backdrop.style.zIndex = '2040'; 
            modalEl.style.zIndex = '2050'; 
        }, { once: true });

        // Handle Redirection/Reloading
        if (redirectUrl) {
            modalEl.addEventListener('hidden.bs.modal', () => { 
                window.location.href = redirectUrl; 
            }, { once: true });
        }
    }, 10);
}


// (async function init() {
//   const res = await getRemoteData(appointmentsURL);
//   totalNumOfAppointments = res.length;
//   render(res);
// })();

catSelectEl.addEventListener("input", (e) => {
  const [id, catName] = e.target.value.split(",").map((v) => v.trim());

  testTableVisibilityEl.style.display = "block";

  console.log(id, catName);

  if (catName.toLowerCase() === "radiology") {
    bacterialTestDivEl.classList.remove("bac__hidden");
    bacterialTestDivEl.classList.add("bac__visible");
  }

  if (catName.toLowerCase() === "laboratory investigations") {
    chemistryTestDivEl.classList.remove("chem__hidden");
    chemistryTestDivEl.classList.add("chem__visible");
  }

  buildDynamicURLParam("test_category_type", Number(id));
});

searchBacterialTestEl.addEventListener("input", (e) => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(async () => {
    const value = e.target.value;
    buildDynamicURLParam("name", value);
    const data = await performSearch(value);
    renderBacteriaSearchResults(data);
  }, 300);
});

searchChemTestEl.addEventListener("input", (e) => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(async () => {
    const value = e.target.value;
    buildDynamicURLParam("name", value);
    const data = await performSearch(value);
    renderChemistrySearchResults(data);
  }, 300);
});

bacteriaSearchResultsEl.addEventListener("change", (e) => {
  const checkbox = e.target.closest(".bac__option");
  if (!checkbox) return;

  const id = Number(checkbox.dataset.bacId);
  const price = Number(checkbox.dataset.bacPrice);
  const name = checkbox.dataset.bacName;

  if (checkbox.checked) {
    selectedTests.bacteriology.push(id);
    selectedTestOrderList.push({ id, price, name });
  } else {
    selectedTests.bacteriology = selectedTests.bacteriology.filter(
      (x) => x !== id,
    );

    selectedTestOrderList = selectedTestOrderList.filter((x) => x.id !== id);
  }

  computeTotalPrice(selectedTestOrderList);
  accordionListRender(selectedTestOrderList);
});

chemSearchResultsEl.addEventListener("change", (e) => {
  const checkbox = e.target.closest(".chem_option");
  if (!checkbox) return;

  const id = Number(checkbox.dataset.chemId);
  const price = Number(checkbox.dataset.chemPrice);
  const name = checkbox.dataset.chemName;

  if (checkbox.checked) {
    selectedTests.chemistry.push(id);
    selectedTestOrderList.push({ id, price, name });
  } else {
    selectedTests.chemistry = selectedTests.chemistry.filter((x) => x !== id);

    selectedTestOrderList = selectedTestOrderList.filter((x) => x.id !== id);
  }

  computeTotalPrice(selectedTestOrderList);
  accordionListRender(selectedTestOrderList);
});


appointmentForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  // 1. Loading State: Disable button and show spinner
  const submitBtn = appointmentForm.querySelector('button[type="submit"]');
  const originalBtnText = submitBtn.innerHTML;
  
  submitBtn.disabled = true;
  submitBtn.innerHTML = `
    <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
    Booking...
  `;

  const formData = new FormData(appointmentForm);
  const payload = {
    patient_id: Number(formData.get("patient_id")),
    doctor_id: Number(formData.get("staff_id")),
    notes: formData.get("notes"),
    mode_of_payment: formData.get("payment_mode"),
    total_price: Number(totalSelectedPrice),
    test_ids: [...new Set([...selectedTests.bacteriology, ...selectedTests.chemistry])],
  };

  try {
    const res = await fetch("/api/v1/appointments/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Server error occurred");
    }

    // 2. Success Path: Close Modal and show Toast
    const addModalEl = document.getElementById('add_modal');
    const modalInstance = bootstrap.Modal.getInstance(addModalEl);
    if (modalInstance) modalInstance.hide();

    showToast("Appointment successfully created!", "success");

    // 3. Reset Local State & Form
    selectedTests["bacteriology"] = [];
    selectedTests["chemistry"] = [];
    totalSelectedPrice = 0;
    appointmentForm.reset();

    // 4. Page Reload: Wait 2 seconds so they can read the toast
    setTimeout(() => {
        location.reload(); 
    }, 2000);

  } catch (error) {
    console.error("Submission Error:", error);
    // Show error toast - no reload needed so they can fix the form
    showToast(error.message || "Appointment creation failed.", "error");
    
    // Re-enable button so they can try again
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalBtnText;
  }
  // Note: We don't use 'finally' here because if successful, 
  // the page reloads, and if failed, we re-enable in the catch block.
});


// TODO: DONE show appointment details
appointmentsTableEL.addEventListener("click", async (e) => {
  const button = e.target.closest(".view__appointment__btn");
  if (!button) return;

  const appointmentId = button.dataset.appointmentid;

  try {
    const res = await fetch(`/api/v1/appointments/${appointmentId}/`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) throw new Error("Failed to fetch appointment");
    
    const appointment = await res.json();
    populateAppointmentDetailModal(appointment);

  } catch (error) {
    console.error(error);

     showToast(error.message || "Failed to load appointment details.", "error");
    
    // REPLACED ALERT WITH MODAL
    // showFeedback({ 
    //   title: "Error", 
    //   message: "Failed to load appointment details. Please try again.", 
    //   type: 'error' 
    // });
  }
});


// TODO: DONE show edit appointment form with requested data
appointmentsTableEL.addEventListener("click", async (e) => {
  const button = e.target.closest(".edit__appointment__btn");
  if (!button) return;

  const appointmentId = button.dataset.appointmentid;

  try {
    const res = await fetch(`/api/v1/appointments/${appointmentId}/`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    
    if (!res.ok) throw new Error("Failed to fetch appointment");
    
    const appointment = await res.json();
    console.log("DEBUG: appointment detail", appointment);

    populateEditModal(appointment);

  } catch (error) {
    console.error(error);
    
    showToast(error.message || "Failed to load appointment details for editing.", "error");
    // REPLACED ALERT WITH MODAL
    // showFeedback({ 
    //   title: "Error", 
    //   message: "Failed to load appointment details for editing. Please try again.", 
    //   type: 'error' 
    // });
  }
});


// TODO: DONE submit the edit made to the appointment
document.querySelector(".edit__appointment__form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const appointmentId = form.dataset.appointmentId;

    const payload = {
        patient_id: document.getElementById("edit_patient").value,
        doctor_id: document.getElementById("edit_staff").value,
        appointment_at: document.getElementById("edit_appointment_at").value,
        start_time: document.getElementById("edit_start_time").value,
        end_time: document.getElementById("edit_end_time").value,
        notes: document.getElementById("edit_note").value,
        status: document.getElementById("edit_status").value,
        mode_of_payment: document.getElementById("edit_mode_of_payment").value,
        test_ids: currentSelectedTests.map(t => t.id) 
    };

    try {
        const res = await fetch(`/api/v1/appointments/${appointmentId}/`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (res.ok) {
            // 1. Hide the Edit Modal
            const editModalEl = document.getElementById('edit_modal');
            const modalInstance = bootstrap.Modal.getInstance(editModalEl);
            if (modalInstance) modalInstance.hide();

            // 2. Show the Toast
            showToast("Appointment updated successfully!", "success");

            // 3. Optional: Reload or refresh the table data
            setTimeout(() => {
                location.reload(); 
            }, 1500); // Small delay so they can actually read the toast
        } else {
            showToast("Failed to update appointment.", "error");
        }
    } catch (error) {
        console.error("Update Error:", error);
        showToast("Network error. Please try again.", "error");
    }
});


// update appointment status
document
  .querySelector("#status__container")
  .addEventListener("click", async (e) => {
    e.preventDefault();

    const button = e.target.closest(".status__updater");
    if (!button) return;

    const status = button.dataset.status;
    const appointmentId = Number(button.dataset.appointmentId);

    const payload = { status: status };

    try {
      const res = await fetch(`/api/v1/appointments/${appointmentId}/`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Failed to update appointment status");

      const data = await res.json();
      populateAppointmentDetailModal(data);

      // REPLACED ALERT WITH SUCCESS MODAL
      // showFeedback({
      //   title: "Status Updated",
      //   message: `The appointment has been successfully marked as ${status.replace('_', ' ')}.`,
      //   type: 'success'
      // });

      showToast(`The appointment has been successfully marked as ${status.replace('_', ' ')}.`, "success");

    } catch (error) {
      console.error(error);
      showToast(error.message || "Could not update the appointment status. Please try again.", "error")
      // showFeedback({
      //   title: "Update Error",
      //   message: "Could not update the appointment status. Please try again.",
      //   type: 'error'
      // });
    }
  });

// delete appointment - setting the ID for the confirmation modal
appointmentsTableEL.addEventListener("click", async (e) => {
  const button = e.target.closest(".delete__appointment__btn");
  if (!button) return;

  const appointmentId = button.dataset.appointmentid;
  document.querySelector(".delete__appointment").dataset.appointmentid = appointmentId;
});

// delete appointment - actual execution
document
  .querySelector(".delete__appointment")
  .addEventListener("click", async (e) => {
    e.preventDefault();
    const button = e.target;
    if (!button) return;

    const appointmentId = button.dataset.appointmentid;

    try {
      const res = await fetch(`/api/v1/appointments/${appointmentId}/`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
      });

      if (!res.ok) throw new Error("Failed to delete appointment");

      // REPLACED ALERT WITH SUCCESS MODAL + RELOAD
      // showFeedback({
      //   title: "Deleted",
      //   message: "The appointment record has been permanently removed.",
      //   type: 'success',
      //   redirectUrl: window.location.href // Refresh the table list
      // });

      showToast("The appointment record has been permanently removed.", "success");

    } catch (error) {
      console.error(error);
      // REPLACED ALERT(error) WITH MODAL
      showToast(error.message || "An error occurred while trying to delete the record. Try again","error");
      // showFeedback({
      //   title: "Deletion Failed",
      //   message: "An error occurred while trying to delete the record.",
      //   type: 'error'
      // });
    }
  });





// TODO: DONE
// Get appointment data for sample
appointmentsTableEL.addEventListener("click", async (e) => {
  const button = e.target.closest(".add__sample__btn");
  if (!button) return;

  const appointmentId = +button.dataset.appointmentid;

  // fetch appointment data
  try {
    const res = await fetch(`/api/v1/appointments/${appointmentId}/`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    
    if (!res.ok) throw new Error("Failed to fetch appointment");
    
    const appointment = await res.json();
    console.log(appointment);

    populateAddSampleModal(
      appointment.tests,
      appointment.id,
      appointment.patient.id,
    );

    // Listen to event on the checkbox to populate selectedTestForSample
    document
      .querySelector("#test__requested")
      .addEventListener("click", (e) => {
        let selectedInputEl = e.target.closest(".test__required__choice");
        if (!selectedInputEl) return;

        let inputValue = Number(selectedInputEl.value);

        if (selectedTestForSample.includes(inputValue)) {
          selectedTestForSample = selectedTestForSample.filter(
            (e) => e !== inputValue,
          );
        } else {
          selectedTestForSample.push(inputValue);
        }
      });
      
  } catch (error) {
    console.error(error);
    // REPLACED ALERT WITH MODAL
    // showFeedback({
    //   title: "Loading Error",
    //   message: "Could not retrieve appointment tests. Please try again.",
    //   type: 'error'
    // });
    showToast("Could not retrieve appointment tests. Please try again", "error")
  }
});

// add sample
addSampleForm.addEventListener("submit", async function (e) {
  e.preventDefault();

  // Basic validation: ensure at least one test is selected
  if (selectedTestForSample.length === 0) {
    showToast("Please select at least one test for this sample");
    // showFeedback({
    //   title: "Selection Required",
    //   message: "Please select at least one test for this sample."
    // });
    return;
  }

  const formData = new FormData(addSampleForm);
  const patientId = this.dataset.patientId;
  const appointmentId = this.dataset.appointmentId;

  const payload = {
    patient_id: +patientId,
    appointment_id: +appointmentId,
    sample_type: +formData.get("add__sample__categories"),
    test_requested: [...selectedTestForSample],
    priority: formData.get("add__priority"),
    storage_location: formData.get("add__storage__location"),
    collection_site: formData.get("add__collection__site"),
    sample_condition: formData.get("add__sample__condition"),
  };

  try {
    const res = await fetch("/api/v1/samples/", {
      headers: { "Content-Type": "application/json" },
      method: "POST",
      body: JSON.stringify(payload),
    });

   if (res.ok) {
            // 1. Hide the Add Sample Modal
            const sampleModalEl = document.getElementById('add_sample_modal');
            const sampleModalInstance = bootstrap.Modal.getInstance(sampleModalEl);
            if (sampleModalInstance) sampleModalInstance.hide();

            // 2. Show Success
            // showFeedback({
            //     title: "Sample Recorded",
            //     message: "The lab sample has been successfully added.",
            //     type: 'success'
            // });
            showToast("The lab sample has been successfully added", "success")

            addSampleForm.reset();
            selectedTestForSample = [];
        } else {
            throw new Error("Failed to post sample");
        }
    } catch (error) {
        // showFeedback({ title: "Error", message: "Could not save sample.", type: 'error' });
        showToast("Could not save sample", "error")
    }
});



// TODO: DONE
// Add new sample category
addSampleCategoryForm.addEventListener("submit", async function(e) {
  e.preventDefault();

  const formData = new FormData(addSampleCategoryForm);
  const payload =  {
    category_name: formData.get("sample_name")
  };
  
  try {
    const res = await fetch("/api/v1/samples/sample-categories/", {
      headers: { "Content-Type": "application/json" },
      method: "POST",
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error("Failed to save sample category");

    const data = await res.json();
    console.log(data);

    // SUCCESS MODAL + RELOAD
    // showFeedback({
    //   title: "Category Created",
    //   message: "New sample category has been added successfully.",
    //   type: 'success',
    //   redirectUrl: window.location.href 
    // });

    showToast("New sample category has been added successfully", "success");

  } catch (error) {
    console.error(error);
    showToast(error.message || "An error occurred while saving the new category. Please try again.", "error")
    // showFeedback({
    //   title: "Creation Failed",
    //   message: "An error occurred while saving the new category.",
    //   type: 'error'
    // });
  }

  addSampleCategoryForm.reset();
});

// Search patients by staff
searchStaff.addEventListener("input", (e) => {
  clearTimeout(searchTimeout);

  searchTimeout = setTimeout(async () => {
    try {
      let value = e.target.value;
      buildAppointmentDynamicURLParam("doctor", value);
      const data = await performSearch(value, true);
      renderStaffSearchResults(data);
    } catch (error) {
      console.error("Staff search error:", error);
      // Optional: showFeedback here if you want to notify of search failures
      showToast("An error was encountered while searching. Please try again", "error")
    }
  }, 300); // Added slight delay for better performance
});

// Search patients by patient name
patientSearch.addEventListener("input", (e) => {
  clearTimeout(searchTimeout);

  searchTimeout = setTimeout(async () => {
    try {
      let value = e.target.value;
      buildAppointmentDynamicURLParam("patient", value);
      const data = await performSearch(value, true);
      renderPatientsSearchResults(data);
    } catch (error) {
      console.error("Patient search error:", error);
    }
  }, 300);
});

// FILTERING BY STATUS
statusFilter.forEach((statusOption) =>
  statusOption.addEventListener("change", async (e) => {
    try {
      buildAppointmentDynamicURLParam(
        "status",
        e.currentTarget.dataset.status,
        e.currentTarget.checked,
      );

      const data = await getRemoteData(appointmentsURL);
      render(data);
    } catch (error) {
      console.error("Filter error:", error);
      // showFeedback({
      //   title: "Filter Error",
      //   message: "Could not refresh the list with the selected filters.",
      //   type: 'error'
      // });

      showToast("Could not refresh the list with the selected filter", "error")
    }
  }),
);




/**
 * render patient search results (search by patient name)
 * @param {object} data
 */
function renderPatientsSearchResults(data) {
  const searchResultsHTML = data
    .map((appointment) => {
      const htmlElement = `
            <li>
              <label class="dropdown-item px-2 d-flex align-items-center rounded-1">
                  <input class="form-check-input m-0 me-2" type="checkbox">
                  <span class="avatar avatar-xs rounded-circle me-2"><img src="/static/img/doctors/doctor-01.jpg" class="flex-shrink-0 rounded" alt="img"></span>${appointment.patient.first_name} ${appointment.patient.other_names ? appointment.patient.other_names : ""} ${appointment.patient.surname}
              </label>
          </li>
        `;
      return htmlElement;
    })
    .join("");

  const resultUlEl = document.querySelector(".patient__search__results");

  // Remove all li elements except the first one (search input)
  while (resultUlEl.children.length > 1) {
    resultUlEl.removeChild(resultUlEl.children[1]);
  }

  // Insert new results after the first li
  resultUlEl.insertAdjacentHTML("beforeend", searchResultsHTML);
}

/**
 * render patient search results (search by staff name)
 * @param {object} data
 */
function renderStaffSearchResults(data) {
  const searchResultsHTML = data
    .map((appointment) => {
      const htmlElement = `
            <li>
              <label class="dropdown-item px-2 d-flex align-items-center rounded-1">
                  <input class="form-check-input m-0 me-2" type="checkbox">
                  <span class="avatar avatar-xs rounded-circle me-2"><img src="/static/img/doctors/doctor-01.jpg" class="flex-shrink-0 rounded" alt="img"></span>${appointment.doctor.full_name}
              </label>
          </li>
        `;
      return htmlElement;
    })
    .join("");

  const resultUlEl = document.querySelector(".staff__search__results");

  // Remove all li elements except the first one (search input)
  while (resultUlEl.children.length > 1) {
    resultUlEl.removeChild(resultUlEl.children[1]);
  }

  // Insert new results after the first li
  resultUlEl.insertAdjacentHTML("beforeend", searchResultsHTML);
}

// implement the refresh button functionality
document.querySelector(".ti-refresh").addEventListener("click", async (e) => {
  const data = await getRemoteData(appointmentsURL);
  render(data);
});

/**
 * Renders a list of test request in the browser
 * @param {Array[object]} samples
 * @param {Number} appointmentId
 * @param {Number} patientId
 */
function populateAddSampleModal(samples, appointmentId, patientId) {
  console.log("status update: ", samples);
  const requestedTestsHTML = samples
    .map((sample) => {
      return `
    <li class="list-group-item">
        <input class="form-check-input me-1 test__required__choice" type="checkbox" value="${sample.id}" data-name="${sample.name}">
        ${sample.name}
    </li>
    `;
    })
    .join("");

  document.getElementById("test__requested").innerHTML = requestedTestsHTML;
  document.querySelector("#add_sample_modal form").dataset.appointmentId =
    appointmentId;
  document.querySelector("#add_sample_modal form").dataset.patientId =
    patientId;
}

/**
 * Fetch all test-categories data
 * @returns Array[objects]
 */
async function getRemoteData(url) {
  const res = await fetch(url);
  const data = await res.json();
  return data;
}


/**
 * Render a list of objects as html elements and display in DOM
 * @param {Array[Object]} appointmentsList
 */
window.render = function(appointmentsList) {
    const tableSelector = '.datatable';
    
    // 1. Safety check for jQuery and DataTables
    if (!window.jQuery || !$.fn.DataTable) {
        setTimeout(() => window.render(appointmentsList), 100);
        return;
    }

    const $table = $(tableSelector);

    // 2. Destroy existing instance if it exists to prevent "Re-initialization" errors
    if ($.fn.DataTable.isDataTable(tableSelector)) {
        $table.DataTable().clear().destroy();
    }

    // 3. Inject Rows into the DOM
    const tbody = document.querySelector(".appointments__table");
    if (tbody) {
        // Handle empty state gracefully
        if (appointmentsList.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" class="text-center py-4">No records found for the selected range.</td></tr>';
            return; 
        }
        tbody.innerHTML = appointmentsList.map(app => renderData(app)).join("");
    }

    // 4. Initialize DataTable with Export Buttons
    // We explicitly name the buttons so our custom triggers work
    const table = $table.DataTable({
        dom: 'Bfrtip', 
        pageLength: 10,
        buttons: [
            {
                extend: 'excelHtml5',
                className: 'buttons-excel d-none', // Added explicit class name here
                title: 'Appointments_Report_' + new Date().toISOString().slice(0, 10),
                exportOptions: { columns: ':visible:not(:last-child)' } 
            },
            {
                extend: 'pdfHtml5',
                className: 'buttons-pdf d-none', // Added explicit class name here
                title: 'Appointments_Report',
                orientation: 'landscape',
                pageSize: 'A4',
                exportOptions: { columns: ':visible:not(:last-child)' }
            }
        ],
        language: {
            search: " ",
            searchPlaceholder: "Search records...",
            paginate: {
                next: '<i class="ti ti-chevron-right"></i>',
                previous: '<i class="ti ti-chevron-left"></i>'
            }
        }
    });

    // 5. Link Custom UI Buttons to DataTable Actions
    // .off('click') is crucial to prevent multiple downloads if render is called again
    $('.export-excel').off('click').on('click', function(e) {
        e.preventDefault();
        table.button('.buttons-excel').trigger();
    });

    $('.export-pdf').off('click').on('click', function(e) {
        e.preventDefault();
        table.button('.buttons-pdf').trigger();
    });

    console.log("DataTable Rendered with " + appointmentsList.length + " records.");
};


/**
 * Renders the patient data into html.
 * @param {Map} patient
 * @returns htmlement
 */
function renderData(appointment) {
  console.log("Appointment information: ===", appointment)
  // Extract invoice ID safely
  const invoiceId = appointment.invoice ? appointment.invoice.id : null;
  const isPaid = appointment.invoice && appointment.invoice.status === 'paid';

  const htmlElement = ` <tr>
        <td>
            <div class="form-check form-check-md">
                <input class="form-check-input" type="checkbox">
            </div>
        </td>
        <td><a href="javascript:void(0);" data-bs-toggle="modal" data-bs-target="#view_modal">${
          appointment.display_id
        }</a></td>
        <td>
            <div class="d-flex align-items-center">
                <a href="patient-details.html" class="avatar avatar-xs me-2">
                    <img src="${appointment.patient.profile_image}" alt="img" class="rounded">
                </a>
                <div>
                    <h6 class="fs-14 mb-0 fw-medium"><a href="patient-details.html">${
                      appointment.patient.first_name
                    } ${
                      appointment.patient.other_names
                        ? appointment.patient.other_names
                        : ""
                    } ${appointment.patient.surname}</a></h6>
                </div>
            </div>
        </td>
        <td>
            <div class="d-flex align-items-center">
                <a href="doctor-details.html" class="avatar avatar-xs me-2">
                    <img src="${appointment.doctor.avatar}" alt="img" class="rounded">
                </a>
                <div>
                    <h6 class="fs-14 mb-0 fw-medium"><a href="doctor-details.html">Dr. ${
                      appointment.doctor.full_name
                    }</a></h6>
                </div>
            </div>
        </td>
       
        <td>${formatDate(appointment.appointment_at)}, ${formatTime(appointment.start_time)}</td>
        ${
          appointment.status == "completed"
            ? `<td><span class="badge badge-soft-success border border-success text-success py-1 ps-1 d-inline-flex align-items-center"><i class="ti ti-point-filled me-0 fs-14"></i>Completed</span></td>`
            : appointment.status == "upcoming"
              ? `<td><span class="badge badge-soft-info border border-info text-info py-1 ps-1 d-inline-flex align-items-center"><i class="ti ti-point-filled me-0 fs-14"></i>Upcoming</span></td>`
              : appointment.status == "cancelled"
                ? `<td><span class="badge badge-soft-danger border border-danger text-danger py-1 ps-1 d-inline-flex align-items-center"><i class="ti ti-point-filled me-0 fs-14"></i>Cancelled</span></td>`
                : `<td><span class="badge badge-soft-warning border border-warning text-warning py-1 ps-1 d-inline-flex align-items-center"><i class="ti ti-point-filled me-0 fs-14"></i>In Progress</span></td>`
        }
        <td class="text-end">
            <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown"><i class="ti ti-dots-vertical"></i></a>
            <ul class="dropdown-menu p-2">
                <li>
                    <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center pay__appointment__btn" 
                       data-bs-toggle="modal" data-bs-target="#paymentModal" 
                       data-invoiceId="${invoiceId}" 
                       data-appointmentId="${appointment.id}">
                       <i class="ti ti-cash me-1"></i>${isPaid ? 'View Billing' : 'Receive Payment'}
                    </a>
                </li>
                <hr class="dropdown-divider">
                <li>
                    <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center add__sample__btn" data-bs-toggle="modal" data-bs-target="#add_sample_modal" data-appointmentId=${appointment.id}><i class="ti ti-plus me-1"></i>Add Sample</a>
                </li>
                <li>
                    <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center view__appointment__btn" data-bs-toggle="modal" data-bs-target="#view_modal" data-appointmentId=${appointment.id}><i class="ti ti-eye me-1"></i>View Details</a>
                </li>
                <li>
                    <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center edit__appointment__btn" data-bs-toggle="modal" data-bs-target="#edit_modal" data-appointmentId=${appointment.id}><i class="ti ti-edit me-1"></i>Edit</a>
                </li>
                <li>
                    <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center delete__appointment__btn" data-appointmentId=${appointment.id} data-bs-toggle="modal" data-bs-target="#delete_modal"><i class="ti ti-trash me-1"></i>Delete</a>
                </li>
            </ul>
        </td>
    </tr>`;

  return htmlElement;
}


document.addEventListener('click', async (e) => {
    const payBtn = e.target.closest('.pay__appointment__btn');
    if (payBtn) {
        // Stop any default behavior
        e.preventDefault();
        
        const appointmentId = payBtn.dataset.appointmentid;
        
        // Populate the modal with a loader while fetching
        document.getElementById('paymentTestList').innerHTML = '<tr><td colspan="3" class="text-center">Loading...</td></tr>';
        
        try {
            const response = await fetch(`/api/v1/appointments/${appointmentId}/`);
            if (!response.ok) throw new Error("Fetch failed");
            
            const appointment = await response.json();
            populatePaymentModal(appointment);
            
            // Note: We don't need modal.show() here because 
            // data-bs-toggle="modal" on the button handles it!
        } catch (error) {
            console.error(error);
            // If it fails, close the modal so the user isn't stuck with an overlay
            const modalEl = document.getElementById('paymentModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
            showToast("Failed to load billing details", "error");
        }
    }
});



/**
 * Populates the Payment Modal with Invoice and Test data.
 */
function populatePaymentModal(appointment) {
    const invoice = appointment.invoice;
    const testListBody = document.getElementById('paymentTestList');
    
    // Safety check: If no invoice exists, we can't process payment
    if (!invoice) {
        showToast("No invoice found for this appointment.", "danger");
        return;
    }

    console.log(`FINDING INVOVICE IN APP>>>>>>>>>>>>>>>>>>:}`,appointment)
    // 1. Set Header Info & Store Invoice ID for the Process button
    document.getElementById('payInvoiceNo').innerText = invoice.invoice_no;
    document.getElementById('payInvoiceNo').dataset.invoiceId = invoice.id; // Store raw ID
    
    document.getElementById('payPatientName').innerText = 
        `${appointment.patient.first_name} ${appointment.patient.other_names || ''} ${appointment.patient.surname}`;
    
    // Use Number() or parseFloat() to ensure these render nicely if they come as strings
    document.getElementById('payTotalAmount').innerText = `GHS ${Number(invoice.total_amount).toFixed(2)}`;
    document.getElementById('payAmountPaid').innerText = `GHS ${Number(invoice.amount_paid).toFixed(2)}`;
    document.getElementById('payBalance').innerText = `GHS ${Number(invoice.balance).toFixed(2)}`;
    
    // 2. Reset the "Select All" checkbox and Amount Input
    const selectAllBox = document.getElementById('selectAllTests');
    if (selectAllBox) selectAllBox.checked = false;
    document.getElementById('payAmountInput').value = "";

    // 3. Clear and populate tests
    testListBody.innerHTML = '';
    
    if (invoice.items && invoice.items.length > 0) {
        invoice.items.forEach(item => {
            const isPaid = item.is_paid;
            
            // We use 'table-success' or 'table-light' for paid items to distinguish them visually
            const rowClass = isPaid ? 'table-light text-muted' : '';
            
            testListBody.innerHTML += `
                <tr class="${rowClass}">
                    <td>
                        <div class="form-check">
                            <input type="checkbox" class="form-check-input test-pay-checkbox" 
                                value="${item.id}" 
                                data-price="${item.unit_price}"
                                ${isPaid ? 'checked disabled' : ''}>
                        </div>
                    </td>
                    <td>
                        <span class="fw-medium">${item.description}</span>
                        ${isPaid ? '<span class="badge badge-soft-success ms-2"><i class="ti ti-check me-1"></i>Paid</span>' : ''}
                    </td>
                    <td class="text-end fw-bold">GHS ${Number(item.unit_price).toFixed(2)}</td>
                </tr>
            `;
        });
    } else {
        testListBody.innerHTML = '<tr><td colspan="3" class="text-center">No tests found on this invoice.</td></tr>';
    }

    // 4. Re-initialize the calculation logic
    updateAmountOnCheck();
}


function updateAmountOnCheck() {
    const checkboxes = document.querySelectorAll('.test-pay-checkbox:not(:disabled)');
    const amountInput = document.getElementById('payAmountInput');
    
    checkboxes.forEach(cb => {
        cb.addEventListener('change', () => {
            let total = 0;
            document.querySelectorAll('.test-pay-checkbox:not(:disabled):checked').forEach(checkedCb => {
                total += parseFloat(checkedCb.dataset.price);
            });
            amountInput.value = total > 0 ? total.toFixed(2) : "";
        });
    });
}


// SELECT ALL TEST 

// Use a delegated event listener or ensure this runs after DOM is loaded
document.getElementById('btnProcessPayment').addEventListener('click', async function() {
    const btn = this;
    const invoiceId = document.getElementById('payInvoiceNo').dataset.invoiceId;
    
    // 1. Get Selected Tests
    const selectedCheckboxes = document.querySelectorAll('.test-pay-checkbox:checked:not(:disabled)');
    const testIdsToClear = Array.from(selectedCheckboxes).map(cb => parseInt(cb.value));

    // 2. Get Payment Details
    const amount = parseFloat(document.getElementById('payAmountInput').value);
    const method = document.getElementById('payMethod').value;

    console.log("Processing Payment for Invoice:", invoiceId);
    console.log("Tests to unlock:", testIdsToClear);
    console.log("Amount:", amount);

    // 3. Simple Validation
    if (!invoiceId) return alert("Invoice ID missing. Please reload.");
    if (isNaN(amount) || amount <= 0) return alert("Please enter a valid amount.");

    try {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';

        const response = await fetch(`/api/v1/billing/${invoiceId}/payments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                amount: amount,
                method: method,
                test_ids_to_clear: testIdsToClear,
                description: "Payment received at desk"
            })
        });

        // const result = await response.json();

        if (response.ok) {
                
            const result = await response.json();
          showToast("Payment Processed!", "success");
          // modal.hide();

          // Instead of a confirm box, just open the print page in a new small window
          // const receiptUrl = `/api/v1/billing/payments/${result.payment_id}/print`;
          // window.open(receiptUrl, 'ReceiptPrint', 'width=600,height=800');
          
          // Refresh the background page to show the "Paid" status
          setTimeout(() => location.reload(), 1000);
              } else {
                  alert("Error: " + (result.detail || "Unknown error"));
                  btn.disabled = false;
                  btn.innerText = "Process Payment";
              }
    } catch (error) {
        console.error("Payment Request Failed:", error);
        showToast("Payment Request Failed", "success");
        // modal.hide();
        btn.disabled = false;
        btn.innerText = "Process Payment";
    }
});


document.getElementById('selectAllTests').addEventListener('change', (e) => {
    const checkboxes = document.querySelectorAll('.test-pay-checkbox:not(:disabled)');
    checkboxes.forEach(cb => {
        cb.checked = e.target.checked;
        cb.dispatchEvent(new Event('change')); // Trigger total calculation
    });
});




function populateAppointmentDetailModal(appointment) {
  console.log("status update: ", appointment);
  document.getElementById("patient_name").innerText =
    `${appointment.patient.first_name} ${appointment.patient.other_names ? appointment.patient.other_names : ""} ${appointment.patient.surname}`;
  document.getElementById("preffered_mode").innerText =
    `${appointment.preffered_mode == "in_person" ? "In Person" : appointment.preffered_mode}`;
  document.getElementById("payment_mode").innerText =
    `Paid: ${appointment.mode_of_payment}`;
  document.getElementById("staff").innerText = appointment.doctor.full_name;
  document.getElementById("staff_role").innerText = appointment.doctor.role;
  document.getElementById("note").innerText = appointment.notes;
  document.getElementById("schedule").innerText =
    `${formatDate(appointment.appointment_at)}, ${formatTime(appointment.start_time)} to ${appointment.end_time ? formatTime(appointment.end_time) : "Not available"}`;
  document.getElementById("current_status").innerText =
    `${appointment.status == "in_progress" ? "In Progress" : appointment.status == "completed" ? "Completed" : appointment.status == "upcoming" ? "Up-Coming" : "Cancelled"}`;

  // add appointment id to all li's with the class 'status_updater' that will be used to update the status of an appointment.
  document
    .querySelectorAll(".status__updater")
    .forEach((e) => (e.dataset.appointmentId = appointment.id));
}

/**
 * Prepopulates the edit model of visit for the client to make changes
 * @param {Object} visit
 */
function populateEditModal(appointment) {
  // IDs for foreign keys
  document.getElementById("edit_patient").value = appointment.patient.id;
  document.getElementById("edit_staff").value = appointment.doctor.id;
  
  // Date handling (Extracts YYYY-MM-DD)
  if(appointment.appointment_at) {
      document.getElementById("edit_appointment_at").value = appointment.appointment_at.split('T')[0];
  }

  // Time handling (Extracts HH:mm)
  if(appointment.start_time) {
      document.getElementById("edit_start_time").value = appointment.start_time.substring(0, 5);
  }
  if(appointment.end_time) {
      document.getElementById("edit_end_time").value = appointment.end_time.substring(0, 5);
  }

  // Enums and Text
  document.getElementById("edit_preferred_mode").value = appointment.preffered_mode || "in_person";
  document.getElementById("edit_status").value = appointment.status || "pending";
  document.getElementById("edit_note").value = appointment.notes || "";
  document.getElementById("edit_mode_of_payment").value = appointment.mode_of_payment || "cash";

  // Financial & Lab Summaries (Read Only badges)
  const invBadge = document.getElementById("badge_invoice_status");
  const labBadge = document.getElementById("badge_lab_status");
  const balanceText = document.getElementById("text_balance");
  const paymentContainer = document.getElementById("payment_action_container");
  const markPaidBtn = document.getElementById("btn_mark_as_paid");


  if (appointment.invoice) {
    console.log("^^^^", appointment.invoice.status.toUpperCase())
    invBadge.textContent = appointment.invoice.status.toUpperCase();
    invBadge.className = `badge ${appointment.invoice.status === 'paid' ? 'bg-success' : 'bg-warning text-dark'}`;
    balanceText.textContent = `Bal: GHS ${parseFloat(appointment.invoice.balance).toFixed(2)}`;
  }

  if (appointment.lab_order) {
    labBadge.textContent = appointment.lab_order.status.replace('_', ' ').toUpperCase();
  }



  if (appointment.invoice) {
    const isPaid = appointment.invoice.status === 'paid';
    
    // Update Badge
    invBadge.textContent = appointment.invoice.status.toUpperCase();
    invBadge.className = `badge ${isPaid ? 'bg-success' : 'bg-warning text-dark'}`;
    
    // Update Balance Text
    balanceText.textContent = `Bal: GHS ${parseFloat(appointment.invoice.balance).toFixed(2)}`;

    // Toggle Payment Button: Hide if already paid
    if (isPaid) {
      paymentContainer.classList.add('d-none');
    } else {
      paymentContainer.classList.remove('d-none');
      // Store invoice info on the button for the click event
      markPaidBtn.dataset.invoiceId = appointment.invoice.id;
      markPaidBtn.dataset.total = appointment.invoice.total_amount;
    }
  } else {
    paymentContainer.classList.add('d-none');
  }

  document.querySelector("#edit_modal form").dataset.appointmentId = appointment.id;


  // Store appointment id
  document.querySelector("#edit_modal form").dataset.appointmentId = appointment.id;

  currentSelectedTests = appointment.tests.map(t => ({
        id: t.id,
        name: t.name,
        price: t.price_ghs
    }));
    
    renderSelectedTests();
}

// updating billing status
document.getElementById("btn_mark_as_paid").addEventListener("click", async (e) => {
  console.log(document.getElementById("btn_mark_as_paid"), "html obj")
    const btn = e.currentTarget;
    const invoiceId = btn.dataset.invoiceId;
    const totalAmount = btn.dataset.total;

    if (!confirm("Confirm that full payment has been received?")) return;

    try {
        const res = await fetch(`/api/v1/billing/invoices/${invoiceId}/pay`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                amount: totalAmount,
                payment_method: document.getElementById("edit_mode_of_payment").value
            })
        });

        if (res.ok) {
            alert("Payment recorded successfully!");
            // Refresh the modal data or close it
            location.reload(); 
        } else {
            const error = await res.json();
            alert(`Error: ${error.detail}`);
        }
    } catch (err) {
      alert(err)
        console.error("Payment Error:", err);
    }
});




function add(acc, cur) {
  return acc + cur;
}

/**
 * Takes a Map with values of int and retuns the total
 * @param {object} data
 */
function computeTotalPrice(data) {
  if (data.length == 0) return 0;

  const results = data.reduce((acc, currrent) => {
    const x = acc.find((item) => item.id == currrent.id);
    if (!x) {
      return acc.concat([currrent]);
    } else {
      return acc;
    }
  }, []);
  const totalPrice = results.map((ord) => ord.price).reduce(add);

  showComputedAmount(totalPrice);

  return totalPrice;
}

/**
 * Display computed total on the form
 * @param {Number} totalAmount
 */
function showComputedAmount(totalAmount) {
  totalPriceEL.textContent = `${totalAmount}`;
  totalSelectedPrice = totalAmount;
}

// VIEW:
/**
 * Render a list of selected Tests to the DOM when the client selects a list of tests
 * @param {Array[object]} selectedTestList
 */
function accordionListRender(selectedTestList) {
  console.log(selectedTestList);
  if (selectedTestList.length === 0) {
    selectedTestAccordionListEl.innerHTML = `<p class="p-4 fs-4 text-align-center">No test selected</p>`;
  } else {
    const filterDuplicate = selectedTestList.reduce((acc, currrent) => {
      const x = acc.find((item) => item.id == currrent.id);
      if (!x) {
        return acc.concat([currrent]);
      } else {
        return acc;
      }
    }, []);

    const accordionListHTML = filterDuplicate
      .map((selectedTest) => {
        return `
      <li class="list-group-item d-flex justify-content-between align-items-start selected__accordion">
        <div class="ms-2 me-auto">
       ${selectedTest.name}
        </div>
        <span class="badge text-bg-primary rounded-pill">${selectedTest.price}</span>
      </li>
      `;
      })
      .join("");

    selectedTestAccordionListEl.innerHTML = accordionListHTML;
  }
}

function buildDynamicURLParam(key, value, state) {
  const url = new URL(testCategoriesURL, window.location.origin);

  // patient filtering parameter
  if (key === "test_category_type") {
    if (value && value) {
      url.searchParams.set("test_category_type", value);
    } else {
      url.searchParams.delete("test_category_type");
    }

    testCategoriesURL = url.pathname + url.search;
    return;
  }

  // test name filtering parameter
  if (key === "name") {
    if (value && value.trim()) {
      url.searchParams.set("name", value.trim());
    } else {
      url.searchParams.delete("name");
    }

    testCategoriesURL = url.pathname + url.search;
    return;
  }

  // department filtering parameter
  if (key === "department") {
    if (value && value.trim()) {
      url.searchParams.set("department", value.trim());
    } else {
      url.searchParams.delete("department");
    }

    testCategoriesURL = url.pathname + url.search;
    return;
  }

  // search parameter
  if (key === "search") {
    if (value && value.trim()) {
      url.searchParams.set("search", value.trim());
    } else {
      url.searchParams.delete("search");
    }

    testCategoriesURL = url.pathname + url.search;
    return;
  }

  // filter params
  const currentValues = url.searchParams.getAll(key);

  if (state) {
    if (!currentValues.includes(value)) {
      url.searchParams.append(key, value);
    }
  } else {
    url.searchParams.delete(key);
    currentValues
      .filter((v) => v !== value)
      .forEach((v) => url.searchParams.append(key, v));
  }

  testCategoriesURL = url.pathname + url.search;
}

function buildAppointmentDynamicURLParam(key, value, state) {
  const url = new URL(appointmentsURL, window.location.origin);

  // filter by patient
  if (key === "patient") {
    if (value && value.trim()) {
      url.searchParams.set("patient", value.trim());
    } else {
      url.searchParams.delete("patient");
    }

    appointmentsURL = url.pathname + url.search;
    return;
  }

  // filter by doctor
  if (key === "doctor") {
    if (value && value.trim()) {
      url.searchParams.set("doctor", value.trim());
    } else {
      url.searchParams.delete("doctor");
    }

    appointmentsURL = url.pathname + url.search;
    return;
  }

  // search parameter
  if (key === "search") {
    if (value && value.trim()) {
      url.searchParams.set("search", value.trim());
    } else {
      url.searchParams.delete("search");
    }

    appointmentsURL = url.pathname + url.search;
    return;
  }

  // filter params
  const currentValues = url.searchParams.getAll(key);

  if (state) {
    if (!currentValues.includes(value)) {
      url.searchParams.append(key, value);
    }
  } else {
    url.searchParams.delete(key);
    currentValues
      .filter((v) => v !== value)
      .forEach((v) => url.searchParams.append(key, v));
  }

  appointmentsURL = url.pathname + url.search;
}


// function to perform search
/**
 * @param {string} query
 * @param {bool} useAppointment
 * @returns {Array}
 */
async function performSearch(query, useAppointment) {
  // Only search if query is at least 3 characters
  if (query.length < 3) return [];

  // Cancel any ongoing search request
  if (activeController) {
    activeController.abort();
  }

  activeController = new AbortController();

  try {
    let url = useAppointment ? appointmentsURL : testCategoriesURL;

    const res = await fetch(url, {
      signal: activeController.signal,
      headers: { "Content-Type": "application/json" }
    });

    if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);

    const data = await res.json();
    return data;

  } catch (err) {
    // ignore AbortError because it happens intentionally when a user keeps typing
    if (err.name === "AbortError") return;

    console.error("Search error:", err);
    
    // NOTIFY USER OF ACTUAL SEARCH ERRORS
    // showFeedback({
    //   title: "Search Error",
    //   message: "An error occurred while searching. Please check your connection.",
    //   type: 'error'
    // });

    showToast("An error occurred while searching. Please try again.", "error")
    
    return [];
  }
}

/**
 * render bacteria search results
 * @param {object} data
 */

function renderBacteriaSearchResults(data) {
  const searchResultsHTML = data
    .map((bac) => {
      const bac_exits = selectedTests["bacteriology"].includes(bac.id);

      const htmlElement = `
             <li>
                <label class="dropdown-item px-2 d-flex align-items-center rounded-1">
                    <input data-bac-id=${bac.id} data-bac-price=${bac.price_ghs} data-bac-name="${bac.name}" class="form-check-input m-0 me-2 bac__option" type="checkbox" ${bac_exits ? "checked" : ""}>
                    <span class="avatar avatar-xs rounded-circle me-2"></span>${bac.name}
                </label>
            </li>
        `;
      return htmlElement;
    })
    .join("");

  const resultUlEl = document.querySelector(".bac__search__results");

  // Remove all li elements except the first one (search input)
  while (resultUlEl.children.length > 1) {
    resultUlEl.removeChild(resultUlEl.children[1]);
  }

  // Insert new results after the first li
  resultUlEl.insertAdjacentHTML("beforeend", searchResultsHTML);
}

/**
 * render ultra-scan search results
 * @param {object} data
 */
function renderChemistrySearchResults(data) {
  const searchResultsHTML = data
    .map((chem) => {
      const htmlElement = `
             <li>
                <label class="dropdown-item px-2 d-flex align-items-center rounded-1">
                    <input class="form-check-input m-0 me-2 chem_option" type="checkbox" data-chem-id=${chem.id} data-chem-price=${chem.price_ghs} data-chem-name=${chem.name}>
                    <span class="avatar avatar-xs rounded-circle me-2"></span>${chem.name}
                </label>
            </li>
        `;
      return htmlElement;
    })
    .join("");

  const resultUlEl = document.querySelector(".chem__search__results");

  // Remove all li elements except the first one (search input)
  while (resultUlEl.children.length > 1) {
    resultUlEl.removeChild(resultUlEl.children[1]);
  }

  // Insert new results after the first li
  resultUlEl.insertAdjacentHTML("beforeend", searchResultsHTML);
}

function formatDate(dateStr) {
  // "2026-01-13" → "13 Jan, 2026"
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatTime(timeStr) {
  // "08:17" → "08:17 AM"
  if (!timeStr) return "not set";
  const [h, m] = timeStr.split(":");
  const date = new Date();
  date.setHours(h, m);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

//  <td>15 Jan 2025, 05:30 PM to 06:30 PM</td>



let currentSelectedTests = []; // Array of {id, name, price}

// 1. Function to refresh the "Selected" UI
function renderSelectedTests() {
    const container = document.getElementById("selected_tests_container");
    const noTestsMsg = document.getElementById("no_tests_msg");
    const previewTotalEl = document.getElementById("preview_total_price");
    
    container.innerHTML = "";
    let runningTotal = 0;

    if (currentSelectedTests.length === 0) {
        noTestsMsg.classList.remove("d-none");
    } else {
        noTestsMsg.classList.add("d-none");
        
        currentSelectedTests.forEach(test => {
            // Add to running total (ensure it's a number)
            runningTotal += parseFloat(test.price) || 0;

            const badge = document.createElement("div");
            badge.className = "badge bg-info-lite text-info d-flex align-items-center gap-2 p-2 mb-1";
            badge.style.fontSize = "0.85rem";
            badge.innerHTML = `
                <span class="fw-medium">${test.name}</span>
                <i class="ti ti-circle-x-filled cursor-pointer text-danger" onclick="removeTest(${test.id})"></i>
            `;
            container.appendChild(badge);
        });
    }

    // Update the visual preview
    previewTotalEl.textContent = runningTotal.toFixed(2);
}


// 2. Remove test function
window.removeTest = function(testId) {
    currentSelectedTests = currentSelectedTests.filter(t => t.id !== testId);
    renderSelectedTests();
};

// 3. Search logic (Debounced)
let searchTimer;


document.getElementById("test_search_input").addEventListener("input", (e) => {
    clearTimeout(searchTimer);
    const query = e.target.value;
    
    // Safety check for category filter
    const categoryFilter = document.getElementById("test_category_filter");
    const categoryId = categoryFilter ? categoryFilter.value : "";

    const resultsWrapper = document.getElementById("search_results_area");
    const resultsArea = document.getElementById("test_search_results");

    // Only search if user typed at least 2 characters
    if (query.length < 2) {
        if (resultsWrapper) resultsWrapper.classList.add("d-none");
        return;
    }

    searchTimer = setTimeout(async () => {
        try {
            const url = `/api/v1/test-categories/?test_category_type=${categoryId}&name=${query}`;
            const res = await fetch(url);
            
            if (!res.ok) throw new Error("Search failed");
            
            const tests = await res.json();
            
            if (!resultsArea || !resultsWrapper) return;
            
            resultsArea.innerHTML = "";
            
            if (tests.length === 0) {
                resultsArea.innerHTML = '<div class="list-group-item small text-muted text-center">No tests found</div>';
            } else {
                tests.forEach(test => {
                    const item = document.createElement("button");
                    item.type = "button";
                    item.className = "list-group-item list-group-item-action d-flex justify-content-between align-items-center";
                    item.innerHTML = `
                        <div>
                            <h6 class="mb-0 fs-13">${test.name}</h6>
                            <small class="text-muted">GHS ${parseFloat(test.price_ghs).toFixed(2)}</small>
                        </div>
                        <i class="ti ti-plus text-success"></i>
                    `;
                    
                    item.onclick = () => {
                        // Avoid adding duplicates to the list
                        if (!currentSelectedTests.find(t => t.id === test.id)) {
                            currentSelectedTests.push({
                                id: test.id, 
                                name: test.name, 
                                price: test.price_ghs
                            });
                            renderSelectedTests();
                        }
                        // Clear search after selection
                        document.getElementById("test_search_input").value = "";
                        resultsWrapper.classList.add("d-none");
                    };
                    resultsArea.appendChild(item);
                });
            }
            resultsWrapper.classList.remove("d-none");
            
        } catch (err) {
            console.error("Search Error:", err);
            showToast("Encountered an error while searching for tests. Please try again.", "error")
        }
    }, 400); 
});


