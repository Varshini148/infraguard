/**
 * INFRAGUARD — SENSOR ANALYSIS & AUKF CLIENT LOGIC
 * Manages CSV telemetry uploads, Chart.js time-series streams, and anomaly logging.
 */

let accelVibChart = null;
let speedCovChart = null;

document.addEventListener('DOMContentLoaded', () => {
  initSensorListeners();
});

function initSensorListeners() {
  const form = document.getElementById('sensor-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById('sensor-file');
    if (!fileInput.files || fileInput.files.length === 0) {
      showToast('Please select a telemetry CSV file.', 'warning');
      return;
    }
    await processSensorFile(fileInput.files[0]);
  });

  document.getElementById('btn-load-sample').addEventListener('click', async () => {
    try {
      showToast('Fetching synthetic NH-544 sensor stream...', 'info');
      const res = await fetch('/api/sensors/generate-sample-csv');
      const blob = await res.blob();
      const file = new File([blob], 'nh544_salem_telemetry.csv', { type: 'text/csv' });
      await processSensorFile(file);
    } catch (e) {
      console.error('Failed to load sample sensor data:', e);
      showToast('Sample load error: ' + e.message, 'warning');
    }
  });
}

async function processSensorFile(file) {
  const btn = document.getElementById('btn-fuse');
  btn.disabled = true;
  btn.textContent = 'Running Unscented Kalman Filtering...';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await api.uploadSensors(formData);
    
    // Update Diagnostics
    document.getElementById('fusion-status-badge').textContent = 'Validated & Fused';
    document.getElementById('fusion-status-badge').className = 'badge badge-low';
    document.getElementById('diag-samples').textContent = res.summary.total_samples;
    document.getElementById('diag-anomalies').textContent = res.summary.anomalies_detected;
    document.getElementById('diag-max-vib').textContent = res.summary.max_vibration.toFixed(2);
    document.getElementById('diag-mean-roughness').textContent = res.summary.mean_roughness.toFixed(3);
    document.getElementById('fusion-notes').textContent = `Sensors detected: [${res.sensor_types.join(', ')}]. Processed across ${res.summary.duration_seconds} seconds.`;

    // Render Charts
    renderSensorCharts(res.first_estimates_preview);

    // Populate Table
    populateAnomalyTable(res.first_estimates_preview);

    showToast(`AUKF Fusion complete: ${res.summary.anomalies_detected} kinematic anomalies identified!`, 'low');
  } catch (err) {
    console.error('AUKF fusion failed:', err);
    showToast('Fusion Error: ' + err.message, 'critical');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Execute AUKF Fusion';
  }
}

function renderSensorCharts(estimates) {
  if (!estimates || estimates.length === 0) return;

  const labels = estimates.map((e, idx) => `${idx * 0.1}s`);
  const accelData = estimates.map(e => e.vertical_accel_mps2);
  const roughnessData = estimates.map(e => e.roughness_index);
  const speedData = estimates.map(e => e.estimated_speed_kmh);
  const covData = estimates.map(e => e.covariance_trace * 1000); // scaled for visualization

  // Chart 1: Acceleration & Roughness
  const ctx1 = document.getElementById('accelVibChart');
  if (accelVibChart) accelVibChart.destroy();

  accelVibChart = new Chart(ctx1, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Vertical Accel (m/s²)',
          data: accelData,
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          borderWidth: 2,
          pointRadius: 1,
          tension: 0.2
        },
        {
          label: 'Roughness Index (η)',
          data: roughnessData,
          borderColor: '#0284c7',
          borderWidth: 2,
          pointRadius: 1,
          tension: 0.2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top', labels: { font: { family: 'Inter', size: 11 } } }
      },
      scales: {
        x: { ticks: { maxTicksLimit: 12, font: { family: 'Inter' } } },
        y: { beginAtZero: true, grid: { color: '#f1f5f9' } }
      }
    }
  });

  // Chart 2: Speed & Covariance Trace
  const ctx2 = document.getElementById('speedCovChart');
  if (speedCovChart) speedCovChart.destroy();

  speedCovChart = new Chart(ctx2, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Kinematic Speed (km/h)',
          data: speedData,
          borderColor: '#059669',
          borderWidth: 2,
          pointRadius: 1,
          tension: 0.2
        },
        {
          label: 'Covariance Trace (x1000)',
          data: covData,
          borderColor: '#8b5cf6',
          borderDash: [5, 5],
          borderWidth: 1.5,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top', labels: { font: { family: 'Inter', size: 11 } } }
      },
      scales: {
        x: { ticks: { maxTicksLimit: 12, font: { family: 'Inter' } } },
        y: { beginAtZero: true, grid: { color: '#f1f5f9' } }
      }
    }
  });
}

function populateAnomalyTable(estimates) {
  const tbody = document.getElementById('anomaly-tbody');
  if (!tbody) return;

  const anomalies = estimates.filter(e => e.anomaly_score > 0.40);
  if (anomalies.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-light); padding: 1.5rem;">No significant vibration anomalies identified across this stream.</td></tr>`;
    return;
  }

  tbody.innerHTML = anomalies.map(a => {
    const timeFormatted = a.timestamp.split('T')[1]?.substring(0, 8) || a.timestamp;
    const scoreColor = a.anomaly_score > 0.65 ? 'color: #dc2626; font-weight: 700;' : 'color: #ea580c;';

    return `
      <tr>
        <td>${timeFormatted}</td>
        <td><code>${a.estimated_lat.toFixed(6)}, ${a.estimated_lng.toFixed(6)}</code></td>
        <td>${a.estimated_speed_kmh.toFixed(1)} km/h</td>
        <td><strong>${a.vertical_accel_mps2.toFixed(3)}</strong></td>
        <td>${a.roughness_index.toFixed(3)}</td>
        <td style="${scoreColor}">${a.anomaly_score.toFixed(3)}</td>
        <td>${Math.round(a.confidence_factor * 100)}%</td>
      </tr>
    `;
  }).join('');
}
