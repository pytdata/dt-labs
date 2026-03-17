const patientProfileImage = document.getElementById("profile_img");

document.addEventListener("DOMContentLoaded", async function (e) {
  const patientURL = `/api/v1/patients/${+currentPatient}/`;
  const appointmentsURL = `/api/v1/appointments/?patient_id=${currentPatient}`;
  const labResultsURL = `/api/v1/patients/${currentPatient}/lab-results/`;

  

  try {
    const res = await fetch(patientURL);
    if (!res.ok) throw new Error("Failed to fetch patient data", res);
    const data = await res.json();
    populateProfileBadge(data);
  } catch (error) {
    alert("Failed to fetch patient data.")
    console.log(error);
  }

  try {
    const res = await fetch(appointmentsURL);
    if (!res.ok) throw new Error("Failed to load appointment data", res);
    const data = await res.json();
    // console.log(data);
    renderAppointmentBadge(data);
    populateBooksInfo(data)
  } catch (error) {
    console.log(error);
  }

  try {
    // const labResults = await getRemoteData(labResultsURL);
    const res = await fetch(labResultsURL);
    if (!res.ok) throw new Error("Failed to load appointment");
    const data =await res.json();
    console.log("lab results: ", data)
    renderLabResults(data)
  } catch (error) {
    console.error(error);
  }
});


function renderLabResults(dataList) {
  console.log("BOOM: ", dataList)
  const renderedHTML = dataList.length == 0 ? "<p class='fs-5 text-center'>Not Available</p>" : dataList.map((data) => {

    return  `
    <div class="card shadow flex-fill w-100">
              <div class="card-header d-flex align-items-center justify-content-between">
                  <h5 class="fw-bold mb-0 text-truncate"><i class="ti ti-user-shield me-1"></i>Prescriptions</h5>
                  <a href="patient-details-prescription.html" class="btn btn-sm btn-outline-white flex-shrink-0">View All</a>
              </div>
              <div class="card-body">

                  <div class="card">
                      <div class="card-body">

                          <div class="d-flex align-items-center justify-content-between flex-wrap gap-2">
                              <div class="d-flex align-items-center">
                                  <a href="javascript:void(0);" class="avatar flex-shrink-0 bg-dark">
                                      <i class="ti ti-prescription fs-16"></i>
                                  </a>
                                  <div class="ms-2">
                                      <div>
                                          <h6 class="fw-semibold fs-14 text-truncate mb-1"><a href="javascript:void(0);">Dupixent + Entresto + Entyvio + Farxiga</a></h6>
                                          <p class="fs-13 mb-0">Medicines : 06<span class="mx-1"><i class="ti ti-point-filled text-primary"></i></span>Days : 4</p>
                                      </div>
                                  </div>
                              </div>
                              <div>
                                  <p class="fs-13 mb-0">Prescribed by : <span class="text-dark">Dr.Adrian</span></p>
                              </div>
                                <div class="text-sm-end">
                                  <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light me-1"><i class="ti ti-download"></i></a>
                                  <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="modal" data-bs-target="#view_modal"><i class="ti ti-eye"></i></a>
                              </div>
                          </div>

                      </div>
                  </div>

                  <div class="card">
                      <div class="card-body">

                          <div class="d-flex align-items-center justify-content-between flex-wrap gap-2">
                              <div class="d-flex align-items-center">
                                  <a href="javascript:void(0);" class="avatar flex-shrink-0 bg-dark">
                                      <i class="ti ti-prescription fs-16"></i>
                                  </a>
                                  <div class="ms-2">
                                      <div>
                                          <h6 class="fw-semibold fs-14 text-truncate mb-1"><a href="javascript:void(0);">Acetaminophen 20mg + Cymbalta 4mg</a></h6>
                                          <p class="fs-13 mb-0">Medicines : 12<span class="mx-1"><i class="ti ti-point-filled text-primary"></i></span>Days : 6</p>
                                      </div>
                                  </div>
                              </div>
                              <div>
                                  <p class="fs-13 mb-0">Prescribed by : <span class="text-dark">Dr.Evans</span></p>
                              </div>
                                <div class="text-sm-end">
                                  <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light me-1"><i class="ti ti-download"></i></a>
                                  <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="modal" data-bs-target="#view_modal"><i class="ti ti-eye"></i></a>
                              </div>
                          </div>

                      </div>
                  </div>

                  <div class="card mb-0">
                      <div class="card-body">

                          <div class="d-flex align-items-center justify-content-between flex-wrap gap-2">
                              <div class="d-flex align-items-center">
                                  <a href="javascript:void(0);" class="avatar flex-shrink-0 bg-dark">
                                      <i class="ti ti-prescription fs-16"></i>
                                  </a>
                                  <div class="ms-2">
                                      <div>
                                          <h6 class="fw-semibold fs-14 text-truncate mb-1"><a href="javascript:void(0);">Pantoprazole + Prednisone Rybelsus</a></h6>
                                          <p class="fs-13 mb-0">Medicines : 4<span class="mx-1"><i class="ti ti-point-filled text-primary"></i></span>Days : 5</p>
                                      </div>
                                  </div>
                              </div>
                              <div>
                                  <p class="fs-13 mb-0">Prescribed by : <span class="text-dark">Dr.Victoria</span></p>
                              </div>
                                <div class="text-sm-end">
                                  <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light me-1"><i class="ti ti-download"></i></a>
                                  <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="modal" data-bs-target="#view_modal"><i class="ti ti-eye"></i></a>
                              </div>
                          </div>

                      </div>
                  </div>

              </div>
         </div>
                     
  `;
  }).join("");

  document.querySelector(".labresults__container").innerHTML = renderedHTML;
}


function renderAppointmentBadge(dataList) {
  const selectedData = dataList.slice(0, 2);
  const renderHTML = selectedData.length == 0 ? "<p class='text-center fs-5'>Not Available</p>" : selectedData
    .map((data) => {
      console.log("data:", data)
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
                        <h6 class="fs-14 fw-semibold mb-1">Staff</h6>
                        <div class="d-flex align-items-center">
                            <span class="avatar avatar-xs flex-shrink-0">
                                <img src="${data.doctor.avatar}" class="rounded" alt="img">
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
  document.querySelector("#patient__name").textContent = data.full_name;
  patientProfileImage.innerHTML = `<img src="${data.profile_image}" alt="img" class="rounded">`
}

function populateBooksInfo(data) {
    document.querySelector(".total__bookings").textContent = data.length;

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



 