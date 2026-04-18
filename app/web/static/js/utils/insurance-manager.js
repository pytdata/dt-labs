const InsuranceManager = {
    apiURL: "/api/v1/settings/insurance/",

    init() {
        this.form = document.querySelector("#insurance__form");
        this.container = document.querySelector("#insurance__list__container");
        this.bindEvents();
        this.loadData();
    },

    bindEvents() {
        this.form?.addEventListener("submit", (e) => this.handleSubmit(e));
    },

    async loadData() {
        try {
            const res = await fetch(this.apiURL);
            const data = await res.json();
            this.render(data);
        } catch (err) {
            window.showToast("Failed to load insurance data", "danger");
        }
    },

    async handleSubmit(e) {
        e.preventDefault();
        const btn = document.querySelector("#saveInsuranceBtn");
        btn.disabled = true;

        const formData = new FormData(e.target);
        const payload = Object.fromEntries(formData.entries());

        try {
            const res = await fetch(this.apiURL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error("Could not save company");

            window.showToast("Insurance company added!", "success");
            bootstrap.Modal.getInstance(document.querySelector("#insuranceModal")).hide();
            e.target.reset();
            this.loadData();
        } catch (err) {
            window.showToast(err.message, "danger");
        } finally {
            btn.disabled = false;
        }
    },

   render(items) {
    if (!items.length) {
        this.container.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No insurance companies registered.</td></tr>';
        return;
    }

    this.container.innerHTML = items.map(item => {
        // High visibility logic
        const isPublic = item.type === 'public';
        const badgeClass = isPublic ? 'bg-success' : 'bg-primary';
        const icon = isPublic ? 'ti-building-community' : 'ti-shield-lock';
        const label = isPublic ? 'PUBLIC (NHIS)' : 'PRIVATE';

        return `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="avatar avatar-sm bg-light me-2">
                             <i class="ti ${icon} text-dark fs-16"></i>
                        </div>
                        <span class="fw-bold text-dark">${item.name}</span>
                    </div>
                </td>
                <td>
                    <span class="badge ${badgeClass} d-inline-flex align-items-center px-2 py-1 shadow-sm">
                        <i class="ti ${icon} me-1 fs-10"></i>
                        ${label}
                    </span>
                </td>
                <td>
                    <div class="d-flex flex-column">
                        <span class="text-dark fw-medium fs-13"><i class="ti ti-phone me-1"></i>${item.phone || 'N/A'}</span>
                        <span class="text-muted fs-11"><i class="ti ti-mail me-1"></i>${item.email || 'N/A'}</span>
                    </div>
                </td>
                <td class="text-end">
                    <div class="dropdown">
                        <button class="btn btn-sm btn-icon btn-light" data-bs-toggle="dropdown">
                            <i class="ti ti-dots-vertical"></i>
                        </button>
                        <ul class="dropdown-menu dropdown-menu-end">
                            <li><a class="dropdown-item text-danger" href="javascript:void(0);" onclick="InsuranceManager.delete('${item.id}')">
                                <i class="ti ti-trash me-2"></i>Delete
                            </a></li>
                        </ul>
                    </div>
                </td>
            </tr>
        `;
    }).join("");
}
};

document.addEventListener("DOMContentLoaded", () => InsuranceManager.init());


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
