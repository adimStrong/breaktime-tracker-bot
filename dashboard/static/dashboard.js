/**
 * Breaktime Tracker Dashboard - Frontend JavaScript
 */

const API_BASE = window.location.origin;
const REFRESH_INTERVAL = 5000; // 5 seconds for realtime sync
const REALTIME_INTERVAL = 3000; // 3 seconds for quick metrics

// Chart instances
let distributionChart = null;
let trendChart = null;
let hourlyChart = null;

// State
let dashboardData = null;
let agentData = [];
let previousBreakCount = 0;

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    loadDashboard();

    // Full dashboard refresh every 5 seconds
    setInterval(loadDashboard, REFRESH_INTERVAL);

    // Quick realtime metrics every 3 seconds
    setInterval(loadRealtimeMetrics, REALTIME_INTERVAL);

    // Search functionality
    document.getElementById('agentSearch').addEventListener('input', filterAgents);
});

// ============================================
// API CALLS
// ============================================

async function fetchAPI(endpoint) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`API Error: ${endpoint}`, error);
        updateConnectionStatus(false);
        return null;
    }
}

async function loadDashboard() {
    const data = await fetchAPI('/api/dashboard');
    if (!data) return;

    dashboardData = data;
    updateConnectionStatus(true);
    updateLastRefresh();

    // Check for new data
    const currentBreakCount = data.realtime?.completed_breaks_today || 0;
    if (previousBreakCount > 0 && currentBreakCount > previousBreakCount) {
        flashUpdate();
    }
    previousBreakCount = currentBreakCount;

    // Update all components
    updateStats(data.realtime, data.break_distribution);
    updateDistributionChart(data.break_distribution);
    updateTrendChart(data.compliance_trend);
    updateAgentTable(data.agent_performance);
    updateHourlyChart(data.hourly_distribution);
}

async function loadRealtimeMetrics() {
    const data = await fetchAPI('/api/realtime');
    if (!data) return;

    // Quick update of key metrics only
    const currentBreakCount = data.completed_breaks_today || 0;
    if (previousBreakCount > 0 && currentBreakCount > previousBreakCount) {
        flashUpdate();
        previousBreakCount = currentBreakCount;
        // Trigger full refresh when new data detected
        loadDashboard();
    }

    // Update connection status and time
    updateConnectionStatus(true);
    updateLastRefresh();
}

function flashUpdate() {
    // Visual feedback for new data
    const cards = document.querySelectorAll('.stat-card');
    cards.forEach(card => {
        card.classList.add('ring-2', 'ring-green-400', 'ring-opacity-75');
        setTimeout(() => {
            card.classList.remove('ring-2', 'ring-green-400', 'ring-opacity-75');
        }, 1000);
    });
}

// ============================================
// UI UPDATES
// ============================================

function updateStats(realtime, distribution) {
    document.getElementById('completedToday').textContent = realtime.completed_breaks_today;
    document.getElementById('totalBreakTime').textContent = formatDuration(realtime.total_break_time_today);
    document.getElementById('agentsActive').textContent = `${realtime.agents_active_today} agents active`;

    // Find eating and smoke breaks from distribution
    let eating = { count: 0, duration: 0 };
    let smoke = { count: 0, duration: 0 };

    for (const d of distribution) {
        if (d.break_type.toLowerCase().includes('eating')) {
            eating = { count: d.count, duration: d.total_duration };
        } else if (d.break_type.toLowerCase().includes('smoke')) {
            smoke = { count: d.count, duration: d.total_duration };
        }
    }

    document.getElementById('eatingBreaks').textContent = eating.count;
    document.getElementById('eatingDuration').textContent = formatDuration(eating.duration) + ' total';
    document.getElementById('smokeBreaks').textContent = smoke.count;
    document.getElementById('smokeDuration').textContent = formatDuration(smoke.duration) + ' total';
}

function updateAgentTable(agents) {
    agentData = agents;
    renderAgentTable(agents);
}

function renderAgentTable(agents) {
    const tbody = document.getElementById('agentTable');

    if (agents.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="px-4 py-8 text-center text-gray-400">No agents active today</td></tr>';
        return;
    }

    tbody.innerHTML = agents.map(a => {
        return `
            <tr class="table-row">
                <td class="px-4 py-3">
                    <div class="flex items-center gap-2">
                        <div class="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center text-xs font-medium">
                            ${getInitials(a.full_name)}
                        </div>
                        <span class="font-medium text-gray-800">${a.full_name}</span>
                    </div>
                </td>
                <td class="px-4 py-3 text-center">
                    <div class="flex items-center justify-center gap-2">
                        <span class="status-dot status-available"></span>
                        <span class="text-sm text-gray-600">Available</span>
                    </div>
                </td>
                <td class="px-4 py-3 text-center">
                    <span class="font-medium">${a.total_breaks}</span>
                </td>
                <td class="px-4 py-3 text-center">
                    <span class="font-medium">${a.total_duration.toFixed(0)}m</span>
                </td>
                <td class="px-4 py-3 text-center">
                    <span class="font-medium">${a.avg_duration.toFixed(1)}m</span>
                </td>
            </tr>
        `;
    }).join('');
}

function filterAgents() {
    const search = document.getElementById('agentSearch').value.toLowerCase();
    const filtered = agentData.filter(a => a.full_name.toLowerCase().includes(search));
    renderAgentTable(filtered);
}

