"""
ingest_celestrak.py
Converts realistic Celestrak TLEs (Two-Line Elements) into the (r, v) state vectors
used by the ACM backend, and ingests them into the simulation.
"""

import requests
import re
from datetime import datetime, timezone
from sgp4.api import Satrec
from sgp4.api import WGS84, jday
import json

def parse_tles(file_path):
    """Parse a TLE file and yield (name, line1, line2)."""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
        
    for i in range(0, len(lines) - 2, 3):
        # Depending on the file format, the name might be on its own line
        name = lines[i]
        line1 = lines[i+1]
        line2 = lines[i+2]
        
        # Super simple check that lines start with 1 and 2
        if line1.startswith("1 ") and line2.startswith("2 "):
            yield name, line1, line2
        elif lines[i].startswith("1 ") and lines[i+1].startswith("2 "):
            # No name line, just 1 and 2
            yield "UNKNOWN", lines[i], lines[i+1]


def get_state_vector(line1, line2, dt):
    """Use SGP4 to compute position (km) and velocity (km/s) at datetime dt."""
    try:
        satellite = Satrec.twoline2rv(line1, line2)
        jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        e, r, v = satellite.sgp4(jd, fr)
        
        if e != 0:
            return None, None
            
        return r, v
    except Exception as e:
        return None, None


def main():
    # Target time exactly matches the simulation start time set in other scripts
    sim_time = datetime(2026, 3, 12, 8, 0, 0, tzinfo=timezone.utc)
    print(f"Propagating TLE orbits to target sim time: {sim_time}")
    
    objects = []
    
    # 1. Process Active Satellites (Limit to ~50 for the PS requirements)
    print("Parsing celestrak_active.tle...")
    sat_count = 0
    try:
        for name, l1, l2 in parse_tles("celestrak_active.tle"):
            r, v = get_state_vector(l1, l2, sim_time)
            if r is not None and v is not None:
                # Clean up name for ID
                clean_id = re.sub(r'[^A-Z0-9-]', '', name.upper().replace(" ", "-"))
                if not clean_id:
                    clean_id = f"SAT-{sat_count:04d}"
                    
                objects.append({
                    "id": clean_id,
                    "type": "SATELLITE",
                    "r": {"x": r[0], "y": r[1], "z": r[2]},
                    "v": {"x": v[0], "y": v[1], "z": v[2]},
                    "fuel_kg": 50.0  # Reset fuel to nominal start
                })
                sat_count += 1
                if sat_count >= 50:
                    break
    except FileNotFoundError:
        print("ERROR: celestrak_active.tle not found.")
        
    # 2. Process Debris (Limit to 10,000 to match stress test scale)
    print("Parsing celestrak_debris.tle...")
    deb_count = 0
    try:
        for name, l1, l2 in parse_tles("celestrak_debris.tle"):
            r, v = get_state_vector(l1, l2, sim_time)
            if r is not None and v is not None:
                # To prevent extremely long ID strings from real debris names
                cat_num = l1[2:7].strip() 
                clean_id = f"DEB-{cat_num}"
                
                objects.append({
                    "id": clean_id,
                    "type": "DEBRIS",
                    "r": {"x": r[0], "y": r[1], "z": r[2]},
                    "v": {"x": v[0], "y": v[1], "z": v[2]}
                })
                deb_count += 1
                # Standard limit
                if deb_count >= 10000:
                    break
    except FileNotFoundError:
        print("ERROR: celestrak_debris.tle not found.")

    print(f"\nGenerated {len(objects)} valid state vectors.")
    print(f"  - Satellites: {sat_count}")
    print(f"  - Debris:     {deb_count}")
    
    if len(objects) == 0:
        print("No objects to send!")
        return

    # 3. Form payload and save to JSON file as requested by the user
    payload = {
        "timestamp": "2026-03-12T08:00:00.000Z",
        "objects": objects
    }
    
    out_file = "celestrak_data.json"
    with open(out_file, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nSaved raw simulation data format to '{out_file}'!")
    
    # 4. Optional: Send to backend
    print("\nSending payload to backend (http://127.0.0.1:8000)...")
    try:
        res = requests.post("http://127.0.0.1:8000/api/telemetry", json=payload, timeout=60)
        print("Status:", res.status_code)
        print("Response:", res.json())
        print("\nSUCCESS! Open http://localhost:3000 and click RUN SIMULATION to use real Celestrak orbits.")
    except Exception as e:
        print("Error sending data:", e)

if __name__ == "__main__":
    main()
