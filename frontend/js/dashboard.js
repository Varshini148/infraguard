/**
 * INFRAGUARD — DASHBOARD CLIENT SCRIPT
 * Fetches authority statistics, renders Chart.js analytics and Leaflet overview map.
 */

let categoryChart = null;
let riskSeverityChart = null;
let deteriorationChart = null;
let miniMap = null;

document.addEventListener('DOMContentLoaded', async () => {
  await loadDashboardData();
  initMiniMap();
});

async function loadDashboardData() {
  try {
    const summary = await api.getDashboardSummary();
    
    // Update KPI values
    document.getElementById('kpi-total-defects').textContent = summary.total_defects || 0;
    document.getElementById('kpi-critical-risk').textContent = summary.critical_risk || 0;
    document.getElementById('kpi-high-risk').textContent = summary.high_risk || 0;
    document.getElementById('kpi-sensor-supported').textContent = summary.sensor_supported_count || 0;
    document.getElementById('kpi-worsening').textContent = (summary.by_deterioration && summary.by_deterioration.worsening) || 0;
    document.getElementById('kpi-duplicates').textContent = summary.duplicates_count || 0;

    // Update Category Pills
    if (summary.by_category) {
      document.getElementById('cat-count-road').textContent = `${summary.by_category.road || 0} defects`;
      document.getElementById('cat-count-bridge').textContent = `${summary.by_category.bridge || 0} defects`;
      document.getElementById('cat-count-pipeline').textContent = `${summary.by_category.pipeline || 0} defects`;
      document.getElementById('cat-count-powergrid').textContent = `${summary.by_category.power_grid || 0} defects`;
    }

    // Render Charts
    renderCategoryChart(summary.by_category || {});
    renderRiskSeverityChart(summary.by_severity || {}, summary.sensor_supported_count || 0);
    renderDeteriorationChart(summary.by_deterioration || {});

    // Populate Recent Records Table
    populateRecentTable(summary.recent_defects || []);

  } catch (err) {
    console.error('Failed to load dashboard statistics:', err);
    showToast('Failed to load live metrics: ' + err.message, 'warning');
  }
}

function renderCategoryChart(byCategory) {
  const ctx = document.getElementById('categoryChart');
  if (!ctx) return;

  if (categoryChart) categoryChart.destroy();

  const labels = ['Roads', 'Bridges', 'Pipelines', 'Power Grids'];
  const data = [
    byCategory.road || 0,
    byCategory.bridge || 0,
    byCategory.pipeline || 0,
    byCategory.power_grid || 0
  ];

  categoryChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: [
          '#38bdf8', // Pastel Sky Blue
          '#a78bfa', // Pastel Lavender
          '#34d399', // Pastel Mint
          '#fb923c'  // Pastel Peach
        ],
        borderWidth: 2,
        borderColor: '#ffffff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { font: { family: 'Inter', size: 12 }, boxWidth: 14 }
        }
      },
      cutout: '65%'
    }
  });
}

function renderRiskSeverityChart(bySeverity, sensorCount) {
  const ctx = document.getElementById('riskSeverityChart');
  if (!ctx) return;

  if (riskSeverityChart) riskSeverityChart.destroy();

  riskSeverityChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Critical', 'Severe', 'Moderate', 'Minor', 'Sensor-Linked'],
      datasets: [{
        label: 'Defect Count',
        data: [
          bySeverity.critical || 0,
          bySeverity.severe || 0,
          bySeverity.moderate || 0,
          bySeverity.minor || 0,
          sensorCount
        ],
        backgroundColor: [
          '#f87171', // Red
          '#fb923c', // Orange
          '#facc15', // Amber
          '#4ade80', // Green
          '#38bdf8'  // Blue
        ],
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { stepSize: 1, font: { family: 'Inter' } },
          grid: { color: '#f1f5f9' }
        },
        x: {
          ticks: { font: { family: 'Inter' } },
          grid: { display: false }
        }
      }
    }
  });
}

