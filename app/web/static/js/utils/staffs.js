/**
 * STAFF MANAGEMENT MODULE
 * Handles CRUD operations, Real-time Client-side Filtering, and Pagination
 */
const StaffManager = {
    staffURL: "/api/v1/staffs/",
    isRequestPending: false,
    searchTimeout: null,
    
    // Data State
    allStaffData: [],    // Master cache from server
    filteredData: [],    // Currently filtered set
    
    // Pagination State
    currentPage: 1,
    pageSize: 10,

    elements: {
        listContainer: document.querySelector(".staff__list__container"),
        addForm: document.querySelector("#staffForm"),
        editForm: document.querySelector("#edit__staff__form"),
        refreshBtn: document.querySelector("#staff_data_refresh"),
        searchName: document.querySelector(".search__staff"),
        searchRole: document.querySelector(".search__role"),
        genderFilters: document.querySelectorAll(".filter__gender"),
        deleteBtn: document.querySelector(".delete__staff"),
        // Pagination Elements
        paginationInfo: document.querySelector("#staff-pagination-info"),
        paginationControls: document.querySelector("#staff-pagination-controls")
    },

    async init() {
        if (window.StaffManagerInitialized) return;
        window.StaffManagerInitialized = true;

        // Add listeners for both add and edit image inputs
        ["staff_image_input", "edit_staff_image_input"].forEach(id => {
            const input = document.getElementById(id);
            if (input) {
                input.addEventListener("change", function() {
                    if (this.files && this.files[0]) {
                        const reader = new FileReader();
                        const previewId = id === "staff_image_input" ? "staff_image_preview" : "edit_staff_preview";
                        reader.onload = (e) => {
                            document.getElementById(previewId).src = e.target.result;
                        };
                        reader.readAsDataURL(this.files[0]);
                    }
                });
            }
        });

        this.bindEvents();
        await this.loadStaffData();
        await this.fetchAndPopulateRoles("staff_role");
    },

    /**
     * Fetch all staff from server and update local cache
     */
    async loadStaffData() {
        try {
            const res = await this.getRemoteData(this.staffURL);
            this.allStaffData = res; 
            this.applyFilters(); // Initial render and pagination setup
        } catch (error) {
            window.showToast(error.message, "danger");
        }
    },

    bindEvents() {
        // --- 1. FILTERING & SEARCH EVENTS ---
        
        // Search by Name
        this.elements.searchName?.addEventListener("input", () => {
            this.currentPage = 1; // Reset to first page on new search
            this.debounceFilter();
        });

        // Search by Role
        this.elements.searchRole?.addEventListener("input", () => {
            this.currentPage = 1;
            this.debounceFilter();
        });

        // Gender Checkboxes
        this.elements.genderFilters.forEach(cb => {
            cb.addEventListener("change", () => {
                this.currentPage = 1;
                this.applyFilters();
            });
        });

        // --- 2. PAGINATION EVENTS ---
        this.elements.paginationControls?.addEventListener("click", (e) => {
            e.preventDefault();
            const link = e.target.closest(".page-link");
            if (!link) return;

            const targetPage = link.dataset.page;
            if (targetPage) {
                this.currentPage = parseInt(targetPage);
                this.updateTableView();
            }
        });

        // --- 3. CRUD EVENTS ---

        this.elements.addForm?.addEventListener("submit", async (e) => {
            e.preventDefault();
            if (this.isRequestPending) return;
            const submitBtn = e.target.querySelector('[type="submit"]');
            await this.handleFormSubmission(e.target, this.staffURL, "POST", "add_staff", submitBtn);
        });

        this.elements.editForm?.addEventListener("submit", async (e) => {
            e.preventDefault();
            if (this.isRequestPending) return;
            const staffId = e.target.dataset.staffId;
            const submitBtn = e.target.querySelector('[type="submit"]');
            await this.handleFormSubmission(e.target, `${this.staffURL}${staffId}/`, "PUT", "edit_staff", submitBtn);
        });

        this.elements.listContainer?.addEventListener("click", (e) => this.handleTableClick(e));
        this.elements.deleteBtn?.addEventListener("click", (e) => this.handleDelete(e));
        this.elements.refreshBtn?.addEventListener("click", () => this.loadStaffData());
    },

    /**
     * Logic to filter the master cache
     */
    applyFilters() {
        const nameQuery = this.elements.searchName?.value.toLowerCase().trim() || "";
        const roleQuery = this.elements.searchRole?.value.toLowerCase().trim() || "";
        
        const activeGenders = Array.from(this.elements.genderFilters)
            .filter(cb => cb.checked)
            .map(cb => cb.getAttribute('data-gender').toLowerCase());

        this.filteredData = this.allStaffData.filter(staff => {
            const matchesName = staff.full_name.toLowerCase().includes(nameQuery);
            
            // Matches nested role object name or slug
            const staffRoleName = typeof staff.role === 'object' 
            ? (staff.role?.name || "").toLowerCase() 
            : (staff.role || "").toLowerCase();
            const matchesRole = staffRoleName.includes(roleQuery);
            
            const staffGender = (staff.gender || "").toLowerCase();
            const matchesGender = activeGenders.length === 0 || activeGenders.includes(staffGender);

            return matchesName && matchesRole && matchesGender;
        });

        this.updateTableView();
    },

    /**
     * Slices the filtered data for pagination and triggers render
     */
    updateTableView() {
        const totalItems = this.filteredData.length;
        const totalPages = Math.ceil(totalItems / this.pageSize);
        
        // Safety check for current page bounds
        if (this.currentPage > totalPages) this.currentPage = totalPages || 1;
        if (this.currentPage < 1) this.currentPage = 1;

        const start = (this.currentPage - 1) * this.pageSize;
        const end = start + this.pageSize;
        const paginatedSlice = this.filteredData.slice(start, end);

        // 1. Render Table Rows
        this.render(paginatedSlice);

        // 2. Update "Showing X to Y of Z" text
        if (this.elements.paginationInfo) {
            const from = totalItems === 0 ? 0 : start + 1;
            const to = Math.min(end, totalItems);
            this.elements.paginationInfo.innerText = `Showing ${from} to ${to} of ${totalItems} entries`;
        }

        // 3. Render Pagination Buttons
        this.renderPaginationControls(totalPages);
    },

    renderPaginationControls(totalPages) {
        if (!this.elements.paginationControls) return;
        
        let html = '';
        
        // Previous Button
        html += `
            <li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${this.currentPage - 1}">Previous</a>
            </li>`;

        // Page Number Buttons
        for (let i = 1; i <= totalPages; i++) {
            html += `
                <li class="page-item ${this.currentPage === i ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${ i }">${ i }</a>
                </li>`;
        }

        // Next Button
        html += `
            <li class="page-item ${this.currentPage === totalPages || totalPages === 0 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${this.currentPage + 1}">Next</a>
            </li>`;

        this.elements.paginationControls.innerHTML = html;
    },

    debounceFilter() {
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => this.applyFilters(), 300);
    },

    async handleFormSubmission(form, url, method, modalId, submitBtn = null) {
        this.isRequestPending = true;
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Processing...';
        }

        // 1. Initialize FormData from the form element
        // This automatically captures the "profile_picture" file input
        const formData = new FormData(form);

        /**
         * 2. Remap field names to match FastAPI Form parameters
         */
        formData.set("full_name", formData.get("staff_full_name"));
        formData.set("email", formData.get("staff_email"));
        formData.set("phone_number", formData.get("phone"));
        formData.set("role", formData.get("staff_role"));
        
        // Handle Active Status (Boolean logic for FastAPI Form)
        if (method === "PUT") {
            const statusCheckbox = form.querySelector(".edit_status_checked");
            // We send "true" or "false" strings which FastAPI can parse as booleans
            formData.set("is_active", statusCheckbox ? statusCheckbox.checked : true);
        } else {
            formData.set("is_active", true);
        }

        // Clean up redundant frontend-specific keys
        formData.delete("staff_full_name");
        formData.delete("staff_email");
        formData.delete("phone");
        formData.delete("staff_role");

        // 3. Password handling: Only send if it has a value
        const pwd = formData.get("password");
        if (!pwd || pwd.trim().length === 0) {
            formData.delete("password");
        }

        try {
            const res = await fetch(url, {
                method: method,
                // Do NOT set Content-Type header; fetch sets it to multipart/form-data automatically
                body: formData, 
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Operation failed.");

            window.showToast(method === "POST" ? "Staff created successfully!" : "Staff updated successfully!", "success");
            
            // Hide modal
            const modalEl = document.getElementById(modalId);
            if (modalEl) {
                const actualModal = modalEl.closest('.modal') || modalEl;
                bootstrap.Modal.getOrCreateInstance(actualModal).hide();
            }
            
            // 4. Reset Form and Image Previews
            form.reset();
            
            // Clear Add Modal Preview
            const addPreview = document.getElementById("staff_image_preview");
            if (addPreview) addPreview.src = "/static/img/defaults/default-user-icon.jpeg";
            
            // Clear Edit Modal Preview
            const editPreview = document.getElementById("edit_staff_preview");
            if (editPreview) editPreview.src = "/static/img/defaults/default-user-icon.jpeg";

            await this.loadStaffData(); 

        } catch (error) {
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
            const res = await fetch(`${this.staffURL}${staffId}/`);
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
            const res = await fetch(`${this.staffURL}${staffId}/`, { method: "DELETE" });
            if (!res.ok) throw new Error("Delete failed.");

            window.showToast("Staff deleted successfully.", "success");
            bootstrap.Modal.getOrCreateInstance(document.getElementById('delete_modal')).hide();
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
        } catch (e) { console.error("Role population error:", e); }
    },

   /**
     * Populates the Edit Modal with staff details
     */
    async populateEditModal(staff) {
        // 1. Identity & IDs
        document.getElementById("edit_staff_edit").value = staff.display_id || staff.id;
        this.elements.editForm.dataset.staffId = staff.id;

        // 2. Text Fields
        document.getElementById("edit_name").value = staff.full_name || "";
        document.getElementById("edit_gender").value = (staff.gender || "male").toLowerCase();
        document.getElementById("edit_phone").value = staff.phone_number || "";
        document.getElementById("edit_email").value = staff.email || "";

        // 3. Current Role Label (The workaround)
        const roleLabel = document.getElementById("current_role_label");
        if (roleLabel) {
            const roleName = typeof staff.role === 'object' ? (staff.role?.name || "No Role") : (staff.role || "No Role");
            roleLabel.innerText = `Current: ${roleName}`;
        }

        // 4. Populate Dropdown (Still runs in background)
        const roleSlug = typeof staff.role === 'object' ? staff.role?.slug : staff.role;
        this.fetchAndPopulateRoles("edit_role", roleSlug);

        // 5. Avatar Update
        const editAvatarImg = document.querySelector("#edit_staff .avatar-xl");
        if (editAvatarImg) {
            editAvatarImg.src = staff.avatar || '/static/img/defaults/default-user-icon.jpeg';
        }

        // 6. Status Toggle
        const statusContainer = document.getElementById("edit_status");
        if (statusContainer) {
            statusContainer.innerHTML = `
                <input name="status" class="form-check-input m-0 edit_status_checked" 
                type="checkbox" role="switch" ${staff.is_active ? 'checked' : ''}>`;
        }
    },

    /**
     * Populates the View Modal with staff details
     */
    populateViewModal(staff) {
        // 1. Header & Identity
        document.getElementById("staff_id").innerText = staff.display_id || `#${staff.id}`;
        document.getElementById("staff_name").innerText = staff.full_name;
        
        // Handle Role (string vs object)
        const roleName = typeof staff.role === 'object' ? (staff.role?.name || "N/A") : (staff.role || "N/A");
        document.getElementById("view_staff_role").innerText = roleName;

        // 2. Avatar
        const avatarImg = document.getElementById("view_staff_avatar");
        if (avatarImg) {
            avatarImg.src = staff.avatar || '/static/img/defaults/default-user-icon.jpeg';
        }

        // 3. Status Switch & Text
        const statusToggle = document.getElementById("view_staff_status_toggle");
        const statusText = document.getElementById("view_staff_status_text");
        if (statusToggle) {
            statusToggle.checked = staff.is_active;
        }
        if (statusText) {
            statusText.innerText = staff.is_active ? "Active" : "Inactive";
            statusText.className = `fs-13 mb-0 text-truncate ${staff.is_active ? 'text-success' : 'text-danger'}`;
        }

        // 4. Basic Info
        document.getElementById("staff_mobile").innerText = staff.phone_number || "N/A";
        
        console.log("=======", staff.email, document.getElementById("staff_email"))
        document.getElementById("view_email").innerText = staff.email || "N/A";
        document.getElementById("staff_gender").innerText = staff.gender ? staff.gender.charAt(0).toUpperCase() + staff.gender.slice(1) : "N/A";
    },

    render(staffLists) {
        if (!staffLists.length) {
            this.elements.listContainer.innerHTML = '<tr><td colspan="9" class="text-center">No staff found matching criteria.</td></tr>';
            return;
        }
        this.elements.listContainer.innerHTML = staffLists.map(staff => `
            <tr>
                <td><div class="form-check form-check-md"><input class="form-check-input" type="checkbox"></div></td>
                <td><a href="#" class="view__staff__btn" data-staff-id="${staff.id}">${staff.display_id || '#' + staff.id}</a></td>
                <td>
                    <div class="d-flex align-items-center">
                        <span class="avatar avatar-xs me-2"><img src="${staff.avatar || '/static/img/defaults/default-user-icon.jpeg'}" alt="img" class="rounded"></span>
                        <h6 class="fs-14 mb-0 fw-medium">${staff.full_name}</h6>
                    </div>
                </td>
                <td>${staff.gender?.toUpperCase() || "-"}</td>
                <td>
                 <span class="badge bg-primary-soft text-primary">
                    ${typeof staff.role === 'object' ? (staff.role?.name || "No Role") : (staff.role || "No Role")}
                </span>
            </td>
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

// Initialize the module
StaffManager.init();



window.showToast  = function(message, type = 'success') {
    const toastEl = document.getElementById('appCustomToast');
    const toastText = document.getElementById('appCustomToastText');
    const toastIcon = document.getElementById('toastIcon');

    if (!toastEl) return;

    // CRITICAL: Move toast to body to escape any parent 'overflow:hidden'
    const container = toastEl.closest('.toast-container');
    if (container && container.parentElement !== document.body) {
        document.body.appendChild(container);
    }

    // Reset classes
    toastEl.classList.remove('bg-success', 'bg-danger');
    if (toastIcon) toastIcon.className = 'ti fs-4 me-2';

    // Set content
    toastText.innerText = message;
    if (type === 'success') {
        toastEl.classList.add('bg-success');
        if (toastIcon) toastIcon.classList.add('ti-circle-check');
    } else {
        toastEl.classList.add('bg-danger');
        if (toastIcon) toastIcon.classList.add('ti-alert-triangle');
    }

    // Show the toast
    const toast = bootstrap.Toast.getOrCreateInstance(toastEl, { 
        delay: 4000,
        autohide: true 
    });
    toast.show();
};

