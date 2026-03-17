let invoiceContainerEL = document.querySelector(".invoice__container");
let totalInvoiceEl = document.querySelector(".total__invoices");

let invoiceURL = "/api/v1/payments/invoices";

(async function init() {
  const res = await getRemoteData(invoiceURL);
  console.log(res);

  render(res);
})();


/**cp = CompanyProfile(name="YKG LAB & DIAGNOSTIC CENTER")
        # db.add(cp)
        # await db.commit()
        # await db.refresh(cp)
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
  const statusClass = invoice.status.toLowerCase() === "paid" ? "badge-soft-success" : "badge-soft-danger";
  
  return `
     <tr>
        <td><div class="form-check form-check-md"><input class="form-check-input" type="checkbox"></div></td>
        <td>
            <a href="javascript:void(0);" onclick="viewInvoiceDetail(${invoice.id})" class="tb-data fw-bold text-primary">#INV-${invoice.id}</a>
        </td>
        <td>
            <div class="d-flex align-items-center">
                <div class="avatar avatar-md me-2">
                    <img src="${invoice.patient.profile_image || '/static/img/default-user.png'}" class="rounded-circle" alt="user">
                </div>
                <div>
                    <h6 class="fw-medium mb-0 fs-14">${invoice.patient.full_name}</h6>
                    <small class="text-muted">${invoice.patient.patient_no}</small>
                </div>
            </div>
        </td>
        <td>${formatDate(invoice.created_at)}</td>
        <td class="fw-bold">${Number(invoice.total_amount).toLocaleString()}</td>
        <td>$0</td>
        <td>${formatDate(invoice.updated_at || invoice.created_at)}</td>
        <td>
            <span class="badge ${statusClass} d-inline-flex align-items-center">
                <i class="ti ti-point-filled me-1"></i>${invoice.status}
            </span>
        </td>
        <td>
            <div class="action-icon">
                <button class="btn btn-sm btn-light" onclick="viewInvoiceDetail(${invoice.id})">
                    <i class="ti ti-eye"></i>
                </button>
            </div>
        </td>
    </tr>`;
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

window.viewInvoiceDetail = async function(invoiceId) {
    try {
        // 1. Concurrent Fetch: Invoice + Company Profile
        const [invRes, compRes] = await Promise.all([
            fetch(`/api/v1/payments/invoices/${invoiceId}`),
            fetch(`/api/v1/company`) // Assuming this is your company route
        ]);

        if (!invRes.ok) throw new Error("Invoice fetch failed");
        
        const invoice = await invRes.json();
        // Fallback object if company profile isn't set yet
        const company = compRes.ok ? await compRes.json() : { 
            name: "YKG LAB & DIAGNOSTIC CENTER",
            address: "Location not set",
            phone: "",
            email: ""
        };

        // 2. Map Company Branding (Invoice From)
        document.getElementById('modal_from_name').innerText = company.name;
        document.getElementById('modal_from_details').innerHTML = `
            ${company.address || ''}<br>
            ${company.phone || ''}<br>
            ${company.email || ''}
        `;
        
        // Update Logo dynamically
        const logoImg = document.querySelector('#invoiceDetailModal img[alt="Logo"]');
        if (logoImg) {
            logoImg.src = company.logo || "/static/img/logo.png";
        }

        // 3. Map Invoice & Patient Info (Bill To)
        document.getElementById('modal_inv_number').innerText = `#INV-${invoice.id}`;
        document.getElementById('modal_to_name').innerText = invoice.patient.full_name;
        
        const patientDetails = `
            ID: ${invoice.patient.patient_no}<br>
            Tel: ${invoice.patient.phone || 'N/A'}<br>
            Email: ${invoice.patient.email || ''}
        `;
        document.getElementById('modal_to_details').innerHTML = patientDetails;
        
        // Status Badge
        const statusBadge = document.getElementById('modal_inv_status_badge');
        const isPaid = invoice.status.toLowerCase() === 'paid';
        statusBadge.className = isPaid ? 'badge bg-success px-3' : 'badge bg-danger px-3';
        statusBadge.innerText = invoice.status.toUpperCase();

        // 4. Populate Items Table
        const itemsTable = document.getElementById('modal_invoice_items');
        itemsTable.innerHTML = ''; 
        
        if (invoice.items && invoice.items.length > 0) {
            invoice.items.forEach((item, index) => {
                const itemName = item.test ? item.test.name : (item.item_description || "Medical Service");
                itemsTable.innerHTML += `
                    <tr>
                        <td class="text-center">${index + 1}</td>
                        <td>
                            <h6 class="mb-0 fs-14 fw-bold text-dark">${itemName}</h6>
                        </td>
                        <td class="text-center">${item.quantity || 1}</td>
                        <td class="text-end">${Number(item.unit_price).toLocaleString()}</td>
                        <td class="text-end fw-bold">${Number(item.total_price).toLocaleString()}</td>
                    </tr>`;
            });
        }

        // 5. Totals
        const total = Number(invoice.total_amount).toLocaleString();
        document.getElementById('modal_subtotal').innerText = total;
        document.getElementById('modal_total').innerText = total;

        // 6. Show Modal
        const modalEl = document.getElementById('invoiceDetailModal');
        bootstrap.Modal.getOrCreateInstance(modalEl).show();
        
    } catch (err) {
        console.error("Invoice Modal Error:", err);
        showToast("Error loading invoice data", "error");
    }
};


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
