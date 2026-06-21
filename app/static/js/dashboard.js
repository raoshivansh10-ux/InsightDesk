/**
 * InsightDesk — Dashboard Initialization
 */

document.addEventListener('DOMContentLoaded', async () => {
    if (typeof DATASET_ID === 'undefined') return;

    try {
        const response = await fetch(`/dashboard/api/${DATASET_ID}/charts`);
        if (!response.ok) throw new Error('Failed to fetch chart data');
        const data = await response.json();

        initTrendChart(data.trend, data.forecast);
        initCategoryChart(data.category);
    } catch (error) {
        console.error('Error loading charts:', error);
    }
});

let trendChartInst = null;
let categoryChartInst = null;

function initTrendChart(data, forecastData) {
    const ctx = document.getElementById('trendChart').getContext('2d');
    
    // Create gradient fill
    const gradientFill = ctx.createLinearGradient(0, 0, 0, 400);
    gradientFill.addColorStop(0, COLORS.purpleAlpha);
    gradientFill.addColorStop(1, 'rgba(139, 92, 246, 0)');

    if (trendChartInst) trendChartInst.destroy();
    
    let labels = [...data.labels];
    let datasets = [{
        label: 'Historical Revenue',
        data: [...data.revenue],
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
    }];
    
    if (forecastData && forecastData.dates && forecastData.dates.length > 0) {
        const histLen = data.labels.length;
        // Append dates
        labels = labels.concat(forecastData.dates);
        
        // Pad historical data with nulls so it ends
        const paddedHist = [...data.revenue];
        for (let i=0; i<forecastData.dates.length; i++) paddedHist.push(null);
        datasets[0].data = paddedHist;
        
        // Create Forecast dataset
        const forecastVals = Array(histLen - 1).fill(null);
        // Connect the last historical point
        forecastVals.push(data.revenue[histLen - 1]);
        forecastVals.push(...forecastData.predicted_values);
        
        datasets.push({
            label: 'Forecast',
            data: forecastVals,
            borderColor: COLORS.teal,
            borderWidth: 2,
            borderDash: [5, 5], // Dashed line
            tension: 0.4,
            fill: false,
            pointBackgroundColor: COLORS.teal,
            pointRadius: 0,
            pointHoverRadius: 4
        });
        
        // Add confidence bounds if available (Upper Bound)
        if (forecastData.upper_bounds) {
            const upperVals = Array(histLen - 1).fill(null);
            upperVals.push(data.revenue[histLen - 1]);
            upperVals.push(...forecastData.upper_bounds);
            datasets.push({
                label: 'Upper Bound',
                data: upperVals,
                borderColor: 'transparent',
                backgroundColor: 'rgba(6, 182, 212, 0.1)',
                fill: '-1', // fill to previous dataset (Forecast)
                pointRadius: 0,
                pointHoverRadius: 0
            });
        }
        
        // Lower Bound
        if (forecastData.lower_bounds) {
            const lowerVals = Array(histLen - 1).fill(null);
            lowerVals.push(data.revenue[histLen - 1]);
            lowerVals.push(...forecastData.lower_bounds);
            datasets.push({
                label: 'Lower Bound',
                data: lowerVals,
                borderColor: 'transparent',
                backgroundColor: 'rgba(6, 182, 212, 0.1)',
                fill: '-2', // fill to Forecast
                pointRadius: 0,
                pointHoverRadius: 0
            });
        }
    }
    
    trendChartInst = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
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
