"""
InfraGuard Adaptive Unscented Kalman Filter (AUKF) Sensor Fusion Engine
======================================================================

THEORY & MATHEMATICAL FOUNDATION:
---------------------------------
The Adaptive Unscented Kalman Filter (AUKF) solves non-linear kinematic state estimation
and disturbance tracking for multi-infrastructure vehicle and drone inspections.

1. State Vector (Dimension n = 5):
   x = [ p_lat, p_lng, v, a_z, eta ]^T
   - p_lat: Latitude (degrees)
   - p_lng: Longitude (degrees)
   - v:     Forward velocity (m/s)
   - a_z:   Vertical/normal acceleration disturbance (m/s^2)
   - eta:   Surface anomaly / roughness index (normalized 0.0 to 1.0)

2. Process Model f(x, dt):
   - Earth radius R_e = 6,378,137 m
   - p_lat_{k} = p_lat_{k-1} + (v_{k-1} * dt / R_e) * (180 / pi)
   - p_lng_{k} = p_lng_{k-1} + (v_{k-1} * dt / (R_e * cos(p_lat_{k-1} * pi / 180))) * (180 / pi)
   - v_{k}     = max(0.0, v_{k-1})
   - a_z_{k}   = gamma * a_z_{k-1}  (damping factor gamma = 0.85)
   - eta_{k}   = lambda_r * eta_{k-1} + (1 - lambda_r) * min(1.0, |a_z_k| / a_threshold)

3. Measurement Vector z:
   z = [ z_lat, z_lng, z_v, z_az, z_vib ]^T (Available subset handled dynamically)

4. Unscented Transform (UT) Sigma Points:
   - 2n + 1 = 11 sigma points generated around x_k:
     X_0 = x_k
     X_i = x_k + sqrt(n + lambda) * (chol(P))_i
     X_{i+n} = x_k - sqrt(n + lambda) * (chol(P))_i
   - Weights:
     W_m^{(0)} = lambda / (n + lambda)
     W_c^{(0)} = lambda / (n + lambda) + (1 - alpha^2 + beta)
     W_m^{(i)} = W_c^{(i)} = 1 / (2 * (n + lambda))
   - Tuning parameters: alpha = 1e-3, beta = 2.0 (optimal for Gaussian), kappa = 0.0

5. Adaptive Measurement Noise (Sage-Husa / Covariance-Matching):
   - Innovation residual: nu_k = z_k - z_hat_k
   - Adaptive R_k update: R_k = (1 - d_k) * R_{k-1} + d_k * (nu_k * nu_k^T - P_zz)
     with eigenvalue bounding ensuring strictly positive-definite R_k.
   - When vibration spike occurs, process noise Q_k on a_z and eta increases adaptively.
"""

import math
from pathlib import Path
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta

EARTH_RADIUS = 6378137.0  # WGS-84 equatorial radius in meters