function renderDeteriorationChart(byDet) {
  const ctx = document.getElementById('deteriorationChart');
  if (!ctx) return;

  if (deteriorationChart) deteriorationChart.destroy();

  deteriorationChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['New Baseline', 'Stable', 'Worsening', 'Unresolved', 'Inconclusive'],
      datasets: [{
        label: 'Records',
        data: [
          byDet.new || 0,
          byDet.stable || 0,
          byDet.worsening || 0,
          byDet.unresolved || 0,
          byDet.inconclusive || 0
        ],
        backgroundColor: [
          '#60a5fa', // Blue
          '#34d399', // Mint
          '#f43f5e', // Rose/Red
          '#f59e0b', // Amber
          '#94a3b8'  // Slate
        ],
        borderRadius: 6
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: {
          beginAtZero: true,
          ticks: { stepSize: 1, font: { family: 'Inter' } },
          grid: { color: '#f1f5f9' }
        },
        y: {
          ticks: { font: { family: 'Inter' } },
          grid: { display: false }
        }
      }
    }
  });
}

async function initMiniMap() {
  const mapElem = document.getElementById('mini-map');
  if (!mapElem || typeof L === 'undefined') return;

  // Center on Tamil Nadu, India (Salem/Erode NH 544 region)
  miniMap = L.map('mini-map').setView([11.4883, 77.8683], 8);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(miniMap);

  try {
    const geojson = await api.getGeoJSON();
    if (geojson && geojson.features && geojson.features.length > 0) {
      L.geoJSON(geojson, {
        pointToLayer: (feature, latlng) => {
          const risk = feature.properties.risk_level || 'low';
          let color = '#059669'; // low = green
          if (risk === 'critical') color = '#dc2626';
          else if (risk === 'high') color = '#ea580c';
          else if (risk === 'medium') color = '#d97706';

          return L.circleMarker(latlng, {
            radius: 7,
            fillColor: color,
            color: '#ffffff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.85
          });
        },
        onEachFeature: (feature, layer) => {
          const p = feature.properties;
          layer.bindPopup(`
            <div style="font-family: Inter, sans-serif; font-size: 12px;">
              <strong>${p.id}</strong><br/>
              <span>${p.category.toUpperCase()} &bull; ${p.defect_type}</span><br/>
              <span>Risk: <strong>${p.risk_score}</strong> (${p.risk_level})</span><br/>
              <span>Status: ${p.deterioration_status}</span>
            </div>
          `);
        }
      }).addTo(miniMap);
    }
  } catch (e) {
    console.warn('Mini-map GeoJSON loading skipped:', e);
  }
}

function populateRecentTable(defects) {
  const tbody = document.getElementById('recent-defects-tbody');
  if (!tbody) return;

  if (defects.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-light); padding: 1.5rem;">No defect records found. Upload inspection media to begin.</td></tr>`;
    return;
  }

  tbody.innerHTML = defects.map(d => {
    const sevBadge = `badge-${d.severity.toLowerCase()}`;
    const catBadge = `badge-${d.category.toLowerCase().replace('_', '')}`;
    const sensorIcon = d.sensor_supported 
      ? `<span class="badge badge-low" title="AUKF kinematic anomaly confirmed">AUKF Yes</span>`
      : `<span style="color: var(--text-light); font-size: 0.75rem;">Visual Only</span>`;

    let verifBadge = '<span class="badge badge-medium">Unverified</span>';
    if (d.verification_status === 'verified_by_inspection') {
      verifBadge = '<span class="badge badge-low">Verified</span>';
    } else if (d.verification_status === 'rejected') {
      verifBadge = '<span class="badge badge-critical">Rejected</span>';
    } else if (d.verification_status === 'pending_review') {
      verifBadge = '<span class="badge badge-high">In Review</span>';
    }

    return `
      <tr>
        <td><strong>${d.id}</strong></td>
        <td><span class="badge ${catBadge}">${d.category.toUpperCase()}</span></td>
        <td>${d.defect_type}</td>
        <td><span class="badge ${sevBadge}">${d.severity.toUpperCase()}</span></td>
        <td><strong>${d.risk_score.toFixed(1)}</strong></td>
        <td><span class="text-small">${d.confidence_grade}</span></td>
        <td>${sensorIcon}</td>
        <td>${verifBadge}</td>
        <td>
          <a href="/pages/records.html?defect_id=${d.id}" class="btn btn-secondary" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;">
            Inspect
          </a>
        </td>
      </tr>
    `;
  }).join('');
}
