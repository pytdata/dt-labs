/**
 * PATIENT PROFILE DASHBOARD - CONSOLIDATED & STANDARDIZED
 */
const patientProfileImage = document.getElementById("profile_img");

document.addEventListener("DOMContentLoaded", async function (e) {
    // currentPatient is assumed to be defined globally (e.g., from URL params)
    const patientURL = `/api/v1/patients/${+currentPatient}/`;
    const appointmentsURL = `/api/v1/appointments/?patient_id=${currentPatient}`;
    const labResultsURL = `/api/v1/patients/${currentPatient}/lab-results/`;

    // 1. Fetch Patient Basic Info
    try {
        const res = await fetch(patientURL);
        if (!res.ok) throw new Error("Failed to fetch patient data");
        const data = await res.json();
        populateProfileBadge(data);
    } catch (error) {
        console.error("Profile Fetch Error:", error);
    }

    // 2. Fetch Appointments
    try {
        const res = await fetch(appointmentsURL);
        if (!res.ok) throw new Error("Failed to load appointment data");
        const data = await res.json();
        renderAppointmentBadge(data);
        populateBooksInfo(data);
    } catch (error) {
        console.error("Appointment Fetch Error:", error);
    }

    // 3. Fetch Lab Results
    try {
        const res = await fetch(labResultsURL);
        if (!res.ok) throw new Error("Failed to load lab results");
        const data = await res.json();
        renderLabResults(data);
    } catch (error) {
        console.error("Lab Result Fetch Error:", error);
    }
});

/**
 * RENDER: Lab Results Card
 */
function renderLabResults(dataList) {
    const container = document.querySelector(".labresults__container");
    if (!container) return;

    if (dataList.length === 0) {
        container.innerHTML = `
            <div class="card shadow-none border">
                <div class="card-body text-center py-5">
                    <i class="ti ti-flask-off fs-1 text-muted mb-2"></i>
                    <p class="fs-5 text-muted">No lab results found for this patient.</p>
                </div>
            </div>`;
        return;
    }

    const renderedHTML = `
    <div class="card shadow flex-fill w-100">
        <div class="card-header d-flex align-items-center justify-content-between">
            <h5 class="fw-bold mb-0 text-truncate"><i class="ti ti-flask me-1 text-primary"></i>Laboratory Investigations</h5>
            <a href="patient-lab-history.html" class="btn btn-sm btn-outline-primary flex-shrink-0">View History</a>
        </div>
        <div class="card-body">
            ${dataList.map((item) => {
                const testName = item.order_item?.test?.name || "Investigation";
                const dateReceived = moment(item.received_at).format('DD MMM YYYY, hh:mm A');
                const source = item.source === 'analyzer' ? 'Auto-Analyzer' : 'Manual Entry';
                
                let statusBadge = 'badge-soft-warning';
                if (item.status === 'verified') statusBadge = 'badge-soft-success';
                if (item.status === 'printed') statusBadge = 'badge-soft-info';

                return `
                <div class="card mb-3 border-dashed">
                    <div class="card-body">
                        <div class="d-flex align-items-center justify-content-between flex-wrap gap-2">
                            <div class="d-flex align-items-center">
                                <a href="javascript:void(0);" class="avatar flex-shrink-0 bg-light-primary text-primary">
                                    <i class="ti ti-test-pipe fs-20"></i>
                                </a>
                                <div class="ms-3">
                                    <div>
                                        <h6 class="fw-semibold fs-15 mb-1">
                                            <a href="javascript:void(0);" class="text-dark">${testName}</a>
                                            <span class="badge ${statusBadge} ms-2 fs-10">${item.status.toUpperCase()}</span>
                                        </h6>
                                        <p class="fs-13 mb-0 text-muted">
                                            ID: <span class="text-primary fw-medium">${item.display_id || 'N/A'}</span>
                                            <span class="mx-1">|</span>
                                            Source: ${source}
                                        </p>
                                    </div>
                                </div>
                            </div>
                            <div class="text-sm-end">
                                <p class="fs-12 mb-1 text-muted"><i class="ti ti-calendar-event me-1"></i>${dateReceived}</p>
                                <div class="d-flex align-items-center justify-content-sm-end gap-1">
                                    <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light"><i class="ti ti-download"></i></a>
                                    <button class="btn btn-sm btn-primary px-3" onclick="viewLabResultDetails(${item.id})">
                                        <i class="ti ti-eye me-1"></i>View
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>`;
            }).join("")}
        </div>
    </div>`;

    container.innerHTML = renderedHTML;
}

