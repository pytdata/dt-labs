function renderTemplateFields(templates) {
  const container = document.getElementById("template-fields");
  container.innerHTML = "";

  const renderedHTML = templates
    .map((t) => {
      const fields = `
         <tr>
            <th scope="row">${t.test_name}</th>
            <td>
                <input class="form-control form-control-sm result__input" type="textarea">
            </td>
            <td>${t.unit}</td>
           <td class="ref__range" data-min="${t.min_reference_range}" data-max="${t.max_reference_range}"> ${t.min_reference_range} - ${t.max_reference_range}</td>
           <td>
             <input class="form-control form-control-sm" type="textarea">
           </td>
            <td class="result__flag">
             -
           </td>
        </tr>
    `;

      return fields;
    })
    .join("");

  const resultBody = `
    <table class="table">
    <thead>
        <tr>
        <th scope="col">TEST NAME</th>
        <th scope="col">RESULT</th>
        <th scope="col">UNIT</th>
        <th scope="col">REFERENCE RANGE</th>
        <th scope="col">COMMENT</th>
        <th scope="col">FLAG</th>
        </tr>
    </thead>
    <tbody class="show__results">
        ${renderedHTML}
    </tbody>
    </table>
    `;

  container.innerHTML = resultBody;
}

async function loadTemplates(testId) {
  try {
    const res = await fetch(`/api/v1/tests-templates/by-test/${testId}`);
    if (!res.ok) throw new Error("Failed to fetch data");
    const templates = await res.json();
    console.log(templates, "temp source data");
    renderTemplateFields(templates);
  } catch (error) {
    alert(error);
  }
}

labTestsContainerEl.addEventListener("click", async (e) => {
  const button = e.target.closest(".edit__btn");
  console.log(button);
  if (!button) return;

  const labResultId = +button.dataset.labresultId;
  const testNo = button.dataset.testNo;
  const testName = button.dataset.testName;
  const testId = +button.dataset.testId;

  // get lab result id in form element to be used later for updating
  document.querySelector("#test__result__form").dataset.id = labResultId;
  document.querySelector("#test__result__form").dataset.testNo = testNo;
  document.querySelector("#test__result__form").dataset.testName = testName;

  console.log(testId, "test id is =====");

  await loadTemplates(testId);

  document.querySelector(".show__results").addEventListener("input", (e) => {
    const input = e.target.closest(".result__input");
    if (!input) return;

    // get the row the input belongs to
    const row = input.closest("tr");

    const rangeEl = row.querySelector(".ref__range");
    const flagEl = row.querySelector(".result__flag");

    const minRange = parseFloat(rangeEl.dataset.min);
    const maxRange = parseFloat(rangeEl.dataset.max);
    const value = parseFloat(input.value);

    if (isNaN(value)) {
      flagEl.innerHTML = "-";
      return;
    }

    if (value >= minRange && value <= maxRange) {
      flagEl.innerHTML = `<span class="badge bg-success">N</span>`;
    } else if (value > maxRange) {
      flagEl.innerHTML = `<span class="badge bg-danger">H</span>`;
    } else {
      flagEl.innerHTML = `<span class="badge bg-warning">L</span>`;
    }
  });
});

function serializeLabResultForm() {
  const rows = document.querySelectorAll(".show__results tr");

  const results = [];

  rows.forEach((row) => {
    const fieldName = row.querySelector("th").innerText.trim();

    const resultValue = row.querySelector(".result__input")?.value.trim() || "";

    const unit = row.children[2].innerText.trim();

    const refRangeCell = row.querySelector(".ref__range");
    const referenceRange = refRangeCell?.innerText.trim() || "";

    const dataMin = refRangeCell.dataset.min;
    const dataMax = refRangeCell.dataset.max;

    console.log(dataMax, dataMin);

    const comment = row.children[4].querySelector("input")?.value.trim() || "";

    results.push({
      field_name: fieldName,
      result: resultValue,
      unit: unit,
      reference_range: referenceRange,
      comment: comment,
      ref_min: parseFloat(dataMin),
      ref_max: parseFloat(dataMax),
    });
  });

  return {
    fields: results,
  };
}

