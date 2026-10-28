/**
 * INFRAGUARD — UNIFIED FRONTEND API CLIENT
 * Connects frontend pages to FastAPI backend endpoints.
 */

const API_BASE = window.location.origin;

class InfraGuardAPI {
  constructor() {
    this.tokenKey = 'infraguard_jwt_token';
    this.userKey = 'infraguard_current_user';
  }

  getToken() {
    return localStorage.getItem(this.tokenKey);
  }

  setSession(token, user) {
    localStorage.setItem(this.tokenKey, token);
    localStorage.setItem(this.userKey, JSON.stringify(user));
  }

  clearSession() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
  }

  getUser() {
    const raw = localStorage.getItem(this.userKey);
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  async ensureDefaultAuth() {
    // If not authenticated, automatically log in as default demonstration admin
    if (!this.getToken()) {
      try {
        const res = await fetch(`${API_BASE}/api/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: 'admin', password: 'admin123' })
        });
        if (res.ok) {
          const data = await res.json();
          this.setSession(data.access_token, data.user);
          console.log('Auto-authenticated as default administrator.');
        }
      } catch (e) {
        console.warn('Auto-login error:', e);
      }
    }
  }

  async request(endpoint, options = {}) {
    await this.ensureDefaultAuth();
    const token = this.getToken();

    const headers = options.headers || {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Do not set Content-Type if FormData is used
    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const config = {
      ...options,
      headers
    };

    const response = await fetch(`${API_BASE}${endpoint}`, config);

    if (!response.ok) {
      let errorMsg = `HTTP Error ${response.status}: ${response.statusText}`;
      try {
        const errJson = await response.json();
        if (errJson.detail) errorMsg = errJson.detail;
      } catch {}
      throw new Error(errorMsg);
    }

    // If downloading file
    const disposition = response.headers.get('content-disposition');
    if (disposition && disposition.includes('attachment')) {
      return response.blob();
    }

    return response.json();
  }

  // Dashboard & Reports
  async getDashboardSummary() {
    return this.request('/api/reports/summary');
  }

  // AI Detection & Models
  async getModels() {
    return this.request('/api/detection/models');
  }

  async detectImage(formData) {
    return this.request('/api/detection/image', {
      method: 'POST',
      body: formData
    });
  }

  async detectVideo(formData) {
    return this.request('/api/detection/video', {
      method: 'POST',
      body: formData
    });
  }

  // Sensors & AUKF
  async uploadSensors(formData) {
    return this.request('/api/sensors/upload', {
      method: 'POST',
      body: formData
    });
  }

  async getSensorDatasets() {
    return this.request('/api/sensors/datasets');
  }

  async getSensorEstimates(datasetId) {
    return this.request(`/api/sensors/${datasetId}/estimates`);
  }

  // Infrastructure & Defects
  async getAssets(category) {
    const q = category ? `?category=${category}` : '';
    return this.request(`/api/infrastructure/assets${q}`);
  }

  async getDefects(filters = {}) {
    const params = new URLSearchParams();
    for (const [key, val] of Object.entries(filters)) {
      if (val !== undefined && val !== null && val !== '') {
        params.append(key, val);
      }
    }
    return this.request(`/api/infrastructure/defects?${params.toString()}`);
  }

  async getDefect(defectId) {
    return this.request(`/api/infrastructure/defects/${defectId}`);
  }

  async updateDefectVerification(defectId, status, notes) {
    return this.request(`/api/infrastructure/defects/${defectId}/verification`, {
      method: 'PATCH',
      body: JSON.stringify({ verification_status: status, verification_notes: notes })
    });
  }

  async updateDefectCoordinates(defectId, lat, lng) {
    return this.request(`/api/infrastructure/defects/${defectId}/coordinates?lat=${lat}&lng=${lng}`, {
      method: 'PATCH'
    });
  }

  async getDefectTimeline(defectId) {
    return this.request(`/api/infrastructure/defects/${defectId}/timeline`);
  }

  async getDuplicates(status) {
    const q = status ? `?status=${status}` : '';
    return this.request(`/api/infrastructure/duplicates${q}`);
  }

  async resolveDuplicate(duplicateId, action, notes) {
    return this.request(`/api/infrastructure/duplicates/${duplicateId}`, {
      method: 'PATCH',
      body: JSON.stringify({ action, notes })
    });
  }

  async getGeoJSON(category, riskLevel) {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (riskLevel) params.append('risk_level', riskLevel);
    return this.request(`/api/infrastructure/geojson?${params.toString()}`);
  }

  // Risk & Prioritization
  async recalculateRisk(category) {
    const q = category ? `?category=${category}` : '';
    return this.request(`/api/risk/recalculate${q}`, { method: 'POST' });
  }

  async getPriorities(category) {
    const q = category ? `?category=${category}` : '';
    return this.request(`/api/risk/priorities${q}`);
  }

  // Datasets
  async getDatasets(category) {
    const q = category ? `?category=${category}` : '';
    return this.request(`/api/datasets${q}`);
  }

  async updateDatasetStatus(datasetId, status) {
    return this.request(`/api/datasets/${datasetId}/status?status=${status}`, {
      method: 'PATCH'
    });
  }

  // Users & Staff
  async getStaff() {
    return this.request('/api/auth/users');
  }

  async createStaff(userData) {
    return this.request('/api/auth/users', {
      method: 'POST',
      body: JSON.stringify(userData)
    });
  }
}

const api = new InfraGuardAPI();

// Toast helper
function showToast(message, type = 'info') {
  let toastContainer = document.getElementById('toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.style.position = 'fixed';
    toastContainer.style.bottom = '20px';
    toastContainer.style.right = '20px';
    toastContainer.style.zIndex = '9999';
    toastContainer.style.display = 'flex';
    toastContainer.style.flexDirection = 'column';
    toastContainer.style.gap = '8px';
    document.body.appendChild(toastContainer);
  }

  const toast = document.createElement('div');
  toast.className = `alert alert-${type}`;
  toast.style.margin = '0';
  toast.style.boxShadow = 'var(--shadow-md)';
  toast.style.animation = 'fadeIn 0.2s ease';
  toast.textContent = message;

  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}
