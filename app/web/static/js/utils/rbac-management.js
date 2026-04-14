document.addEventListener('DOMContentLoaded', async function() {
    const rowContainer = document.getElementById('dynamic-permission-rows');
    const addBtn = document.getElementById('add-permission-row');
    const roleNameInput = document.getElementById('role_name');
    const roleSlugInput = document.getElementById('role_slug');
    const roleModalEl = document.getElementById('roleModal');
    
    // State Management
    let editingRoleId = null;
    let availableResources = []; // Will be populated from the API
    const actions = ['read', 'write', 'update', 'delete'];

    /**
     * INITIALIZE: Fetch resources from the backend once on load
     */
    async function initializeResources() {
        try {
            const response = await fetch('/api/v1/settings/resources');
            if (!response.ok) throw new Error("Failed to load system resources");
            availableResources = await response.json();
        } catch (error) {
            console.error(error);
            // Fallback to minimal set if API fails to prevent total UI breakage
            availableResources = ['patients', 'billing', 'staff', 'settings'];
            showToast("Warning: Using fallback resource list.", "warning");
        }
    }

    // Auto-generate slug from name (only if not editing)
    roleNameInput.addEventListener('input', (e) => {
        if (!editingRoleId) {
            roleSlugInput.value = e.target.value
                .toLowerCase()
                .replace(/\s+/g, '_')
                .replace(/[^\w-]+/g, '');
        }
    });

    /**
     * CORE: Create a Permission Row
     * @param {string} selectedResource - Optional resource to pre-select
     * @param {Array} selectedActions - Optional actions to pre-check
     */
    function createPermissionRow(selectedResource = "", selectedActions = []) {
        const rowId = Date.now() + Math.random().toString(36).substr(2, 9);
        const rowHtml = `
            <div class="row g-2 mb-2 align-items-center permission-row" id="row_${rowId}">
                <div class="col-md-5">
                    <select class="form-select resource-select">
                        <option value="">-- Select Module --</option>
                        ${availableResources.map(r => `
                            <option value="${r}" ${r === selectedResource ? 'selected' : ''}>
                                ${r.toUpperCase().replace('_', ' ')}
                            </option>
                        `).join('')}
                    </select>
                </div>
                <div class="col-md-5">
                    <div class="d-flex gap-2 flex-wrap">
                        ${actions.map(a => `
                            <div class="form-check">
                                <input class="form-check-input action-check" type="checkbox" value="${a}" 
                                    id="${a}_${rowId}" ${selectedActions.includes(a) ? 'checked' : ''}>
                                <label class="form-check-label small" for="${a}_${rowId}">${a}</label>
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div class="col-md-2 text-end">
                    <button type="button" class="btn btn-sm btn-outline-danger border-0" onclick="document.getElementById('row_${rowId}').remove()">
                        <i class="ti ti-trash"></i>
                    </button>
                </div>
            </div>
        `;
        rowContainer.insertAdjacentHTML('beforeend', rowHtml);
    }

    addBtn.addEventListener('click', () => createPermissionRow());

    /**
     * FETCH & RENDER ALL ROLES
     */
    async function fetchAndRenderRoles() {
        const container = document.getElementById('roles_list_container');
        try {
            const response = await fetch('/api/v1/settings/roles');
            if (!response.ok) throw new Error("Failed to fetch roles");
            const roles = await response.json();
            
            if (roles.length === 0) {
                container.innerHTML = `<tr><td colspan="4" class="text-center py-4 text-muted">No custom roles defined yet.</td></tr>`;
                return;
            }

            container.innerHTML = roles.map(role => {
                const moduleCount = role.permissions ? new Set(role.permissions.map(p => p.resource)).size : 0;
                return `
                    <tr>
                        <td class="ps-4 fw-medium">${role.name}</td>
                        <td><span class="badge bg-light text-primary border">${role.slug}</span></td>
                        <td><span class="text-dark fw-bold">${moduleCount}</span> <span class="text-muted small">Modules</span></td>
                        <td class="text-end pe-4">
                            <button class="btn btn-sm btn-icon btn-flat-info edit-role-btn" data-id="${role.id}">
                                <i class="ti ti-edit"></i>
                            </button>
                            <button class="btn btn-sm btn-icon btn-flat-danger delete-role-btn" data-id="${role.id}">
                                <i class="ti ti-trash"></i>
                            </button>
                        </td>
                    </tr>`;
            }).join('');
        } catch (error) {
            console.error(error);
            container.innerHTML = `<tr><td colspan="4" class="text-center text-danger py-4">Error loading roles.</td></tr>`;
        }
    }

    /**
     * EDIT ROLE: Fetch individual role and populate modal
     */
    document.getElementById('roles_list_container').addEventListener('click', async function(e) {
        const editBtn = e.target.closest('.edit-role-btn');
        if (!editBtn) return;

        editingRoleId = editBtn.dataset.id;
        
        try {
            const response = await fetch(`/api/v1/settings/roles/${editingRoleId}`);
            if (!response.ok) throw new Error("Could not fetch role data");
            const role = await response.json();

            // Populate static fields
            roleNameInput.value = role.name;
            roleSlugInput.value = role.slug;
            
            // Clear current rows
            rowContainer.innerHTML = '';

            // Group permissions by resource to recreate rows
            const grouped = {};
            role.permissions.forEach(p => {
                if (!grouped[p.resource]) grouped[p.resource] = [];
                grouped[p.resource].push(p.action);
            });

            Object.entries(grouped).forEach(([resource, actions]) => {
                createPermissionRow(resource, actions);
            });

            // Update UI
            document.querySelector('#roleModal .modal-title').innerText = "Edit System Role";
            const modal = bootstrap.Modal.getOrCreateInstance(roleModalEl);
            modal.show();

        } catch (error) {
            showToast("Failed to load role data", "danger");
        }
    });

    /**
     * SAVE ROLE (POST or PUT)
     */
    document.getElementById('saveRoleBtn').addEventListener('click', async function() {
        const btn = this;
        const originalText = btn.innerHTML;
        
        const payload = {
            name: roleNameInput.value.trim(),
            slug: roleSlugInput.value.trim(),
            description: "", 
            access_map: {} 
        };

        if (!payload.name || !payload.slug) {
            showToast("Please provide a Role Name and Slug.", "danger");
            return;
        }

        const rows = document.querySelectorAll('.permission-row');
        rows.forEach(row => {
            const resource = row.querySelector('.resource-select').value;
            const selectedActions = Array.from(row.querySelectorAll('.action-check:checked')).map(c => c.value);
            if (resource && selectedActions.length > 0) {
                if (payload.access_map[resource]) {
                    payload.access_map[resource] = [...new Set([...payload.access_map[resource], ...selectedActions])];
                } else {
                    payload.access_map[resource] = selectedActions;
                }
            }
        });

        if (Object.keys(payload.access_map).length === 0) {
            showToast("No module actions selected.", "warning");
            return;
        }

        try {
            btn.disabled = true;
            btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> Saving...`;

            const url = editingRoleId ? `/api/v1/settings/roles/${editingRoleId}` : '/api/v1/settings/roles';
            const method = editingRoleId ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                showToast("Role saved successfully!", "success");
                bootstrap.Modal.getInstance(roleModalEl).hide();
                setTimeout(() => location.reload(), 1000);
            } else {
                const resData = await response.json();
                showToast(resData.detail || "Error saving role", "danger");
            }
        } catch (error) {
            showToast("Connection Error. Please try again.", "danger");
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    });

    // Reset editing state when modal is closed
    roleModalEl.addEventListener('hidden.bs.modal', function () {
        editingRoleId = null;
        document.getElementById('role_config_form').reset();
        rowContainer.innerHTML = '';
        document.querySelector('#roleModal .modal-title').innerText = "Configuration: System Role";
    });

    // EXECUTION FLOW
    // 1. Load resources first so the "Add Row" button works immediately
    await initializeResources();
    // 2. Render the table
    fetchAndRenderRoles();
});

// Toast Utility
window.showToast = window.showToast || function(message, type = 'success') {
    const toastEl = document.getElementById('appCustomToast');
    const toastText = document.getElementById('appCustomToastText');
    const toastIcon = document.getElementById('toastIcon');
    if (!toastEl) return;

    toastEl.classList.remove('bg-success', 'bg-danger', 'bg-warning');
    toastText.innerText = message;

    if (type === 'success') {
        toastEl.classList.add('bg-success');
        if (toastIcon) toastIcon.className = 'ti ti-circle-check fs-4 me-2';
    } else if (type === 'warning') {
        toastEl.classList.add('bg-warning');
        if (toastIcon) toastIcon.className = 'ti ti-alert-circle fs-4 me-2';
    } else {
        toastEl.classList.add('bg-danger');
        if (toastIcon) toastIcon.className = 'ti ti-alert-triangle fs-4 me-2';
    }

    bootstrap.Toast.getOrCreateInstance(toastEl).show();
};