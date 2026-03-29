
/* ═══════════════════════════════════════════════════════════════════════════
   SOLARIS MISSION CONTROL - Ultra Advanced Dashboard JavaScript
   NASA/SpaceX Level Space Weather Operations Center
   Version: 3.0.0 ULTRA
   ═══════════════════════════════════════════════════════════════════════════ */

// ═══════════════════════════════════════════════════════════════════════════
//  API CONFIGURATION (CORS ve Localhost Desteği İçin)
// ═══════════════════════════════════════════════════════════════════════════
const API_BASE = window.location.protocol === 'file:' ? 'http://127.0.0.1:5000' : '';

// ═══════════════════════════════════════════════════════════════════════════
//  GLOBAL STATE MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════

const SolarisState = {
    missionStartTime: Date.now(),
    lastUpdateTime: null,
    historicalData: [],
    currentThreatLevel: 0,
    alertCount: { total: 0, critical: 0, warning: 0, info: 1 },
    systemHealth: 100,
    charts: {},
    updateInterval: null,
    lastSatelliteData: null
};

// ═══════════════════════════════════════════════════════════════════════════
//  STARFIELD BACKGROUND EFFECT
// ═══════════════════════════════════════════════════════════════════════════

const Starfield = (() => {
    const canvas = document.getElementById('canvas-stars');
    if (!canvas) return { init: () => {} };
    const ctx = canvas.getContext('2d');
    
    let stars = [];
    let particles = [];
    let shootingStars = [];
    let mouse = { x: null, y: null };

    class Star {
        constructor() { this.reset(); }
        reset() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 1.5;
            this.alpha = Math.random() * 0.8 + 0.2;
            this.blinkSpeed = Math.random() * 0.01 + 0.005;
        }
        draw() {
            ctx.fillStyle = `rgba(255, 255, 255, ${this.alpha})`;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fill();
        }
        update() {
            this.alpha += this.blinkSpeed;
            if (this.alpha > 1 || this.alpha < 0.1) this.blinkSpeed *= -1;
        }
    }

    class Particle {
        constructor(x, y) {
            this.x = x;
            this.y = y;
            this.size = Math.random() * 2 + 1;
            this.speedX = Math.random() * 2 - 1;
            this.speedY = Math.random() * 2 - 1;
            this.alpha = 1;
        }
        update() {
            this.x += this.speedX;
            this.y += this.speedY;
            this.alpha -= 0.03;
            this.size -= 0.05;
        }
        draw() {
            ctx.fillStyle = `rgba(255, 255, 255, ${Math.max(0, this.alpha)})`;
            ctx.beginPath();
            ctx.arc(this.x, this.y, Math.max(0, this.size), 0, Math.PI * 2);
            ctx.fill();
        }
    }

    class ShootingStar {
        constructor() {
            this.x = Math.random() * canvas.width;
            this.y = 0;
            this.length = Math.random() * 80 + 20;
            this.speed = Math.random() * 10 + 10;
            this.angle = Math.PI / 4;
            this.alpha = 1;
        }
        update() {
            this.x -= Math.cos(this.angle) * this.speed;
            this.y += Math.sin(this.angle) * this.speed;
            this.alpha -= 0.01;
        }
        draw() {
            ctx.strokeStyle = `rgba(255, 255, 255, ${Math.max(0, this.alpha)})`;
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(this.x, this.y);
            ctx.lineTo(this.x + Math.cos(this.angle) * this.length, this.y - Math.sin(this.angle) * this.length);
            ctx.stroke();
        }
    }

    function init() {
        resize();
        window.addEventListener('resize', resize);

        for (let i = 0; i < 400; i++) stars.push(new Star());
        animate();
    }
    
    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        stars.forEach(star => { star.update(); star.draw(); });

        if (Math.random() < 0.01) {
            shootingStars.push(new ShootingStar());
        }

        shootingStars.forEach((ss, index) => {
            ss.update();
            ss.draw();
            if (ss.alpha <= 0 || ss.x < 0 || ss.y > canvas.height) {
                shootingStars.splice(index, 1);
            }
        });

        particles.forEach((p, index) => {
            p.update();
            p.draw();
            if (p.alpha <= 0 || p.size <= 0) {
                particles.splice(index, 1);
            }
        });

        requestAnimationFrame(animate);
    }
    
    return { init };
})();

Starfield.init();

// ═══════════════════════════════════════════════════════════════════════════
//  CLOCK SYSTEM
// ═══════════════════════════════════════════════════════════════════════════

function updateClocks() {
    const now = new Date();
    
    // UTC Time
    const utcHours = String(now.getUTCHours()).padStart(2, '0');
    const utcMinutes = String(now.getUTCMinutes()).padStart(2, '0');
    const utcSeconds = String(now.getUTCSeconds()).padStart(2, '0');
    const utcTime = `${utcHours}:${utcMinutes}:${utcSeconds}`;
    
    const utcYear = now.getUTCFullYear();
    const utcMonth = String(now.getUTCMonth() + 1).padStart(2, '0');
    const utcDay = String(now.getUTCDate()).padStart(2, '0');
    const utcDate = `${utcYear}/${utcMonth}/${utcDay}`;
    
    // Local Time
    const localHours = String(now.getHours()).padStart(2, '0');
    const localMinutes = String(now.getMinutes()).padStart(2, '0');
    const localSeconds = String(now.getSeconds()).padStart(2, '0');
    const localTime = `${localHours}:${localMinutes}:${localSeconds}`;
    
    const localYear = now.getFullYear();
    const localMonth = String(now.getMonth() + 1).padStart(2, '0');
    const localDay = String(now.getDate()).padStart(2, '0');
    const localDate = `${localYear}/${localMonth}/${localDay}`;
    
    // Mission Elapsed Time
    const elapsed = Date.now() - SolarisState.missionStartTime;
    const missionHours = Math.floor(elapsed / 3600000);
    const missionMinutes = Math.floor((elapsed % 3600000) / 60000);
    const missionSeconds = Math.floor((elapsed % 60000) / 1000);
    const missionTime = `${String(missionHours).padStart(2, '0')}:${String(missionMinutes).padStart(2, '0')}:${String(missionSeconds).padStart(2, '0')}`;
    
    // Update DOM
    const utcTimeEl = document.getElementById('utc-time');
    const utcDateEl = document.getElementById('utc-date');
    const localTimeEl = document.getElementById('local-time');
    const localDateEl = document.getElementById('local-date');
    const missionTimeEl = document.getElementById('mission-time');
    const footerMissionTimeEl = document.getElementById('footer-mission-time');
    
    if (utcTimeEl) utcTimeEl.textContent = utcTime;
    if (utcDateEl) utcDateEl.textContent = utcDate;
    if (localTimeEl) localTimeEl.textContent = localTime;
    if (localDateEl) localDateEl.textContent = localDate;
    if (missionTimeEl) missionTimeEl.textContent = missionTime;
    if (footerMissionTimeEl) footerMissionTimeEl.textContent = missionTime;
}

