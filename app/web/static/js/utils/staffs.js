const staffListContainerEl = document.querySelector(".staff__list__container");
const addStaffForm = document.querySelector("#staffForm");
const editFormData = document.querySelector("#edit__staff__form");
const refreshStaffEl = document.querySelector("#staff_data_refresh");

let staffURL = "/api/v1/staffs/";

(async function init() {
  try {
    
    const res = await getRemoteData(staffURL);
    render(res);
  } catch (error) {
    // TODO: Add toast notification
    alert(error)
  }
})();

// show staff detail
staffListContainerEl.addEventListener("click", async (e) => {
  const button = e.target.closest(".view__staff__btn");

  if (!button) return;

  const staffId = button.dataset.staffId;

  try {
    const res = await fetch(`/api/v1/staffs/${staffId}/`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) throw new Error("Failed to fetch staff data: ", res);

    const staff = await res.json();
    populateStaffDetailModal(staff);

  } catch (error) {
     // TODO: Add toast notification
    alert(error);
  }
});

// submit new staff data
addStaffForm.addEventListener("submit", async function (e) {
  e.preventDefault();

  const formData = new FormData(addStaffForm);
  const payload = {
    full_name: formData.get("staff_full_name"),
    gender: formData.get("gender"),
    email: formData.get("staff_email"),
    phone_number: formData.get("phone"),
    role: formData.get("staff_role"),
    password: formData.get("password"),
  };

  try {
    const res = await fetch("/api/v1/staffs/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error("Failed to create staff: ", res);

    const data = await res.json();
  } catch (error) {
    console.log(error);
    // TODO: Add toast notification
    alert(error);
  }

  addStaffForm.reset();
});

// show edit staff form
staffListContainerEl.addEventListener("click", async (e) => {
  const button = e.target.closest(".edit__staff__btn");
  if (!button) return;

  const staffId = +button.dataset.staffId;

  try {
    const res = await fetch(`/api/v1/staffs/${staffId}/`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) throw new Error("Failed to fetch staff data: ", res);
    const staff = await res.json();

    populateEditStaffModal(staff);
  } catch (error) {
    console.error(error);
    alert("Failed to load staff data");
    // TODO: app toast notification
  }
});

// submit edit made to staff
editFormData.addEventListener("submit", async function (e) {
  e.preventDefault();

  const staffId = +this.dataset.staffId;
  const newForm = new FormData(editFormData);

  const statusCheckbox = document.querySelector(".edit_status_checked");
  console.log(statusCheckbox);

  const payload = {
    full_name: newForm.get("staff_full_name"),
    gender: newForm.get("gender"),
    email: newForm.get("staff_email"),
    phone_number: newForm.get("phone"),
    role: newForm.get("staff_role"),
    password: newForm.get("password"),
    is_active: statusCheckbox.checked,
  };

  try {
    const res = await fetch(`/api/v1/staffs/${staffId}/`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error("Failed to update staff");

    const data = await res.json();
    console.log(data);

    // reset the form
    document.querySelector("#edit__staff__form").reset();
  } catch (error) {
    console.log(error);
    // TODO: Add toast notification
    alert(error);
  }
});

/**
 * Prepopulates the edit model of staff for the client to make changes
 * @param {Object} staff
 */
function populateEditStaffModal(staff) {
  console.log(staff);
  // Selects
  document.getElementById("edit_staff_edit").value = staff.id;
  document.getElementById("edit_name").value = staff.full_name;
  // document.getElementById("department").value = staff.department.id;
  document.getElementById("edit_gender").value = staff.gender;
  document.getElementById("edit_phone").value = staff.phone_number;

  // Inputs
  document.getElementById("edit_email").value = staff.email;
  // check if staff is active
  document.getElementById("edit_status").innerHTML = staff.is_active
    ? `<input class="form-check-input m-0 edit_status_checked" name="status" type="checkbox" checked>`
    : `<input class="form-check-input m-0 edit_status_checked" name="status" type="checkbox">`;

  // Store staff id for submit
  document.querySelector("#edit_staff form").dataset.staffId = staff.id;
}

function populateStaffDetailModal(staffData) {
  document.getElementById("staff_id").innerText = staffData.id;
  document.getElementById("staff_name").innerText =
    staffData.full_name.toLocaleUpperCase();
  document.getElementById("staff_mobile").innerText = staffData.phone_number
    ? staffData.phone_number
    : "-Not available";
  document.getElementById("staff_email").innerText = staffData.email;
  document.getElementById("staff_gender").innerText = staffData.gender
    ? staffData.gender
    : "Not Available";
  document.getElementById("is_staff_active").innerHTML = staffData.is_active
    ? `<input class="form-check-input me-0 edit_status_checked" type="checkbox" role="switch" name="status" checked>`
    : `<input class="form-check-input me-0 edit_status_checked" name="status" type="checkbox" role="switch">`;
}

// delete staff
staffListContainerEl.addEventListener("click", async (e) => {
  const button = e.target.closest(".delete__staff__btn");
  if (!button) return;

  const staffId = button.dataset.staffId;
  document.querySelector(".delete__staff").dataset.staffId = staffId;
});

document
  .querySelector(".delete__staff")
  .addEventListener("click", async (e) => {
    e.preventDefault();

    const button = e.target;
    if (!button) return;

    const staffId = +button.dataset.staffId;
    try {
      const res = await fetch(`/api/v1/staffs/${staffId}/`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error("Failed to delete staff: ", res);
    } catch (error) {
      // TODO: Add toast notification
      console.error(error);
      alert(error);
    }
  });

// refresh data
refreshStaffEl.addEventListener("click", async (e) => {
  const data = await getRemoteData(staffURL);
  render(data);
});

/**
 * Fetch data from backend
 * @returns Array[objects]
 */
async function getRemoteData(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch staff data");
    const data = await res.json();
    return data;
  } catch (error) {
    throw new Error(error)
  }
}

/**
 * Render a lsit of object as html elements and display in DOM
 * @param {Array[Object]} users
 */
function render(staffLists) {
  // render patients data into html and join the results into an html string
  const renderedHTML = staffLists
    .map((staff) => {
      return renderData(staff);
    })
    .join("");

  // insert data into DOM
  staffListContainerEl.innerHTML = renderedHTML;
}

/**
 * Renders the staff data into html.
 * @param {Map} staff
 * @returns htmlement
 */
function renderData(staffData) {
  const htmlElement = ` 
         <tr>
            <td>
                <div class="form-check form-check-md">
                    <input class="form-check-input" type="checkbox">
                </div>
            </td>
            <td><a href="javascript:void(0);" data-bs-toggle="modal" data-bs-target="#view_modal">${staffData.id}</a></td>
            <td>
                <div class="d-flex align-items-center">
                        <a href="javascript:void(0);" class="avatar avatar-xs me-2" data-bs-toggle="modal"
                        data-bs-target="#view_modal">
                        <img src="/static/img/users/user-30.jpg" alt="img" class="rounded">
                    </a>
                    <div>
                        <h6 class="fs-14 mb-0 fw-medium"><a href="javascript:void(0);" data-bs-toggle="modal" data-bs-target="#view_modal">${staffData.full_name}</a></h6>
                    </div>
                </div>
            </td>
            <td>${staffData.gender ? staffData.gender.toLocaleUpperCase() : "-"}</td>
            <td>${staffData.role.toLocaleUpperCase()}</td>
            <td>${staffData.phone_number ? staffData.phone_number : "-"}</td>
            <td><a href="/cdn-cgi/l/email-protection" class="__cf_email__" data-cfemail="b2d8dddcd3c6dad3dcf2d7cad3dfc2ded79cd1dddf">${staffData.email}</a></td>
            <td>17 Jun 2025</td>
            <td class="text-end">
                <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown"><i class="ti ti-dots-vertical"></i></a>
                <ul class="dropdown-menu p-2">
                    <li>
                        <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center view__staff__btn" data-bs-toggle="modal" data-staff-id=${staffData.id} data-bs-target="#view_modal"><i class="ti ti-eye me-1"></i>View Details</a>
                    </li>
                    <li>
                        <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center edit__staff__btn" data-bs-toggle="modal" data-staff-id=${staffData.id} data-bs-target="#edit_staff"><i class="ti ti-edit me-1"></i>Edit</a>
                    </li>
                    <li>
                        <a href="javascript:void(0);" class="dropdown-item d-flex align-items-center delete__staff__btn" data-bs-toggle="modal" data-staff-id=${staffData.id} data-bs-target="#delete_modal"><i class="ti ti-trash me-1"></i>Delete</a>
                    </li>
                </ul>
            </td>
        </tr>
  `;

  return htmlElement;
}
