/**
 * InsightDesk — Chart.js Global Configuration
 * Premium dark mode styling
 */

Chart.defaults.color = '#9ca3af'; // text-secondary
Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";
Chart.defaults.scale.grid.color = 'rgba(255, 255, 255, 0.05)';
Chart.defaults.scale.grid.borderColor = 'transparent';

// Theme colors
const COLORS = {
    purple: 'rgb(139, 92, 246)',
    purpleAlpha: 'rgba(139, 92, 246, 0.2)',
    teal: 'rgb(6, 182, 212)',
    tealAlpha: 'rgba(6, 182, 212, 0.2)',
    pink: 'rgb(236, 72, 153)',
    pinkAlpha: 'rgba(236, 72, 153, 0.2)',
    emerald: 'rgb(16, 185, 129)',
    amber: 'rgb(245, 158, 11)'
};

// Create a linear gradient for charts
function createGradient(ctx, colorStart, colorEnd) {
    if (!ctx) return colorStart;
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, colorStart);
    gradient.addColorStop(1, colorEnd);
    return gradient;
}
