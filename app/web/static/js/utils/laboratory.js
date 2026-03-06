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



function populateLabResultModal(data, testName) {
 document.querySelector("#test__result__form .test__name").value = testName;

 console.log(data)
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
    alert("Failed to fetch data")
    console.error(error)
  }
}



/**
 * Renders the Radiology item into html row.
 */
function renderData(item) {
  // Determine badge color based on status
  const statusColors = {
    "awaiting_results": "badge-soft-warning text-warning border-warning",
    "in_progress": "badge-soft-primary text-primary border-primary",
    "completed": "badge-soft-success text-success border-success"
  };
  const statusClass = statusColors[item.status] || "badge-soft-secondary text-secondary";
  const statusText = item.status.replace("_", " ").toUpperCase();

  return `  
  <tr class="align-middle">
    <td>
        <div class="form-check form-check-md">
            <input class="form-check-input" type="checkbox">
        </div>
    </td>
    <td class="fw-bold text-dark">#ORD-${item.id}</td>
    <td>
        <div class="d-flex flex-column">
            <span class="text-dark fw-medium">${item.order.appointment.patient.full_name}</span>
            <small class="text-muted">${item.order.appointment.patient.patient_no}</small>
        </div>
    </td>
    <td>${item.test.name}</td>
    <td>
        <span class="text-uppercase small fw-bold text-muted">
            <i class="ti ti-scan me-1"></i>${item.test.category?.name || 'Radiology'}
        </span>
    </td>
    <td>${formatDate(item.created_at)}</td>
    <td>
        <span class="badge badge-md ${statusClass}">${statusText}</span>
    </td>
    <td class="text-end">
        <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown">
            <i class="ti ti-dots-vertical"></i>
        </a>
        <ul class="dropdown-menu p-2 shadow-sm">
            <li>
                <a href="javascript:void(0);" 
                   class="dropdown-item d-flex align-items-center" 
                   onclick="openRadiologyResultModal(${item.id}, '${item.test.name}')">
                   <i class="ti ti-edit-circle me-2"></i>Enter Findings
                </a>
            </li>
            <li>
                <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center text-danger" href="#">
                   <i class="ti ti-ban me-2"></i>Cancel Test
                </a>
            </li>
        </ul>
    </td>
</tr>
  `;
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



// const laboratoryURL = "/api/v1/tests/active-appointments/";

// // DOM ELEMENTS
// const labTestsContainerEl = document.querySelector(".labtest__container");
// const editSubmitFormEl = document.querySelector("#test__result__form");
// const totalLabTestsEl = document.querySelector("#total__test__count");


// (async function init() {
//   const res = await getRemoteData(laboratoryURL);
//   console.log(res)
//   render(res);

// })();



// function populateLabResultModal(data, testName) {
//  document.querySelector("#test__result__form .test__name").value = testName;

//  console.log(data)
// //  if (!data.results) return;

// //  document.querySelector("#test__result__form .result__data").value = data.results.result;
// // document.querySelector("#test__result__form .data__comment").value = data.results.comment ? data.results.comment : '';
// // document.querySelector("#test__result__form .data__unit").value = data.results.unit;
// // document.querySelector("#test__result__form .data__range").value = data.results.ref_range;

// }


// /**
//  * Render a lsit of object as html elements and display in DOM
//  * @param {Array[Object]} appointmentsList
//  */
// function render(labList) {

//   totalLabTestsEl.textContent = labList.length;

//   // render patients data into html and join the results into an html string
//   const renderedHTML = labList
//     .map((lab) => {
//       return renderData(lab);
//     })
//     .join("");

//   // insert data into DOM
//   labTestsContainerEl.innerHTML = renderedHTML;
// }


// /**
//  * Fetch remote data
//  * @returns Array[objects]
//  */
// async function getRemoteData(url) {
//   try {
//     const res = await fetch(url);
//     if (!res.ok) throw new Error("Failed to fetch data.")
//     const data = await res.json();
//     return data;
//   } catch (error) {
//     // TODO: Add toast notification
//     alert("Failed to fetch data")
//     console.error(error)
//   }
// }




// /**
//  * Renders the patient data into html.
//  * @param {Map} patient
//  * @returns htmlement
//  */
// function renderData(labresult) {
//   console.log(labresult)
//   const htmlElement = `  
//   <tr>
//     <td>
//         <div class="form-check form-check-md">
//             <input class="form-check-input" type="checkbox">
//         </div>
//     </td>
//     <td><a href="javascript:void(0);" data-bs-toggle="modal" data-bs-target="#view_modal">${labresult.test_no ? labresult.test_no : '-'}</a></td>
//         <td><a href="javascript:void(0);" data-bs-toggle="modal" data-bs-target="#view_modal">${labresult.patient_no}</a></td>
//     <td>${labresult.test_name}</td>
//     <td>${labresult.test_duration ? labresult.test_duration : '-'}</td>
//     <td>${formatDate(labresult.created_at)}</td>
//     <!-- <td>Anaesthesiology</td> -->
//     <td>${labresult.amount}</td>
//     <td><span class="badge badge-md badge-soft-success border border-success text-success">${labresult.result_status}</span></td>
//     <td class="text-end">
//         <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown"><i class="ti ti-dots-vertical"></i></a>
//         <ul class="dropdown-menu p-2">

//             <li>
//                 <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center edit__btn" data-bs-toggle="modal" data-bs-target="#edit_modal" data-labresult-id="${labresult.lab_result_id}" data-test-no="${labresult.test_no}" data-test-name="${labresult.test_name}" data-test-id="${labresult.test_id}"><i class="ti ti-edit me-1"></i>Edit</a>
//             </li>
           
//         </ul>
//     </td>
// </tr>
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

