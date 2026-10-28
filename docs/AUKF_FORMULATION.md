# Adaptive Unscented Kalman Filter (AUKF) — Mathematical Formulation

## 1. Overview and Objective
InfraGuard employs an **Adaptive Unscented Kalman Filter (AUKF)** for fusing noisy GPS, speed, vertical accelerometer ($a_z$), and vibrometer signals captured during mobile infrastructure inspections (moving survey vehicles, drones, and pipeline crawlers).

Unlike standard Extended Kalman Filters (EKF) which compute first-order Taylor series Jacobian matrices, the Unscented Kalman Filter utilizes the **Unscented Transform (UT)** to capture true non-linear kinematics without truncation errors. Furthermore, the **Adaptive (Sage-Husa / Covariance-Matching)** component dynamically updates measurement noise covariance $R_k$ and inflates process noise $Q_k$ during sudden acceleration spikes (such as potholes, speed breakers, or bridge expansion joints), preventing filter divergence.

---

## 2. State Vector ($n = 5$)
The system state vector at discrete time step $k$ is defined as:
$$\mathbf{x}_k = \begin{bmatrix} p_{lat} \\ p_{lng} \\ v \\ a_z \\ \eta \end{bmatrix}$$

- $p_{lat}$: Latitude (degrees)
- $p_{lng}$: Longitude (degrees)
- $v$: Forward longitudinal velocity ($m/s$)
- $a_z$: Normal / vertical acceleration disturbance ($m/s^2$)
- $\eta$: Infrastructure surface roughness / vibration index ($0.0 \le \eta \le 1.0$)

---

## 3. Kinematic Process Model
Given time step $\Delta t$, the non-linear state transition function $\mathbf{f}(\mathbf{x}_{k-1}, \Delta t)$ is governed by:

$$\begin{aligned}
p_{lat,k} &= p_{lat,k-1} + \left( \frac{v_{k-1} \Delta t}{R_{earth}} \right) \cdot \left( \frac{180}{\pi} \right) \\
p_{lng,k} &= p_{lng,k-1} + \left( \frac{v_{k-1} \Delta t}{R_{earth} \cos(p_{lat,k-1} \cdot \pi / 180)} \right) \cdot \left( \frac{180}{\pi} \right) \\
v_k &= \max(0, v_{k-1}) \\
a_{z,k} &= \gamma \cdot a_{z,k-1} \quad (\text{damping factor } \gamma = 0.85) \\
\eta_k &= \lambda_r \cdot \eta_{k-1} + (1 - \lambda_r) \cdot \min\left(1.0, \frac{|a_{z,k}|}{a_{threshold}}\right)
\end{aligned}$$
where $R_{earth} = 6,378,137\text{ m}$, $\lambda_r = 0.90$, and $a_{threshold} = 4.0\text{ m/s}^2$.

---

## 4. Unscented Transform (UT) Sigma Points
For state dimension $n = 5$, $2n + 1 = 11$ deterministic sigma points are computed:

$$\begin{aligned}
\mathbf{X}_0 &= \mathbf{x}_{k-1} \\
\mathbf{X}_i &= \mathbf{x}_{k-1} + \sqrt{n + \lambda} \cdot \left(\mathbf{L}\right)_i, \quad i = 1, \dots, n \\
\mathbf{X}_{i+n} &= \mathbf{x}_{k-1} - \sqrt{n + \lambda} \cdot \left(\mathbf{L}\right)_i, \quad i = 1, \dots, n
\end{aligned}$$
where $\mathbf{L} \mathbf{L}^T = \mathbf{P}_{k-1}$ is the Cholesky factorization of state covariance $\mathbf{P}$.

### Scaling Parameters
- $\alpha = 10^{-3}$ (determines spread of sigma points)
- $\beta = 2.0$ (optimal for Gaussian distributions)
- $\kappa = 0$
- $\lambda = \alpha^2 (n + \kappa) - n$

### Weights
$$\begin{aligned}
W_m^{(0)} &= \frac{\lambda}{n + \lambda} \\
W_c^{(0)} &= \frac{\lambda}{n + \lambda} + (1 - \alpha^2 + \beta) \\
W_m^{(i)} = W_c^{(i)} &= \frac{1}{2(n + \lambda)}, \quad i = 1, \dots, 2n
\end{aligned}$$

---

## 5. Adaptive Measurement Noise Formulation
The measurement vector $\mathbf{z}_k$ maps available telemetry:
$$\mathbf{z}_k = \left[ z_{lat}, z_{lng}, z_v, z_{az}, z_{vib} \right]^T$$

When GPS dropouts occur, the measurement dimension is dynamically reduced without halting the filter.

### Residual (Innovation)
$$\boldsymbol{\nu}_k = \mathbf{z}_k - \hat{\mathbf{z}}_k$$

### Sage-Husa Covariance Matching
$$\mathbf{R}_k = (1 - d_k) \mathbf{R}_{k-1} + d_k \left( \boldsymbol{\nu}_k \boldsymbol{\nu}_k^T - \mathbf{P}_{zz,k} \right)$$
where $d_k = \frac{1 - b}{1 - b^k}$ with forgetting factor $b = 0.95$. Eigenvalue clipping guarantees $\mathbf{R}_k \succ 0$.
