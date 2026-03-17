console.log("appointments.js loaded");

let searchBacterialTestEl = document.querySelector(".search__bact");
let searchChemTestEl = document.querySelector(".search__chem");
let catSelectEl = document.querySelector(".test__cat__type");
let appointmentsTableEL = document.querySelector(".appointments__table");

let testTableVisibilityEl = document.querySelector(".is_cat_table_hidden"); // toggle test categoy visibility
let bacterialTestDivEl = document.querySelector("#bacteria-test");
let chemistryTestDivEl = document.querySelector("#chemistry-test");

let totalPriceEL = document.querySelector(".total__price");
let totalNumOfAppointments = 0;

// render accordion
let selectedTestAccordionListEl = document.querySelector(
  ".selected__accordion",
);

let testCategoriesURL = "/api/v1/test-categories";
let appointmentsURL = "/api/v1/appointments/";
let searchTimeout = null;
let activeController = null;
const selectedTests = {
  bacteriology: [],
  chemistry: [],
};
let selectedTestOrderList = [];

// VIEW: search results
let bacteria_search_resultsEl = document.querySelector(".bac__search__results");
let chem__search__resultsEl = document.querySelector(".chem__search__results");

// VIEW: form data
let appointmentForm = document.querySelector(".appointmentForm");

// FILTERING / SEARCH
const searchPatientEl = document.querySelector(".search__patient");
const searchStaffEl = document.querySelector(".search__staff");
const filterByStatus = document.querySelector(".appointment_status");

