const labResultsContainerEl = document.querySelector(".lab__container");
const totalLabResultsEl = document.querySelector(".lab__results__total");

let labResultsURL = "/api/v1/patients/lab-results";

(async function init() {
  const res = await getRemoteData(labResultsURL);
  totalLabResultsEl.textContent = res.length;
  console.log(res.length);
    render(res);
})();

/**
 * Fetch all lab-results data
 * @returns Array[objects]
 */
async function getRemoteData(url) {
  try {
    const res = await fetch(url);

    if (!res.ok) throw new Error("Failed to fetch data");
    const data = await res.json();
    return data;
  } catch (error) {
    console.error(error);
  }
}

/**
 * Render a lsit of object as html elements and display in DOM
 * @param {Array[Object]} labResultsList
 */
function render(labResultsList) {
  // render patients data into html and join the results into an html string
  const renderedHTML = labResultsList
    .map((labResults) => {
      return renderData(labResults);
    })
    .join("");

  // insert data into DOM
  labResultsContainerEl.innerHTML = renderedHTML;
}

/**
 * Render a lsit of object as html elements and display in DOM
 * @param {Array[Object]} labResultsList
 */
function render(labResultsList) {
  // render patients data into html and join the results into an html string
  const renderedHTML = labResultsList
    .map((labReults) => {
      return renderData(labReults);
    })
    .join("");

  // insert data into DOM
  labResultsContainerEl.innerHTML = renderedHTML;
}

/**
 * Renders the patient data into html.
 * @param {Map} patient
 * @returns htmlement
 */
function renderData(latResults) {
  console.log(latResults)
  const htmlElement = `
       <tr>
            <td>
                <div class="form-check form-check-md">
                    <input class="form-check-input" type="checkbox">
                </div>
            </td>
            <td><a href="javascript:void(0);" data-bs-toggle="modal" data-bs-target="#view_modal">#TE0025</a></td>
            <td>
                <div class="d-flex align-items-center">
                    <a href="patient-details.html" class="avatar avatar-xs me-2">
                        <img src="/static/img/users/avatar-5.jpg" alt="img" class="rounded">
                    </a>
                    <div>
                        <h6 class="fs-14 mb-0 fw-medium"><a href="patient-details.html">James Carter</a></h6>
                    </div>
                </div>
            </td>
            <td>Male</td>
            <td>17 Jun 2025</td>
            <td>
                <div class="d-flex align-items-center">
                    <a href="doctor-details.html" class="avatar avatar-xs me-2">
                        <img src="/static/img/doctors/doctor-01.jpg" alt="img" class="rounded">
                    </a>
                    <div>
                        <h6 class="fs-14 mb-0 fw-medium"><a href="doctor-details.html">Dr. Andrew Clark</a></h6>
                    </div>
                </div>
            </td>
            <td>Blood Test</td>
            <td><span class="badge badge-md badge-soft-success border border-success text-success">Received</span></td>
            <td class="text-end">
                <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown"><i class="ti ti-dots-vertical"></i></a>
                <ul class="dropdown-menu p-2">
                    <li>
                        <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center" data-bs-toggle="modal" data-bs-target="#view_modal"><i class="ti ti-eye me-1"></i>View Details</a>
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
