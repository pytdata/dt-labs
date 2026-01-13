//
const visitTableEL = document.querySelector(".list__visits");

let visitsURL = "/api/v1/visits";
let searchTimeout = null;
let activeController = null;

document.addEventListener("DOMContentLoaded", init);

async function init(e) {
  const visitsList = await getPatientsData(visitsURL);
  console.log(visitsList);

  render(visitsList)
}

/**
 * Fetch all patients data
 * @returns Array[objects]
 */
async function getPatientsData(url) {
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
        <td><a href="javascript:void(0);" data-bs-toggle="modal" data-bs-target="#view_modal">${visit.patient.patient_no}</a></td>
        <td>
            <div class="d-flex align-items-center">
                <a href="patient-details.html" class="avatar avatar-xs me-2">
                    <img src="/static/img/users/avatar-5.jpg" alt="img" class="rounded">
                </a>
                <div>
                    <h6 class="fs-14 mb-0 fw-medium"><a href="patient-details.html">${visit.patient.full_name} </a></h6>
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
                    <h6 class="fs-14 mb-0 fw-medium"><a href="doctor-details.html">Dr. ${visit.doctor.full_name}</a></h6>
                </div>
            </div>
        </td>
        <td>${formatDate(visit.visit_date)}</td>
        ${visit.status == "pending" ? `<td><span class="badge badge-soft-primary border border-primary text-primary py-1 ps-1 d-inline-flex align-items-center"><i class="ti ti-point-filled me-0 fs-14"></i>${visit.status}</span></td>` : visit.status == "completed" ? ` <td><span class="badge badge-soft-success border border-success text-success py-1 ps-1 d-inline-flex align-items-center"><i class="ti ti-point-filled me-0 fs-14"></i>${visit.status}</span></td>` : ` <td><span class="badge badge-soft-primary border border-primary text-primary py-1 ps-1 d-inline-flex align-items-center"><i class="ti ti-point-filled me-0 fs-14"></i>${visit.status}</span></td>`}
        
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
                    <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center" data-bs-toggle="modal" data-bs-target="#edit_modal"><i class="ti ti-edit me-1"></i>Edit</a>
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



function formatDate(date_arg) {
  const date = new Date(date_arg);
  const formatted = date.toISOString().split("T")[0];
  return formatted;
}

