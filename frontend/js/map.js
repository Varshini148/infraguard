/**
 * INFRAGUARD — INFRASTRUCTURE MAP CLIENT LOGIC
 * Interactive Leaflet mapping defaulted to Tamil Nadu, India.
 * Handles spatial clustering, risk indicators, filters, and manual coordinate updates.
 */

let map = null;
let defectLayerGroup = null;
let assetLayerGroup = null;

// Tamil Nadu Centroid (approx. Trichy / Salem corridor)
const TN_DEFAULT_COORDS = [11.1271, 78.6569];
const TN_DEFAULT_ZOOM = 7;

document.addEventListener('DOMContentLoaded', () => {
  initMap();
  initMapFilters();
});

function initMap() {
  map = L.map('map-viewport').setView(TN_DEFAULT_COORDS, TN_DEFAULT_ZOOM);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors | InfraGuard Spatial Engine'
  }).addTo(map);

  assetLayerGroup = L.layerGroup().addTo(map);
  defectLayerGroup = L.layerGroup().addTo(map);

  loadInfrastructureAssets();
  loadMapDefects();

  document.getElementById('btn-center-tn').addEventListener('click', () => {
    map.setView(TN_DEFAULT_COORDS, TN_DEFAULT_ZOOM);
  });

  document.getElementById('btn-export-geojson').addEventListener('click', async () => {
    try {
      const cat = document.getElementById('filter-category').value;
      const risk = document.getElementById('filter-risk').value;
      const data = await api.getGeoJSON(cat, risk);
      
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/geo+json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `infraguard_defects_${Date.now()}.geojson`;
      a.click();
      URL.revokeObjectURL(url);
      showToast('GeoJSON exported successfully!', 'low');
    } catch (e) {
      showToast('GeoJSON export error: ' + e.message, 'warning');
    }
  });

  // Modal form listener
  document.getElementById('coords-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const defectId = document.getElementById('modal-defect-id').value;
    const lat = parseFloat(document.getElementById('modal-lat').value);
    const lng = parseFloat(document.getElementById('modal-lng').value);

    try {
      await api.updateDefectCoordinates(defectId, lat, lng);
      showToast(`Coordinates updated for ${defectId}`, 'low');
      closeCoordsModal();
      loadMapDefects();
    } catch (err) {
      showToast('Failed to update coordinates: ' + err.message, 'critical');
    }
  });
}

function initMapFilters() {
  const filters = ['filter-category', 'filter-risk', 'filter-verification'];
  filters.forEach(id => {
    document.getElementById(id).addEventListener('change', () => {
      loadMapDefects();
    });
  });
}

async function loadInfrastructureAssets() {
  try {
    const assets = await api.getAssets();
    assetLayerGroup.clearLayers();

    assets.forEach(a => {
      const iconHtml = `<div style="background: #ffffff; border: 2px solid #0284c7; border-radius: 50%; width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; color: #0284c7; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">A</div>`;
      const customIcon = L.divIcon({ html: iconHtml, className: '', iconSize: [22, 22] });

      const marker = L.marker([a.lat, a.lng], { icon: customIcon });
      marker.bindPopup(`
        <div style="font-family: Inter, sans-serif; font-size: 12px; width: 200px;">
          <div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">${a.name}</div>
          <div style="color: #64748b; font-size: 11px;">Code: <strong>${a.code}</strong></div>
          <div style="color: #64748b; font-size: 11px;">Sector: <strong>${a.category.toUpperCase()}</strong></div>
          <div style="color: #64748b; font-size: 11px;">Importance: <strong>${a.importance_level.toUpperCase()}</strong></div>
          <div style="margin-top: 4px; font-size: 11px;">${a.location_description || ''}</div>
        </div>
      `);
      assetLayerGroup.addLayer(marker);
    });
  } catch (e) {
    console.warn('Assets loading skipped:', e);
  }
}

async function loadMapDefects() {
  const category = document.getElementById('filter-category').value;
  const risk = document.getElementById('filter-risk').value;
  const verification = document.getElementById('filter-verification').value;

  try {
    const res = await api.getDefects({
      category: category || undefined,
      risk_level: risk || undefined,
      verification_status: verification || undefined,
      has_coords_only: true,
      limit: 300
    });

    defectLayerGroup.clearLayers();

    res.items.forEach(d => {
      if (!d.lat || !d.lng) return;

      let color = '#059669'; // low
      let radius = 7;
      if (d.risk_level === 'critical') { color = '#dc2626'; radius = 10; }
      else if (d.risk_level === 'high') { color = '#ea580c'; radius = 8; }
      else if (d.risk_level === 'medium') { color = '#d97706'; radius = 7; }

      const circle = L.circleMarker([d.lat, d.lng], {
        radius: radius,
        fillColor: color,
        color: '#ffffff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.85
      });

      const sensorTag = d.sensor_supported 
        ? `<span class="badge badge-low" style="font-size: 10px;">AUKF Sensor Supported</span>` 
        : `<span class="badge badge-road" style="font-size: 10px;">Visual Telemetry</span>`;

      circle.bindPopup(`
        <div style="font-family: Inter, sans-serif; font-size: 12px; width: 230px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
            <strong style="color: #0f172a;">${d.id}</strong>
            <span class="badge badge-${d.severity.toLowerCase()}">${d.severity.toUpperCase()}</span>
          </div>
          <div style="font-weight: 600; color: #1e293b; margin-bottom: 2px;">${d.defect_type}</div>
          <div style="font-size: 11px; color: #64748b; margin-bottom: 4px;">
            Sector: <strong>${d.category.toUpperCase()}</strong> &bull; Rank: <strong>#${d.repair_priority_rank}</strong>
          </div>
          <div style="display: flex; gap: 4px; margin-bottom: 6px;">
            ${sensorTag}
          </div>
          <div style="font-size: 11px; margin-bottom: 6px;">
            Risk Score: <strong>${d.risk_score.toFixed(1)}</strong> (${d.risk_level})<br/>
            Deterioration: <strong>${d.deterioration_status}</strong><br/>
            Verification: <em>${d.verification_status}</em>
          </div>
          <div style="display: flex; gap: 4px; border-top: 1px solid #e2e8f0; padding-top: 6px; margin-top: 6px;">
            <button class="btn btn-secondary" style="padding: 2px 6px; font-size: 10px;" onclick="openCoordsModal('${d.id}', ${d.lat}, ${d.lng})">
              Adjust GPS
            </button>
            <a href="/pages/records.html?defect_id=${d.id}" class="btn btn-primary" style="padding: 2px 6px; font-size: 10px; color: white;">
              Full Details
            </a>
          </div>
        </div>
      `);

      defectLayerGroup.addLayer(circle);
    });

  } catch (e) {
    console.error('Failed to load map defects:', e);
  }
}

function openCoordsModal(defectId, lat, lng) {
  document.getElementById('modal-defect-id').value = defectId;
  document.getElementById('modal-defect-label').value = defectId;
  document.getElementById('modal-lat').value = lat;
  document.getElementById('modal-lng').value = lng;
  document.getElementById('coords-modal').classList.add('active');
}

function closeCoordsModal() {
  document.getElementById('coords-modal').classList.remove('active');
}
