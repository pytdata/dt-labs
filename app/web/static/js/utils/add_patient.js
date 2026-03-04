const addNewPatientFormEl = document.querySelector("#add_new_patient")

addNewPatientFormEl.addEventListener("submit", async (e) => {

    e.preventDefault();

    const data = new FormData(addNewPatientFormEl);
    
    let payload = Object.fromEntries(data.entries());
    // Filter out entries where the value is an empty string
    payload = Object.fromEntries(
    Object.entries(payload).filter(([_, value]) => value !== "")
    );

    try {
        const res = await fetch("/api/v1/patients/", {
            "method": "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error("Failed to create patient.");

        const data = await res.json();
        console.log("Patient created successfully", data)

        alert("Patient created successfully", data)

    } catch (error) {
        // TODO: Add notification alert
        console.log(error);
        alert(error)
    }

})