/**
 * RENDER: Appointment Badges
 */
function renderAppointmentBadge(dataList) {
    const container = document.querySelector(".appointment__container");
    if (!container) return;

    const selectedData = dataList.slice(0, 2);
    container.innerHTML = selectedData.length === 0 
        ? "<p class='text-center fs-5 py-4'>No upcoming appointments available</p>" 
        : selectedData.map((data) => `
        <div class="col-xl-6">
            <div class="p-3 border rounded shadow-sm h-100">
                <div class="d-flex align-items-center justify-content-between border-bottom mb-3 pb-3">
                    <span class="badge badge-soft-warning text-warning border border-warning px-2">${data.status.toUpperCase()}</span>
                    <span class="text-primary fw-bold small">${data.display_id || ''}</span>
                </div>
                <div class="row row-gap-3">
                    <div class="col-sm-6">
                        <h6 class="fs-13 text-muted mb-1">Preferred Mode</h6>
                        <p class="fs-14 fw-medium mb-0">${data.preffered_mode || 'In-Person'}</p>
                    </div>
                    <div class="col-sm-6">
                        <h6 class="fs-13 text-muted mb-1">Doctor / Staff</h6>
                        <div class="d-flex align-items-center">
                            <span class="avatar avatar-xs flex-shrink-0">
                                <img src="${data.doctor?.avatar || 'assets/img/default-user.png'}" class="rounded-circle" alt="img">
                            </span>
                            <p class="fs-13 mb-0 ms-2 text-truncate fw-medium">${data.doctor?.full_name || 'Unassigned'}</p>
                        </div>
                    </div>
                    <div class="col-sm-6">
                        <h6 class="fs-13 text-muted mb-1">Date & Time</h6>
                        <p class="fs-14 fw-medium mb-0">${formatDate(data.appointment_at)}, ${formatTime(data.start_time)}</p>
                    </div>
                    <div class="col-sm-6">
                        <h6 class="fs-13 text-muted mb-1">Location</h6>
                        <p class="fs-14 fw-medium mb-0 text-truncate">Main Clinic Branch</p>
                    </div>
                </div>
            </div>
        </div>`).join("");
}

/**
 * POPULATE: Patient Sidebar Info
 */
function populateProfileBadge(data) {
    // Fill basic text fields
    document.querySelector(".added__on").textContent = formatDate(data.created_at);
    document.querySelector(".date__of__birth").textContent = formatDate(data.date_of_birth);
    document.querySelector(".phone__number").textContent = data.phone || 'N/A';
    document.querySelector(".patient__email").textContent = data.email || 'N/A';
    document.querySelector(".patient__address").textContent = data.address || 'N/A';
    document.querySelector(".patient__gender").textContent = data.sex || 'N/A';
    document.querySelector(".patient__type").textContent = data.patient_type || 'General';
    document.querySelector("#patient__name").textContent = data.full_name;

    // Standardized Patient ID in Sidebar
    const idContainer = document.querySelector(".patient__id_badge");
    if (idContainer) idContainer.textContent = data.display_id;

    // Image Handling
    if (patientProfileImage) {
        patientProfileImage.innerHTML = `<img src="${data.profile_image}" alt="img" class="rounded border shadow-sm" style="width: 100px; height: 100px; object-fit: cover;">`;
    }
}

/**
 * UTILS: Counters & Formatters
 */
function populateBooksInfo(data) {
    const totalEl = document.querySelector(".total__bookings");
    if (totalEl) totalEl.textContent = data.length;
}

function formatDate(dateStr) {
    if (!dateStr) return "N/A";
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

function formatTime(timeStr) {
    if (!timeStr) return "Not Set";
    const [h, m] = timeStr.split(":");
    const date = new Date();
    date.setHours(h, m);
    return date.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
    });
}