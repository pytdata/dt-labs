//
const visitTableEL = document.querySelector(".list__visits");
const searchDoctorEl = document.querySelector(".search__doctor");
const searchDepartmentEl = document.querySelector(".search__department");
const searchPatientEl = document.querySelector(".search__patient");
const fitlerByStatusEl = document.querySelectorAll(".visit__status");


let visitsURL = "/api/v1/visits";
let searchTimeout = null;
let activeController = null;

document.addEventListener("DOMContentLoaded", init);

async function init(e) {
  let visitsList = await getVisitsData(visitsURL);

  render(visitsList);

  // search by doctor
  searchDoctorEl.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);

    searchTimeout = setTimeout(async () => {
      let value = e.target.value;
      buildDynamicURLParam("doctor", value);
      const data = await performSearch(value);

      renderDoctorSearchResults(data);
    });
  });

  // search by department
  searchDepartmentEl.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);

    searchTimeout = setTimeout(async () => {
      let value = e.target.value;
      buildDynamicURLParam("department", value);
      const data = await performSearch(value);
      renderDepartmentSearchResults(data);
    });
  });

  // search by patient
  searchPatientEl.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);

    searchTimeout = setTimeout(async () => {
      let value = e.target.value;
      buildDynamicURLParam("patient", value);
      const data = await performSearch(value);
      renderPatientSearchResults(data);
    });
  });

  // Filtering by status
  fitlerByStatusEl.forEach((statusOption) => {
    statusOption.addEventListener("change", async (e) => {
      buildDynamicURLParam(
        "status",
        e.currentTarget.dataset.status,
        e.currentTarget.checked
      );

      // make request to backend
      visitsList = await getVisitsData(visitsURL);
      render(visitsList);

      console.log(visitsList)
    });
  });


document.querySelector(".list__visits").addEventListener("click", async function(e) {
  const button = e.target.closest(".edit__visit__btn");
    if (!button) return;

   // send changes to the backend and save
   const visitId = button.dataset.visitId;

   try {
        const res = await fetch(`/api/v1/visits/${visitId}`);
        if (!res.ok) throw new Error("Failed to fetch visit");

        const visit = await res.json();

        console.log(visit)

        populateEditModal(visit);
        // openVisitModal();

    } catch (err) {
        console.error(err);
        alert("Could not load visit details");
    }

});

// submit the edit made to the visit.
document.querySelector(".edit__form").addEventListener("submit", async function (e) {
    e.preventDefault();


    const visitId = this.dataset.visitId;

    const payload = {
        patient_id: document.getElementById("patient").value,
        patient_type: document.getElementById("patient_type").value,
        department_id: document.getElementById("department").value,
        doctor_id: document.getElementById("doctor").value,
        visit_date: document.getElementById("visit_date").value,
        visit_time: document.getElementById("visit_time").value,
        reason: document.getElementById("reason").value,
        payment_mode: document.getElementById("payment_mode").value
    };

    await fetch(`/api/v1/visits/${visitId}/`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    // location.reload(); // or re-render list
});


}

/**
 * Prepopulates the edit model of visit for the client to make changes
 * @param {Object} visit 
 */
function populateEditModal(visit) {
    // Selects
    document.getElementById("patient").value = visit.patient.id;
    document.getElementById("patient_type").value = visit.patient_type;
    document.getElementById("department").value = visit.department.id;
    document.getElementById("doctor").value = visit.doctor.id;
    document.getElementById("payment_mode").value = visit.mode_of_payment ? visit.mode_of_payment :"cash";

    // Inputs
    document.getElementById("visit_date").value = formatDate(visit.visit_date);
    document.getElementById("visit_time").value = formatTime(visit.time_of_visit);
    document.getElementById("reason").value = visit.reason;

    // Store visit id for submit
    document.querySelector("#edit_modal form").dataset.visitId = visit.id;
}



/**
 * render patient search results
 * @param {object} data
 */
