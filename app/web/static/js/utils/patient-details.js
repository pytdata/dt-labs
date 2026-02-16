document.addEventListener("DOMContentLoaded", async function (e) {
  const patientURL = `/api/v1/patients/${+currentPatient}/`;
  const appointmentsURL = `/api/v1/appointments/?patient_id=${currentPatient}`;
  const labResultsURL = `/api/v1/patients/${currentPatient}/lab-results/`;

  const labResults = await getRemoteData(labResultsURL);
  console.log(labResults, "lab results =============");

  try {
    const res = await fetch(patientURL);
    if (!res.ok) throw new Error("Failed to fetch patient data", res);
    const data = await res.json();
    console.log("patient data ==========", data)
    populateProfileBadge(data);
  } catch (error) {
    alert("Failed to fetch patient data.")
    console.log(error);
  }

  try {
    const res = await fetch(appointmentsURL);
    if (!res.ok) throw new Error("Failed to loaad appointment data", res);
    const data = await res.json();
    // console.log(data);
    renderAppointmentBadge(data);
  } catch (error) {
    console.log(error);
  }
});

function renderAppointmentBadge(dataList) {
  const selectedData = dataList.slice(0, 2);
  console.log(selectedData);
  const renderHTML = selectedData
    .map((data) => {
      return `
        <div class="col-xl-6">
            <div class="p-3 border rounded">
                <div class="d-flex align-items-center justify-content-between border-bottom mb-3 pb-3">
                    <span class="badge badge-md badge-soft-warning text-warning border border-warning">${data.status}</span>
                   
                </div>
                <div class="row row-gap-3">
                    <div class="col-sm-6">
                        <h6 class="fs-14 fw-semibold mb-1">Preferred Mode</h6>
                        <p class="fs-13 mb-0">${data.preffered_mode}</p>
                    </div>
                    <div class="col-sm-6">
                        <h6 class="fs-14 fw-semibold mb-1">Doctor</h6>
                        <div class="d-flex align-items-center">
                            <span class="avatar avatar-xs flex-shrink-0">
                                <img src="/static/img/doctors/doctor-01.jpg" class="rounded" alt="img">
                            </span>
                            <p class="fs-13 mb-0 ms-2 text-truncate">${data.doctor.full_name}</p>
                        </div>
                    </div>
                    <div class="col-sm-6">
                        <h6 class="fs-14 fw-semibold mb-1">Date & Time</h6>
                        <p class="fs-13 mb-0 text-truncate">${formatDate(data.appointment_at)}, ${formatTime(data.start_time)}</p>
                    </div>
                    <div class="col-sm-6">
                        <h6 class="fs-14 fw-semibold mb-1">Booked On</h6>
                        <p class="fs-13 mb-0 text-truncate">${formatDate(data.appointment_at)}</p>
                    </div>
                </div>
            </div>
        </div>
        
        `;
    })
    .join("");

  document.querySelector(".appointment__container").innerHTML = renderHTML;
}

function populateProfileBadge(data) {
  document.querySelector(".added__on").textContent = formatDate(
    data.created_at,
  );
  document.querySelector(".date__of__birth").textContent = formatDate(
    data.date_of_birth,
  );
  document.querySelector(".phone__number").textContent = data.phone;
  document.querySelector(".patient__email").textContent = data.email;
  document.querySelector(".patient__address").textContent = data.address;
  document.querySelector(".patient__gender").textContent = data.sex;
  document.querySelector(".patient__type").textContent = data.patient_type;
  document.querySelector(".total__bookings").textContent = "Loading...";
  document.querySelector("#patient__name").textContent = data.full_name;
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






/**
 * Fetch all test-categories data
 * @returns Array[objects]
 */
async function getRemoteData(url) {
  const res = await fetch(url);
  const data = await res.json();
  return data;
}

