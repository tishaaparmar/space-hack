import numpy as np
import math

class PhysicsEngine:
    def __init__(self):
        self.capacity = 20000
        self.count = 0
        
        # ID to index mapping for O(1) lookups
        self.id_map = {}
        self.ids = [""] * self.capacity
        self.types = np.zeros(self.capacity, dtype=np.int8)  # 1=SAT, 0=DEBRIS
        
        self.positions = np.zeros((self.capacity, 3), dtype=np.float64)
        self.velocities = np.zeros((self.capacity, 3), dtype=np.float64)
        self.fuel_kg = np.zeros(self.capacity, dtype=np.float64)
        
        # Nominal orbital slots (for station-keeping / uptime tracking)
        self.nominal_positions = np.zeros((self.capacity, 3), dtype=np.float64)
        self.nominal_velocities = np.zeros((self.capacity, 3), dtype=np.float64)
        
        # Uptime tracking per satellite
        self.uptime_seconds = np.zeros(self.capacity, dtype=np.float64)
        self.outage_seconds = np.zeros(self.capacity, dtype=np.float64)
        
        # Station-keeping tolerance
        self.DRIFT_TOLERANCE_KM = 10.0
        
        # Constants
        self.EARTH_MU = 398600.4418
        self.EARTH_RADIUS = 6378.137
        self.J2 = 1.08263e-3
        
    def ingest_objects(self, objects_data):
        """Ingest new or updated objects."""
        for obj in objects_data:
            obj_id = obj.id
            obj_type = 1 if obj.type == "SATELLITE" else 0
            rx, ry, rz = obj.r.x, obj.r.y, obj.r.z
            vx, vy, vz = obj.v.x, obj.v.y, obj.v.z
            
            if obj_id in self.id_map:
                idx = self.id_map[obj_id]
                self.positions[idx] = [rx, ry, rz]
                self.velocities[idx] = [vx, vy, vz]
            else:
                if self.count >= self.capacity:
                    self._expand_arrays()
                idx = self.count
                self.id_map[obj_id] = idx
                self.ids[idx] = obj_id
                self.types[idx] = obj_type
                
                self.positions[idx] = [rx, ry, rz]
                self.velocities[idx] = [vx, vy, vz]
                self.fuel_kg[idx] = obj.fuel_kg if obj.fuel_kg is not None else 0.0
                
                # Store initial position as nominal slot (for satellites)
                if obj_type == 1:
                    self.nominal_positions[idx] = [rx, ry, rz]
                    self.nominal_velocities[idx] = [vx, vy, vz]
                
                self.count += 1

    def _expand_arrays(self):
        """Double the capacity of the arrays if we hit the limit."""
        new_cap = self.capacity * 2
        self.positions = np.vstack((self.positions, np.zeros((self.capacity, 3))))
        self.velocities = np.vstack((self.velocities, np.zeros((self.capacity, 3))))
        self.types = np.append(self.types, np.zeros(self.capacity, dtype=np.int8))
        self.fuel_kg = np.append(self.fuel_kg, np.zeros(self.capacity, dtype=np.float64))
        self.nominal_positions = np.vstack((self.nominal_positions, np.zeros((self.capacity, 3))))
        self.nominal_velocities = np.vstack((self.nominal_velocities, np.zeros((self.capacity, 3))))
        self.uptime_seconds = np.append(self.uptime_seconds, np.zeros(self.capacity, dtype=np.float64))
        self.outage_seconds = np.append(self.outage_seconds, np.zeros(self.capacity, dtype=np.float64))
        self.ids.extend([""] * self.capacity)
        self.capacity = new_cap

    def compute_acceleration(self, pos):
        """Compute acceleration with J2 perturbation."""
        r_sq = np.sum(pos * pos, axis=1, keepdims=True)
        r_norm = np.sqrt(r_sq)
        r_norm = np.maximum(r_norm, 1e-6)
        
        r_norm_cubed = r_norm ** 3
        a_twobody = -self.EARTH_MU * pos / r_norm_cubed
        
        r_norm_fifth = r_norm ** 5
        z = pos[:, 2:3]
        z_sq = z * z
        factor = 1.5 * self.J2 * self.EARTH_MU * (self.EARTH_RADIUS ** 2) / r_norm_fifth
        five_z2_over_r2 = 5.0 * z_sq / r_sq
        
        a_j2 = np.zeros_like(pos)
        a_j2[:, 0:1] = factor * pos[:, 0:1] * (five_z2_over_r2 - 1.0)
        a_j2[:, 1:2] = factor * pos[:, 1:2] * (five_z2_over_r2 - 1.0)
        a_j2[:, 2:3] = factor * pos[:, 2:3] * (five_z2_over_r2 - 3.0)
        
        return a_twobody + a_j2

    def step(self, dt_seconds):
        """Advance simulation using RK4 with sub-stepping. Also propagates nominal slots."""
        if self.count == 0:
            return
        
        max_substep = 60.0
        remaining = dt_seconds
        while remaining > 0:
            h = min(remaining, max_substep)
            self._rk4_step(h)
            self._propagate_nominals(h)
            remaining -= h
        
        # Update uptime tracking for satellites
        self._update_uptime(dt_seconds)
    
    def _rk4_step(self, dt):
        """Single RK4 integration step for all objects."""
        pos = self.positions[:self.count]
        vel = self.velocities[:self.count]
        
        k1_v = self.compute_acceleration(pos)
        k1_r = vel
        k2_v = self.compute_acceleration(pos + 0.5 * dt * k1_r)
        k2_r = vel + 0.5 * dt * k1_v
        k3_v = self.compute_acceleration(pos + 0.5 * dt * k2_r)
        k3_r = vel + 0.5 * dt * k2_v
        k4_v = self.compute_acceleration(pos + dt * k3_r)
        k4_r = vel + dt * k3_v
        
        self.positions[:self.count] = pos + (dt / 6.0) * (k1_r + 2*k2_r + 2*k3_r + k4_r)
        self.velocities[:self.count] = vel + (dt / 6.0) * (k1_v + 2*k2_v + 2*k3_v + k4_v)
    
    def _propagate_nominals(self, dt):
        """Propagate nominal slots using same physics as actual propagation.
        
        For non-maneuvered satellites, nominals should track actuals exactly.
        We propagate them with the same RK4 to ensure consistency, using .copy()
        to prevent aliasing issues.
        """
        sat_mask = self.types[:self.count] == 1
        if not np.any(sat_mask):
            return
        
        sat_indices = np.where(sat_mask)[0]
        pos = self.nominal_positions[sat_indices].copy()
        vel = self.nominal_velocities[sat_indices].copy()
        
        # RK4 for nominals (identical physics)
        k1_v = self.compute_acceleration(pos)
        k1_r = vel.copy()
        k2_v = self.compute_acceleration(pos + 0.5 * dt * k1_r)
        k2_r = vel + 0.5 * dt * k1_v
        k3_v = self.compute_acceleration(pos + 0.5 * dt * k2_r)
        k3_r = vel + 0.5 * dt * k2_v
        k4_v = self.compute_acceleration(pos + dt * k3_r)
        k4_r = vel + dt * k3_v
        
        self.nominal_positions[sat_indices] = pos + (dt / 6.0) * (k1_r + 2*k2_r + 2*k3_r + k4_r)
        self.nominal_velocities[sat_indices] = vel + (dt / 6.0) * (k1_v + 2*k2_v + 2*k3_v + k4_v)
    
    def _update_uptime(self, dt_seconds):
        """Track uptime: satellite within 10km of nominal slot = uptime, else outage."""
        for i in range(self.count):
            if self.types[i] != 1:
                continue
            drift = self.get_drift_km(i)
            if drift <= self.DRIFT_TOLERANCE_KM:
                self.uptime_seconds[i] += dt_seconds
            else:
                self.outage_seconds[i] += dt_seconds
    
    def get_drift_km(self, idx):
        """Get drift distance (km) from nominal slot."""
        diff = self.positions[idx] - self.nominal_positions[idx]
        return float(np.linalg.norm(diff))
    
    def get_uptime_pct(self, idx):
        """Get uptime percentage for a satellite."""
        total = self.uptime_seconds[idx] + self.outage_seconds[idx]
        if total < 1e-6:
            return 100.0
        return float(self.uptime_seconds[idx] / total * 100.0)

    def get_snapshot(self):
        """Return lists of sats and debris for frontend with enriched data."""
        sats = []
        debris = []
        for i in range(self.count):
            x, y, z = self.positions[i]
            r = math.sqrt(x*x + y*y + z*z)
            if r < 1e-6:
                continue
            lat = math.asin(z / r) * (180.0 / math.pi)
            lon = math.atan2(y, x) * (180.0 / math.pi)
            
            if self.types[i] == 1:
                drift = self.get_drift_km(i)
                uptime_pct = self.get_uptime_pct(i)
                fuel = float(self.fuel_kg[i])
                
                # Status based on drift and fuel
                if fuel < 2.5:  # 5% of 50kg
                    status = "EOL"
                elif drift > self.DRIFT_TOLERANCE_KM:
                    status = "DRIFTING"
                else:
                    status = "NOMINAL"
                
                sats.append({
                    "id": self.ids[i],
                    "lat": float(lat),
                    "lon": float(lon),
                    "alt": float(r - self.EARTH_RADIUS),
                    "fuel_kg": fuel,
                    "status": status,
                    "drift_km": float(drift),
                    "uptime_pct": float(uptime_pct)
                })
            else:
                debris.append([
                    self.ids[i],
                    float(lat),
                    float(lon),
                    float(r - self.EARTH_RADIUS)
                ])
        return sats, debris
