let paymentTableEL = document.querySelector(".payment__table");
let totalTransactionEl = document.querySelector(".total__amount");
let searchTransacPatient = document.querySelector(".search__transaction__patient");

let transactionURL = "/api/v1/payments/";

// data

// search
let searchTimeout = null;
let activeController = null;

(async function init() {
  const res = await getRemoteData(transactionURL);
  console.log(res);

  render(res);
})();

/**
 * Fetch remote data
 * @returns Array[objects]
 */
async function getRemoteData(url) {
  const res = await fetch(url);
  const data = await res.json();
  return data;
}


searchTransacPatient.addEventListener("input", (e) => {
   clearTimeout(searchTimeout);
  searchTimeout = setTimeout(async () => {
    const value = e.target.value;
    buildDynamicURLParam("name", value);
    const data = await performSearch(value);
    renderChemistrySearchResults(data);
  }, 300);
})

/**
 * Render a lsit of object as html elements and display in DOM
 * @param {Array[Object]} appointmentsList
 */
function render(transactionList) {
  // total transaction
  totalTransactionEl.textContent = transactionList.length;

  // render patients data into html and join the results into an html string

  const renderedHTML = transactionList
    .map((payment) => {
      return renderData(payment);
    })
    .join("");

  // insert data into DOM
  paymentTableEL.innerHTML = renderedHTML;
}

/**
 * Renders the patient data into html.
 * @param {Map} patient
 * @returns htmlement
 */
function renderData(transaction) {
  console.log(transaction);
  const htmlElement = `
  <tr>
        <td>
            <div class="form-check form-check-md">
                <input class="form-check-input" type="checkbox">
            </div>
        </td>
        <td><a href="javascript:void(0);" data-bs-toggle="modal" data-bs-target="#view_modal">#TS0025</a></td>
        <td>
            <div class="d-flex align-items-center">
                <a href="patient-details.html" class="avatar avatar-xs me-2">
                    <img src="${transaction.invoice.patient.profile_image}" alt="img" class="rounded">
                </a>
                <div>
                    <h6 class="fs-14 mb-0 fw-medium"><a href="patient-details.html">${transaction.invoice.patient.full_name}</a></h6>
                </div>
            </div>
        </td>
        <td>${formatDate(transaction.transaction_date)}</td>
        <td><p class="text-truncate mb-0">${transaction.description ? transaction.description : `Not description`}</p></td>
        <td>${transaction.invoice.amount_paid}</td>
        <td>${transaction.method}</td>

        ${transaction.invoice.status == "paid" ? `<td><span class="badge badge-md badge-soft-success border border-success text-success">${transaction.invoice.status}</span></td>` : `<td><span class="badge badge-md badge-soft-warning border border-warning text-warning">${transaction.invoice.status}</span></td>`}
        
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

function formatDate(dateStr) {
  // "2026-01-13" → "13 Jan, 2026"
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
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
    hour12: true,
  });
}


function buildDynamicURLParam(key, value, state) {
  const url = new URL(transactionURL, window.location.origin);

  // patient filtering parameter
  if (key === "test_category_type") {
    if (value && value) {
      url.searchParams.set("test_category_type", value);
    } else {
      url.searchParams.delete("test_category_type");
    }

    transactionURL = url.pathname + url.search;
    return;
  }

  // test name filtering parameter
  if (key === "name") {
    if (value && value.trim()) {
      url.searchParams.set("name", value.trim());
    } else {
      url.searchParams.delete("name");
    }

    transactionURL = url.pathname + url.search;
    return;
  }

  // department filtering parameter
  if (key === "department") {
    if (value && value.trim()) {
      url.searchParams.set("department", value.trim());
    } else {
      url.searchParams.delete("department");
    }

    transactionURL = url.pathname + url.search;
    return;
  }

  // search parameter
  if (key === "search") {
    if (value && value.trim()) {
      url.searchParams.set("search", value.trim());
    } else {
      url.searchParams.delete("search");
    }

    transactionURL = url.pathname + url.search;
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

  transactionURL = url.pathname + url.search;
}