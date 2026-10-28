/**
 * INFRAGUARD — DETECTION PAGE CLIENT LOGIC
 * Manages image/video uploads, category switching, and defect rendering.
 */

let modelsInfo = {};

document.addEventListener('DOMContentLoaded', async () => {
  await loadModelStatuses();
  initFormListeners();
});

async function loadModelStatuses() {
  try {
    modelsInfo = await api.getModels();
    updateModelInfoView('road');
  } catch (e) {
    console.error('Failed to load models status:', e);
  }
}

function updateModelInfoView(category) {
  const m = modelsInfo[category];
  if (!m) return;

  document.getElementById('model-name').textContent = m.name;
  document.getElementById('model-version').textContent = `Version: ${m.version} | License: ${m.license}`;
  document.getElementById('model-limitations').textContent = m.limitations;

  // Render Classes Chips
  const chipsContainer = document.getElementById('model-classes-chips');
  chipsContainer.innerHTML = m.supported_classes.map(c => `
    <span class="badge badge-road" style="font-size: 0.72rem; padding: 0.2rem 0.5rem;">${c}</span>
  `).join('');

  // Status & weights
  const statusBadge = document.getElementById('model-status-badge');
  const weightDesc = document.getElementById('model-weight-desc');

  if (m.status === 'loaded') {
    statusBadge.className = 'badge badge-low';
    statusBadge.textContent = 'PyTorch Weights Active';
    weightDesc.innerHTML = `<strong>Trained Weights:</strong> Active and running real-time YOLOv8 inference.`;
  } else {
    statusBadge.className = 'badge badge-medium';
    statusBadge.textContent = 'Vision Fallback Engine';
    weightDesc.innerHTML = `
      <strong>Status:</strong> ${m.weight_status}.<br/>
      <span class="text-small text-secondary">${m.obtaining_instructions}</span>
    `;
  }
}

function initFormListeners() {
  // Category switching
  document.querySelectorAll('.cat-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.cat-btn').forEach(b => {
        b.className = 'btn btn-secondary cat-btn';
      });
      btn.className = 'btn btn-pastel-blue cat-btn active';
      
      const cat = btn.dataset.category;
      document.getElementById('category').value = cat;
      document.getElementById('active-category-badge').textContent = cat.toUpperCase();
      updateModelInfoView(cat);
    });
  });

  // Media Mode Toggle
  const modeImg = document.getElementById('mode-image');
  const modeVid = document.getElementById('mode-video');
  const vidOpts = document.getElementById('video-options');

  modeImg.addEventListener('change', () => { if (modeImg.checked) vidOpts.style.display = 'none'; });
  modeVid.addEventListener('change', () => { if (modeVid.checked) vidOpts.style.display = 'block'; });

  // Use Sample Evidence Button (generates simulated realistic road image in canvas and creates a File object)
  document.getElementById('btn-demo-image').addEventListener('click', () => {
    loadSampleCanvasImage();
  });

  // Form Submit
  const form = document.getElementById('detection-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    await executeDetection();
  });
}

function loadSampleCanvasImage() {
  const canvas = document.createElement('canvas');
  canvas.width = 640;
  canvas.height = 480;
  const ctx = canvas.getContext('2d');

  // Draw asphalt background
  ctx.fillStyle = '#374151';
  ctx.fillRect(0, 0, 640, 480);

  // Road markings
  ctx.strokeStyle = '#fef08a';
  ctx.lineWidth = 12;
  ctx.setLineDash([40, 30]);
  ctx.beginPath();
  ctx.moveTo(320, 0);
  ctx.lineTo(320, 480);
  ctx.stroke();

  // Draw simulated pothole distress
  ctx.fillStyle = '#111827';
  ctx.beginPath();
  ctx.ellipse(280, 240, 75, 45, 0.2, 0, Math.PI * 2);
  ctx.fill();

  // Edge cracks
  ctx.strokeStyle = '#030712';
  ctx.lineWidth = 3;
  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.moveTo(210, 230);
  ctx.lineTo(160, 210);
  ctx.lineTo(130, 240);
  ctx.moveTo(350, 250);
  ctx.lineTo(410, 260);
  ctx.stroke();

  canvas.toBlob((blob) => {
    const file = new File([blob], 'sample_tamil_nadu_nh544_pothole.jpg', { type: 'image/jpeg' });
    const dt = new DataTransfer();
    dt.items.add(file);
    document.getElementById('media-file').files = dt.files;
    showToast('Loaded sample road distress inspection image (NH 544).', 'info');
  }, 'image/jpeg');
}

