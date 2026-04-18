async function refreshTopMetrics() {
    try {
        const response = await fetch('/api/v1/analytics/top-metrics');
        const data = await response.json();

        // 1. Update Patient Card
        document.getElementById('total-patients-count').innerText = data.patients.value;
        renderSparkline('#chart-1', data.patients.trend, '#4e73df');

        // 2. Update Appointments Card
        const appointCard = document.querySelector('#chart-2').closest('.card');
        appointCard.querySelector('h6').innerText = data.appointments.value;
        renderSparkline('#chart-2', data.appointments.trend, '#6f42c1'); // Secondary color

        // 3. Update Doctors Card
        const doctorCard = document.querySelector('#chart-3').closest('.card');
        doctorCard.querySelector('h6').innerText = data.doctors.value;
        renderSparkline('#chart-3', data.doctors.trend, '#36b9cc'); // Info color

        // 4. Update Transactions Card
        const transCard = document.querySelector('#chart-4').closest('.card');
        transCard.querySelector('h6').innerText = data.transactions.value;
        renderSparkline('#chart-4', data.transactions.trend, '#1cc88a'); // Success color

    } catch (error) {
        console.error("Error loading top metrics:", error);
    }
}

/**
 * Renders a small Sparkline using ApexCharts
 */
function renderSparkline(selector, data, color) {
    const options = {
        series: [{ data: data }],
        chart: {
            type: 'area',
            height: 40,
            sparkline: { enabled: true },
            animations: { enabled: true }
        },
        stroke: { curve: 'smooth', width: 2 },
        fill: {
            opacity: 0.3,
            colors: [color]
        },
        colors: [color],
        tooltip: { enabled: false }
    };

    const container = document.querySelector(selector);
    if (container) {
        container.innerHTML = ''; // Clear previous
        new ApexCharts(container, options).render();
    }
}


async function refreshPatientStatistics() {
    try {
        const response = await fetch('/api/v1/analytics/patient-statistics');
        if (!response.ok) throw new Error("Failed to fetch patient stats");
        
        const data = await response.json();
        
        // Data format: series[0] = New, series[1] = Old
        const newCount = data.series[0];
        const oldCount = data.series[1];
        const total = newCount + oldCount;

        // 1. Update the Text Label
        const textElement = document.getElementById('total-patients-text');
        if (textElement) {
            textElement.innerText = total;
        }

        // 2. Render Chart
        const options = {
            series: [newCount, oldCount],
            chart: {
                type: 'donut',
                height: 280,
                fontFamily: 'Inter, sans-serif',
            },
            labels: ["New Patients", "Old Patients"],
            // MATCHING COLORS: 
            // Index 0 (New) -> Primary Blue
            // Index 1 (Old) -> Secondary Grey
            colors: ['#4e73df', '#858796'], 
            stroke: {
                show: true,
                width: 2,
                colors: ['#fff']
            },
            dataLabels: {
                enabled: false
            },
            legend: {
                show: false 
            },
            plotOptions: {
                pie: {
                    donut: {
                        size: '75%',
                        labels: {
                            show: true,
                            name: { show: false },
                            value: {
                                show: true,
                                fontSize: '24px',
                                fontWeight: 'bold',
                                color: '#1e293b',
                                formatter: () => total
                            },
                            total: {
                                show: true,
                                label: 'Total',
                                formatter: () => total
                            }
                        }
                    }
                }
            },
            tooltip: {
                y: {
                    formatter: (val) => `${val} Patients`
                }
            }
        };

        const chartContainer = document.querySelector("#chart-5");
        if (chartContainer) {
            chartContainer.innerHTML = ''; 
            const chart = new ApexCharts(chartContainer, options);
            chart.render();
        }

    } catch (error) {
        console.error("Error loading patient statistics:", error);
    }
}
async function refreshPatientRecords() {
    try {
        const response = await fetch('/api/v1/analytics/recent-patient-records');
        if (!response.ok) throw new Error("Failed to fetch records");
        
        const patients = await response.json();
        const tableBody = document.getElementById('patient-record-table');
        
        if (!tableBody) return;
        
        tableBody.innerHTML = patients.map(p => `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <a href="/patients/${p.id}" class="avatar avatar-xs me-2">
                            <img src="${p.image}" 
                                 alt="img" 
                                 class="rounded" 
                                 onerror="this.src='/static/img/defaults/male-patient.jpeg'">
                        </a>
                        <div>
                            <h6 class="fs-14 mb-0 fw-medium">
                                <a href="/patients/${p.id}">${p.full_name}</a>
                            </h6>
                        </div>
                    </div>
                </td>
                <td><span class="text-muted">${p.patient_no}</span></td>
                <td><span class="badge bg-light text-dark">${p.sex}</span></td>
                <td>${p.created_at}</td>
                <td class="text-end">
                    <a href="/patients/${p.id}" class="btn btn-icon btn-sm btn-outline-light">
                        <i class="ti ti-eye"></i>
                    </a>
                </td>
            </tr>
        `).join('');

    } catch (error) {
        // console.error("Error loading patient records:", error);
        showToast("Error loading patient records", "error")
    }
}