class AdaptiveUKF:
    def __init__(
        self,
        alpha: float = 1e-3,
        beta: float = 2.0,
        kappa: float = 0.0,
        forgetting_factor: float = 0.95
    ):
        self.n = 5  # State dimension: [lat, lng, v, a_z, eta]
        self.alpha = alpha
        self.beta = beta
        self.kappa = kappa
        self.forgetting_factor = forgetting_factor
        
        # Scaling parameter lambda
        self.lambda_ = (alpha ** 2) * (self.n + kappa) - self.n
        self.gamma = math.sqrt(self.n + self.lambda_)

        # Compute weights
        self.Wm = np.zeros(2 * self.n + 1)
        self.Wc = np.zeros(2 * self.n + 1)
        
        self.Wm[0] = self.lambda_ / (self.n + self.lambda_)
        self.Wc[0] = self.lambda_ / (self.n + self.lambda_) + (1.0 - alpha ** 2 + beta)
        
        for i in range(1, 2 * self.n + 1):
            w = 1.0 / (2.0 * (self.n + self.lambda_))
            self.Wm[i] = w
            self.Wc[i] = w

        # Initial State Estimate: [lat, lng, v, a_z, eta]
        self.x = np.zeros(self.n)
        
        # Initial State Covariance P
        self.P = np.diag([1e-6, 1e-6, 1.0, 4.0, 0.2])

        # Baseline Process Noise Q
        self.Q_base = np.diag([1e-8, 1e-8, 0.05, 0.5, 0.02])
        self.Q = self.Q_base.copy()

        # Baseline Measurement Noise R for [lat, lng, v, a_z, vib]
        self.R_base = np.diag([1e-6, 1e-6, 0.25, 0.36, 0.04])
        self.R = self.R_base.copy()

        # Step counter
        self.step_k = 0

    def initialize_state(self, lat: float, lng: float, speed_mps: float = 0.0):
        """Seed the filter with starting spatial state."""
        self.x[0] = lat
        self.x[1] = lng
        self.x[2] = max(0.0, speed_mps)
        self.x[3] = 0.0
        self.x[4] = 0.0
        self.P = np.diag([1e-6, 1e-6, 1.0, 4.0, 0.2])
        self.step_k = 0

    def _generate_sigma_points(self) -> np.ndarray:
        """Calculate 2n+1 sigma points using Cholesky decomposition of P."""
        sigma_points = np.zeros((2 * self.n + 1, self.n))
        sigma_points[0] = self.x

        # Enforce symmetry and positive-definiteness on P
        P_sym = 0.5 * (self.P + self.P.T) + 1e-9 * np.eye(self.n)
        try:
            L = np.linalg.cholesky(P_sym)
        except np.linalg.LinAlgError:
            # Fallback to eigenvalue reconstruction if ill-conditioned
            vals, vecs = np.linalg.eigh(P_sym)
            vals = np.maximum(vals, 1e-9)
            L = vecs @ np.diag(np.sqrt(vals))

        scaled_L = self.gamma * L
        for i in range(self.n):
            sigma_points[i + 1] = self.x + scaled_L[:, i]
            sigma_points[i + 1 + self.n] = self.x - scaled_L[:, i]

        return sigma_points

    def _state_transition(self, sigma_pt: np.ndarray, dt: float) -> np.ndarray:
        """Non-linear dynamic kinematics model."""
        lat, lng, v, a_z, eta = sigma_pt
        
        # Earth coordinate translation
        lat_rad = math.radians(lat)
        d_lat_deg = (v * dt / EARTH_RADIUS) * (180.0 / math.pi)
        denom_lng = max(0.01, math.cos(lat_rad))
        d_lng_deg = (v * dt / (EARTH_RADIUS * denom_lng)) * (180.0 / math.pi)
        
        new_lat = lat + d_lat_deg
        new_lng = lng + d_lng_deg
        new_v = max(0.0, v)
        new_az = 0.85 * a_z  # Damped disturbance decay
        new_eta = 0.90 * eta + 0.10 * min(1.0, abs(a_z) / 4.0)

        return np.array([new_lat, new_lng, new_v, new_az, new_eta])

    def predict(self, dt: float):
        """Unscented Kalman Filter prediction step."""
        if dt <= 0:
            dt = 0.1

        sigma_points = self._generate_sigma_points()
        propagated_sigmas = np.zeros_like(sigma_points)

        for i in range(2 * self.n + 1):
            propagated_sigmas[i] = self._state_transition(sigma_points[i], dt)

        # Prior Mean x_pred
        x_pred = np.zeros(self.n)
        for i in range(2 * self.n + 1):
            x_pred += self.Wm[i] * propagated_sigmas[i]

        # Prior Covariance P_pred
        P_pred = np.zeros((self.n, self.n))
        for i in range(2 * self.n + 1):
            diff = propagated_sigmas[i] - x_pred
            P_pred += self.Wc[i] * np.outer(diff, diff)

        # Adaptive process noise inflation during strong acceleration disturbance
        if abs(x_pred[3]) > 2.0:
            adaptive_Q = self.Q_base.copy()
            adaptive_Q[3, 3] *= 3.0  # Inflate acceleration uncertainty
            adaptive_Q[4, 4] *= 2.5  # Inflate roughness uncertainty
        else:
            adaptive_Q = self.Q_base

        self.x = x_pred
        self.P = P_pred + adaptive_Q
        self.propagated_sigmas = propagated_sigmas

    def update(self, measurement: Dict[str, Optional[float]]):
        """
        Adaptive measurement update step.
        Handles missing dimensions (e.g. GPS dropouts or missing accelerometer) dynamically.
        """
        self.step_k += 1

        # Map available measurements: [lat, lng, v, a_z, vib]
        meas_indices = []
        meas_values = []

        if measurement.get("lat") is not None and measurement.get("lng") is not None:
            meas_indices.extend([0, 1])
            meas_values.extend([measurement["lat"], measurement["lng"]])

        if measurement.get("speed_mps") is not None:
            meas_indices.append(2)
            meas_values.append(measurement["speed_mps"])

        if measurement.get("accel_z") is not None:
            meas_indices.append(3)
            meas_values.append(measurement["accel_z"])

        if measurement.get("vibration_level") is not None:
            meas_indices.append(4)
            meas_values.append(measurement["vibration_level"])

        if not meas_indices:
            # No measurements available in this time step; prediction remains prior
            return

        m_dim = len(meas_indices)
        z_actual = np.array(meas_values)

        # Transform sigma points through measurement function h(X)
        Z_sigmas = np.zeros((2 * self.n + 1, m_dim))
        for i in range(2 * self.n + 1):
            for k_idx, state_idx in enumerate(meas_indices):
                Z_sigmas[i, k_idx] = self.propagated_sigmas[i, state_idx]

        # Predicted measurement mean
        z_pred = np.zeros(m_dim)
        for i in range(2 * self.n + 1):
            z_pred += self.Wm[i] * Z_sigmas[i]

        # Innovation covariance P_zz
        P_zz = np.zeros((m_dim, m_dim))
        for i in range(2 * self.n + 1):
            diff_z = Z_sigmas[i] - z_pred
            P_zz += self.Wc[i] * np.outer(diff_z, diff_z)

        # Extract baseline R for available dimensions
        R_sub = np.zeros((m_dim, m_dim))
        for i, idx_i in enumerate(meas_indices):
            for j, idx_j in enumerate(meas_indices):
                R_sub[i, j] = self.R[idx_i, idx_j]

        # Cross-covariance P_xz
        P_xz = np.zeros((self.n, m_dim))
        for i in range(2 * self.n + 1):
            diff_x = self.propagated_sigmas[i] - self.x
            diff_z = Z_sigmas[i] - z_pred
            P_xz += self.Wc[i] * np.outer(diff_x, diff_z)

        # Total innovation covariance S
        S = P_zz + R_sub
        S_inv = np.linalg.pinv(S)

        # Kalman Gain K
        K = P_xz @ S_inv

        # Innovation residual
        nu = z_actual - z_pred

        # Posterior State and Covariance Update
        self.x = self.x + K @ nu
        self.P = self.P - K @ S @ K.T

        # Adaptive R_k update via Sage-Husa covariance matching
        d_k = (1.0 - self.forgetting_factor) / (1.0 - (self.forgetting_factor ** max(1, self.step_k)))
        d_k = min(0.25, max(0.01, d_k))
        
        nu_outer = np.outer(nu, nu)
        R_adaptive = (1.0 - d_k) * R_sub + d_k * (nu_outer - P_zz)
        
        # Enforce minimum noise floor and symmetry
        for i in range(m_dim):
            state_idx = meas_indices[i]
            min_floor = self.R_base[state_idx, state_idx] * 0.5
            max_ceiling = self.R_base[state_idx, state_idx] * 20.0
            new_val = min(max_ceiling, max(min_floor, R_adaptive[i, i]))
            self.R[state_idx, state_idx] = new_val

    def get_current_estimate(self) -> Dict[str, Any]:
        """Return formatted current state, anomalies, and covariance trace."""
        trace = float(np.trace(self.P))
        # Anomaly score synthesized from roughness index and acceleration magnitude
        anomaly = min(1.0, max(0.0, float(self.x[4] * 0.6 + (abs(self.x[3]) / 5.0) * 0.4)))
        
        return {
            "estimated_lat": round(float(self.x[0]), 6),
            "estimated_lng": round(float(self.x[1]), 6),
            "estimated_speed_kmh": round(float(self.x[2] * 3.6), 2),
            "vertical_accel_mps2": round(float(self.x[3]), 3),
            "roughness_index": round(float(self.x[4]), 3),
            "anomaly_score": round(anomaly, 3),
            "covariance_trace": round(trace, 6),
            "confidence_factor": round(max(0.1, min(1.0, 1.0 / (1.0 + trace * 10.0))), 3)
        }