document.addEventListener("DOMContentLoaded", async (e) => {
  const res = await getTestCategoriessData(appointmentsURL);
  // total number of appointment
  totalNumOfAppointments = res.length;

  render(res);

  // listen to changes on the test category drop down list
  catSelectEl.addEventListener("input", (e) => {
    const selectedValue = e.target.value;
    const [id, cat_name] = selectedValue.split(",").map((e) => e.trim());

    // change visibility to block
    if (testTableVisibilityEl.classList.contains("is_cat_table_hidden")) {
      testTableVisibilityEl.style.display = "block";

      console.log(cat_name);

      if (cat_name.toLowerCase() == "bacteriology") {
        if (bacterialTestDivEl.classList.contains("bac__hidden")) {
          bacterialTestDivEl.classList.remove("bac__hidden");
          bacterialTestDivEl.classList.add("bac__visible");
        }
      }

      // toggle chemistry seach bar
      if (cat_name.toLowerCase() == "ultra-scan") {
        if (chemistryTestDivEl.classList.contains("chem__hidden")) {
          chemistryTestDivEl.classList.remove("chem__hidden");
          chemistryTestDivEl.classList.add("chem__visible");
        }
      }
    }
    buildDynamicURLParam("test_category_type", Number.parseInt(id));
  });

  // Search bacteriology test
  searchBacterialTestEl.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);

    searchTimeout = setTimeout(async () => {
      let value = e.target.value;
      buildDynamicURLParam("name", value);
      const data = await performSearch(value);
      console.log("renderrr:", data);

      renderBacteriaSearchResults(data);
    });
  });

  // search chem test
  searchChemTestEl.addEventListener("input", (e) => {
    clearTimeout(searchTimeout);

    searchTimeout = setTimeout(async () => {
      let value = e.target.value;
      buildDynamicURLParam("name", value);
      const data = await performSearch(value);
      console.log(data);

      renderChemistrySearchResults(data);
    });
  });

  // add event to bacteria_search_resultsEl to get selected test
  bacteria_search_resultsEl.addEventListener("change", (e) => {
    // e.stopPropagation();
    let checkbox = e.target;
    if (!checkbox.classList.contains("bac__option")) return;
    const optionId = Number(checkbox.dataset.bacId);
    const priceOfTest = Number(checkbox.dataset.bacPrice);
    const testName = checkbox.dataset.bacName;
    console.log("test name: ", testName);

    if (checkbox.checked) {
      selectedTests["bacteriology"].push(optionId);

      // add selected item to selected test list
      const selectedOption = {
        id: optionId,
        price: priceOfTest,
        name: testName,
      };

      selectedTestOrderList.push(selectedOption);
      const totalPrice = computeTotalPrice(selectedTestOrderList);

      // render accordion
      accordionListRender(selectedTestOrderList);
    } else {
      selectedTests["bacteriology"] = selectedTests["bacteriology"].filter(
        (id) => id !== optionId,
      );

      // remove test from testlist
      selectedTestOrderList = selectedTestOrderList.filter(
        (item) => item.id !== optionId,
      );
      let totalPrice2 = computeTotalPrice(selectedTestOrderList);
    }

    // render accordion
    accordionListRender(selectedTestOrderList);
    // console.log(selectedTestOrderList);
  });

  // listen to event on the chem search bar.
  chem__search__resultsEl.addEventListener("change", (e) => {
    let checkbox = e.target;
    if (!checkbox.classList.contains("chem_option")) return;
    const optionId = Number(checkbox.dataset.chemId);
    const priceOfTest = Number(checkbox.dataset.chemPrice);
    const testName = checkbox.dataset.chemName;

    if (checkbox.checked) {
      selectedTests["chemistry"].push(optionId);

      // add selected test to selectedtest list
      const selectedOption = {
        id: optionId,
        price: priceOfTest,
        name: testName,
      };
      selectedTestOrderList.push(selectedOption);
      let totalPrice = computeTotalPrice(selectedTestOrderList);
      console.log(totalPrice);

      // render accordion
      accordionListRender(selectedTestOrderList);
    } else {
      selectedTests["chemistry"] = selectedTests["chemistry"].filter(
        (id) => id !== optionId,
      );

      // from test from testlist
      selectedTestOrderList = selectedTestOrderList.filter(
        (item) => item.id !== optionId,
      );
      // re-compute the total score
      let totalPrice2 = computeTotalPrice(selectedTestOrderList);
      console.log(totalPrice2, "is now");

      // render accordion
      accordionListRender(selectedTestOrderList);
    }
  });

  // Event: submit appointment form
  document
    .querySelector("#appointmentForm")
    .addEventListener("submit", async (e) => {
      e.preventDefault();

      // show notification
      const appointment_toast = document.getElementById("liveToast");
      const toastAppointment =
        bootstrap.Toast.getOrCreateInstance(appointment_toast);
      console.log(toastAppointment);

      const form = e.target;
      const formData = new FormData(form);

      const payload = {
        patient_id: Number(formData.get("patient_id")),
        doctor_id: Number(formData.get("staff_id")),
        notes: formData.get("notes"),
        mode_of_payment: formData.get("payment_mode"),
        total_price: Number(formData.get("total__price")),

        test_ids: [
          ...new Set([
            ...selectedTests["bacteriology"],
            ...selectedTests["chemistry"],
          ]),
        ],
      };

      try {
        // send data to backend
        const res = await fetch("/api/v1/appointments/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await res.json();

        console.log("created appo", data);

        // close modal
        const modalEl = document.getElementById("add_modal");
        const modalInstance =
          bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);

        modalInstance.hide();

        // reset form data and global state for forms
        form.reset();
        selectedTests["bacteriology"] = [];
        selectedTests["chemistry"] = [];
        selectedTestOrderList = [];

        // set success notification information for toast to show
        document.querySelector(".notification__header").textContent =
          "New Appointment Added";
        document.querySelector(".notification__body").textContent =
          "Appointment was successfully added.";

        if (
          !document.querySelector(".toast").classList.contains("bg-success")
        ) {
          document.querySelector(".toast").classList.add("bg-success");
        } else {
          document.querySelector(".toast").classList.remove("bg-success");
        }

        // show toast
        toastAppointment.show();
      } catch (error) {
        console.log(error);
        // set success notification information for toast to show
        document.querySelector(".notification__header").textContent =
          "New Appointment Failed";
        document.querySelector(".notification__body").textContent =
          "Failed to add new Appointment. Please try again.";

        // show toast
        toastAppointment.show();
      }
    });

  // edit button to show edit modal
  document
    .querySelector(".appointments__table")
    .addEventListener("click", async function (e) {
      const button = e.target.closest(".edit__appointment__btn");
      if (!button) return;
      console.log(button.dataset);
    });
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
                    <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center" data-bs-toggle="modal" data-bs-target="#view_modal"><i class="ti ti-eye me-1"></i>View Details</a>
                </li>
                <li>
                    <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center edit__appointment__btn" data-bs-toggle="modal" data-bs-target="#edit_modal" data-appointmentId=${appointment.id}><i class="ti ti-edit me-1"></i>Edit</a>
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

/**
 * Fetch all test-categories data
 * @returns Array[objects]
 */
async function getTestCategoriessData(url) {
  const res = await fetch(url);
  const data = await res.json();
  return data;
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

// function to perform search
async function performSearch(query) {
  // cancel previous request
  if (query.length < 3) return [];

  if (activeController) {
    activeController.abort();
  }

  activeController = new AbortController();

  try {
    const url = testCategoriesURL;

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