async function submitLabResults(testId, testName, labID) {
  const result_data = serializeLabResultForm();

  const payload = {
    test_name_type: testName,
    test_code: testId,
    result: [...result_data.fields],
  };

  console.log(payload);
  try {
    const res = await fetch(`/api/v1/tests/${labID}`, {
      headers: {
        "Content-Type": "application/json",
      },
      method: "PATCH",
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error("Failed to update lab results.");

    const data = await res.json();
    console.log(data);
  } catch (error) {
    console.log(error);
  }
}

document.querySelector("#edit_modal form").addEventListener("submit", (e) => {
  e.preventDefault();

  const testId = document.querySelector("#test__result__form").dataset.testNo;
  const testName = document.querySelector("#test__result__form").dataset
    .testName;
  const labID = +document.querySelector("#test__result__form").dataset.id;

  submitLabResults(testId, testName, labID);
});

labTestsContainerEl.addEventListener("click", async (e) => {
  const button = e.target.closest(".edit__btn");
  if (!button) return;

  const labResultId = +button.dataset.labresultId;
  const testNo = button.dataset.testNo;
  const testName = button.dataset.testName;
  const testId = button.dataset.testId;

  // get lab result id in form element to be used later for updating
  document.querySelector("#test__result__form").dataset.id = labResultId;
  document.querySelector("#test__result__form").dataset.testNo = testNo;
  document.querySelector("#test__result__form").dataset.testName = testName;
  document.querySelector("#test__result__form").dataset.testId = testId;

  try {
    const res = await fetch(`/api/v1/tests/${labResultId}/`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) throw new Error("Failed to fetch labresult: ", res);

    const labresults = await res.json();

    populateLabResultModal(labresults, testName);
    renderSavedLabResultsInModal(labresults.results);
  } catch (error) {
    console.log(error);
  }
});

function renderSavedLabResultsInModal(jsonString) {
  const parsed =
    typeof jsonString === "string" ? JSON.parse(jsonString) : jsonString;

  const container = document.querySelector("#template-fields");
  container.innerHTML = "";

  const renderedHTML = parsed.result
    .map((item) => {
      let flagBadge = "";

      const value = parseFloat(item.result);

      if (!isNaN(value)) {
        if (value > item.ref_max) {
          flagBadge = `<span class="badge bg-secondary">H</span>`;
        } else if (value < item.ref_min) {
          flagBadge = `<span class="badge bg-warning">L</span>`;
        } else {
          flagBadge = `<span class="badge bg-primary">N</span>`;
        }
      }

      const fields = `
         <tr>
            <th scope="row">${item.field_name}</th>
            <td>
                <input class="form-control form-control-sm result__input" type="textarea" value="${item.result}">
            </td>
            <td>${item.unit}</td>
           <td class="ref__range" data-min="${item.ref_min}" data-max="${item.ref_max}"> ${item.ref_min} - ${item.ref_max}</td>
           <td>
             <input class="form-control form-control-sm" type="textarea" value="${item.comment}">
           </td>
            <td class="result__flag">
             ${flagBadge}
           </td>
        </tr>
    `;

      return fields;
    })
    .join("");

  const resultBody = `
    <table class="table">
    <thead>
        <tr>
        <th scope="col">TEST NAME</th>
        <th scope="col">RESULT</th>
        <th scope="col">UNIT</th>
        <th scope="col">REFERENCE RANGE</th>
        <th scope="col">COMMENT</th>
        <th scope="col">FLAG</th>
        </tr>
    </thead>
    <tbody class="show__results">
        ${renderedHTML}
    </tbody>
    </table>
    `;

  container.innerHTML = resultBody;
}

function computeFlag(value, min, max) {
  if (value > max) return "H";
  if (value < min) return "L";
  return "N";
}