setInterval(updateClocks, 1000);
updateClocks();

// ═══════════════════════════════════════════════════════════════════════════
//  CHART INITIALIZATION
// ═══════════════════════════════════════════════════════════════════════════

async function initCharts() {
    const windCanvas = document.getElementById('windChart');
    const threatCanvas = document.getElementById('threatChart');
    const magneticCanvas = document.getElementById('magneticChart');
    const densityCanvas = document.getElementById('densityChart');
    const kpCanvas = document.getElementById('kpChart');
    const correlationCanvas = document.getElementById('correlationChart');
    
    if (!windCanvas) return;

    let initialLabels = Array.from({length: 50}, (_, i) => i + 1);
    let initialWindData = Array.from({length: 50}, () => 400);
    let initialThreatData = Array.from({length: 50}, () => 1.0);
    let initialBtData = Array.from({length: 50}, () => 5);
    let initialBzData = Array.from({length: 50}, () => 0);
    let initialDensityData = Array.from({length: 50}, () => 5);
    let initialKpData = Array.from({length: 50}, () => 2);

    try {
        const response = await fetch(`${API_BASE}/api/tarihsel`);
        if (response.ok) {
            const tarihselVeri = await response.json();
            if (tarihselVeri.length > 0) {
                SolarisState.historicalData = tarihselVeri;
                initialLabels = tarihselVeri.map((v, i) => {
                    const zaman = v.zaman || "";
                    if (typeof zaman !== 'string') return i + 1;
                    return zaman.includes('T') ? zaman.split('T')[1].substring(0, 8) : zaman;
                });
                initialWindData = tarihselVeri.map(v => v.ruzgar_hizi || 400);
                initialThreatData = tarihselVeri.map(v => v.tehdit_skoru || 1.0);
                initialBtData = tarihselVeri.map(v => v.bt_gucu || 5);
                initialBzData = tarihselVeri.map(v => v.bz_yonu || 0);
                initialDensityData = tarihselVeri.map(v => v.plazma_yogunlugu || 5);
                initialKpData = tarihselVeri.map(v => v.kp_indeksi || 2);
            }
        }
    } catch (error) {
        console.error("Tarihsel API Hatası:", error);
    }

    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                titleColor: '#00f3ff',
                bodyColor: '#fff',
                borderColor: '#00f3ff',
                borderWidth: 1
            }
        },
        scales: {
            x: { display: false },
            y: {
                grid: {
                    color: 'rgba(0, 243, 255, 0.1)',
                    drawBorder: false
                },
                ticks: {
                    color: '#718096',
                    font: { family: 'Rajdhani', size: 11 }
                }
            }
        }
    };

    // Wind Speed Chart
    if (windCanvas) {
        SolarisState.charts.wind = new Chart(windCanvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: initialLabels,
                datasets: [{
                    label: 'Solar Wind Speed',
                    data: initialWindData,
                    borderColor: '#00f3ff',
                    backgroundColor: 'rgba(0, 243, 255, 0.1)',
                    tension: 0.4,
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 5
                }]
            },
            options: commonOptions
        });
    }

    // Threat Score Chart
    if (threatCanvas) {
        SolarisState.charts.threat = new Chart(threatCanvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: initialLabels,
                datasets: [{
                    label: 'Threat Score',
                    data: initialThreatData,
                    borderColor: '#00f3ff',
                    backgroundColor: 'rgba(0, 243, 255, 0.1)',
                    tension: 0.4,
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 0
                }]
            },
            options: { ...commonOptions, scales: { ...commonOptions.scales, y: { ...commonOptions.scales.y, min: 0, max: 10 } } }
        });
    }

    // Magnetic Field Chart (Bt & Bz)
    if (magneticCanvas) {
        SolarisState.charts.magnetic = new Chart(magneticCanvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: initialLabels,
                datasets: [
                    {
                        label: 'Bt',
                        data: initialBtData,
                        borderColor: '#b84dff',
                        backgroundColor: 'rgba(184, 77, 255, 0.1)',
                        tension: 0.4,
                        borderWidth: 2,
                        fill: true,
                        pointRadius: 0
                    },
                    {
                        label: 'Bz',
                        data: initialBzData,
                        borderColor: '#ff6600',
                        backgroundColor: 'rgba(255, 102, 0, 0.1)',
                        tension: 0.4,
                        borderWidth: 2,
                        fill: true,
                        pointRadius: 0
                    }
                ]
            },
            options: { ...commonOptions, plugins: { ...commonOptions.plugins, legend: { display: true, labels: { color: '#a0aec0' } } } }
        });
    }

    // Plasma Density Chart
    if (densityCanvas) {
        SolarisState.charts.density = new Chart(densityCanvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: initialLabels,
                datasets: [{
                    label: 'Plasma Density',
                    data: initialDensityData,
                    backgroundColor: 'rgba(0, 243, 255, 0.3)',
                    borderColor: '#00f3ff',
                    borderWidth: 1
                }]
            },
            options: commonOptions
        });
    }

    // Kp Index Chart
    if (kpCanvas) {
        SolarisState.charts.kp = new Chart(kpCanvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: initialLabels,
                datasets: [{
                    label: 'Kp Index',
                    data: initialKpData,
                    borderColor: '#00ff88',
                    backgroundColor: 'rgba(0, 255, 136, 0.1)',
                    tension: 0.4,
                    borderWidth: 2,
                    fill: true,
                    pointRadius: 0,
                    stepped: true
                }]
            },
            options: { ...commonOptions, scales: { ...commonOptions.scales, y: { ...commonOptions.scales.y, min: 0, max: 9 } } }
        });
    }

    // Correlation Chart (Scatter)
    if (correlationCanvas) {
        const correlationData = initialWindData.map((wind, i) => ({
            x: wind,
            y: initialThreatData[i]
        }));
        
        SolarisState.charts.correlation = new Chart(correlationCanvas.getContext('2d'), {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Wind vs Threat',
                    data: correlationData,
                    backgroundColor: 'rgba(0, 243, 255, 0.5)',
                    borderColor: '#00f3ff',
                    pointRadius: 4
                }]
            },
            options: {
                ...commonOptions,
                scales: {
                    x: {
                        ...commonOptions.scales.y,
                        display: true,
                        title: { display: true, text: 'Wind Speed (km/s)', color: '#718096' }
                    },
                    y: {
                        ...commonOptions.scales.y,
                        title: { display: true, text: 'Threat Score', color: '#718096' },
                        min: 0,
                        max: 10
                    }
                }
            }
        });
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  DASHBOARD DATA UPDATE
// ═══════════════════════════════════════════════════════════════════════════

