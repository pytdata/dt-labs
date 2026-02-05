let invoiceContainerEL = document.querySelector(".invoice__container");
let totalInvoiceEl = document.querySelector(".total__invoices");

let invoiceURL = "/api/v1/payments/invoices";

(async function init() {
  const res = await getRemoteData(invoiceURL);
  console.log(res);

  render(res);
})();


/**
 * Render a lsit of object as html elements and display in DOM
 * @param {Array[Object]} appointmentsList
 */
function render(invoiceList) {
  // total transaction
  totalInvoiceEl.textContent = invoiceList.length;

  // render patients data into html and join the results into an html string

  const renderedHTML = invoiceList
    .map((payment) => {
      return renderData(payment);
    })
    .join("");

  // insert data into DOM
  invoiceContainerEL.innerHTML = renderedHTML;
}


/**
 * Renders the patient data into html.
 * @param {Map} patient
 * @returns htmlement
 */
function renderData(invoice) {
  console.log(invoice);
  const htmlElement = `
     <tr>
        <td>
            <div class="form-check form-check-md">
                <input class="form-check-input" type="checkbox">
            </div>
        </td>
        <td>
            <a href="invoice-details.html" class="tb-data">INV-1454</a>
        </td>
        <td>
            <div class="d-flex align-items-center">
                <a href="invoice-details.html" class="avatar avatar-lg me-2">
                    <img src="/static/img/users/user-01.jpg" class="rounded-circle" alt="user">
                </a>
                <div>
                    <h6 class="fw-medium mb-1 fs-14"><a href="invoice-details.html">${invoice.patient.full_name}</a>
                    </h6>
                    <span class="fs-12"><a href="/cdn-cgi/l/email-protection" class="__cf_email__" data-cfemail="2c4d4258444342556c49544d415c4049024f4341">${invoice.patient.email}</a></span>
                </div>
            </div>
        </td>
        <td>${formatDate(invoice.created_at)} </td>
        <td>${invoice.total_amount}</td>
        <td>$0</td>
        <td>14 Jan 2024, 04:27 AM</td>
        <td>
        ${invoice.status == "paid" ? `<span class="badge badge-soft-success d-inline-flex align-items-center">
                <i class="ti ti-point-filled me-1"></i>${invoice.status}
            </span>` : `<span class="badge badge-soft-danger d-inline-flex align-items-center">
														<i class="ti ti-point-filled me-1"></i>${invoice.status}
													</span>`}
            
        </td>
        <td>
            <div class="action-icon d-inline-flex">
                <a href="invoice-details.html" class="me-2"><i class="ti ti-eye"></i></a>
              <!--  <a href="#delete_modal" class="" data-bs-toggle="modal" data-bs-target="#delete_modal"><i class="ti ti-trash"></i></a> -->
            </div>
        </td>
    </tr>

                                   
`;
  return htmlElement;
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
