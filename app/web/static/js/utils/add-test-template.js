// DOM Elements
const testsDropDownEl = document.getElementById("test_type");
const addTemplateBtn = document.getElementById("add__template__btn");
const addFieldBtn = document.querySelector(".btn-success");
const dynamicFieldsContainer = document.querySelector("#dynamic-fields");
const submitBtn = document.querySelector("#submitForm");
const testTemplatesViewContainerEL = document.querySelector(
  ".view__test__templates",
);

let currentMode = "create"; // "create" | "edit"
let currentEditTestId = null;


// URL
let testURL = "/api/v1/tests/tests/";
let testTemplates = "/api/v1/tests-templates/";

(async function init() {
  const res = await getRemoteData(testTemplates);
  renderTemplates(res);
})();

function renderTemplates(data) {
  const renderedHTML = data
    .map((e) => {
      return `
      <tr>
        <th scope="row">${formatDate(e.created_on)}</th>
        <td>${e.test.name}</td>
        <td>
          <span class="mx-3">
            <button
              class="btn btn-info edit-template-btn"
              data-test-id="${e.test.id}"
              data-template-id="${e.id}"
            >
              Edit Template
            </button>
          </span>

          <span>
            <button
              class="btn btn-outline-danger delete-template-btn"
              data-template-id="${e.id}"
            >
              Delete
            </button>
          </span>
        </td>
        <td>${e.id}</td>
      </tr>
    `;
    })
    .join("");

  testTemplatesViewContainerEL.innerHTML = renderedHTML;
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

/**
 * Fetch all test data
 * @returns Array[objects]
 */
async function getRemoteData(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch data", res);

    const data = await res.json();
    console.log(data);
    return data;
  } catch (error) {
    console.log("Error getting test data");
  }
}

// Add first field automatically when modal opens
addField();

addFieldBtn.addEventListener("click", () => {
  addField();
});

// listen to event on the add template button and call the method to fetch and render the data;

addTemplateBtn.addEventListener("click", async (_) => {
  renderTestOptions();
});

/**
 * Takes a list of data from the remote call and renders them to html that is inserted into the DOM
 * @returns null
 */
async function renderTestOptions() {
  // fetch test data
  const data = await getRemoteData(testURL);

  if (data) {
    const renderedHTML = data
      .map((test) => {
        return `
             <option class="test_template_opt" value="${test.id}" >${test.name}</option>
            `;
      })
      .join("");
    testsDropDownEl.innerHTML = renderedHTML;
    return;
  }

  // else
  testsDropDownEl.innerHTML =
    " <option>No Test available. A test is needed to be added before a template</option>";
}



function addField(existingData = null) {
  const fieldHTML = `
    <div class="card mb-3 field-block p-3">
      <div class="row mb-2">
        <div class="col-md-6">
          <label class="form-label">Test Name</label>
          <input type="text" class="form-control test_name"
            value="${existingData?.test_name || ""}">
        </div>

        <div class="col-md-6">
          <label class="form-label">Short Code</label>
          <input type="text" class="form-control short_code"
            value="${existingData?.short_code || ""}">
        </div>
      </div>

      <div class="row mb-2">
        <div class="col-md-4">
          <label class="form-label">Unit</label>
          <input type="text" class="form-control unit"
            value="${existingData?.unit || ""}">
        </div>

        <div class="col-md-4">
          <label class="form-label">Min Reference Range</label>
          <input type="number" step="any" class="form-control min_range"
            value="${existingData?.min_reference_range || ""}">
        </div>

        <div class="col-md-4">
          <label class="form-label">Max Reference Range</label>
          <input type="number" step="any" class="form-control max_range"
            value="${existingData?.max_reference_range || ""}">
        </div>
      </div>

      <button type="button" class="btn btn-sm btn-danger remove-field">
        Remove
      </button>
    </div>
  `;

  dynamicFieldsContainer.insertAdjacentHTML("beforeend", fieldHTML);
}



dynamicFieldsContainer.addEventListener("click", (e) => {
  if (e.target.classList.contains("remove-field")) {
    e.target.closest(".field-block").remove();
  }
});

// submitBtn.addEventListener("click", async () => {
//   const testTypeId = document.querySelector("#test_type").value;

//   if (!testTypeId) {
//     alert("Select a test type first");
//     return;
//   }

//   const fieldBlocks = document.querySelectorAll(".field-block");

//   const payload = [];

//   fieldBlocks.forEach((block) => {
//     payload.push({
//       test_id: parseInt(testTypeId),
//       test_name: block.querySelector(".test_name").value.trim(),
//       short_code: block.querySelector(".short_code").value.trim(),
//       unit: block.querySelector(".unit").value.trim(),
//       min_reference_range: parseFloat(block.querySelector(".min_range").value),
//       max_reference_range: parseFloat(block.querySelector(".max_range").value),
//     });
//   });

//   try {
//     const response = await fetch("/api/v1/tests-templates/bulk", {
//       method: "POST",
//       headers: {
//         "Content-Type": "application/json",
//       },
//       body: JSON.stringify(payload),
//     });

//     if (!response.ok) {
//       console.log(response);
//       throw new Error("Failed to save templates");
//     }

//     alert("Templates created successfully");

//     location.reload();
//   } catch (err) {
//     console.error(err);
//     alert("Error creating templates");
//   }
// });




submitBtn.addEventListener("click", async () => {
  const testTypeId = document.querySelector("#test_type").value;

  if (!testTypeId) {
    alert("Select a test type first");
    return;
  }

  const fieldBlocks = document.querySelectorAll(".field-block");

  const payload = [];

  fieldBlocks.forEach((block) => {
    payload.push({
      test_id: parseInt(testTypeId),
      test_name: block.querySelector(".test_name").value.trim(),
      short_code: block.querySelector(".short_code").value.trim(),
      unit: block.querySelector(".unit").value.trim(),
      min_reference_range: parseFloat(block.querySelector(".min_range").value),
      max_reference_range: parseFloat(block.querySelector(".max_range").value),
    });
  });

  try {
    let response;

    if (currentMode === "create") {
      response = await fetch("/api/v1/tests-templates/bulk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } else {
      response = await fetch(
        `/api/v1/tests-templates/by-test/${currentEditTestId}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );
    }

    if (!response.ok) throw new Error("Failed operation");

    alert(
      currentMode === "create"
        ? "Templates created successfully"
        : "Templates updated successfully"
    );

    location.reload();
  } catch (err) {
    console.error(err);
    alert("Error saving templates");
  }
});




testTemplatesViewContainerEL.addEventListener("click", async (e) => {
  const btn = e.target.closest(".edit-template-btn");
  if (!btn) return;

  currentMode = "edit";
  currentEditTestId = +btn.dataset.testId;

  // Change modal title
  document.getElementById("exampleModalLabel").innerText =
    "Edit Test Template";

  // Fetch templates for that test
  const templates = await getRemoteData(
    `/api/v1/tests-templates/by-test/${currentEditTestId}`
  );

  // Clear previous dynamic fields
  dynamicFieldsContainer.innerHTML = "";

  // Populate with existing fields
  templates.forEach((template) => {
    addField(template); // pass existing data
  });

  // Set test dropdown to selected test
  testsDropDownEl.value = currentEditTestId;

  const modal = new bootstrap.Modal(
    document.getElementById("exampleModal")
  );
  modal.show();
});
