"""
simulate_data2.py — Same scale as simulate_data.py (50 sats + 10,000 debris)
but injects 8 guaranteed collision threats that WILL trigger TCA-based COLA.

Key fix: threat debris shares the same orbital plane as the target satellite,
offset only in cross-track, with a controlled closing velocity ensuring
miss distance < 1 km at TCA.
"""
import requests
import random
import uuid
import math
import numpy as np

def generate_telemetry(num_sats=50, num_debris=10000, num_threats=8):
    objects = []
    sat_list = []
    
    def generate_random_object(prefix, r_min, r_max, is_sat=False):
        r_mag = random.uniform(r_min, r_max)
        theta = random.uniform(0, 2 * math.pi)
        phi = math.acos(random.uniform(-1, 1))
        
        rx = r_mag * math.sin(phi) * math.cos(theta)
        ry = r_mag * math.sin(phi) * math.sin(theta)
        rz = r_mag * math.cos(phi)
        
        ux = random.uniform(-1, 1)
        uy = random.uniform(-1, 1)
        uz = random.uniform(-1, 1)
        
        cx = ry * uz - rz * uy
        cy = rz * ux - rx * uz
        cz = rx * uy - ry * ux
        
        c_mag = math.sqrt(cx*cx + cy*cy + cz*cz)
        if c_mag < 0.001:
            cx, cy, cz = 1.0, 0.0, 0.0
            c_mag = 1.0
            
        v_mag = math.sqrt(398600.4418 / r_mag)
        vx = (cx / c_mag) * v_mag
        vy = (cy / c_mag) * v_mag
        vz = (cz / c_mag) * v_mag
        
        obj = {
            "id": f"{prefix}-{str(uuid.uuid4())[:8].upper()}",
            "type": "SATELLITE" if is_sat else "DEBRIS",
            "r": {"x": rx, "y": ry, "z": rz},
            "v": {"x": vx, "y": vy, "z": vz}
        }
        
        if is_sat:
            obj["fuel_kg"] = 50.0
            
        return obj

    # Generate satellites
    for _ in range(num_sats):
        obj = generate_random_object("SAT", 6600, 7200, True)
        objects.append(obj)
        sat_list.append(obj)
        
    # Generate random debris (safe background)
    for _ in range(num_debris - num_threats):
        objects.append(generate_random_object("DEB", 6500, 7300, False))
    
    # Inject guaranteed collision threats
    # Strategy: place debris on same orbit as satellite, just slightly ahead
    # in the velocity direction, with a tiny closing velocity.
    # This guarantees d0 ≈ 0 at TCA and the TCA algorithm MUST respond.
    threat_targets = random.sample(sat_list, min(num_threats, len(sat_list)))
    
    for i, sat in enumerate(threat_targets):
        sx = sat["r"]["x"]
        sy = sat["r"]["y"]
        sz = sat["r"]["z"]
        svx = sat["v"]["x"]
        svy = sat["v"]["y"]
        svz = sat["v"]["z"]
        
        s_pos = np.array([sx, sy, sz])
        s_vel = np.array([svx, svy, svz])
        v_mag = np.linalg.norm(s_vel)
        v_hat = s_vel / v_mag
        r_hat = s_pos / np.linalg.norm(s_pos)
        
        # Place debris 3-6 km AHEAD in the velocity direction (same orbit)
        offset_km = random.uniform(3.0, 6.0)
        deb_pos = s_pos + v_hat * offset_km
        
        # Debris velocity: same circular orbit speed, but slightly slower
        # so the satellite CATCHES UP to it (closing speed ~20-30 m/s)
        closing_speed_km_s = random.uniform(0.02, 0.03)  # 20-30 m/s
        deb_vel = s_vel - v_hat * closing_speed_km_s  # slightly slower
        
        # Add tiny cross-track offset (0.05 km = 50m) for near-miss
        c_hat = np.cross(v_hat, r_hat)
        c_hat = c_hat / np.linalg.norm(c_hat)
        deb_pos = deb_pos + c_hat * 0.05  # 50m cross-track offset
        
        # Compute expected TCA and miss distance
        r_rel = s_pos - deb_pos
        v_rel = s_vel - deb_vel
        v_rel_sq = np.dot(v_rel, v_rel)
        tca = -np.dot(r_rel, v_rel) / v_rel_sq
        r_tca = r_rel + v_rel * tca
        d0 = np.linalg.norm(r_tca)
        
        deb_id = f"DEB-THR-{i+1:03d}"
        print(f"  {deb_id} -> {sat['id']}: ahead={offset_km:.0f}km, closing={closing_speed_km_s*1000:.0f}m/s, TCA={tca:.0f}s, miss={d0*1000:.0f}m")
        
        objects.append({
            "id": deb_id,
            "type": "DEBRIS",
            "r": {"x": float(deb_pos[0]), "y": float(deb_pos[1]), "z": float(deb_pos[2])},
            "v": {"x": float(deb_vel[0]), "y": float(deb_vel[1]), "z": float(deb_vel[2])}
        })
    
    return objects


def main():
    random.seed(2026)
    print("Generating 10,050 objects (50 sats + 10,000 debris + 8 collision threats)...")
    data = generate_telemetry(50, 10000, 8)
    payload = {
        "timestamp": "2026-03-12T08:00:00.000Z",
        "objects": data
    }
    
    print(f"\nSending {len(data)} objects to backend...")
    try:
        res = requests.post("http://127.0.0.1:8000/api/telemetry", json=payload, timeout=30)
        print("Response:", res.json())
    except Exception as e:
        print("Error:", e)
    
    print("\nDone! Open http://localhost:3000 and click RUN SIMULATION.")
    print("Maneuvers should appear within the first 1-2 steps.")

if __name__ == "__main__":
    main()
