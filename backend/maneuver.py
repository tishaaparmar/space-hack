import numpy as np
import math

class ManeuverPlanner:
    def __init__(self, engine):
        self.engine = engine
        self.g0_m = 9.80665 # m/s^2
        self.isp = 300.0 # seconds
        self.dry_mass = 500.0 # kg
        
        # Ground stations (lat, lon)
        self.ground_stations = [
            (34.0, -118.0), # LA
            (51.5, -0.1),   # London
            (35.0, 139.0)   # Tokyo
        ]
        
    def check_los(self, sat_pos):
        """Check if sat_pos (km) has Line Of Sight with any ground station."""
        r_earth = self.engine.EARTH_RADIUS
        for lat, lon in self.ground_stations:
            lat_rad = math.radians(lat)
            lon_rad = math.radians(lon)
            gs_x = r_earth * math.cos(lat_rad) * math.cos(lon_rad)
            gs_y = r_earth * math.cos(lat_rad) * math.sin(lon_rad)
            gs_z = r_earth * math.sin(lat_rad)
            gs_pos = np.array([gs_x, gs_y, gs_z])
            
            r_sat_norm = np.linalg.norm(sat_pos)
            if r_sat_norm < 1e-6:
                continue
                
            cos_theta = np.dot(gs_pos, sat_pos) / (r_earth * r_sat_norm)
            
            # Horizon threshold
            if cos_theta > (r_earth / r_sat_norm):
                return True
        return False
        
    def calculate_fuel_usage(self, current_fuel_kg, dv_m_s):
        initial_mass = self.dry_mass + current_fuel_kg
        final_mass = initial_mass * math.exp(-dv_m_s / (self.isp * self.g0_m))
        fuel_used = initial_mass - final_mass
        return fuel_used
        
    def plan_directional_avoidance(self, sat_idx, deb_idx):
        """Plan a dynamic directional maneuver vector to avoid collision. Returns dV in km/s"""
        sat_pos = self.engine.positions[sat_idx]
        deb_pos = self.engine.positions[deb_idx]
        sat_vel = self.engine.velocities[sat_idx]
        
        # Distance to debris
        direction = sat_pos - deb_pos
        dist_km = np.linalg.norm(direction)
        
        # Step 1: Dynamic dV magnitude (max 15 m/s, min 2 m/s based on 100km threshold)
        dv_m_s = max(2.0, 15.0 * (1.0 - min(dist_km / 100.0, 1.0)))
        dv_km_s = dv_m_s / 1000.0
        
        # Step 2: In-track + Radial direction preference
        v_norm = np.linalg.norm(sat_vel)
        r_norm = np.linalg.norm(sat_pos)
        
        if v_norm < 1e-6 or r_norm < 1e-6 or dist_km < 1e-6:
            v_dir = np.array([1.0, 0.0, 0.0])
        else:
            t_hat = sat_vel / v_norm  # Tangential
            r_hat = sat_pos / r_norm  # Radial
            
            # c_dir points from debris TO satellite
            sign_t = 1.0 if np.dot(direction, t_hat) >= 0 else -1.0
            sign_r = 1.0 if np.dot(direction, r_hat) >= 0 else -1.0
            
            # 80% tangential (most efficient for SMA change), 20% radial (immediate separation)
            v_dir = 0.8 * sign_t * t_hat + 0.2 * sign_r * r_hat
            v_dir = v_dir / np.linalg.norm(v_dir)
            
        return v_dir * dv_km_s

    def execute_maneuver(self, sat_id, dv_vector_km_s):
        """Execute maneuver if fuel and LOS constraints allow."""
        if sat_id not in self.engine.id_map:
            return False, "Satellite not found"
            
        idx = self.engine.id_map[sat_id]
        if self.engine.types[idx] != 1:
            return False, "Object is not a satellite"
            
        sat_pos = self.engine.positions[idx]
        if not self.check_los(sat_pos):
            return False, "No Line of Sight to ground station"
            
        dv_m_s = np.linalg.norm(dv_vector_km_s) * 1000.0
        # Re-enforcing the realistic 15 m/s physical threshold per Hackathon constraints
        if dv_m_s > 15.0:
            return False, f"Delta-V {dv_m_s:.2f} exceeds 15 m/s limit"
            
        fuel_needed = self.calculate_fuel_usage(self.engine.fuel_kg[idx], dv_m_s)
        if fuel_needed > self.engine.fuel_kg[idx]:
            return False, "Insufficient fuel"
            
        # Apply maneuver
        self.engine.fuel_kg[idx] -= fuel_needed
        self.engine.velocities[idx] += dv_vector_km_s
        return True, "Success"
