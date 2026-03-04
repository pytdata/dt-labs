// DOM ELEMENTS
const phlebotomyContainerEl = document.querySelector(".phlebotomy__container");


let phlebotomyURL = `/api/v1/phlebotomy/pending`;

(async function init() {
  const res = await getRemoteData(phlebotomyURL);
  console.log(res)
//   totalNumOfAppointments = res.length;
  render(res);
})();

/**
 * Fetch all data
 * @returns Array[objects]
 */
async function getRemoteData(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch data");
    const data = await res.json();
    return data;
  } catch (error) {
    alert(error);
  }
}



/**
 * Render a lsit of object as html elements and display in DOM
 * @param {Array[Object]} phlebotomy
 */
function render(phlebotomyList) {
  // render patients data into html and join the results into an html string
  const renderedHTML = phlebotomyList
    .map((phlebotomy) => {
      return renderData(phlebotomy);
    })
    .join("");

  // insert data into DOM
  phlebotomyContainerEl.innerHTML = renderedHTML;
}



/**
 * Renders the patient data into html.
 * @param {Map} patient
 * @returns htmlement
 */
function renderData(phlebotomy) {
  const htmlElement = ` 
  <tr>
        <td>
            <div class="form-check form-check-md">
                <input class="form-check-input" type="checkbox">
          </div>
      </td>
        <td><a href="javascript:void(0);" data-bs-toggle="modal" data-bs-target="#view_modal">${phlebotomy.appointment.patient.patient_no}</a></td>
        <td>${phlebotomy.appointment.patient.first_name} ${phlebotomy.appointment.patient.surname}</td>
        <td>${formatDate(phlebotomy.created_at)}</td>
        <td>${phlebotomy.collection_site}</td>
        <td><span class="badge badge-md badge-soft-success border border-success text-success">${phlebotomy.status}</span></td>
        <td class="text-end">
            <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown"><i class="ti ti-dots-vertical"></i></a>
            <ul class="dropdown-menu p-2">
                <li>
                    <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center" data-bs-toggle="modal" data-bs-target="#view_modal" onclick="openDetailSamplesModal(${phlebotomy.id})"><i class="ti ti-eye me-1"></i>View Details</a>
              </li>
                <li>
                    <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center" data-bs-toggle="modal" data-bs-target="#addSamplesModal" onclick="openSampleModal(${phlebotomy.id}, ${phlebotomy.appointment.id}, ${phlebotomy.appointment.patient.id})"><i class="ti ti-edit me-1"></i>Add Sample</a>
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



function formatDate(dateStr) {
  // "2026-01-13" → "13 Jan, 2026"
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}




async function openDetailSamplesModal(phlebotomyId) {

    const container = document.getElementById("samplesContainer");

    container.innerHTML = `
        <div class="text-center py-4">
            <span class="text-muted">Loading samples...</span>
        </div>
    `;

    const modal = new bootstrap.Modal(
        document.getElementById("viewSamplesModal")
    );

    modal.show();

    try {
        const response = await fetch(
            `/api/v1/phlebotomy/${phlebotomyId}/samples/`
        );

        if (!response.ok) {
            throw new Error("Failed to fetch samples");
        }

        const samples = await response.json();

        if (samples.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4 text-muted">
                    No samples added yet.
                </div>
            `;
            return;
        }

        let tableHTML = `
            <table class="table table-bordered table-sm align-middle">
                <thead class="table-light">
                    <tr>
                        <th>Sample Type</th>
                        <th>Test</th>
                        <th>Priority</th>
                        <th>Storage</th>
                        <th>Condition</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
        `;

        samples.forEach(sample => {

            if (!sample.tests || sample.tests.length === 0) {

                // tableHTML += `
                //     <tr>
                //         <td>${sample.sample_type}</td>
                //         <td class="text-muted">No tests</td>
                //         <td>${sample.priority ?? '-'}</td>
                //         <td>${sample.storage_location ?? '-'}</td>
                //         <td>${sample.sample_condition ?? '-'}</td>
                //         <td>-</td>
                //     </tr>
                // `;

                // continue

            } else {

                sample.tests.forEach(test => {
                    tableHTML += `
                        <tr>
                            <td>${sample.sample_type}</td>
                            <td>${test.name}</td>
                            <td>${sample.priority ?? '-'}</td>
                            <td>${sample.storage_location ?? '-'}</td>
                            <td>${sample.sample_condition ?? '-'}</td>
                            <td>
                                <button class="btn btn-sm btn-danger"
                                    onclick="deleteSampleTest(${test.sample_test_id}, ${phlebotomyId})">
                                    Remove
                                </button>
                            </td>
                        </tr>
                    `;
                });

            }
        });

        tableHTML += `</tbody></table>`;
        container.innerHTML = tableHTML;

    } catch (error) {
        container.innerHTML = `
            <div class="text-danger text-center py-4">
                Error loading samples.
            </div>
        `;
        console.error(error);
    }
}





async function deleteSampleTest(sampleTestId, phlebotomyId) {

    if (!confirm("Are you sure you want to remove this test from the sample?")) {
        return;
    }

    try {
        const response = await fetch(
            `/api/v1/phlebotomy/sample-tests/${sampleTestId}`,
            {
                method: "DELETE"
            }
        );

        if (!response.ok) {
            alert("Failed to remove test");
            return;
        }

        // Reload modal content correctly
        openDetailSamplesModal(phlebotomyId);

    } catch (error) {
        console.error(error);
        alert("Error removing test");
    }
}