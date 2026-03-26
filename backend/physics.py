import numpy as np

class PhysicsEngine:
    def __init__(self):
        # Data stored column-wise or row-wise. We use parallel arrays for efficiency.
        # Max capacity for pre-allocation can improve performance, but we'll use dynamic resizing wrapper.
        self.capacity = 20000
        self.count = 0
        
        # ID to index mapping for O(1) lookups
        self.id_map = {}
        self.ids = [""] * self.capacity
        self.types = np.zeros(self.capacity, dtype=np.int8) # 1=SAT, 0=DEBRIS
        
        self.positions = np.zeros((self.capacity, 3), dtype=np.float64) # r (km)
        self.velocities = np.zeros((self.capacity, 3), dtype=np.float64) # v (km/s)
        self.fuel_kg = np.zeros(self.capacity, dtype=np.float64)
        
        # Constants
        self.EARTH_MU = 398600.4418 # km^3 / s^2
        self.EARTH_RADIUS = 6371.0 # km
        
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
                
                self.count += 1

    def _expand_arrays(self):
        """Double the capacity of the arrays if we hit the limit."""
        new_cap = self.capacity * 2
        self.positions = np.vstack((self.positions, np.zeros((self.capacity, 3))))
        self.velocities = np.vstack((self.velocities, np.zeros((self.capacity, 3))))
        self.types = np.append(self.types, np.zeros(self.capacity, dtype=np.int8))
        self.fuel_kg = np.append(self.fuel_kg, np.zeros(self.capacity, dtype=np.float64))
        self.ids.extend([""] * self.capacity)
        self.capacity = new_cap

    def compute_gravity(self, pos):
        """Compute acceleration due to point-mass Earth."""
        # a = -MU * r / |r|^3
        r_norm = np.linalg.norm(pos, axis=1, keepdims=True)
        # Avoid division by zero
        r_norm = np.maximum(r_norm, 1e-6)
        return -self.EARTH_MU * pos / (r_norm**3)

    def step(self, dt_seconds):
        """Advance the simulation by dt_seconds using Runge-Kutta 4th order."""
        if self.count == 0:
            return
            
        # Only process active elements
        pos = self.positions[:self.count]
        vel = self.velocities[:self.count]
        
        # RK4 Integration
        k1_v = self.compute_gravity(pos)
        k1_r = vel
        
        k2_v = self.compute_gravity(pos + 0.5 * dt_seconds * k1_r)
        k2_r = vel + 0.5 * dt_seconds * k1_v
        
        k3_v = self.compute_gravity(pos + 0.5 * dt_seconds * k2_r)
        k3_r = vel + 0.5 * dt_seconds * k2_v
        
        k4_v = self.compute_gravity(pos + dt_seconds * k3_r)
        k4_r = vel + dt_seconds * k3_v
        
        # Update state
        self.positions[:self.count] = pos + (dt_seconds / 6.0) * (k1_r + 2*k2_r + 2*k3_r + k4_r)
        self.velocities[:self.count] = vel + (dt_seconds / 6.0) * (k1_v + 2*k2_v + 2*k3_v + k4_v)

    def get_snapshot(self):
        """Return lists of sats and debris for frontend."""
        import math
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
                sats.append({
                    "id": self.ids[i],
                    "lat": float(lat),
                    "lon": float(lon),
                    "alt": float(r - self.EARTH_RADIUS),
                    "fuel_kg": float(self.fuel_kg[i]),
                    "status": "NOMINAL"
                })
            else:
                debris.append([
                    self.ids[i],
                    float(lat),
                    float(lon),
                    float(r - self.EARTH_RADIUS)
                ])
        return sats, debris
