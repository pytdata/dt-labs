// Helper Function for Interactive Feedback
function showFeedback({ title, message, type = 'success', redirectUrl = null }) {
    const modalEl = document.getElementById('feedbackModal');
    const titleEl = document.getElementById('feedbackTitle');
    const messageEl = document.getElementById('feedbackMessage');
    const iconContainer = document.getElementById('feedbackIconContainer');
    const closeBtn = document.getElementById('feedbackCloseBtn');

    // Set Content
    titleEl.innerText = title;
    messageEl.innerText = message;

    // Set Visual Style (Success vs Error)
    if (type === 'success') {
        iconContainer.innerHTML = `<div class="bg-light-success text-success rounded-circle d-inline-flex align-items-center justify-content-center" style="width: 70px; height: 70px; font-size: 2rem;"><i class="ti ti-circle-check"></i></div>`;
        closeBtn.className = 'btn btn-success py-2';
    } else {
        iconContainer.innerHTML = `<div class="bg-light-danger text-danger rounded-circle d-inline-flex align-items-center justify-content-center" style="width: 70px; height: 70px; font-size: 2rem;"><i class="ti ti-alert-circle"></i></div>`;
        closeBtn.className = 'btn btn-danger py-2';
    }

    const modal = new bootstrap.Modal(modalEl);
    modal.show();

    // Handle Redirect on Close
    if (redirectUrl) {
        modalEl.addEventListener('hidden.bs.modal', () => {
            window.location.href = redirectUrl;
        }, { once: true });
    }
}

// Form Submission logic
const addNewPatientFormEl = document.querySelector("#add_new_patient");

addNewPatientFormEl.addEventListener("submit", async (e) => {
    e.preventDefault();

    const data = new FormData(addNewPatientFormEl);
    let payload = Object.fromEntries(data.entries());
    
    // Clean payload
    payload = Object.fromEntries(
        Object.entries(payload).filter(([_, value]) => value !== "")
    );

    try {
        const res = await fetch("/api/v1/patients/", {
            method: "POST", 
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload)
        });

        const result = await res.json();

        if (!res.ok) {
            // Handle specific backend errors (like duplicate phone numbers)
            throw new Error(result.detail || "Failed to create patient.");
        }

        // Success Flow
        showFeedback({
            title: "Patient Saved!",
            message: `${payload.first_name} ${payload.surname} has been registered successfully.`,
            type: 'success',
            redirectUrl: "/patients" // The redirect path you wanted
        });

    } catch (error) {
        // Error Flow
        showFeedback({
            title: "Registration Failed",
            message: error.message,
            type: 'error'
        });
    }
});