document.addEventListener('DOMContentLoaded', function() {
    loadTests();
    loadSamples();

    // 1. SUBMIT NEW SAMPLE
    document.getElementById('addSampleForm').onsubmit = async function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const payload = { category_name: formData.get('category_name') };

        try {
            const res = await fetch('/api/v1/sample-categories', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                bootstrap.Modal.getInstance(document.getElementById('addSampleModal')).hide();
                this.reset();
                loadSamples();
            } else {
                const err = await res.json();
                alert(err.detail || "Error saving sample");
            }
        } catch (error) { console.error(error); }
    };

    // 2. SUBMIT NEW TEST
    document.getElementById('addTestForm').onsubmit = async function(e) {
        e.preventDefault();
        const fd = new FormData(this);
        const payload = {
            name: fd.get('name'),
            test_category_id: parseInt(fd.get('test_category_id')),
            sample_category_id: fd.get('sample_category_id') ? parseInt(fd.get('sample_category_id')) : null,
            department: fd.get('department'),
            price_ghs: parseFloat(fd.get('price_ghs')),
            requires_phlebotomy: fd.get('requires_phlebotomy') === 'on'
        };

        try {
            const res = await fetch('/api/v1/tests', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                bootstrap.Modal.getInstance(document.getElementById('addTestModal')).hide();
                this.reset();
                loadTests();
            }
        } catch (error) { console.error(error); }
    };
});

async function loadSamples() {
    const res = await fetch('/api/v1/sample-categories');
    const samples = await res.json();
    
    // Fill Table
    const container = document.getElementById('sample_list_container');
    container.innerHTML = samples.map(s => `
        <tr>
            <td>#${s.id}</td>
            <td class="fw-bold">${s.category_name.toUpperCase()}</td>
            <td class="text-end"><button class="btn btn-sm btn-outline-danger"><i class="ti ti-trash"></i></button></td>
        </tr>
    `).join('');

    // Fill Dropdown in Test Modal
    const dropdown = document.getElementById('modal_sample_cat');
    dropdown.innerHTML = '<option value="">No sample required</option>' + 
        samples.map(s => `<option value="${s.id}">${s.category_name.toUpperCase()}</option>`).join('');
}

async function loadTests() {
    const res = await fetch('/api/v1/tests');
    const tests = await res.json();
    
    const container = document.getElementById('test_list_container');
    container.innerHTML = tests.map(t => `
        <tr>
            <td><div class="fw-bold text-dark">${t.name}</div></td>
            <td><span class="badge bg-soft-primary text-primary">${t.test_category?.category_name || 'N/A'}</span></td>
            <td>${t.department || '-'}</td>
            <td>${t.sample_category?.category_name || 'None'}</td>
            <td class="fw-bold">GHS ${parseFloat(t.price_ghs).toFixed(2)}</td>
            <td class="text-end">
                <button class="btn btn-sm btn-light"><i class="ti ti-edit"></i></button>
            </td>
        </tr>
    `).join('');
}