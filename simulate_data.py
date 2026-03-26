import requests
import random
import uuid
import math

def generate_telemetry(num_sats=50, num_debris=10000):
    objects = []
    
    def generate_object(prefix, r_min, r_max, is_sat=False):
        # 1. Random position on sphere
        r_mag = random.uniform(r_min, r_max)
        theta = random.uniform(0, 2 * math.pi)
        phi = math.acos(random.uniform(-1, 1))
        
        rx = r_mag * math.sin(phi) * math.cos(theta)
        ry = r_mag * math.sin(phi) * math.sin(theta)
        rz = r_mag * math.cos(phi)
        
        # 2. Random velocity perpendicular to r
        ux = random.uniform(-1, 1)
        uy = random.uniform(-1, 1)
        uz = random.uniform(-1, 1)
        
        # Cross product r x u
        cx = ry * uz - rz * uy
        cy = rz * ux - rx * uz
        cz = rx * uy - ry * ux
        
        c_mag = math.sqrt(cx*cx + cy*cy + cz*cz)
        if c_mag < 0.001:
            cx, cy, cz = 1.0, 0.0, 0.0
            c_mag = 1.0
            
        # Velocity magnitude for circular orbit = sqrt(MU/r)
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
            obj["mass_kg"] = 500.0
            obj["fuel_kg"] = 50.0
            
        return obj

    for _ in range(num_sats):
        objects.append(generate_object("SAT", 6600, 7200, True))
        
    for _ in range(num_debris):
        objects.append(generate_object("DEB", 6500, 7300, False))
        
    return objects


def main():
    print("Generating 10,050 objects with proper spherical orbital dynamics...")
    data = generate_telemetry(50, 10000)
    payload = {"objects": data}
    
    print("Sending to backend (http://localhost:8000/api/telemetry)...")
    try:
        res = requests.post("http://127.0.0.1:8000/api/telemetry", json=payload, timeout=20)
        print("Response:", res.json())
    except Exception as e:
        print("Error sending telemetry:", e)

if __name__ == "__main__":
    main()