async function refreshBottomWidgets() {
    try {
        const response = await fetch('/api/v1/analytics/dashboard-bottom-widgets');
        const data = await response.json();

        // 1. Populate Lab Technicians
        const techContainer = document.querySelector('.col-xl-4:first-child .overflow-auto');
        if (techContainer && data.technicians.length > 0) {
            techContainer.innerHTML = data.technicians.map(t => `
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <div class="d-flex align-items-center">
                        <div class="avatar flex-shrink-0">
                            <img src="${t.avatar}" class="rounded" alt="img">
                        </div>
                        <div class="ms-2">
                            <h6 class="fw-semibold fs-14 text-truncate mb-1">${t.name}</h6>
                            <p class="fs-13 mb-0">${t.role}</p>
                        </div>
                    </div>
                    <div class="flex-shrink-0 ms-2">
                       <span class="badge text-dark border fs-13 d-flex align-items-center ps-1">
                        <i class="ti ti-point-filled ${t.status === 'Available' ? 'text-success' : 'text-danger'} me-1"></i>
                        ${t.status}
                       </span>
                    </div>
                </div>
            `).join('');
        }

        // 2. Update Total Earnings
        const earningsTitle = document.querySelector('.col-xl-4:nth-child(2) h6');
        if (earningsTitle) earningsTitle.innerText = data.earnings.total;

        // 3. Populate Lab Results Table
        const resultsTable = document.querySelector('.col-xl-4:last-child tbody');
        if (resultsTable) {
            resultsTable.innerHTML = data.results.map(r => `
                <tr>
                    <td class="border-0 p-2">
                        <div class="d-flex align-items-center">
                            <a href="javascript:void(0);" class="avatar me-2 ${r.type === 'Lab' ? 'bg-success' : 'bg-primary'} rounded-circle">
                                <i class="ti ti-report-analytics fs-20"></i>
                            </a>
                            <div>
                              <h6 class="fs-14 mb-1 fw-semibold">${r.test}</h6>
                              <p class="mb-0 fs-13 d-inline-flex align-items-center">
                                <i class="ti ti-calendar me-1"></i>${r.date}
                              </p>
                            </div>
                        </div>
                    </td>
                    <td class="border-0 p-2">
                        <div class="avatar avatar-sm me-2">
                            <img src="${r.patient_img}" alt="img" class="rounded-circle">
                        </div>
                    </td>
                    <td class="text-end border-0 p-2">
                        <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light me-1"><i class="ti ti-download"></i></a>
                    </td>
                </tr>
            `).join('');
        }

    } catch (error) {
        console.error("Error updating bottom widgets:", error);
    }
}


async function refreshRecentAppointments() {
    try {
        const response = await fetch('/api/v1/analytics/recent-appointments');
        const appointments = await response.json();
        const tableBody = document.querySelector('#recent-appointments-table');
        
        if (!tableBody) return;

        tableBody.innerHTML = appointments.map(appt => {
            // Logic for status badge colors
            let badgeClass = 'badge-soft-info border-info text-info';
            if (appt.status.toLowerCase() === 'completed') badgeClass = 'badge-soft-success border-success text-success';
            if (appt.status.toLowerCase() === 'cancelled') badgeClass = 'badge-soft-danger border-danger text-danger';

            return `
                <tr>
                    <td><a href="javascript:void(0);" class="link-muted">#${appt.patient_no}</a></td>
                    <td>
                        <div class="d-flex align-items-center">
                            <a href="/patients/${appt.id}" class="avatar avatar-xs me-2">
                                <img src="${appt.patient_img}" alt="img" class="rounded">
                            </a>
                            <div>
                                <h6 class="fs-14 mb-0 fw-medium">
                                    <a href="/patients/${appt.id}">${appt.patient_name}</a>
                                </h6>
                            </div>
                        </div>
                    </td>
                    <td>${appt.session_type}</td>
                    <td>
                        <div class="d-flex align-items-center">
                            <div class="avatar avatar-xs me-2">
                                <img src="${appt.doctor_img}" alt="img" class="rounded">
                            </div>
                            <div>
                                <h6 class="fs-14 mb-0 fw-medium">${appt.doctor_name}</h6>
                            </div>
                        </div>
                    </td>
                    <td>${appt.date_time}</td>
                    <td>
                        <span class="badge ${badgeClass} py-1 ps-1 d-inline-flex align-items-center">
                            <i class="ti ti-point-filled me-0 fs-14"></i>${appt.status}
                        </span>
                    </td>
                    <td class="text-end">
                        <a href="javascript:void(0);" class="btn btn-icon btn-sm btn-outline-light" data-bs-toggle="dropdown">
                            <i class="ti ti-dots-vertical"></i>
                        </a>
                        <ul class="dropdown-menu p-2">
                            <li><a href="#" class="dropdown-item d-flex align-items-center"><i class="ti ti-eye me-1"></i>View Details</a></li>
                        </ul>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error("Error loading appointments:", error);
    }
}



document.addEventListener('DOMContentLoaded', () => {
    refreshBottomWidgets();
    refreshPatientRecords();
    refreshRecentAppointments();
    refreshPatientStatistics();
    refreshTopMetrics();
});