/**
 * InsightDesk — Dashboard Initialization
 */

document.addEventListener('DOMContentLoaded', async () => {
    if (typeof DATASET_ID === 'undefined') return;

    try {
        const response = await fetch(`/dashboard/api/${DATASET_ID}/charts`);
        if (!response.ok) throw new Error('Failed to fetch chart data');
        const data = await response.json();

        initTrendChart(data.trend);
        initCategoryChart(data.category);
    } catch (error) {
        console.error('Error loading charts:', error);
    }
});

let trendChartInst = null;
let categoryChartInst = null;

function initTrendChart(data) {
    const ctx = document.getElementById('trendChart').getContext('2d');
    
    // Create gradient fill
    const gradientFill = ctx.createLinearGradient(0, 0, 0, 400);
    gradientFill.addColorStop(0, COLORS.purpleAlpha);
    gradientFill.addColorStop(1, 'rgba(139, 92, 246, 0)');

    if (trendChartInst) trendChartInst.destroy();
    
    trendChartInst = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Revenue',
                data: data.revenue,
                borderColor: COLORS.purple,
                backgroundColor: gradientFill,
                borderWidth: 3,
                tension: 0.4, // Smooth curves
                fill: true,
                pointBackgroundColor: COLORS.purple,
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: COLORS.purple,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(17, 25, 40, 0.9)',
                    titleFont: { size: 13, family: "'Plus Jakarta Sans', sans-serif" },
                    bodyFont: { size: 14, weight: 'bold' },
                    padding: 12,
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            let val = context.raw;
                            return ' $' + val.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            if (value >= 1000000) return '$' + (value/1000000).toFixed(1) + 'M';
                            if (value >= 1000) return '$' + (value/1000).toFixed(1) + 'k';
                            return '$' + value;
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index',
            },
        }
    });
}

function initCategoryChart(data) {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    
    // Sort data descending
    let combined = data.labels.map((l, i) => ({ label: l, value: data.revenue[i] }));
    combined.sort((a, b) => b.value - a.value);
    
    // Take top 8 categories to avoid clutter
    combined = combined.slice(0, 8);
    
    const sortedLabels = combined.map(c => c.label);
    const sortedData = combined.map(c => c.value);

    // Color palette for bars
    const palette = [
        COLORS.purple, COLORS.teal, COLORS.pink, COLORS.emerald, 
        COLORS.amber, '#3b82f6', '#8b5cf6', '#06b6d4'
    ];

    if (categoryChartInst) categoryChartInst.destroy();
    
    categoryChartInst = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sortedLabels,
            datasets: [{
                label: 'Revenue',
                data: sortedData,
                backgroundColor: palette.map(c => {
                    const grad = ctx.createLinearGradient(0, 0, 0, 400);
                    grad.addColorStop(0, c);
                    grad.addColorStop(1, 'rgba(0,0,0,0.5)');
                    return grad;
                }),
                borderRadius: 6,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(17, 25, 40, 0.9)',
                    callbacks: {
                        label: function(context) {
                            let val = context.raw;
                            return ' $' + val.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            if (value >= 1000000) return '$' + (value/1000000).toFixed(1) + 'M';
                            if (value >= 1000) return '$' + (value/1000).toFixed(1) + 'k';
                            return '$' + value;
                        }
                    }
                }
            }
        }
    });
}