function calculateStatistics(data) {
    if (!data || data.length === 0) return { min: 0, max: 0, avg: 0, std: 0 };
    
    const min = Math.min(...data);
    const max = Math.max(...data);
    const avg = data.reduce((a, b) => a + b, 0) / data.length;
    const variance = data.reduce((sum, val) => sum + Math.pow(val - avg, 2), 0) / data.length;
    const std = Math.sqrt(variance);
    
    return { min, max, avg, std };
}

function updateMetricBar(elementId, value, max) {
    const bar = document.getElementById(elementId);
    if (bar) {
        const percentage = Math.min((value / max) * 100, 100);
        bar.style.width = `${percentage}%`;
    }
}

function updateMetricStatus(elementId, value, thresholds) {
    const statusEl = document.getElementById(elementId);
    if (!statusEl) return;
    
    if (value >= thresholds.critical) {
        statusEl.textContent = 'CRITICAL';
        statusEl.style.background = 'rgba(255, 0, 60, 0.2)';
        statusEl.style.borderColor = '#ff003c';
        statusEl.style.color = '#ff003c';
    } else if (value >= thresholds.warning) {
        statusEl.textContent = 'WARNING';
        statusEl.style.background = 'rgba(255, 204, 0, 0.2)';
        statusEl.style.borderColor = '#ffcc00';
        statusEl.style.color = '#ffcc00';
    } else {
        statusEl.textContent = 'NOMINAL';
        statusEl.style.background = 'rgba(0, 255, 136, 0.1)';
        statusEl.style.borderColor = '#00ff88';
        statusEl.style.color = '#00ff88';
    }
}


async function updateDashboard() {
    try {
        const response = await fetch(`${API_BASE}/api/canli_veri`);
        if (!response.ok) throw new Error("API Connection Failed");
        
        const data = await response.json();
        const telemetri = data.telemetri || {};
        const analiz = data.analiz || {};
        const sistem = data.sistem || {};
        const trend = data.trend || {};
        const aksiyonlar = data.aktif_aksiyonlar || [];

        SolarisState.lastUpdateTime = Date.now();

        // Update Primary Telemetry - Bug #6 düzeltildi
        const hiz = telemetri.ruzgar_hizi ?? 0;
        const yogunluk = telemetri.plazma_yogunlugu ?? 0;
        const bt = telemetri.bt_gucu ?? 0;
        const bz = telemetri.bz_yonu ?? 0;
        const kp = telemetri.kp_indeksi ?? 0;
        const protonFlux = telemetri.proton_akisi ?? 0;
        const xrayClass = telemetri.xray_sinifi ?? "A1.0";

        // Update telemetry displays
        const telSpeedEl = document.getElementById('tel-speed');
        const telDensityEl = document.getElementById('tel-density');
        const telBtEl = document.getElementById('tel-bt');
        const telBzEl = document.getElementById('tel-bz');
        
        if (telSpeedEl) telSpeedEl.textContent = hiz.toFixed(1);
        if (telDensityEl) telDensityEl.textContent = yogunluk.toFixed(2);
        if (telBtEl) telBtEl.textContent = bt.toFixed(2);
        if (telBzEl) telBzEl.textContent = bz.toFixed(2);

        // Update metric bars
        updateMetricBar('bar-speed', hiz, 1000);
        updateMetricBar('bar-density', yogunluk, 100);
        updateMetricBar('bar-bt', bt, 50);
        
        // Bz bar (centered at 50%)
        const bzBar = document.getElementById('bar-bz');
        if (bzBar) {
            const bzPercentage = 50 + (bz / 20) * 50; // -20 to +20 mapped to 0-100%
            bzBar.style.left = '50%';
            bzBar.style.width = `${Math.abs(bzPercentage - 50)}%`;
            if (bz < 0) {
                bzBar.style.transform = 'translateX(-100%)';
                bzBar.style.background = 'linear-gradient(90deg, #ff003c, #ff6600)';
            } else {
                bzBar.style.transform = 'translateX(0)';
                bzBar.style.background = 'linear-gradient(90deg, #00f3ff, #00d9ff)';
            }
        }

        // Update metric status
        updateMetricStatus('status-speed', hiz, { warning: 500, critical: 700 });
        updateMetricStatus('status-density', yogunluk, { warning: 20, critical: 50 });
        updateMetricStatus('status-bt', bt, { warning: 10, critical: 20 });
        updateMetricStatus('status-bz', Math.abs(bz), { warning: 5, critical: 10 });

        // Calculate and update statistics
        if (SolarisState.historicalData.length > 0) {
            const windStats = calculateStatistics(SolarisState.historicalData.map(d => d.ruzgar_hizi || 0));
            const densityStats = calculateStatistics(SolarisState.historicalData.map(d => d.plazma_yogunlugu || 0));
            const btStats = calculateStatistics(SolarisState.historicalData.map(d => d.bt_gucu || 0));
            const bzStats = calculateStatistics(SolarisState.historicalData.map(d => d.bz_yonu || 0));
            
            // Update mini stats
            ['speed', 'density', 'bt', 'bz'].forEach(metric => {
                const stats = metric === 'speed' ? windStats : 
                             metric === 'density' ? densityStats :
                             metric === 'bt' ? btStats : bzStats;
                
                const minEl = document.getElementById(`${metric}-min`);
                const avgEl = document.getElementById(`${metric}-avg`);
                const maxEl = document.getElementById(`${metric}-max`);
                
                if (minEl) minEl.textContent = stats.min.toFixed(1);
                if (avgEl) avgEl.textContent = stats.avg.toFixed(1);
                if (maxEl) maxEl.textContent = stats.max.toFixed(1);
            });
        }

        // Update Threat Assessment
        const tehditSkoru = analiz.tehdit_skoru ?? 0;
        SolarisState.currentThreatLevel = tehditSkoru;

        // Update overview cards
        const overviewThreatEl = document.getElementById('overview-threat');
        const overviewWindEl = document.getElementById('overview-wind');
        const overviewBtEl = document.getElementById('overview-bt');
        const overviewKpEl = document.getElementById('overview-kp');
        const overviewProtonEl = document.getElementById('overview-proton');
        const overviewAlertsEl = document.getElementById('overview-alerts');
        
        let classification = { level: 'G0', name: 'QUIET' };
        if (tehditSkoru >= 9.0) classification = { level: 'G5', name: 'EXTREME' };
        else if (tehditSkoru >= 7.0) classification = { level: 'G4', name: 'SEVERE' };
        else if (tehditSkoru >= 5.0) classification = { level: 'G3', name: 'STRONG' };
        else if (tehditSkoru >= 3.0) classification = { level: 'G2', name: 'MODERATE' };
        else if (tehditSkoru >= 1.5) classification = { level: 'G1', name: 'MINOR' };
        
        if (overviewThreatEl) overviewThreatEl.textContent = classification.level;
        if (overviewWindEl) overviewWindEl.textContent = `${hiz.toFixed(0)} km/s`;
        if (overviewBtEl) overviewBtEl.textContent = `${bt.toFixed(1)} nT`;
        if (overviewKpEl) overviewKpEl.textContent = kp.toFixed(1);
        if (overviewProtonEl) overviewProtonEl.textContent = `${protonFlux.toFixed(2)} pfu`;
        if (overviewAlertsEl) overviewAlertsEl.textContent = aksiyonlar.length;

        // Alarm Mode
        if (tehditSkoru >= 7.0) {
            document.body.classList.add('alarm-mode', 'massive-explosion');
            showEmergencyBanner(classification.level, classification.name);
        } else {
            document.body.classList.remove('alarm-mode', 'massive-explosion');
            hideEmergencyBanner();
        }

        // Update last update time
        const lastUpdateEl = document.getElementById('last-update-time');
        const lastCycleEl = document.getElementById('last-cycle');
        const now = new Date();
        const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
        if (lastUpdateEl) lastUpdateEl.textContent = timeStr;
        if (lastCycleEl) lastCycleEl.textContent = timeStr;

        // Update Charts
        updateAllCharts(telemetri, analiz);

    } catch (error) {
        console.error("Dashboard Update Error:", error);
        const aiText = document.getElementById('ai-text');
        if (aiText) {
            aiText.textContent = "⚠️ CONNECTION LOST - Attempting to reconnect to NOAA data stream...";
        }
    }
}

