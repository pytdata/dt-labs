document.addEventListener('DOMContentLoaded', function() {
    const rowContainer = document.getElementById('dynamic-permission-rows');
    const addBtn = document.getElementById('add-permission-row');
    const roleNameInput = document.getElementById('role_name');
    const roleSlugInput = document.getElementById('role_slug');

    // Available resources in your system
    const resources = ['patients', 'billing', 'inventory', 'lab_results', 'staff', 'appointments'];
    // Available actions
    const actions = ['read', 'write', 'update', 'delete'];

    // Auto-generate slug from name
    roleNameInput.addEventListener('input', (e) => {
        roleSlugInput.value = e.target.value.toLowerCase().replace(/\s+/g, '_').replace(/[^\w-]+/g, '');
    });

    function createPermissionRow() {
        const rowId = Date.now();
        const rowHtml = `
            <div class="row g-2 mb-2 align-items-center permission-row" id="row_${rowId}">
                <div class="col-md-5">
                    <select class="form-select resource-select">
                        <option value="">-- Select Module --</option>
                        ${resources.map(r => `<option value="${r}">${r.toUpperCase()}</option>`).join('')}
                    </select>
                </div>
                <div class="col-md-5">
                    <div class="d-flex gap-2 flex-wrap">
                        ${actions.map(a => `
                            <div class="form-check">
                                <input class="form-check-input action-check" type="checkbox" value="${a}" id="${a}_${rowId}">
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

    addBtn.addEventListener('click', createPermissionRow);

    // Collect data for backend
    document.getElementById('saveRoleBtn').addEventListener('click', function() {
        const payload = {
            name: roleNameInput.value,
            slug: roleSlugInput.value,
            permissions: {}
        };

        document.querySelectorAll('.permission-row').forEach(row => {
            const resource = row.querySelector('.resource-select').value;
            const selectedActions = Array.from(row.querySelectorAll('.action-check:checked')).map(c => c.value);
            
            if (resource && selectedActions.length > 0) {
                payload.permissions[resource] = selectedActions;
            }
        });

        console.log("Saving RBAC Payload:", payload);
        // Here you would fetch('/api/v1/settings/roles', { method: 'POST', body: JSON.stringify(payload) })
    });
});