class SensorFusionPipeline:
    def __init__(self):
        self.aukf = AdaptiveUKF()

    def parse_and_validate_sensor_data(self, df_or_filepath) -> pd.DataFrame:
        """
        Validates column names, formats, geographic bounds, and timestamps.
        Standardizes column names to: timestamp, lat, lng, speed_kmh, accel_x, accel_y, accel_z, vibration_level.
        """
        if isinstance(df_or_filepath, (str, Path)):
            df = pd.read_csv(df_or_filepath)
        else:
            df = df_or_filepath.copy()

        # Normalize column names
        col_map = {}
        for c in df.columns:
            cl = c.strip().lower().replace(" ", "_")
            if cl in ["time", "timestamp", "datetime", "date_time"]:
                col_map[c] = "timestamp"
            elif cl in ["latitude", "lat"]:
                col_map[c] = "lat"
            elif cl in ["longitude", "lng", "lon"]:
                col_map[c] = "lng"
            elif cl in ["speed", "speed_kmh", "velocity", "gps_speed"]:
                col_map[c] = "speed_kmh"
            elif cl in ["accel_x", "ax", "acceleration_x"]:
                col_map[c] = "accel_x"
            elif cl in ["accel_y", "ay", "acceleration_y"]:
                col_map[c] = "accel_y"
            elif cl in ["accel_z", "az", "acceleration_z", "vertical_accel"]:
                col_map[c] = "accel_z"
            elif cl in ["vibration", "vibration_level", "vib", "rms_vibration"]:
                col_map[c] = "vibration_level"

        df = df.rename(columns=col_map)

        # Parse timestamps
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        else:
            # Generate synthesized 10Hz timestamps if absent
            base_time = datetime.utcnow()
            df["timestamp"] = [base_time + timedelta(seconds=i * 0.1) for i in range(len(df))]

        # Validate coordinate bounds
        if "lat" in df.columns and "lng" in df.columns:
            invalid_coords = (df["lat"] < -90) | (df["lat"] > 90) | (df["lng"] < -180) | (df["lng"] > 180)
            df.loc[invalid_coords, ["lat", "lng"]] = np.nan

        # Sort and clean
        df = df.sort_values(by="timestamp").reset_index(drop=True)
        return df

    def run_aukf_fusion(self, sensor_df: pd.DataFrame) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Runs sequential AUKF state estimation across the entire time series.
        Returns detailed state estimates and diagnostic anomaly summary.
        """
        clean_df = self.parse_and_validate_sensor_data(sensor_df)
        if clean_df.empty:
            raise ValueError("Sensor dataset contains no valid observations.")

        # Initialize AUKF at first valid coordinate
        first_valid_lat = clean_df["lat"].dropna().iloc[0] if "lat" in clean_df and not clean_df["lat"].dropna().empty else 11.1271
        first_valid_lng = clean_df["lng"].dropna().iloc[0] if "lng" in clean_df and not clean_df["lng"].dropna().empty else 78.6569
        first_speed_kmh = clean_df["speed_kmh"].dropna().iloc[0] if "speed_kmh" in clean_df and not clean_df["speed_kmh"].dropna().empty else 30.0

        self.aukf.initialize_state(
            lat=float(first_valid_lat),
            lng=float(first_valid_lng),
            speed_mps=float(first_speed_kmh) / 3.6
        )

        estimates = []
        anomaly_count = 0
        last_time = clean_df["timestamp"].iloc[0]

        for idx, row in clean_df.iterrows():
            curr_time = row["timestamp"]
            dt = (curr_time - last_time).total_seconds() if idx > 0 else 0.1
            dt = max(0.01, min(2.0, dt))
            last_time = curr_time

            # Step 1: Predict
            self.aukf.predict(dt=dt)

            # Step 2: Build measurement payload
            meas = {}
            if "lat" in row and pd.notnull(row["lat"]):
                meas["lat"] = float(row["lat"])
            if "lng" in row and pd.notnull(row["lng"]):
                meas["lng"] = float(row["lng"])
            if "speed_kmh" in row and pd.notnull(row["speed_kmh"]):
                meas["speed_mps"] = float(row["speed_kmh"]) / 3.6
            if "accel_z" in row and pd.notnull(row["accel_z"]):
                meas["accel_z"] = float(row["accel_z"])
            if "vibration_level" in row and pd.notnull(row["vibration_level"]):
                meas["vibration_level"] = float(row["vibration_level"])

            # Step 3: Update
            self.aukf.update(meas)

            # Step 4: Record output
            est = self.aukf.get_current_estimate()
            est["timestamp"] = curr_time.isoformat()
            if est["anomaly_score"] > 0.45:
                anomaly_count += 1
            estimates.append(est)

        summary = {
            "total_samples": len(clean_df),
            "duration_seconds": round((clean_df["timestamp"].iloc[-1] - clean_df["timestamp"].iloc[0]).total_seconds(), 2),
            "anomalies_detected": anomaly_count,
            "max_vibration": round(float(clean_df["vibration_level"].max()), 2) if "vibration_level" in clean_df else 0.0,
            "mean_roughness": round(float(np.mean([e["roughness_index"] for e in estimates])), 3),
            "status": "fusion_completed_validated"
        }

        return estimates, summary

sensor_fusion_service = SensorFusionPipeline()
