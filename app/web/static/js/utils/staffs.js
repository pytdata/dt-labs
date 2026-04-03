/**
 * STAFF MANAGEMENT MODULE
 */
const StaffManager = {
    staffURL: "/api/v1/staffs/",
    isRequestPending: false,
    searchTimeout: null,

    elements: {
        listContainer: document.querySelector(".staff__list__container"),
        addForm: document.querySelector("#staffForm"),
        editForm: document.querySelector("#edit__staff__form"),
        refreshBtn: document.querySelector("#staff_data_refresh"),
        searchName: document.querySelector(".search__staff"),
        searchRole: document.querySelector(".search__role"),
        genderFilters: document.querySelectorAll(".filter__gender"),
        deleteBtn: document.querySelector(".delete__staff")
    },

    async init() {
        if (window.StaffManagerInitialized) return;
        window.StaffManagerInitialized = true;

        this.bindEvents();
        await this.loadStaffData();
        await this.fetchAndPopulateRoles("staff_role");
    },

    async loadStaffData() {
        try {
            const res = await this.getRemoteData(this.staffURL);
            this.render(res);
        } catch (error) {
            window.showToast(error.message, "danger");
        }
    },

    bindEvents() {
        // 1. CREATE STAFF
        this.elements.addForm?.addEventListener("submit", async (e) => {
            e.preventDefault();
            e.stopImmediatePropagation();
            if (this.isRequestPending) return;
            
            const submitBtn = e.target.querySelector('[type="submit"]');
            await this.handleFormSubmission(e.target, "/api/v1/staffs/", "POST", "add_staff", submitBtn);
        });

        // 2. UPDATE STAFF
        this.elements.editForm?.addEventListener("submit", async (e) => {
            e.preventDefault();
            e.stopImmediatePropagation();
            if (this.isRequestPending) return;

            const staffId = e.target.dataset.staffId;
            const submitBtn = e.target.querySelector('[type="submit"]');
            await this.handleFormSubmission(e.target, `/api/v1/staffs/${staffId}/`, "PUT", "edit_staff", submitBtn);
        });

        this.elements.listContainer?.addEventListener("click", (e) => this.handleTableClick(e));
        this.elements.deleteBtn?.addEventListener("click", (e) => this.handleDelete(e));
        this.elements.refreshBtn?.addEventListener("click", () => this.loadStaffData());
    },

    async handleFormSubmission(form, url, method, modalId, submitBtn = null) {
        this.isRequestPending = true;
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Processing...';
        }

        const formData = new FormData(form);
        const payload = {
            full_name: formData.get("staff_full_name"),
            gender: formData.get("gender"),
            email: formData.get("staff_email"),
            phone_number: formData.get("phone"),
            role: formData.get("staff_role"),
        };

        const pwd = formData.get("password");
        if (pwd) payload.password = pwd;
        
        if (method === "PUT") {
            const statusCheckbox = document.querySelector(".edit_status_checked");
            payload.is_active = statusCheckbox ? statusCheckbox.checked : true;
        }

        try {
            const res = await fetch(url, {
                method: method,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            const data = await res.json();

            if (!res.ok) {
                // FastAPI returns errors in a 'detail' field. 
                // We throw it so it's caught by the catch block below.
                throw new Error(data.detail || "An unexpected error occurred.");
            }

            // --- SUCCESS FLOW ---
            window.showToast(method === "POST" ? "Staff created successfully!" : "Staff updated!", "success");
            
            // Close Modal
            const modalEl = document.getElementById(modalId);
            if (modalEl) {
                const modalInstance = bootstrap.Modal.getOrCreateInstance(modalEl);
                modalInstance.hide();
            }
            
            form.reset();
            await this.loadStaffData();

        } catch (error) {
            // --- ERROR FLOW ---
            // This triggers your custom showToast for backend validation errors (like 409 Conflict)
            window.showToast(error.message, "danger");
        } finally {
            this.isRequestPending = false;
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = method === "POST" ? "Save" : "Save Changes";
            }
        }
    },

    async handleTableClick(e) {
        const btn = e.target.closest(".view__staff__btn, .edit__staff__btn, .delete__staff__btn");
        if (!btn) return;

        e.preventDefault();
        const staffId = btn.dataset.staffId;

        try {
            const res = await fetch(`/api/v1/staffs/${staffId}/`);
            if (!res.ok) throw new Error("Could not fetch staff details.");
            const staff = await res.json();

            if (btn.classList.contains("view__staff__btn")) this.populateViewModal(staff);
            if (btn.classList.contains("edit__staff__btn")) this.populateEditModal(staff);
            if (btn.classList.contains("delete__staff__btn")) this.elements.deleteBtn.dataset.staffId = staffId;
        } catch (error) {
            window.showToast(error.message, "danger");
        }
    },

    async handleDelete(e) {
        if (this.isRequestPending) return;
        const staffId = e.target.dataset.staffId;
        this.isRequestPending = true;

        try {
            const res = await fetch(`/api/v1/staffs/${staffId}/`, { method: "DELETE" });
            if (!res.ok) throw new Error("Delete failed.");

            window.showToast("Staff deleted successfully.", "success");
            const modalEl = document.getElementById('delete_modal');
            bootstrap.Modal.getOrCreateInstance(modalEl).hide();
            await this.loadStaffData();
        } catch (error) {
            window.showToast(error.message, "danger");
        } finally {
            this.isRequestPending = false;
        }
    },

    async fetchAndPopulateRoles(selectId, selectedValue = null) {
        const roleSelect = document.getElementById(selectId);
        if (!roleSelect) return;
        try {
            const res = await fetch('/api/v1/settings/roles');
            const roles = await res.json();
            roleSelect.innerHTML = '<option value="">Select Role</option>';
            roles.forEach(role => {
                const opt = document.createElement('option');
                opt.value = role.slug;
                opt.textContent = role.name;
                if (role.slug === selectedValue) opt.selected = true;
                roleSelect.appendChild(opt);
            });
            if (window.jQuery && $(roleSelect).data('select2')) $(roleSelect).trigger('change');
        } catch (e) { console.error(e); }
    },

    populateEditModal(staff) {
        document.getElementById("edit_staff_edit").value = staff.id;
        document.getElementById("edit_name").value = staff.full_name;
        document.getElementById("edit_gender").value = staff.gender?.toLowerCase() || "male";
        document.getElementById("edit_phone").value = staff.phone_number;
        document.getElementById("edit_email").value = staff.email;
        this.fetchAndPopulateRoles("edit_role", staff.role);
        
        const statusContainer = document.getElementById("edit_status");
        if (statusContainer) {
            statusContainer.innerHTML = `<input name="status" class="form-check-input m-0 edit_status_checked" type="checkbox" role="switch" ${staff.is_active ? 'checked' : ''}>`;
        }
        this.elements.editForm.dataset.staffId = staff.id;
    },

    render(staffLists) {
        if (!staffLists.length) {
            this.elements.listContainer.innerHTML = '<tr><td colspan="9" class="text-center">No staff found</td></tr>';
            return;
        }
        this.elements.listContainer.innerHTML = staffLists.map(staff => `
            <tr>
                <td><div class="form-check form-check-md"><input class="form-check-input" type="checkbox"></div></td>
                <td><a href="#" class="view__staff__btn" data-staff-id="${staff.id}">${staff.display_id}</a></td>
                <td>
                    <div class="d-flex align-items-center">
                        <span class="avatar avatar-xs me-2"><img src="${staff.avatar}" alt="img" class="rounded"></span>
                        <h6 class="fs-14 mb-0 fw-medium">${staff.full_name}</h6>
                    </div>
                </td>
                <td>${staff.gender?.toUpperCase() || "-"}</td>
                <td><span class="badge bg-primary-soft text-primary">${staff.role || "No Role"}</span></td>
                <td>${staff.phone_number || "-"}</td>
                <td>${staff.email}</td>
                <td>${staff.is_active ? '<span class="badge bg-success">Active</span>' : '<span class="badge bg-danger">Inactive</span>'}</td>
                <td class="text-end">
                    <div class="dropdown">
                        <a href="#" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown"><i class="ti ti-dots-vertical"></i></a>
                        <ul class="dropdown-menu p-2">
                            <li><a href="#" class="dropdown-item view__staff__btn" data-bs-toggle="modal" data-staff-id="${staff.id}" data-bs-target="#view_modal">View</a></li>
                            <li><a href="#" class="dropdown-item edit__staff__btn" data-bs-toggle="modal" data-staff-id="${staff.id}" data-bs-target="#edit_staff">Edit</a></li>
                            <li><a href="#" class="dropdown-item delete__staff__btn" data-bs-toggle="modal" data-staff-id="${staff.id}" data-bs-target="#delete_modal">Delete</a></li>
                        </ul>
                    </div>
                </td>
            </tr>
        `).join("");
    },

    async getRemoteData(url) {
        const res = await fetch(url);
        if (!res.ok) throw new Error("Failed to load data.");
        return await res.json();
    }
};

StaffManager.init();



window.showToast = window.showToast || function(message, type = 'success') {
    const toastEl = document.getElementById('appCustomToast');
    const toastText = document.getElementById('appCustomToastText');
    const toastIcon = document.getElementById('toastIcon');
    if (!toastEl) return;

    toastEl.classList.remove('bg-success', 'bg-danger');
    if (toastIcon) toastIcon.className = 'ti fs-4 me-2';
    toastText.innerText = message;

    if (type === 'success') {
        toastEl.classList.add('bg-success');
        if (toastIcon) toastIcon.classList.add('ti-circle-check');
    } else {
        toastEl.classList.add('bg-danger');
        if (toastIcon) toastIcon.classList.add('ti-alert-triangle');
    }

    const toast = bootstrap.Toast.getOrCreateInstance(toastEl);
    toast.show();
};
