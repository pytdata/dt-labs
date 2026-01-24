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

// ACCORDION
const selectedTestAccordionListEl = document.querySelector(
  ".selected__accordion",
);

// SEARCH RESULTS
const bacteriaSearchResultsEl = document.querySelector(".bac__search__results");
const chemSearchResultsEl = document.querySelector(".chem__search__results");

// FORM
const appointmentForm = document.querySelector("#appointmentForm");

let totalNumOfAppointments = 0;
let searchTimeout = null;
let activeController = null;

let testCategoriesURL = "/api/v1/test-categories";
let appointmentsURL = "/api/v1/appointments/";

const selectedTests = {
  bacteriology: [],
  chemistry: [],
};

let selectedTestOrderList = [];

(async function init() {
  const res = await getRemoteData(appointmentsURL);
  totalNumOfAppointments = res.length;
  render(res);
})();

catSelectEl.addEventListener("input", (e) => {
  const [id, catName] = e.target.value.split(",").map((v) => v.trim());

  testTableVisibilityEl.style.display = "block";

  if (catName.toLowerCase() === "bacteriology") {
    bacterialTestDivEl.classList.remove("bac__hidden");
    bacterialTestDivEl.classList.add("bac__visible");
  }

  if (catName.toLowerCase() === "ultra-scan") {
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

  const formData = new FormData(appointmentForm);

  const payload = {
    patient_id: Number(formData.get("patient_id")),
    doctor_id: Number(formData.get("staff_id")),
    notes: formData.get("notes"),
    mode_of_payment: formData.get("payment_mode"),
    total_price: Number(formData.get("total__price")),
    test_ids: [
      ...new Set([...selectedTests.bacteriology, ...selectedTests.chemistry]),
    ],
  };

  try {
    const res = await fetch("/api/v1/appointments/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error("Failed to book appointment.: ", res);

    const data = await res.json();
  } catch (error) {
    console.log(error);
  }

  appointmentForm.reset();
});

// show appointment details
appointmentsTableEL.addEventListener("click", async (e) => {
  const button = e.target.closest(".view__appointment__btn");
  if (!button) return;

  const appointmentId = button.dataset.appointmentid;

  try {
    const res = await fetch(`/api/v1/appointments/${appointmentId}/`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) throw new Error("Failed to fetch appointment: ", res);
    const appointment = await res.json();

    populateAppointmentDetailModal(appointment);
  } catch (error) {
    console.error(error);
    alert("Failed to load appointment");
    // TODO: app toast notification
  }
});

// show edit appointment form with requested data
appointmentsTableEL.addEventListener("click", async (e) => {
  const button = e.target.closest(".edit__appointment__btn");
  if (!button) return;

  const appointmentId = button.dataset.appointmentid;

  try {
    const res = await fetch(`/api/v1/appointments/${appointmentId}/`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) throw new Error("Failed to fetch appointment: ", res);
    const appointment = await res.json();

    populateEditModal(appointment);
  } catch (error) {
    console.error(error);
    alert("Failed to load appointment");
    // TODO: app toast notification
  }
});

// submit the edit made to the appointment
document
  .querySelector(".edit__appointment__form")
  .addEventListener("submit", async function (e) {
    e.preventDefault();

    const appointmentId = this.dataset.appointmentId;

    const payload = {
      patient_id: document.getElementById("patient").value,
      // patient_type: document.getElementById("patient_type").value,
      doctor_id: document.getElementById("staff").value,
      notes: document.getElementById("note").value,
      mode_of_payment: document.getElementById("mode_of_payment").value,
    };

    try {
      const res = await fetch(`/api/v1/appointments/${appointmentId}/`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Failed to update appointment");

      const data = await res.json();
      console.log(data);

      // reset the form
      document.querySelector(".edit__appointment__form").reset();
    } catch (error) {
      console.log(error);
      alert(error);
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
    const appointmentId = Number(button.dataset.appointmentId); // get appointment id from the parent (ul)

    // make patch/put request to update status
    const payload = {
      status: status,
    };
    try {
      const res = await fetch(`/api/v1/appointments/${appointmentId}/`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Failed to update appointment.: ", res);

      const data = await res.json();

      populateAppointmentDetailModal(data);
      // document.querySelector("#current_status").innerText = "loading....";
    } catch (error) {
      console.error(error);
    }
  });

// delete appointment
appointmentsTableEL.addEventListener("click", async (e) => {
  const button = e.target.closest(".delete__appointment__btn");
  if (!button) return;

  const appointmentId = button.dataset.appointmentid;
  document.querySelector(".delete__appointment").dataset.appointmentid =
    appointmentId;
});

document
  .querySelector(".delete__appointment")
  .addEventListener("click", async (e) => {
    // send delete request to delete resources
    e.preventDefault();
    const button = e.target;
    if (!button) return;

    const appointmentId = button.dataset.appointmentid;
    console.log("del", appointmentId);

    try {
      const res = await fetch(`/api/v1/appointments/${appointmentId}/`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error("Failed to delete appointment: ", res);
    } catch (error) {
      console.error(error);
      alert(error);
    }
  });

// Search patients by staff
searchStaff.addEventListener("input", (e) => {
  console.log(e.target.value);
  clearTimeout(searchTimeout);

  searchTimeout = setTimeout(async () => {
    let value = e.target.value;
    buildAppointmentDynamicURLParam("doctor", value);
    console.log(appointmentsURL);
    const data = await performSearch(value, true);
    console.log("Data from search 1:", data);

    renderStaffSearchResults(data);
  });
});

// clear text from searchStaff input
searchStaff.addEventListener("blur", (e) => {
  searchStaff.value = "";
  buildAppointmentDynamicURLParam("doctor");
});

// Search patients by patient name
patientSearch.addEventListener("input", (e) => {
  console.log(e.target.value);
  clearTimeout(searchTimeout);

  searchTimeout = setTimeout(async () => {
    let value = e.target.value;
    buildAppointmentDynamicURLParam("patient", value);
    const data = await performSearch(value, true);
    console.log("Data from search 2:", data);

    renderPatientsSearchResults(data);
  });
});

// clear text from patientsearch input
patientSearch.addEventListener("blur", (e) => {
  patientSearch.value = "";
  buildAppointmentDynamicURLParam("patient");
});

// FILTERING BY STATUS
statusFilter.forEach((statusOption) =>
  statusOption.addEventListener("change", async (e) => {
    buildAppointmentDynamicURLParam(
      "status",
      e.currentTarget.dataset.status,
      e.currentTarget.checked,
    );

    // make request to backend
    const data = await getRemoteData(appointmentsURL);
    render(data);
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
})

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
 * Render a lsit of object as html elements and display in DOM
 * @param {Array[Object]} appointmentsList
 */
function render(appointmentsList) {
  // render patients data into html and join the results into an html string
  const renderedHTML = appointmentsList
    .map((appointment) => {
      return renderData(appointment);
    })
    .join("");

  // insert data into DOM
  appointmentsTableEL.innerHTML = renderedHTML;
}

/**
 * Renders the patient data into html.
 * @param {Map} patient
 * @returns htmlement
 */
function renderData(appointment) {
  const htmlElement = ` <tr>
        <td>
            <div class="form-check form-check-md">
                <input class="form-check-input" type="checkbox">
            </div>
        </td>
        <td><a href="javascript:void(0);" data-bs-toggle="modal" data-bs-target="#view_modal">${
          appointment.id
        }</a></td>
        <td>
            <div class="d-flex align-items-center">
                <a href="patient-details.html" class="avatar avatar-xs me-2">
                    <img src="/static/img/users/user-39.jpg" alt="img" class="rounded">
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
                    <img src="/static/img/doctors/doctor-11.jpg" alt="img" class="rounded">
                </a>
                <div>
                    <h6 class="fs-14 mb-0 fw-medium"><a href="doctor-details.html">Dr. ${
                      appointment.doctor.full_name
                    }</a></h6>
                </div>
            </div>
        </td>
       
        <td>15 Jan 2025, 05:30 PM to 06:30 PM</td>
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
    </tr>
    
  `;

  return htmlElement;
}

function populateAppointmentDetailModal(appointment) {
  console.log("status update: ", appointment);
  document.getElementById("patient_name").innerText =
    `${appointment.patient.first_name} ${appointment.patient.other_names ? appointment.other_names : ""} ${appointment.patient.surname}`;
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
  // Selects
  document.getElementById("patient").value = appointment.patient.id;
  document.getElementById("patient_type").value =
    appointment.patient.patient_type;
  // document.getElementById("department").value = appointment.department.id;
  document.getElementById("staff").value = appointment.doctor.id;
  document.getElementById("mode_of_payment").value = appointment.mode_of_payment
    ? appointment.mode_of_payment
    : "cash";

  // Inputs
  document.getElementById("note").value = appointment.notes
    ? appointment.notes
    : "";

  // Store appointment id for submit
  document.querySelector("#edit_modal form").dataset.appointmentId =
    appointment.id;
}

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
 *
 * @param {string} query
 * @param {bool} useAppointment
 * @returns
 */
async function performSearch(query, useAppointment) {
  // cancel previous request
  if (query.length < 3) return [];

  if (activeController) {
    activeController.abort();
  }

  activeController = new AbortController();

  try {
    let url = testCategoriesURL;
    // set url to appointment url if the useAppointment is set
    if (useAppointment) {
      url = appointmentsURL;
    }

    const res = await fetch(url, {
      signal: activeController.signal,
    });

    const data = await res.json();

    return data;
  } catch (err) {
    // TODO: Add model to show error
    if (err.name !== "AbortError") {
      console.error("Search error:", err);
    }
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
 * render bacteria search results
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
