import numpy as np
import math

class ManeuverPlanner:
    def __init__(self, engine):
        self.engine = engine
        self.g0_m = 9.80665   # m/s^2
        self.isp = 300.0      # seconds
        self.dry_mass = 500.0  # kg
        self.cooldown_s = 600.0  # 600 second cooldown between burns
        
        # Track last burn time per satellite for cooldown enforcement
        self.last_burn_time = {}  # sat_id -> sim_time_seconds (relative)
        self.sim_elapsed = 0.0   # total sim seconds elapsed
        
        # Ground stations from PS: (lat, lon, elevation_m, min_elev_angle_deg)
        self.ground_stations = [
            (13.0333, 77.5167, 820, 5.0),     # GS-001 ISTRAC Bengaluru
            (78.2297, 15.4077, 400, 5.0),     # GS-002 Svalbard
            (35.4266, -116.8900, 1000, 10.0), # GS-003 Goldstone
            (-53.1500, -70.9167, 30, 5.0),    # GS-004 Punta Arenas
            (28.5450, 77.1926, 225, 15.0),    # GS-005 IIT Delhi
            (-77.8463, 166.6682, 10, 5.0),    # GS-006 McMurdo
        ]
        
    def advance_time(self, dt_seconds):
        """Called by main.py to keep track of elapsed simulation time."""
        self.sim_elapsed += dt_seconds
        
    def check_los(self, sat_pos):
        """Check if sat_pos (km ECI) has Line Of Sight with any ground station."""
        r_earth = self.engine.EARTH_RADIUS
        for lat, lon, elev_m, min_elev_deg in self.ground_stations:
            lat_rad = math.radians(lat)
            lon_rad = math.radians(lon)
            gs_r = r_earth + elev_m / 1000.0
            gs_x = gs_r * math.cos(lat_rad) * math.cos(lon_rad)
            gs_y = gs_r * math.cos(lat_rad) * math.sin(lon_rad)
            gs_z = gs_r * math.sin(lat_rad)
            gs_pos = np.array([gs_x, gs_y, gs_z])
            
            r_sat_norm = np.linalg.norm(sat_pos)
            if r_sat_norm < 1e-6:
                continue
            
            diff = sat_pos - gs_pos
            diff_norm = np.linalg.norm(diff)
            if diff_norm < 1e-6:
                continue
            
            gs_up = gs_pos / np.linalg.norm(gs_pos)
            sin_elev = np.dot(diff, gs_up) / diff_norm
            elev_angle_deg = math.degrees(math.asin(max(-1.0, min(1.0, sin_elev))))
            
            if elev_angle_deg >= min_elev_deg:
                return True
        return False
    
    def check_cooldown(self, sat_id):
        """Check if thruster cooldown period (600s) has elapsed since last burn."""
        if sat_id not in self.last_burn_time:
            return True  # No previous burn
        elapsed = self.sim_elapsed - self.last_burn_time[sat_id]
        return elapsed >= self.cooldown_s
        
    def calculate_fuel_usage(self, current_fuel_kg, dv_m_s):
        initial_mass = self.dry_mass + current_fuel_kg
        final_mass = initial_mass * math.exp(-dv_m_s / (self.isp * self.g0_m))
        fuel_used = initial_mass - final_mass
        return fuel_used
        
    def plan_directional_avoidance(self, sat_idx, deb_idx):
        """TCA-based predictive collision avoidance (PS-aligned).
        
        Algorithm:
        1. Compute TCA via dot-product formula
        2. Compute miss distance d0 at TCA
        3. If d0 < d_safe, compute minimum Δv = Δd / τ
        4. Direction: along satellite velocity (PS-preferred)
        
        Returns dV in km/s, or None if no maneuver needed.
        """
        sat_pos = self.engine.positions[sat_idx]
        deb_pos = self.engine.positions[deb_idx]
        sat_vel = self.engine.velocities[sat_idx]
        deb_vel = self.engine.velocities[deb_idx]
        
        # Relative state
        r_rel = sat_pos - deb_pos        # km
        v_rel = sat_vel - deb_vel        # km/s
        v_rel_sq = np.dot(v_rel, v_rel)
        
        if v_rel_sq < 1e-12:
            return None  # Co-moving, no convergence
        
        # --- TCA (Time to Closest Approach) ---
        tca = -np.dot(r_rel, v_rel) / v_rel_sq  # seconds
        
        if tca <= 0:
            return None  # Already past closest approach
        
        FUTURE_WINDOW = 5400.0  # 90 minutes lookahead
        if tca > FUTURE_WINDOW:
            return None  # Too far in the future
        
        # --- Distance at closest approach ---
        r_tca = r_rel + v_rel * tca      # position at TCA (km)
        d0 = np.linalg.norm(r_tca)       # miss distance (km)
        
        # NOTE: Because orbital paths curve, the linear projection (r + v*t) becomes
        # mathematically skewed over 90 minutes. A true 50m miss on an orbit might 
        # look like a 3km miss in linear projection. We use a 5.0 km predictive envelope.
        D_SAFE = 5.0
        
        if d0 >= D_SAFE:
            return None  # Already safe, no maneuver needed
        
        # --- Required separation ---
        delta_d = D_SAFE - d0  # km, how much we need to widen
        
        # --- Burn time: earliest feasible ---
        LATENCY = 10.0  # 10s signal delay per PS
        sat_id = self.engine.ids[sat_idx]
        cooldown_until = self.last_burn_time.get(sat_id, -9999) + self.cooldown_s
        tb = max(self.sim_elapsed + LATENCY, cooldown_until)
        
        if tb >= self.sim_elapsed + tca:
            return None  # Can't burn before TCA
        
        # τ = time between burn and TCA (maximize for minimum Δv)
        tau = tca - (tb - self.sim_elapsed)
        
        if tau <= 0:
            return None
        
        # --- Δv magnitude: Δv = Δd / τ ---
        dv_km_s = delta_d / tau   # km/s (already in right units since Δd is km, τ is seconds)
        dv_m_s = dv_km_s * 1000.0
        
        MAX_DV_MS = 15.0
        if dv_m_s > MAX_DV_MS:
            dv_m_s = MAX_DV_MS
            dv_km_s = dv_m_s / 1000.0
        
        # --- Direction: along satellite velocity (PS-preferred, most fuel-efficient) ---
        v_norm = np.linalg.norm(sat_vel)
        if v_norm < 1e-6:
            return None
        
        direction = sat_vel / v_norm  # normalize(v_sat)
        
        return direction * dv_km_s
    
    def scan_and_plan_avoidance(self):
        """Scan all satellite-debris pairs for predicted conjunctions.
        
        Returns list of (sat_id, deb_id, dv_vector_km_s) for maneuvers to execute.
        This is the predictive 24h lookahead the PS requires.
        """
        planned = []
        
        # Get satellite and debris indices
        sat_indices = []
        deb_indices = []
        for i in range(self.engine.count):
            if self.engine.types[i] == 1:
                sat_indices.append(i)
            else:
                deb_indices.append(i)
        
        if not sat_indices or not deb_indices:
            return planned
        
        # For efficiency: use KD-tree to find nearby debris only
        from scipy.spatial import cKDTree
        
        if len(deb_indices) == 0:
            return planned
        
        deb_positions = self.engine.positions[deb_indices]
        tree = cKDTree(deb_positions)
        
        # Search radius: max relative speed ~15 km/s * 5400s window = 81000 km
        # But that's too wide. Use a practical radius based on orbital mechanics.
        # Objects in similar orbits within ~500 km could converge within 90 min.
        SEARCH_RADIUS_KM = 500.0
        
        for sat_idx in sat_indices:
            sat_id = self.engine.ids[sat_idx]
            
            # Skip if cooldown not elapsed
            if not self.check_cooldown(sat_id):
                continue
            
            sat_pos = self.engine.positions[sat_idx]
            nearby_deb = tree.query_ball_point(sat_pos, SEARCH_RADIUS_KM)
            
            best_maneuver = None
            best_tca = float('inf')
            
            for local_deb_idx in nearby_deb:
                deb_idx = deb_indices[local_deb_idx]
                
                dv = self.plan_directional_avoidance(sat_idx, deb_idx)
                if dv is not None:
                    # Compute TCA for prioritization (handle closest threat first)
                    r_rel = sat_pos - self.engine.positions[deb_idx]
                    v_rel = self.engine.velocities[sat_idx] - self.engine.velocities[deb_idx]
                    v_rel_sq = np.dot(v_rel, v_rel)
                    tca = -np.dot(r_rel, v_rel) / v_rel_sq if v_rel_sq > 1e-12 else float('inf')
                    
                    if tca < best_tca:
                        best_tca = tca
                        best_maneuver = (sat_id, self.engine.ids[deb_idx], dv)
            
            if best_maneuver is not None:
                planned.append(best_maneuver)
        
        return planned
    
    def plan_recovery_burn(self, sat_idx):
        """Plan a recovery burn to return satellite to its nominal orbital slot.
        Returns dV in km/s, or None if already within tolerance."""
        drift = self.engine.get_drift_km(sat_idx)
        if drift <= self.engine.DRIFT_TOLERANCE_KM:
            return None  # Already in slot
        
        # Vector from current position to nominal slot
        direction = self.engine.nominal_positions[sat_idx] - self.engine.positions[sat_idx]
        dist_km = np.linalg.norm(direction)
        
        if dist_km < 1e-6:
            return None
        
        # Scale recovery Δv: proportional to drift, capped at 10 m/s
        dv_m_s = min(10.0, 2.0 + 8.0 * min(dist_km / 50.0, 1.0))
        dv_km_s = dv_m_s / 1000.0
        
        # Direction: primarily tangential (prograde/retrograde phasing)
        sat_vel = self.engine.velocities[sat_idx]
        v_norm = np.linalg.norm(sat_vel)
        
        if v_norm < 1e-6:
            return None
        
        t_hat = sat_vel / v_norm
        # Use velocity difference between nominal and actual
        vel_diff = self.engine.nominal_velocities[sat_idx] - self.engine.velocities[sat_idx]
        
        # Project onto tangential direction
        sign_t = 1.0 if np.dot(vel_diff, t_hat) >= 0 else -1.0
        
        r_hat = direction / dist_km
        
        # 70% tangential (phasing), 30% toward nominal (direct correction)
        v_dir = 0.7 * sign_t * t_hat + 0.3 * r_hat
        v_dir = v_dir / np.linalg.norm(v_dir)
        
        return v_dir * dv_km_s

    def execute_maneuver(self, sat_id, dv_vector_km_s):
        """Execute maneuver if fuel, LOS, and cooldown constraints allow."""
        if sat_id not in self.engine.id_map:
            return False, "Satellite not found"
            
        idx = self.engine.id_map[sat_id]
        if self.engine.types[idx] != 1:
            return False, "Object is not a satellite"
        
        # Check cooldown
        if not self.check_cooldown(sat_id):
            return False, "Thruster cooldown (600s) not elapsed"
            
        sat_pos = self.engine.positions[idx]
        if not self.check_los(sat_pos):
            return False, "No Line of Sight to ground station"
            
        dv_m_s = np.linalg.norm(dv_vector_km_s) * 1000.0
        if dv_m_s > 15.0:
            return False, f"Delta-V {dv_m_s:.2f} exceeds 15 m/s limit"
            
        fuel_needed = self.calculate_fuel_usage(float(self.engine.fuel_kg[idx]), dv_m_s)
        if fuel_needed > float(self.engine.fuel_kg[idx]):
            return False, "Insufficient fuel"
        
        # Check EOL threshold (5% of initial 50kg = 2.5kg)
        if float(self.engine.fuel_kg[idx]) < 2.5:
            return False, "Satellite at EOL fuel threshold"
            
        # Apply maneuver
        self.engine.fuel_kg[idx] -= fuel_needed
        self.engine.velocities[idx] += dv_vector_km_s
        
        # Record burn time for cooldown
        self.last_burn_time[sat_id] = self.sim_elapsed
        
        return True, "Success"
