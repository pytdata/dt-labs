const laboratoryURL = "/api/v1/tests/active-appointments/";

// DOM ELEMENTS
const labTestsContainerEl = document.querySelector(".labtest__container");
const editSubmitFormEl = document.querySelector("#test__result__form");
const totalLabTestsEl = document.querySelector("#total__test__count");


(async function init() {
  const res = await getRemoteData(laboratoryURL);
  console.log(res)
  render(res);

})();

console.log("Test counts: ", totalTests);

// edit lab result
// editSubmitFormEl.addEventListener("submit", async (e) => {
//   e.preventDefault();


//   const formdata = new FormData(editSubmitFormEl);
  
//   const labID = +document.querySelector("#test__result__form").dataset.id;
//   const testId = document.querySelector("#test__result__form").dataset.testNo;
//   const testName = document.querySelector("#test__result__form").dataset.testName;

//   console.log(labID, testId, testName);

//   const payload = {
//     "test_name_type": testName,
//     "test_code": testId,
//     "result": formdata.get("result"),
//     "unit": formdata.get("unit"),
//     "ref_range": formdata.get("range"),
//     "comment": formdata.get("comment"),
//   }

//   console.log(payload)

//   try {
//     const res = await fetch(`/api/v1/tests/${labID}`, {
//       headers: {
//         "Content-Type":"application/json",
//       },
//       method: "PATCH",
//       body: JSON.stringify(payload)
//     });

//     if (!res.ok) throw new Error("Failed to update lab results.");

//     const data = await res.json();
//     console.log(data);
//   } catch (error) {
//     console.log(error) 
//   }
// });

// labTestsContainerEl.addEventListener("click", async (e) => {
//   const button = e.target.closest(".edit__btn");
//   console.log(button)
//   if (!button) return;

//   const labResultId = +button.dataset.labresultId;
//   const testNo = button.dataset.testNo;
//   const testName = button.dataset.testName;
//   const testId = button.dataset.testId;

//   console.log(testNo, testName, "======== results ========")
//   // get lab result id in form element to be used later for updating
//   document.querySelector("#test__result__form").dataset.id = labResultId;
//   document.querySelector("#test__result__form").dataset.testNo = testNo;
//   document.querySelector("#test__result__form").dataset.testName = testName;
//   document.querySelector("#test__result__form").dataset.testId =testId;

//   console.log(labResultId, "id is =====")
  
//   try {
//       const res = await fetch(`/api/v1/tests/${labResultId}/`, {
//         method: "GET",
//         headers: { "Content-Type": "application/json" },
//       });
//       if (!res.ok) throw new Error("Failed to fetch labresult: ", res);
//       const labresults = await res.json();

//       populateLabResultModal(labresults, testName)
//       console.log(labresults, "==================");
//   } catch (error) {
//     console.log(error)
//   }
// });


function populateLabResultModal(data, testName) {
 document.querySelector("#test__result__form .test__name").value = testName;
//  if (!data.results) return;

//  document.querySelector("#test__result__form .result__data").value = data.results.result;
// document.querySelector("#test__result__form .data__comment").value = data.results.comment ? data.results.comment : '';
// document.querySelector("#test__result__form .data__unit").value = data.results.unit;
// document.querySelector("#test__result__form .data__range").value = data.results.ref_range;

}


/**
 * Render a lsit of object as html elements and display in DOM
 * @param {Array[Object]} appointmentsList
 */
function render(labList) {

  totalLabTestsEl.textContent = labList.length;

  // render patients data into html and join the results into an html string
  const renderedHTML = labList
    .map((lab) => {
      return renderData(lab);
    })
    .join("");

  // insert data into DOM
  labTestsContainerEl.innerHTML = renderedHTML;
}


/**
 * Fetch remote data
 * @returns Array[objects]
 */
async function getRemoteData(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch data.")
    const data = await res.json();
    return data;
  } catch (error) {
    // TODO: Add toast notification
    console.error(error)
  }
}




/**
 * Renders the patient data into html.
 * @param {Map} patient
 * @returns htmlement
 */
function renderData(labresult) {
  console.log(labresult)
  const htmlElement = `  
  <tr>
    <td>
        <div class="form-check form-check-md">
            <input class="form-check-input" type="checkbox">
        </div>
    </td>
    <td><a href="javascript:void(0);" data-bs-toggle="modal" data-bs-target="#view_modal">${labresult.test_no ? labresult.test_no : '-'}</a></td>
        <td><a href="javascript:void(0);" data-bs-toggle="modal" data-bs-target="#view_modal">${labresult.patient_no}</a></td>
    <td>${labresult.test_name}</td>
    <td>${labresult.test_duration ? labresult.test_duration : '-'}</td>
    <td>${formatDate(labresult.created_at)}</td>
    <!-- <td>Anaesthesiology</td> -->
    <td>${labresult.amount}</td>
    <td><span class="badge badge-md badge-soft-success border border-success text-success">${labresult.result_status}</span></td>
    <td class="text-end">
        <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown"><i class="ti ti-dots-vertical"></i></a>
        <ul class="dropdown-menu p-2">
            <li>
                <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center" data-bs-toggle="modal" data-bs-target="#view_modal"><i class="ti ti-eye me-1"></i>View Details</a>
            </li>
            <li>
                <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center edit__btn" data-bs-toggle="modal" data-bs-target="#edit_modal" data-labresult-id="${labresult.lab_result_id}" data-test-no="${labresult.test_no}" data-test-name="${labresult.test_name}" data-test-id="${labresult.test_id}"><i class="ti ti-edit me-1"></i>Edit</a>
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