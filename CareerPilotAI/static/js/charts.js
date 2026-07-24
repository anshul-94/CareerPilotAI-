/* ============================================
   CareerPilot AI — Chart Factory
   Reusable Chart.js configurations with dark theme
   ============================================ */

const ChartFactory = {
    // Dark theme defaults
    defaults: {
        fontFamily: "'Inter', sans-serif",
        fontColor: '#A0A0C0',
        gridColor: 'rgba(255, 255, 255, 0.05)',
        primaryColor: '#6C63FF',
        accentColor: '#00D4AA',
        warningColor: '#FFB347',
        dangerColor: '#FF6B6B',
        infoColor: '#3B82F6',
    },

    // Apply global defaults
    applyDefaults() {
        if (typeof Chart === 'undefined') return;
        
        Chart.defaults.color = this.defaults.fontColor;
        Chart.defaults.font.family = this.defaults.fontFamily;
        Chart.defaults.font.size = 12;
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.padding = 15;
        Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 12, 41, 0.95)';
        Chart.defaults.plugins.tooltip.borderColor = 'rgba(255, 255, 255, 0.1)';
        Chart.defaults.plugins.tooltip.borderWidth = 1;
        Chart.defaults.plugins.tooltip.cornerRadius = 8;
        Chart.defaults.plugins.tooltip.padding = 12;
        Chart.defaults.plugins.tooltip.titleFont = { size: 13, weight: '600' };
        Chart.defaults.plugins.tooltip.bodyFont = { size: 12 };
    },

    // ── Line Chart ──────────────────────────────
    createLineChart(ctx, labels, datasets, options = {}) {
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: datasets.map((ds, i) => ({
                    label: ds.label,
                    data: ds.data,
                    borderColor: ds.color || this.getColor(i),
                    backgroundColor: this.hexToRgba(ds.color || this.getColor(i), 0.1),
                    borderWidth: 2,
                    tension: 0.4,
                    fill: ds.fill !== false,
                    pointBackgroundColor: ds.color || this.getColor(i),
                    pointBorderColor: '#0B0B1A',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    ...ds.options
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { color: this.defaults.gridColor, drawBorder: false },
                        ticks: { padding: 10 }
                    },
                    y: {
                        grid: { color: this.defaults.gridColor, drawBorder: false },
                        ticks: { padding: 10 },
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: { position: 'top', align: 'end' }
                },
                ...options
            }
        });
    },

    // ── Bar Chart ───────────────────────────────
    createBarChart(ctx, labels, datasets, options = {}) {
        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: datasets.map((ds, i) => ({
                    label: ds.label,
                    data: ds.data,
                    backgroundColor: ds.colors || this.getGradientColors(labels.length),
                    borderRadius: 6,
                    borderSkipped: false,
                    barThickness: ds.barThickness || 'flex',
                    maxBarThickness: 40,
                    ...ds.options
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { padding: 10 }
                    },
                    y: {
                        grid: { color: this.defaults.gridColor, drawBorder: false },
                        ticks: { padding: 10 },
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: { display: datasets.length > 1 }
                },
                ...options
            }
        });
    },

    // ── Doughnut Chart ──────────────────────────
    createDoughnutChart(ctx, labels, data, options = {}) {
        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{
                    data,
                    backgroundColor: this.getGradientColors(labels.length),
                    borderWidth: 0,
                    cutout: '72%',
                    spacing: 3,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { padding: 15, usePointStyle: true }
                    }
                },
                ...options
            }
        });
    },

    // ── Radar Chart ─────────────────────────────
    createRadarChart(ctx, labels, datasets, options = {}) {
        return new Chart(ctx, {
            type: 'radar',
            data: {
                labels,
                datasets: datasets.map((ds, i) => ({
                    label: ds.label,
                    data: ds.data,
                    borderColor: ds.color || this.getColor(i),
                    backgroundColor: this.hexToRgba(ds.color || this.getColor(i), 0.15),
                    borderWidth: 2,
                    pointBackgroundColor: ds.color || this.getColor(i),
                    pointRadius: 4,
                    ...ds.options
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            stepSize: 20,
                            display: false
                        },
                        grid: { color: this.defaults.gridColor },
                        pointLabels: {
                            font: { size: 11 },
                            color: this.defaults.fontColor
                        },
                        angleLines: { color: this.defaults.gridColor }
                    }
                },
                plugins: {
                    legend: { position: 'bottom' }
                },
                ...options
            }
        });
    },

    // ── Helper Functions ────────────────────────
    getColor(index) {
        const colors = [
            '#6C63FF', '#00D4AA', '#3B82F6', '#FFB347',
            '#FF6B6B', '#8B5CF6', '#EC4899', '#14B8A6'
        ];
        return colors[index % colors.length];
    },

    getGradientColors(count) {
        const colors = [
            '#6C63FF', '#00D4AA', '#3B82F6', '#FFB347',
            '#FF6B6B', '#8B5CF6', '#EC4899', '#14B8A6',
            '#F59E0B', '#10B981', '#EF4444', '#8B83FF'
        ];
        return colors.slice(0, count);
    },

    hexToRgba(hex, alpha = 1) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
};

// Apply defaults when Chart.js is loaded
document.addEventListener('DOMContentLoaded', () => {
    ChartFactory.applyDefaults();
});
