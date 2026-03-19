const patientsEL = document.querySelector(".list__patients");

const sortOptionsEl = document.querySelectorAll(".sort-option");

const genderOptionsEl = document.querySelectorAll(".gender__filter");

const searchEl = document.querySelectorAll(".search__input");

let patientsURL = "/api/v1/patients";

let searchTimeout = null;
let activeController = null;
let dataTableInstance = null; // Store the instance globally

// document.addEventListener("DOMContentLoaded", init);

// async function init(e) {
//   // get patient data

//   let patientList = await getVisitsData(patientsURL);

//   let sortCol = "newest";

//   let sortState = sortCol == "newest" ? true : false;

//   render(patientList);

//   // listen for sort clicks

//   sortOptionsEl.forEach((t) => {
//     t.addEventListener("click", sortPatients);
//   });

//   // sorting

//   function sortPatients(e) {
//     let thisSort = e.currentTarget.dataset.value;

//     if (sortCol === thisSort) sortState = !sortState;

//     sortCol = thisSort;

//     // change sorting algorithm.

//     patientList.sort((a, b) => {
//       if (a[sortCol] < b[sortCol]) return sortState ? 1 : -1;

//       if (a[sortCol] > b[sortCol]) return sortState ? -1 : 1;

//       return 0;
//     });

//     return render(patientList);
//   }

//   // FILTERING

//   genderOptionsEl.forEach((genderOption) => {
//     genderOption.addEventListener("change", async (e) => {
//       buildDynamicURLParam(
//         "sex",

//         e.currentTarget.dataset.gender,

//         e.currentTarget.checked,
//       );

//       // make request to backend

//       patientList = await getVisitsData(patientsURL);

//       render(patientList);
//     });
//   });

//   // Search fields

//   searchEl.forEach((searchField) => {
//     searchField.addEventListener("input", (e) => {
//       clearTimeout(searchTimeout);

//       searchTimeout = setTimeout(async () => {
//         let value = e.target.value;

//         buildDynamicURLParam("search", value);

//         const data = await performSearch(value);

//         renderPatientSearchResults(data ?? []);

//         return data;
//       });
//     });
//   });
// }

function renderPatientSearchResults(data) {
  const searchResultsHtml = data
    .map((patient) => {
      const htmlElement = `

<li>

<label class="dropdown-item px-2 d-flex align-items-center rounded-1">

<input class="form-check-input m-0 me-2" type="checkbox">

<span class="avatar avatar-xs rounded-circle me-2"><img src="/static/img/users/avatar-5.jpg" class="flex-shrink-0 rounded" alt="img"></span> ${patient.first_name}

${patient.other_names ? `${patient.other_names}` : ""}

${patient.surname}

</label>

</li>

`;

      return htmlElement;
    })
    .join("");

  const resultUlEl = document.querySelector(".search__results");

  // Remove all li elements except the first one (search input)

  while (resultUlEl.children.length > 1) {
    resultUlEl.removeChild(resultUlEl.children[1]);
  }

  // Insert new results after the first li

  resultUlEl.insertAdjacentHTML("beforeend", searchResultsHtml);
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
    const url = patientsURL;

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
  const url = new URL(patientsURL, window.location.origin);

  // search parameter

  if (key === "search") {
    if (value && value.trim()) {
      url.searchParams.set("search", value.trim());
    } else {
      url.searchParams.delete("search");
    }

    patientsURL = url.pathname + url.search;

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

  patientsURL = url.pathname + url.search;
}

console.log(",,,,,,,,,,,,.>>>>>>>>>>>>>>>>>>>>>>>");


window.render = function(patientList) {
  if (!patientsEL) return;

  // 1. Destroy existing instance safely
  if ($.fn.DataTable.isDataTable('.datatable')) {
    $('.datatable').DataTable().clear().destroy();
  }

  // 2. Clear HTML
  patientsEL.innerHTML = "";

  // 3. Build new HTML
  const renderedHTML = patientList.map(patient => renderData(patient)).join("");
  patientsEL.innerHTML = renderedHTML;

  // 4. Re-initialize after DOM is ready
  setTimeout(() => {
    const table = $('.datatable').DataTable({
      dom: 'B<"top"f>rt<"bottom"ip><"clear">',
      pageLength: 25,
      buttons: [
        { extend: 'csv', className: 'buttons-csv d-none' },
        { extend: 'excel', className: 'buttons-excel d-none' },
        { extend: 'pdf', className: 'buttons-pdf d-none' },
        { extend: 'print', className: 'buttons-print d-none' }
      ]
    });

    // Re-bind Export Buttons
    $('.export-csv').off('click').on('click', () => table.button('.buttons-csv').trigger());
    $('.export-excel').off('click').on('click', () => table.button('.buttons-excel').trigger());
    $('.export-pdf').off('click').on('click', () => table.button('.buttons-pdf').trigger());
    $('.export-print').off('click').on('click', () => table.button('.buttons-print').trigger());
  }, 50);
};


/**

* Renders the patient data into html.

* @param {Map} patient

* @returns htmlement

*/

function renderData(patient) {
  // generate urls using base urls and the patient id

  const patientDetailURL = patientDetailBaseUrl.replace("__ID__", patient.id);

  const patientBookLabUrl = patientBookLabBaseUrl.replace("__ID__", patient.id);

  const patientNewVisitUrl = patientNewVisitBaseUrl.replace(
    "__ID__",

    patient.id,
  );

  const appointmentAddUrl = appointmentAddBaseUrl.replace("__ID__", patient.id);

  const htmlElement = `

<tr>

<td class="no-sort">

<div class="form-check form-check-md">

<input class="form-check-input" type="checkbox">

</div>

</td>

<td>${patient.patient_no}</td>

<td>

<div class="d-flex align-items-center">

<div class="ms-0">

<h6 class="mb-0">${patient.full_name}</h6>

${patient.email ? `<small class="text-muted">${patient.email}</small>` : ""}

</div>

</div>

</td>

<td class="no-sort">${patient.sex ? patient.sex : "-"}</td>

<td>${patient.phone ? patient.phone : "-"}</td>

<td class="no-sort">${patient.patient_type}</td>

<td>

${patient.last_visit_date ? `${formatDate(patient.last_visit_date)}` : "-"}

</td>

<td class="no-sort">

<span class="badge bg-success">Active</span>

</td>

<td class="no-sort text-end">

<div class="dropdown">

<a class="btn btn-sm btn-outline-primary dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">

Actions

</a>

<ul class="dropdown-menu dropdown-menu-end">

<li><a class="dropdown-item" href="${patientDetailURL}">View Patient</a></li>

<li><a class="dropdown-item" href="${appointmentAddUrl}">Book Appointment</a></li>

</ul>

</div>

</td>

</tr>

`;

  return htmlElement;
}

/**

* Fetch all patients data

* @returns Array[objects]

*/

async function getVisitsData(url) {
  const res = await fetch(url);

  const data = await res.json();

  return data;
}

function formatDate(date_arg) {
  const date = new Date(date_arg);

  const formatted = date.toISOString().split("T")[0];

  return formatted;
}