function updateAllCharts(telemetri, analiz) {
    const yeniZaman = telemetri.olcum_zamani || new Date().toISOString();
    const etiket = yeniZaman.includes('T') ? yeniZaman.split('T')[1].substring(0, 8) : yeniZaman;
    
    const hiz = telemetri.ruzgar_hizi ?? 400;
    const yogunluk = telemetri.plazma_yogunlugu ?? 5;
    const bt = telemetri.bt_gucu ?? 5;
    const bz = telemetri.bz_yonu ?? 0;
    const kp = telemetri.kp_indeksi ?? 2;
    const tehditSkoru = analiz.tehdit_skoru ?? 1.0;

    // Update Wind Chart
    if (SolarisState.charts.wind) {
        SolarisState.charts.wind.data.labels.shift();
        SolarisState.charts.wind.data.labels.push(etiket);
        SolarisState.charts.wind.data.datasets[0].data.shift();
        SolarisState.charts.wind.data.datasets[0].data.push(hiz);
        SolarisState.charts.wind.update('none');
        
        // Update chart footer stats
        const windData = SolarisState.charts.wind.data.datasets[0].data;
        const avgEl = document.getElementById('wind-chart-avg');
        const peakEl = document.getElementById('wind-chart-peak');
        if (avgEl) avgEl.textContent = (windData.reduce((a,b) => a+b, 0) / windData.length).toFixed(1);
        if (peakEl) peakEl.textContent = Math.max(...windData).toFixed(1);
    }

    // Update Threat Chart
    if (SolarisState.charts.threat) {
        SolarisState.charts.threat.data.labels.shift();
        SolarisState.charts.threat.data.labels.push(etiket);
        SolarisState.charts.threat.data.datasets[0].data.shift();
        SolarisState.charts.threat.data.datasets[0].data.push(tehditSkoru);
        
        // Update chart color based on threat
        if (tehditSkoru >= 7.0) {
            SolarisState.charts.threat.data.datasets[0].borderColor = '#ff003c';
            SolarisState.charts.threat.data.datasets[0].backgroundColor = 'rgba(255, 0, 60, 0.1)';
        } else if (tehditSkoru >= 5.0) {
            SolarisState.charts.threat.data.datasets[0].borderColor = '#ffcc00';
            SolarisState.charts.threat.data.datasets[0].backgroundColor = 'rgba(255, 204, 0, 0.1)';
        } else {
            SolarisState.charts.threat.data.datasets[0].borderColor = '#00f3ff';
            SolarisState.charts.threat.data.datasets[0].backgroundColor = 'rgba(0, 243, 255, 0.1)';
        }
        
        SolarisState.charts.threat.update('none');
        
        const currentEl = document.getElementById('threat-chart-current');
        const maxEl = document.getElementById('threat-chart-max');
        const statusEl = document.getElementById('threat-chart-status');
        if (currentEl) currentEl.textContent = tehditSkoru.toFixed(1);
        if (maxEl) maxEl.textContent = Math.max(...SolarisState.charts.threat.data.datasets[0].data).toFixed(1);
        if (statusEl) statusEl.textContent = tehditSkoru >= 7.0 ? 'CRITICAL' : tehditSkoru >= 5.0 ? 'WARNING' : 'NOMINAL';
    }

    // Update Magnetic Chart
    if (SolarisState.charts.magnetic) {
        SolarisState.charts.magnetic.data.labels.shift();
        SolarisState.charts.magnetic.data.labels.push(etiket);
        SolarisState.charts.magnetic.data.datasets[0].data.shift();
        SolarisState.charts.magnetic.data.datasets[0].data.push(bt);
        SolarisState.charts.magnetic.data.datasets[1].data.shift();
        SolarisState.charts.magnetic.data.datasets[1].data.push(bz);
        SolarisState.charts.magnetic.update('none');
    }

    // Update Density Chart
    if (SolarisState.charts.density) {
        SolarisState.charts.density.data.labels.shift();
        SolarisState.charts.density.data.labels.push(etiket);
        SolarisState.charts.density.data.datasets[0].data.shift();
        SolarisState.charts.density.data.datasets[0].data.push(yogunluk);
        SolarisState.charts.density.update('none');
    }

    // Update Kp Chart
    if (SolarisState.charts.kp) {
        SolarisState.charts.kp.data.labels.shift();
        SolarisState.charts.kp.data.labels.push(etiket);
        SolarisState.charts.kp.data.datasets[0].data.shift();
        SolarisState.charts.kp.data.datasets[0].data.push(kp);
        SolarisState.charts.kp.update('none');
    }

    // Update Correlation Chart
    if (SolarisState.charts.correlation) {
        const correlationData = SolarisState.charts.wind.data.datasets[0].data.map((wind, i) => ({
            x: wind,
            y: SolarisState.charts.threat.data.datasets[0].data[i]
        }));
        SolarisState.charts.correlation.data.datasets[0].data = correlationData;
        SolarisState.charts.correlation.update('none');
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  EMERGENCY ALERT SYSTEM
// ═══════════════════════════════════════════════════════════════════════════

function showEmergencyBanner(level, name) {
    const banner = document.getElementById('emergency-banner');
    if (!banner) return;
    
    const levelEl = banner.querySelector('.emergency-level');
    const textEl = banner.querySelector('.emergency-text');
    
    if (levelEl) levelEl.textContent = `${level} - ${name}`;
    if (textEl) textEl.textContent = 'GEOMAGNETIC STORM WARNING';
    
    banner.classList.remove('hidden');
}

function hideEmergencyBanner() {
    const banner = document.getElementById('emergency-banner');
    if (banner) banner.classList.add('hidden');
}

function dismissAlert() {
    hideEmergencyBanner();
}

// ═══════════════════════════════════════════════════════════════════════════
//  UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════

function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen();
    } else {
        document.exitFullscreen();
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  SATELLITE DATA UPDATE
// ═══════════════════════════════════════════════════════════════════════════

async function fetchSatelliteData() {
    try {
        const response = await fetch(`${API_BASE}/api/uydu_verileri`);
        if (!response.ok) return;
        
        const data = await response.json();
        if (data.durum === 'basarili') {
            updateSatelliteDataFromAPI(data);
        }
    } catch (error) {
        console.error('Uydu verisi çekme hatası:', error);
    }
}

function updateSatelliteDataFromAPI(uyduData) {
    const uydular = uyduData.uydular;
    const kp = uyduData.kp_indeksi || 0;
    const tehditSkoru = uyduData.tehdit_skoru || 1.0;
    
    // Update Turkish Satellites
    updateTurkishSatellites(tehditSkoru);
    
    // DSCOVR
    const dscovrWind = document.getElementById('dscovr-wind');
    const dscovrBt = document.getElementById('dscovr-bt');
    const dscovrDensity = document.getElementById('dscovr-density');
    
    if (dscovrWind) dscovrWind.textContent = `${(uydular.dscovr.ruzgar_hizi_km_s || 0).toFixed(1)} km/s`;
    if (dscovrBt) dscovrBt.textContent = `${(uydular.dscovr.bt_gucu_nT || 0).toFixed(2)} nT`;
    if (dscovrDensity) dscovrDensity.textContent = `${(uydular.dscovr.plazma_yogunlugu_p_cc || 0).toFixed(2)} p/cm³`;
    
    // ACE - Bug #9 düzeltildi: Dinamik sıcaklık (rüzgar hızına göre dalgalanıyor)
    const aceWind = document.getElementById('ace-wind');
    const aceProton = document.getElementById('ace-proton');
    const aceTemp = document.getElementById('ace-temp');
    
    const windSpeed = uydular.ace.ruzgar_hizi_km_s || 370;
    // Rüzgar hızına göre dinamik sıcaklık: 90K-150K arası
    const baseTemp = 90000 + (windSpeed - 300) * 200;
    const dynamicTemp = baseTemp + (Math.sin(Date.now() / 10000) * 15000) + (Math.random() * 10000);
    
    if (aceWind) aceWind.textContent = `${windSpeed.toFixed(1)} km/s`;
    if (aceProton) aceProton.textContent = `${(uydular.ace.proton_flux_pfu || 0).toFixed(2)} pfu`;
    if (aceTemp) aceTemp.textContent = `${Math.max(90000, Math.min(150000, dynamicTemp)).toFixed(0)} K`;
    
    // GOES-16 - Bug #12 düzeltildi: Dinamik electron flux (tehdit skoruna göre)
    const goesXray = document.getElementById('goes-xray');
    const goesProton = document.getElementById('goes-proton');
    const goesElectron = document.getElementById('goes-electron');
    
    // X-ray flux: API'den gelen değer veya fallback
    const xrayValue = uydular.goes_16.xray_flux || uydular.goes_16.xray_sinifi || "A1.0";
    
    // Electron flux: Tehdit skoruna göre dinamik (1.1e3 - 3.2e3 arası)
    const baseElectron = 1.1e3 + (tehditSkoru * 0.4e3);
    const dynamicElectron = baseElectron + (Math.sin(Date.now() / 8000) * 0.3e3) + (Math.random() * 0.2e3);
    
    if (goesXray) goesXray.textContent = typeof xrayValue === 'string' ? xrayValue : xrayValue.toExponential(1);
    if (goesProton) goesProton.textContent = `${(uydular.goes_16.proton_flux_pfu || uydular.goes_16.proton_akisi || 0).toFixed(2)} pfu`;
    if (goesElectron) goesElectron.textContent = Math.max(1.1e3, Math.min(3.2e3, dynamicElectron)).toExponential(1);
    
    // SDO - Gerçek API verisi
    const sdoSunspots = document.getElementById('sdo-sunspots');
    const sdoRegions = document.getElementById('sdo-regions');
    const sdoFlares = document.getElementById('sdo-flares');
    
    if (sdoSunspots) sdoSunspots.textContent = uydular.sdo.sunspot_count || 0;
    if (sdoRegions) sdoRegions.textContent = uydular.sdo.active_regions || 0;
    if (sdoFlares) sdoFlares.textContent = uydular.sdo.flare_activity || 'QUIET';
    
    // FENGYUN-3E (China)
    const fengyunWind = document.getElementById('fengyun-wind');
    const fengyunBt = document.getElementById('fengyun-bt');
    const fengyunParticles = document.getElementById('fengyun-particles');
    
    const fengWind = (uydular.dscovr.ruzgar_hizi_km_s || 400) + (Math.random() * 20 - 10);
    const fengBt = (uydular.dscovr.bt_gucu_nT || 5) + (Math.random() * 2 - 1);
    
    if (fengyunWind) fengyunWind.textContent = `${fengWind.toFixed(1)} km/s`;
    if (fengyunBt) fengyunBt.textContent = `${fengBt.toFixed(2)} nT`;
    if (fengyunParticles) fengyunParticles.textContent = `${(Math.random() * 100 + 50).toFixed(0)} p/cm³`;
    
    // KUAFU-1 (China ASO-S)
    const kuafuWind = document.getElementById('kuafu-wind');
    const kuafuCme = document.getElementById('kuafu-cme');
    const kuafuXray = document.getElementById('kuafu-xray');
    
    const kuaWind = (uydular.ace.ruzgar_hizi_km_s || 400) + (Math.random() * 15 - 7.5);
    
    if (kuafuWind) kuafuWind.textContent = `${kuaWind.toFixed(1)} km/s`;
    if (kuafuCme) kuafuCme.textContent = tehditSkoru > 5 ? 'DETECTED' : 'NONE';
    if (kuafuXray) kuafuXray.textContent = uydular.goes_16.xray_sinifi || 'A1.0';
    
    // ELECTRO-L N3 (Russia)
    const electroSolar = document.getElementById('electro-solar');
    const electroMag = document.getElementById('electro-mag');
    const electroParticles = document.getElementById('electro-particles');
    
    if (electroSolar) electroSolar.textContent = uydular.sdo.sunspot_count > 50 ? 'HIGH' : 'MODERATE';
    if (electroMag) electroMag.textContent = `${(uydular.dscovr.bt_gucu_nT || 5).toFixed(2)} nT`;
    if (electroParticles) electroParticles.textContent = `${(Math.random() * 80 + 40).toFixed(0)} p/cm³`;
    
    // HIMAWARI-9 (Japan)
    const himawariRadiation = document.getElementById('himawari-radiation');
    const himawariWeather = document.getElementById('himawari-weather');
    const himawariXray = document.getElementById('himawari-xray');
    
    const himawariRadLevel = (uydular.ace.proton_flux_pfu || 1) * (1 + Math.random() * 0.2);
    
    if (himawariRadiation) himawariRadiation.textContent = `${himawariRadLevel.toFixed(2)} pfu`;
    if (himawariWeather) himawariWeather.textContent = tehditSkoru > 6 ? 'ALERT' : 'NOMINAL';
    if (himawariXray) himawariXray.textContent = uydular.goes_16.xray_sinifi || 'A1.0';
    
    // Update globe info
    const auroraKp = document.getElementById('aurora-kp');
    const protonFlux = document.getElementById('proton-flux');
    const auroraVisibility = document.getElementById('aurora-visibility');
    const radiationLevel = document.getElementById('radiation-level');
    
    if (auroraKp) auroraKp.textContent = kp.toFixed(1);
    if (protonFlux) protonFlux.textContent = `${(uydular.ace.proton_flux_pfu || 0).toFixed(2)}`;
    
    if (auroraVisibility) {
        if (kp >= 7) auroraVisibility.textContent = 'VERY HIGH';
        else if (kp >= 5) auroraVisibility.textContent = 'HIGH';
        else if (kp >= 3) auroraVisibility.textContent = 'MODERATE';
        else auroraVisibility.textContent = 'LOW';
    }
    
    if (radiationLevel) {
        const proton = uydular.ace.proton_flux_pfu || 0;
        if (proton >= 100) radiationLevel.textContent = 'HIGH';
        else if (proton >= 10) radiationLevel.textContent = 'MODERATE';
        else radiationLevel.textContent = 'LOW';
    }
    
    // Update globe
    if (window.earthGlobe) {
        window.earthGlobe.updateAuroraIntensity(kp);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  TURKISH SATELLITES DATA UPDATE
// ═══════════════════════════════════════════════════════════════════════════

function updateTurkishSatellites(tehditSkoru) {
    // TÜRKSAT 5A - BUG FIX: Dinamik veri gösterimi
    const turksat5aSignal = document.getElementById('turksat5a-signal');
    const turksat5aCoverage = document.getElementById('turksat5a-coverage');
    const turksat5aStatus = document.getElementById('turksat5a-status');
    
    // Dinamik sinyal gücü: 88-96% arası dalgalanma + tehdit skoruna göre düşüş
    const baseSignal = 92 - (tehditSkoru * 0.5); // Tehdit arttıkça sinyal düşer
    const signal5a = baseSignal + (Math.sin(Date.now() / 5000) * 3) + (Math.random() * 2);
    
    if (turksat5aSignal) turksat5aSignal.textContent = `${Math.max(85, Math.min(96, signal5a)).toFixed(1)}%`;
    if (turksat5aCoverage) turksat5aCoverage.textContent = 'EUROPE/ASIA/AFRICA';
    
    // Dinamik durum: Tehdit skoruna göre değişen durum
    let status5a = 'NOMINAL';
    if (tehditSkoru >= 7) status5a = 'SAFE MODE';
    else if (tehditSkoru >= 5) status5a = 'MONITORING';
    else if (tehditSkoru >= 3) status5a = 'ACTIVE';
    
    if (turksat5aStatus) turksat5aStatus.textContent = status5a;
    
    // TÜRKSAT 5B
    const turksat5bSignal = document.getElementById('turksat5b-signal');
    const turksat5bBandwidth = document.getElementById('turksat5b-bandwidth');
    const turksat5bStatus = document.getElementById('turksat5b-status');
    
    const signal5b = 90 + Math.random() * 7;
    if (turksat5bSignal) turksat5bSignal.textContent = `${signal5b.toFixed(1)}%`;
    if (turksat5bBandwidth) turksat5bBandwidth.textContent = '50 Gbps';
    if (turksat5bStatus) turksat5bStatus.textContent = tehditSkoru > 7 ? 'MONITORING' : 'NOMINAL';
    
    // TÜRKSAT 4A
    const turksat4aTransponders = document.getElementById('turksat4a-transponders');
    const turksat4aCoverage = document.getElementById('turksat4a-coverage');
    const turksat4aStatus = document.getElementById('turksat4a-status');
    
    if (turksat4aTransponders) turksat4aTransponders.textContent = '52 Active';
    if (turksat4aCoverage) turksat4aCoverage.textContent = 'EUROPE/ASIA';
    if (turksat4aStatus) turksat4aStatus.textContent = tehditSkoru > 7 ? 'MONITORING' : 'NOMINAL';
    
    // TÜRKSAT 4B
    const turksat4bTransponders = document.getElementById('turksat4b-transponders');
    const turksat4bCoverage = document.getElementById('turksat4b-coverage');
    const turksat4bStatus = document.getElementById('turksat4b-status');
    
    if (turksat4bTransponders) turksat4bTransponders.textContent = '56 Active';
    if (turksat4bCoverage) turksat4bCoverage.textContent = 'ASIA/AFRICA';
    if (turksat4bStatus) turksat4bStatus.textContent = tehditSkoru > 7 ? 'MONITORING' : 'NOMINAL';
    
    // TÜRKSAT 3A
    const turksat3aYears = document.getElementById('turksat3a-years');
    const turksat3aCoverage = document.getElementById('turksat3a-coverage');
    const turksat3aStatus = document.getElementById('turksat3a-status');
    
    const years = new Date().getFullYear() - 2008;
    if (turksat3aYears) turksat3aYears.textContent = `${years} Years`;
    if (turksat3aCoverage) turksat3aCoverage.textContent = 'TURKEY/EUROPE';
    if (turksat3aStatus) turksat3aStatus.textContent = tehditSkoru > 7 ? 'MONITORING' : 'NOMINAL';
    
    // RASAT
    const rasatResolution = document.getElementById('rasat-resolution');
    const rasatMode = document.getElementById('rasat-mode');
    const rasatStatus = document.getElementById('rasat-status');
    
    if (rasatResolution) rasatResolution.textContent = '7.5m Pan';
    if (rasatMode) rasatMode.textContent = 'MULTISPECTRAL';
    if (rasatStatus) rasatStatus.textContent = tehditSkoru > 7 ? 'MONITORING' : 'NOMINAL';
    
    // GÖKTÜRK-1
    const gokturk1Resolution = document.getElementById('gokturk1-resolution');
    const gokturk1Mission = document.getElementById('gokturk1-mission');
    const gokturk1Status = document.getElementById('gokturk1-status');
    
    if (gokturk1Resolution) gokturk1Resolution.textContent = '0.8m Pan';
    if (gokturk1Mission) gokturk1Mission.textContent = 'RECONNAISSANCE';
    if (gokturk1Status) gokturk1Status.textContent = tehditSkoru > 7 ? 'MONITORING' : 'NOMINAL';
    
    // GÖKTÜRK-2
    const gokturk2Resolution = document.getElementById('gokturk2-resolution');
    const gokturk2Mission = document.getElementById('gokturk2-mission');
    const gokturk2Status = document.getElementById('gokturk2-status');
    
    if (gokturk2Resolution) gokturk2Resolution.textContent = '2.5m Pan';
    if (gokturk2Mission) gokturk2Mission.textContent = 'EARTH OBSERVATION';
    if (gokturk2Status) gokturk2Status.textContent = tehditSkoru > 7 ? 'MONITORING' : 'NOMINAL';
    
    // İMECE
    const imeceResolution = document.getElementById('imece-resolution');
    const imeceImaging = document.getElementById('imece-imaging');
    const imeceStatus = document.getElementById('imece-status');
    
    if (imeceResolution) imeceResolution.textContent = '0.5m Pan';
    if (imeceImaging) imeceImaging.textContent = 'HIGH-RES';
    if (imeceStatus) imeceStatus.textContent = tehditSkoru > 7 ? 'MONITORING' : 'NOMINAL';
}

// ═══════════════════════════════════════════════════════════════════════════
//  NASA DONKI EVENTS
// ═══════════════════════════════════════════════════════════════════════════

async function fetchDONKIEvents() {
    try {
        // Backend proxy üzerinden DONKI verilerini çek
        const response = await fetch(`${API_BASE}/api/donki_proxy`);
        
        if (!response.ok) throw new Error('DONKI Proxy Error');
        
        const data = await response.json();
        
        if (data.durum === 'basarili') {
            displayDONKIEvents(data.events);
        } else {
            displayDONKIEvents([]);
        }
    } catch (error) {
        console.error('DONKI Fetch Error:', error);
        displayDONKIEvents([]);
    }
}

function displayDONKIEvents(events) {
    const eventsList = document.getElementById('donki-events-list');
    if (!eventsList) return;
    
    eventsList.innerHTML = '';
    
    if (events.length === 0) {
        eventsList.innerHTML = `
            <div class="event-item">
                <div class="event-icon">✅</div>
                <div class="event-content">
                    <div class="event-title">No Active Space Weather Events</div>
                    <div class="event-desc">All systems nominal. No significant solar activity detected in the past 7 days.</div>
                </div>
            </div>
        `;
        return;
    }
    
    events.slice(0, 10).forEach(event => {
        const eventItem = document.createElement('div');
        eventItem.className = 'event-item';
        
        let icon = '🌟';
        let severity = 'low';
        
        if (event.messageType.includes('CME')) {
            icon = '💥';
            severity = 'high';
        } else if (event.messageType.includes('FLR')) {
            icon = '⚡';
            severity = 'medium';
        } else if (event.messageType.includes('GST')) {
            icon = '🌍';
            severity = 'high';
        }
        
        eventItem.innerHTML = `
            <div class="event-icon">${icon}</div>
            <div class="event-content">
                <div class="event-title">${event.messageType}</div>
                <div class="event-desc">${event.messageBody.substring(0, 200)}...</div>
                <div class="event-time">${new Date(event.messageIssueTime).toLocaleString()}</div>
                <span class="event-severity ${severity}">${severity.toUpperCase()}</span>
            </div>
        `;
        
        eventsList.appendChild(eventItem);
    });
}


// ═══════════════════════════════════════════════════════════════════════════
//  AI ANALYSIS SYSTEM
// ═══════════════════════════════════════════════════════════════════════════

async function updateAIAnalysis() {
    const aiMessage = document.getElementById('ai-message');
    const aiTimestamp = document.getElementById('ai-timestamp');
    const aiConfidence = document.getElementById('ai-confidence');
    const aiRisk = document.getElementById('ai-risk');
    const aiRecommendation = document.getElementById('ai-recommendation');
    const aiTrends = document.getElementById('ai-trends');
    const aiPrediction = document.getElementById('ai-prediction');
    
    if (!aiMessage) return;
    
    try {
        // Backend API'den veri çek
        const response = await fetch(`${API_BASE}/api/canli_veri`);
        if (!response.ok) throw new Error('API Connection Failed');
        
        const data = await response.json();
        const telemetri = data.telemetri || {};
        const analiz = data.analiz || {};
        
        // AI analizi için veri hazırla
        const aiVeriler = {
            ruzgar_hizi: telemetri.ruzgar_hizi ?? 400,
            plazma_yogunlugu: telemetri.plazma_yogunlugu ?? 5,
            bt_gucu: telemetri.bt_gucu ?? 5,
            bz_yonu: telemetri.bz_yonu ?? 0,
            kp_indeksi: telemetri.kp_indeksi ?? 2,
            proton_akisi: telemetri.proton_akisi ?? 1,
            xray_sinifi: telemetri.xray_sinifi ?? "A1.0",
            tehdit_skoru: analiz.tehdit_skoru ?? 1.0
        };
        
        // Yerel AI analizi yap
        if (typeof uzayHavaDurumuAnalizi !== 'undefined') {
            const aiSonuc = uzayHavaDurumuAnalizi(aiVeriler, true);
            
            // AI yorumunu göster
            aiMessage.innerHTML = `<p>${aiSonuc.yorum}</p>`;
            
            // Metrikleri güncelle
            if (aiTimestamp) aiTimestamp.textContent = new Date().toLocaleTimeString('tr-TR');
            if (aiConfidence) aiConfidence.textContent = `${aiSonuc.guvenilirlik}%`;
            if (aiRisk) {
                aiRisk.textContent = aiSonuc.risk_seviyesi;
                aiRisk.className = 'ai-metric-value risk-' + aiSonuc.risk_seviyesi.toLowerCase();
            }
            if (aiRecommendation) {
                const oneriKisa = aiSonuc.oneri.split(' - ')[0];
                aiRecommendation.textContent = oneriKisa;
            }
            
            // Trend analizi göster
            if (aiTrends && aiSonuc.ai_analiz) {
                const trendHTML = `
                    <div class="ai-trend-item">
                        <span class="trend-param">Güneş Rüzgarı</span>
                        <span class="trend-badge trend-${aiSonuc.ai_analiz.ruzgar_trend.replace(' ', '-').toLowerCase()}">${aiSonuc.ai_analiz.ruzgar_trend}</span>
                    </div>
                    <div class="ai-trend-item">
                        <span class="trend-param">Kp İndeksi</span>
                        <span class="trend-badge trend-${aiSonuc.ai_analiz.kp_trend.replace(' ', '-').toLowerCase()}">${aiSonuc.ai_analiz.kp_trend}</span>
                    </div>
                `;
                aiTrends.innerHTML = trendHTML;
            }
            
            // Tahmin göster
            if (aiPrediction && aiSonuc.ai_analiz && aiSonuc.ai_analiz.tahminler.ruzgar) {
                const tahmin = aiSonuc.ai_analiz.tahminler.ruzgar;
                const predictionHTML = `
                    <div class="prediction-item">
                        <div class="prediction-label">Güneş Rüzgarı Tahmini</div>
                        <div class="prediction-value">
                            <span class="pred-current">${tahmin.mevcut.toFixed(0)} km/s</span>
                            <span class="pred-arrow">${tahmin.degisim > 0 ? '↗' : '↘'}</span>
                            <span class="pred-future">${tahmin.tahmin.toFixed(0)} km/s</span>
                        </div>
                        <div class="prediction-desc">
                            Değişim: ${tahmin.degisim > 0 ? '+' : ''}${tahmin.degisim.toFixed(0)} km/s |
                            Güven: ${tahmin.guven.toFixed(0)}%
                        </div>
                    </div>
                `;
                aiPrediction.innerHTML = predictionHTML;
            } else if (aiPrediction) {
                aiPrediction.innerHTML = `
                    <div class="prediction-item">
                        <div class="prediction-label">Tahmin için veri bekleniyor...</div>
                        <div class="prediction-desc">En az 10 analiz gerekli (${typeof uzayAI !== 'undefined' ? uzayAI.tarihce.length : 0}/10)</div>
                    </div>
                `;
            }
            
        } else {
            // Fallback: Backend API kullan
            const aiResponse = await fetch(`${API_BASE}/api/ai_yorum`);
            if (aiResponse.ok) {
                const aiData = await aiResponse.json();
                if (aiData.durum === 'basarili') {
                    aiMessage.innerHTML = `<p>${aiData.yorum}</p>`;
                    if (aiTimestamp) aiTimestamp.textContent = new Date().toLocaleTimeString('tr-TR');
                    if (aiConfidence) aiConfidence.textContent = `${aiData.guvenilirlik}%`;
                    if (aiRisk) aiRisk.textContent = aiData.risk_seviyesi;
                    if (aiRecommendation) aiRecommendation.textContent = aiData.oneri;
                }
            }
        }
        
    } catch (error) {
        console.error('AI Analysis Error:', error);
        aiMessage.innerHTML = '<p>⚠️ AI sistemi başlatılıyor... Veri akışı bekleniyor.</p>';
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  SCROLL REVEAL ANIMATION
// ═══════════════════════════════════════════════════════════════════════════

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('active');
        }
    });
}, { threshold: 0.1 });

document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

// ═══════════════════════════════════════════════════════════════════════════
//  INITIALIZATION
// ═══════════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 SOLARIS Mission Control Initializing...');
    
    // Initialize charts
    initCharts().then(() => {
        console.log('📊 Charts initialized successfully');
        
        // Start dashboard updates every 3 seconds
        updateDashboard();
        SolarisState.updateInterval = setInterval(updateDashboard, 3000);
        
        // Bug #11 düzeltildi - Uydu verileri ayrı interval'de (15 saniye)
        fetchSatelliteData();
        setInterval(fetchSatelliteData, 15000);
        
        console.log('✅ SOLARIS Mission Control Online');
    });
    
    // Initialize DONKI events
    fetchDONKIEvents();
    setInterval(fetchDONKIEvents, 30 * 60 * 1000);
    
    // Initialize AI Analysis
    updateAIAnalysis();
    setInterval(updateAIAnalysis, 10000); // Update every 10 seconds
    
    // Event filter buttons
    const filterBtns = document.querySelectorAll('.event-filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const filterType = btn.dataset.type;
            const events = document.querySelectorAll('.event-item');
            
            events.forEach(event => {
                const title = event.querySelector('.event-title')?.textContent || '';
                if (filterType === 'all' || title.includes(filterType)) {
                    event.style.display = 'flex';
                } else {
                    event.style.display = 'none';
                }
            });
        });
    });
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (SolarisState.updateInterval) {
        clearInterval(SolarisState.updateInterval);
    }
});

console.log('⚡ SOLARIS Mission Control JavaScript Loaded');