// ============================================
// CHARTS
// ============================================

function initCharts() {
    // Distribution Chart (Doughnut)
    const distCtx = document.getElementById('distributionChart').getContext('2d');
    distributionChart = new Chart(distCtx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: ['#f59e0b', '#22c55e', '#8b5cf6', '#ef4444'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { padding: 15, usePointStyle: true } }
            },
            cutout: '60%'
        }
    });

    // Trend Chart (Line)
    const trendCtx = document.getElementById('trendChart').getContext('2d');
    trendChart = new Chart(trendCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Total Breaks',
                data: [],
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 4,
                pointBackgroundColor: '#3b82f6'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
                x: { grid: { display: false } }
            }
        }
    });

    // Hourly Chart (Bar)
    const hourlyCtx = document.getElementById('hourlyChart').getContext('2d');
    hourlyChart = new Chart(hourlyCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Break Outs',
                data: [],
                backgroundColor: '#3b82f6',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
                x: { grid: { display: false } }
            }
        }
    });
}

function updateDistributionChart(distribution) {
    if (!distribution || distribution.length === 0) {
        distributionChart.data.labels = ['No data'];
        distributionChart.data.datasets[0].data = [1];
        distributionChart.data.datasets[0].backgroundColor = ['#e5e7eb'];
        distributionChart.update();
        return;
    }

    const labels = distribution.map(d => d.break_type.replace(/[^\w\s]/g, '').trim());
    const data = distribution.map(d => d.count);

    distributionChart.data.labels = labels;
    distributionChart.data.datasets[0].data = data;
    distributionChart.data.datasets[0].backgroundColor = ['#f59e0b', '#22c55e', '#8b5cf6', '#ef4444'];
    distributionChart.update();
}

function updateTrendChart(trend) {
    if (!trend || trend.length === 0) return;

    const labels = trend.map(t => {
        const d = new Date(t.date);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    const data = trend.map(t => t.total_breaks);

    trendChart.data.labels = labels;
    trendChart.data.datasets[0].data = data;
    trendChart.update();
}

function updateHourlyChart(hourly) {
    if (!hourly || hourly.length === 0) return;

    // Filter to working hours (6 AM - 10 PM)
    const filtered = hourly.filter(h => h.hour >= 6 && h.hour <= 22);
    const labels = filtered.map(h => h.hour_label);
    const data = filtered.map(h => h.break_outs);

    hourlyChart.data.labels = labels;
    hourlyChart.data.datasets[0].data = data;
    hourlyChart.update();
}

// ============================================
// UTILITIES
// ============================================

function formatDuration(minutes) {
    if (!minutes || minutes === 0) return '0m';
    if (minutes < 60) return `${Math.round(minutes)}m`;
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    return `${hours}h ${mins}m`;
}

function getInitials(name) {
    return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
}

function updateLastRefresh() {
    const now = new Date();
    document.getElementById('lastUpdate').innerHTML =
        `<i class="fas fa-sync-alt mr-1"></i> ${now.toLocaleTimeString()}`;
}

function updateConnectionStatus(connected) {
    const status = document.getElementById('connectionStatus');
    if (connected) {
        status.className = 'flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/20 text-green-300 text-sm';
        status.innerHTML = '<span class="status-dot status-available"></span> Connected';
    } else {
        status.className = 'flex items-center gap-2 px-3 py-1 rounded-full bg-red-500/20 text-red-300 text-sm';
        status.innerHTML = '<span class="status-dot" style="background:#ef4444"></span> Disconnected';
    }
}

// ============================================
// EXPORT FUNCTIONS
// ============================================

function exportCSV(days = 7) {
    const end = new Date().toISOString().split('T')[0];
    const start = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    window.open(`${API_BASE}/api/export/csv?start=${start}&end=${end}`, '_blank');
}

function showExportModal() {
    const modal = document.createElement('div');
    modal.id = 'exportModal';
    modal.className = 'fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50';
    modal.innerHTML = `
        <div class="bg-white rounded-xl shadow-2xl max-w-sm w-full mx-4 overflow-hidden">
            <div class="bg-indigo-500 px-4 py-3 flex items-center justify-between">
                <h3 class="font-semibold text-white"><i class="fas fa-download mr-2"></i>Export Data</h3>
                <button onclick="closeExportModal()" class="text-white/80 hover:text-white"><i class="fas fa-times"></i></button>
            </div>
            <div class="p-4 space-y-3">
                <button onclick="exportCSV(7); closeExportModal();" class="w-full py-2 px-4 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition">
                    <i class="fas fa-file-csv mr-2"></i>Export CSV (Last 7 Days)
                </button>
                <button onclick="exportCSV(30); closeExportModal();" class="w-full py-2 px-4 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition">
                    <i class="fas fa-file-csv mr-2"></i>Export CSV (Last 30 Days)
                </button>
                <button onclick="exportCSV(90); closeExportModal();" class="w-full py-2 px-4 bg-green-500 text-white rounded-lg hover:bg-green-600 transition">
                    <i class="fas fa-file-csv mr-2"></i>Export CSV (Last 90 Days)
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    modal.onclick = (e) => { if (e.target === modal) closeExportModal(); };
}

function closeExportModal() {
    const modal = document.getElementById('exportModal');
    if (modal) modal.remove();
}

// Keyboard shortcut to close modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeExportModal();
});