function renderPatientSearchResults(data) {
  const searchResultsHTML = data
    .map((visit) => {
      const htmlElement = `
            <li>
                <label class="dropdown-item px-2 d-flex align-items-center rounded-1">
                    <input class="form-check-input m-0 me-2" type="checkbox">
                    <span class="avatar avatar-xs rounded-circle me-2"><img src="/static/img/users/avatar-5.jpg" class="flex-shrink-0 rounded" alt="img"></span>${visit.patient.full_name}
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
 * render doctor search results
 * @param {object} data
 */
function renderDoctorSearchResults(data) {
  const searchResultsHTML = data
    .map((visit) => {
      const htmlElement = `
            <li>
                <label class="dropdown-item px-2 d-flex align-items-center rounded-1">
                    <input class="form-check-input m-0 me-2" type="checkbox">
                    <span class="avatar avatar-xs rounded-circle me-2"><img src="/static/img/doctors/doctor-01.jpg" class="flex-shrink-0 rounded" alt="img"></span>${visit.patient.full_name}
                </label>
            </li>
        `;
      return htmlElement;
    })
    .join("");

  const resultUlEl = document.querySelector(".doctor__search__results");

  // Remove all li elements except the first one (search input)
  while (resultUlEl.children.length > 1) {
    resultUlEl.removeChild(resultUlEl.children[1]);
  }

  // Insert new results after the first li
  resultUlEl.insertAdjacentHTML("beforeend", searchResultsHTML);
}

/**
 * render department search results
 * @param {object} data
 */
function renderDepartmentSearchResults(data) {
  const searchResultsHTML = data
    .map((visit) => {
      const htmlElement = `
            <li>
                <label class="dropdown-item px-2 d-flex align-items-center rounded-1">
                    <input class="form-check-input m-0 me-2" type="checkbox">
                    ${visit.patient.full_name}
                </label>
            </li>
        `;
      return htmlElement;
    })
    .join("");

  const resultUlEl = document.querySelector(".department__search__results");

  // Remove all li elements except the first one (search input)
  while (resultUlEl.children.length > 1) {
    resultUlEl.removeChild(resultUlEl.children[1]);
  }

  // Insert new results after the first li
  resultUlEl.insertAdjacentHTML("beforeend", searchResultsHTML);
}

// function to perform search
async function performSearch(query) {
  // cancel previous request
  if (query.length < 3) return;

  if (activeController) {
    activeController.abort();
  }

  activeController = new AbortController();

  try {
    const url = visitsURL;

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

function buildDynamicURLParam(key, value, state) {
  const url = new URL(visitsURL, window.location.origin);

  // patient filtering parameter
  if (key === "patient") {
    if (value && value.trim()) {
      url.searchParams.set("patient", value.trim());
    } else {
      url.searchParams.delete("patient");
    }

    visitsURL = url.pathname + url.search;
    return;
  }

  // doctor filtering parameter
  if (key === "doctor") {
    if (value && value.trim()) {
      url.searchParams.set("doctor", value.trim());
    } else {
      url.searchParams.delete("doctor");
    }

    visitsURL = url.pathname + url.search;
    return;
  }

  // department filtering parameter
  if (key === "department") {
    if (value && value.trim()) {
      url.searchParams.set("department", value.trim());
    } else {
      url.searchParams.delete("department");
    }

    visitsURL = url.pathname + url.search;
    return;
  }

  // search parameter
  if (key === "search") {
    if (value && value.trim()) {
      url.searchParams.set("search", value.trim());
    } else {
      url.searchParams.delete("search");
    }

    visitsURL = url.pathname + url.search;
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

  visitsURL = url.pathname + url.search;
}

/**
 * Fetch all visits data
 * @returns Array[objects]
 */
async function getVisitsData(url) {
  const res = await fetch(url);
  const data = await res.json();
  return data;
}

function render(visitsList) {
  // render patients data into html and join the results into an html string
  const renderedHTML = visitsList
    .map((visit) => {
      return renderData(visit);
    })
    .join("");

  // insert data into DOM
  visitTableEL.innerHTML = renderedHTML;
}

/**
 * Renders the patient data into html.
 * @param {Map} patient
 * @returns htmlement
 */
function renderData(visit) {
  const htmlElement = `  
     
     <tr>
        <td>
            <div class="form-check form-check-md">
                <input class="form-check-input" type="checkbox">
            </div>
        </td>
        <td><a href="javascript:void(0);" data-bs-toggle="modal" data-bs-target="#view_modal">${
          visit.patient.patient_no
        }</a></td>
        <td>
            <div class="d-flex align-items-center">
                <a href="patient-details.html" class="avatar avatar-xs me-2">
                    <img src="/static/img/users/avatar-5.jpg" alt="img" class="rounded">
                </a>
                <div>
                    <h6 class="fs-14 mb-0 fw-medium"><a href="patient-details.html">${
                      visit.patient.full_name
                    } </a></h6>
                </div>
            </div>
        </td>
        <td>${visit.department.name}</td>
        <td>
            <div class="d-flex align-items-center">
                <a href="doctor-details.html" class="avatar avatar-xs me-2">
                    <img src="/static/img/doctors/doctor-01.jpg" alt="img" class="rounded">
                </a>
                <div>
                    <h6 class="fs-14 mb-0 fw-medium"><a href="doctor-details.html">Dr. ${
                      visit.doctor.full_name
                    }</a></h6>
                </div>
            </div>
        </td>
        <td>${formatDate(visit.visit_date)}</td>
        ${
          visit.status == "pending"
            ? `<td><span class="badge badge-soft-primary border border-primary text-primary py-1 ps-1 d-inline-flex align-items-center"><i class="ti ti-point-filled me-0 fs-14"></i>${visit.status}</span></td>`
            : visit.status == "completed"
            ? ` <td><span class="badge badge-soft-success border border-success text-success py-1 ps-1 d-inline-flex align-items-center"><i class="ti ti-point-filled me-0 fs-14"></i>${visit.status}</span></td>`
            : ` <td><span class="badge badge-soft-primary border border-primary text-primary py-1 ps-1 d-inline-flex align-items-center"><i class="ti ti-point-filled me-0 fs-14"></i>${visit.status}</span></td>`
        }
        
        <td class="text-end">
            <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown"><i class="ti ti-dots-vertical"></i></a>
            <ul class="dropdown-menu p-2">
                <li>
                    <a href="start-visit.html" class="dropdown-item d-flex align-items-center"><i class="ti ti-e-passport me-1"></i>Start Visit</a>
                </li>
                <li>
                    <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center" data-bs-toggle="modal" data-bs-target="#view_modal"><i class="ti ti-eye me-1"></i>View Past History</a>
                </li>
                <li>
                    <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center edit__visit__btn" data-bs-toggle="modal" data-bs-target="#edit_modal" data-visit-id=${visit.id}><i class="ti ti-edit me-1"></i>Edit</a>
                </li>
                <li>
                    <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center" data-bs-toggle="modal" data-bs-target="#delete_modal"><i class="ti ti-trash me-1"></i>Delete</a>
                </li>
            </ul>
        </td>
    </tr>
  `;

  return htmlElement;
}

// function formatDate(date_arg) {
//   const date = new Date(date_arg);
//   const formatted = date.toISOString().split("T")[0];
//   return formatted;
// }


function formatDate(dateStr) {
    // "2026-01-13" → "13 Jan, 2026"
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric"
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
        hour12: true
    });
}