async function executeDetection() {
  const fileInput = document.getElementById('media-file');
  if (!fileInput.files || fileInput.files.length === 0) {
    showToast('Please select an image or video file.', 'warning');
    return;
  }

  const file = fileInput.files[0];
  const category = document.getElementById('category').value;
  const isVideo = document.getElementById('mode-video').checked;
  const lat = document.getElementById('lat').value;
  const lng = document.getElementById('lng').value;
  const sensorVib = document.getElementById('sensor_vibration').value;

  const btn = document.getElementById('btn-detect');
  btn.disabled = true;
  btn.textContent = 'Processing Multimodal Detection...';

  const formData = new FormData();
  formData.append('file', file);
  formData.append('category', category);
  if (lat) formData.append('lat', lat);
  if (lng) formData.append('lng', lng);

  try {
    let result;
    if (isVideo) {
      formData.append('sampling_interval_sec', document.getElementById('sampling_interval').value);
      formData.append('max_frames', document.getElementById('max_frames').value);
      result = await api.detectVideo(formData);
      renderVideoResults(result);
    } else {
      if (sensorVib) formData.append('sensor_vibration', sensorVib);
      result = await api.detectImage(formData);
      renderImageResults(result);
    }
    showToast('Defect detection & evidence saved successfully!', 'low');
  } catch (err) {
    console.error('Detection failed:', err);
    showToast('Detection error: ' + err.message, 'critical');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Run AI Defect Detection';
  }
}

function renderImageResults(res) {
  const card = document.getElementById('results-card');
  card.style.display = 'block';

  document.getElementById('res-total-badge').textContent = `${res.total_detections} Defect(s) Identified`;
  document.getElementById('annotated-preview-img').src = res.annotated_path;
  document.getElementById('res-time-span').textContent = `Inference time: ${res.processing_time_ms} ms`;
  document.getElementById('res-status-span').textContent = `Pipeline: ${res.model_status}`;

  const list = document.getElementById('detections-list');
  if (res.detections.length === 0) {
    list.innerHTML = `<div class="alert alert-info">No structural defects detected above confidence threshold.</div>`;
    return;
  }

  list.innerHTML = res.detections.map((d, i) => {
    const sevBadge = `badge-${d.severity.toLowerCase()}`;
    const defectId = res.saved_defect_ids[i] || 'RECORDED';

    return `
      <div style="background: #ffffff; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 0.85rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
          <strong>${d.defect_type}</strong>
          <span class="badge ${sevBadge}">${d.severity.toUpperCase()}</span>
        </div>
        <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.5rem;">
          <span>Raw Model: <strong>${Math.round(d.confidence * 100)}%</strong></span> &bull; 
          <span>Assessed: <strong>${Math.round(d.assessed_confidence * 100)}%</strong> (${d.confidence_grade})</span>
        </div>
        <div style="font-size: 0.78rem; background: #f8fafc; padding: 0.4rem 0.6rem; border-radius: 4px; margin-bottom: 0.5rem;">
          ${d.confidence_rationale}
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span class="text-small text-secondary">Defect ID: <strong>${defectId}</strong></span>
          <a href="/pages/records.html?defect_id=${defectId}" class="btn btn-secondary" style="padding: 0.2rem 0.5rem; font-size: 0.72rem;">
            Inspect Record
          </a>
        </div>
      </div>
    `;
  }).join('');
}

function renderVideoResults(res) {
  const card = document.getElementById('results-card');
  card.style.display = 'block';

  document.getElementById('res-total-badge').textContent = `${res.unique_detections_count} Unique Detections (${res.extracted_frames_count} Frames)`;
  
  if (res.sampled_frames && res.sampled_frames.length > 0) {
    document.getElementById('annotated-preview-img').src = res.sampled_frames[0].annotated_path;
  }

  document.getElementById('res-time-span').textContent = `Duration: ${res.duration_seconds}s | Frames: ${res.extracted_frames_count}`;
  document.getElementById('res-status-span').textContent = `Keyframe interval: ${res.sampled_frames[0]?.timestamp_sec || 1.0}s`;

  const list = document.getElementById('detections-list');
  list.innerHTML = `
    <div class="alert alert-info" style="margin-bottom: 0.75rem;">
      Extracted ${res.extracted_frames_count} frames across ${res.duration_seconds}s video stream.
      Identified ${res.unique_detections_count} unique defect occurrences saved to database.
    </div>
    <div style="display: flex; flex-direction: column; gap: 0.5rem;">
      ${res.sampled_frames.map(f => `
        <div style="display: flex; justify-content: space-between; align-items: center; background: #f8fafc; padding: 0.5rem 0.75rem; border-radius: var(--radius-md);">
          <span>Frame #${f.frame_index} (at ${f.timestamp_sec}s)</span>
          <span class="badge ${f.detections_count > 0 ? 'badge-high' : 'badge-low'}">
            ${f.detections_count} Defects
          </span>
        </div>
      `).join('')}
    </div>
  `;
}
