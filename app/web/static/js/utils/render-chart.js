// Ensure myChart is globally accessible to this script
window.myChart = null;

const chartColors = [
    '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#858796', '#5a5c69'
];

async function updateChart() {
    try {
        const reportType = document.getElementById('reportType').value;
        const res = await fetch(`/api/v1/account/reports/data?type=${reportType}`);
        const data = await res.json();

        const canvas = document.getElementById('myChart');
        if (!canvas) {
            console.error("Canvas element 'myChart' not found");
            return;
        }
        const ctx = canvas.getContext('2d');

        // FIXED: Check if myChart is an instance of Chart before destroying
        if (window.myChart instanceof Chart) {
            window.myChart.destroy();
        }

        // Prepare datasets
        const formattedDatasets = data.datasets.map((ds) => {
            const isPieOrBar = (data.type === 'doughnut' || data.type === 'pie' || data.type === 'bar');
            return {
                ...ds,
                backgroundColor: isPieOrBar 
                    ? chartColors.slice(0, data.labels.length) 
                    : 'rgba(78, 115, 223, 0.2)',
                borderColor: isPieOrBar ? '#ffffff' : '#4e73df',
                borderWidth: 2,
                fill: data.type === 'line',
                tension: 0.3
            };
        });

        // Create new chart instance
        window.myChart = new Chart(ctx, {
            type: data.type,
            data: {
                labels: data.labels,
                datasets: formattedDatasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    }
                }
            }
        });
    } catch (error) {
        console.error("Failed to render chart:", error);
    }
}

// Attach listener and run initial load
document.addEventListener('DOMContentLoaded', () => {
    const selector = document.getElementById('reportType');
    if (selector) {
        selector.addEventListener('change', updateChart);
        updateChart(); // Load first report automatically
    }
});