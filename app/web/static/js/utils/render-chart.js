/**
 * DASHBOARD CHART RENDERER
 */
let myChartInstance = null;

const chartColors = [
    '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#858796', '#5a5c69'
];

async function updateChart() {
    try {
        const selector = document.getElementById('reportType');
        if (!selector) return;
        
        const reportType = selector.value;
        const res = await fetch(`/api/v1/account/reports/data?type=${reportType}`);
        
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        
        const data = await res.json();

        // 1. Validation: Ensure we have the minimum requirements to draw a chart
        if (!data || !data.type || !data.labels || data.labels.length === 0) {
            console.warn("No data returned for chart type:", reportType);
            showNoDataMessage();
            return;
        }

        const canvas = document.getElementById('myChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        // 2. Destroy existing instance to prevent "ghosting" on hover
        if (myChartInstance) {
            myChartInstance.destroy();
        }

        // 3. Configure Visuals based on Chart Type
        const isPieOrDoughnut = ['doughnut', 'pie'].includes(data.type);
        const isBar = data.type === 'bar';

        const formattedDatasets = data.datasets.map((ds) => {
            return {
                ...ds,
                backgroundColor: isPieOrDoughnut || isBar 
                    ? chartColors.slice(0, data.labels.length) 
                    : 'rgba(78, 115, 223, 0.1)',
                borderColor: isPieOrDoughnut ? '#ffffff' : '#4e73df',
                borderWidth: 2,
                fill: data.type === 'line',
                tension: 0.4, // Smoothing for line charts
                borderRadius: isBar ? 6 : 0 // Rounded corners for bars
            };
        });

        // 4. Initialize Chart
        myChartInstance = new Chart(ctx, {
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
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                            font: { family: 'Inter, sans-serif', size: 12 }
                        }
                    },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        padding: 12,
                        titleFont: { size: 14 },
                        bodyFont: { size: 13 },
                        cornerRadius: 8,
                        displayColors: !isPieOrDoughnut
                    }
                },
                scales: isPieOrDoughnut ? {} : {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.05)', drawBorder: false },
                        ticks: { font: { size: 11 } }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { font: { size: 11 } }
                    }
                }
            }
        });
    } catch (error) {
        console.error("Failed to render chart:", error);
    }
}

/**
 * Helper to show a "No Data" message inside the canvas area
 */
function showNoDataMessage() {
    if (myChartInstance) myChartInstance.destroy();
    const canvas = document.getElementById('myChart');
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.textAlign = 'center';
    ctx.fillStyle = '#64748b';
    ctx.font = '14px Inter';
    ctx.fillText('No data available for this period', canvas.width / 2, canvas.height / 2);
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    const selector = document.getElementById('reportType');
    if (selector) {
        selector.addEventListener('change', updateChart);
        // Add a small delay for DOM rendering if needed
        setTimeout(updateChart, 100); 
    }
});