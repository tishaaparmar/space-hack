"""
Compare both COLA approaches head-to-head:
- TCA-based (your algorithm): predictive, minimum Δv = Δd/τ
- Old reactive: checks current frame only, uses heuristic Δv

Uses debris approaching from ~30km out on crossing trajectories,
giving the TCA algorithm time to act early with lower Δv.
"""
import requests
import json
import math
import numpy as np

BASE = "http://localhost:8000"

def eci_from_latlon(lat_deg, lon_deg, alt_km):
    r = 6378.137 + alt_km
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    x = r * math.cos(lat) * math.cos(lon)
    y = r * math.cos(lat) * math.sin(lon)
    z = r * math.sin(lat)
    return np.array([x, y, z])

def circular_velocity(pos):
    mu = 398600.4418
    r = np.linalg.norm(pos)
    v_mag = math.sqrt(mu / r)
    # Perpendicular to position, in equatorial plane tendency
    cx = -pos[1]
    cy = pos[0]
    cz = 0.0
    c_mag = math.sqrt(cx**2 + cy**2 + cz**2)
    if c_mag < 1e-6:
        return np.array([v_mag, 0.0, 0.0])
    return np.array([cx/c_mag*v_mag, cy/c_mag*v_mag, cz/c_mag*v_mag])

print("=" * 70)
print("  TCA-BASED COLA TEST: Debris approaching from ~20-30 km out")
print("=" * 70)

objects = []

# 5 satellites
sats = [
    ("SAT-TCA-01", 28.5, 77.2, 400, 50.0),
    ("SAT-TCA-02", 13.0, 77.5, 420, 45.0),
    ("SAT-TCA-03", 35.4, -116.9, 380, 38.0),
    ("SAT-TCA-04", 78.2, 15.4, 410, 40.0),
    ("SAT-TCA-05", 40.0, -74.0, 400, 42.0),
]

sat_positions = {}
sat_velocities = {}

for sid, lat, lon, alt, fuel in sats:
    pos = eci_from_latlon(lat, lon, alt)
    vel = circular_velocity(pos)
    sat_positions[sid] = pos
    sat_velocities[sid] = vel
    objects.append({
        "id": sid, "type": "SATELLITE",
        "r": {"x": float(pos[0]), "y": float(pos[1]), "z": float(pos[2])},
        "v": {"x": float(vel[0]), "y": float(vel[1]), "z": float(vel[2])},
        "fuel_kg": fuel
    })

# Create threat debris approaching on crossing trajectories
# Key: place them 20-30 km away, heading TOWARD the satellite
# TCA should be ~300-600 seconds away (5-10 minutes)

threats = []
for i, (sid, lat, lon, alt, fuel) in enumerate(sats[:3]):  # 3 threats
    sat_pos = sat_positions[sid]
    sat_vel = sat_velocities[sid]
    
    # Debris coming from 25 km away, on a crossing orbit
    # Place it ~25km radially offset, with velocity directed toward satellite
    v_hat = sat_vel / np.linalg.norm(sat_vel)
    r_hat = sat_pos / np.linalg.norm(sat_pos)
    
    # Cross-track direction
    c_hat = np.cross(v_hat, r_hat)
    c_hat = c_hat / np.linalg.norm(c_hat)
    
    # Debris positioned 25 km in cross-track direction
    offset_km = 25.0
    deb_pos = sat_pos + c_hat * offset_km
    
    # Debris velocity: circular orbit + component toward satellite (-c_hat * approach_speed)
    deb_vel = circular_velocity(deb_pos) - c_hat * 0.05  # 50 m/s closing in cross-track
    
    deb_id = f"DEB-XING-{i+1:03d}"
    
    # Compute expected TCA
    r_rel = sat_pos - deb_pos
    v_rel = sat_vel - deb_vel
    tca_expected = -np.dot(r_rel, v_rel) / np.dot(v_rel, v_rel)
    r_tca = r_rel + v_rel * tca_expected
    d0 = np.linalg.norm(r_tca)
    
    print(f"  {deb_id} -> {sid}: offset={offset_km}km, TCA≈{tca_expected:.0f}s, miss≈{d0:.3f}km")
    
    threats.append(deb_id)
    objects.append({
        "id": deb_id, "type": "DEBRIS",
        "r": {"x": float(deb_pos[0]), "y": float(deb_pos[1]), "z": float(deb_pos[2])},
        "v": {"x": float(deb_vel[0]), "y": float(deb_vel[1]), "z": float(deb_vel[2])}
    })

# Add 50 background debris
import random
random.seed(42)
for i in range(50):
    lat = random.uniform(-70, 70)
    lon = random.uniform(-180, 180)
    alt = random.uniform(300, 600)
    pos = eci_from_latlon(lat, lon, alt)
    vel = circular_velocity(pos)
    objects.append({
        "id": f"DEB-BG-{i:04d}", "type": "DEBRIS",
        "r": {"x": float(pos[0]), "y": float(pos[1]), "z": float(pos[2])},
        "v": {"x": float(vel[0]+random.uniform(-0.1,0.1)), "y": float(vel[1]+random.uniform(-0.1,0.1)), "z": float(vel[2]+random.uniform(-0.1,0.1))}
    })

print(f"\n[1] Ingesting {len(objects)} objects...")
r = requests.post(f"{BASE}/api/telemetry", json={
    "timestamp": "2026-03-12T08:00:00.000Z",
    "objects": objects
})
data = r.json()
print(f"    Status: {data['status']} | CDM warnings: {data['active_cdm_warnings']}")

# Run simulation in short steps to catch the predictive maneuvers
print(f"\n[2] Running 20 x 30s steps (10 minutes of sim time)...")
total_col = 0
total_man = 0
for step in range(20):
    r = requests.post(f"{BASE}/api/simulate/step", json={"step_seconds": 30})
    s = r.json()
    total_col += s["collisions_detected"]
    total_man += s["maneuvers_executed"]
    tags = ""
    if s["collisions_detected"] > 0: tags += " << COLLISION!"
    if s["maneuvers_executed"] > 0: tags += " << MANEUVER!"
    if tags:
        print(f"    Step {step+1:2d}: t={s['new_timestamp']} | col={s['collisions_detected']} | man={s['maneuvers_executed']}{tags}")

# Fetch final snapshot
print(f"\n[3] Fetching snapshot...")
r = requests.get(f"{BASE}/api/visualization/snapshot")
snap = r.json()

print(f"\n{'='*70}")
print(f"  RESULTS (TCA-BASED ALGORITHM)")
print(f"{'='*70}")
print(f"  Total collisions detected: {total_col}")
print(f"  Total maneuvers executed:  {total_man}")
print(f"  Total Δv consumed:         {snap['fleet_stats']['total_dv_consumed_ms']:.2f} m/s")
print(f"  Fleet uptime:              {snap['fleet_stats']['fleet_uptime_pct']:.1f}%")

if snap.get("maneuvers"):
    print(f"\n  MANEUVER DETAILS:")
    for m in snap["maneuvers"]:
        dv_ms = m.get("dv_magnitude_ms", 0)
        print(f"    >> {m['satellite_id']} vs {m.get('debris_id','?')} | Δv={dv_ms:.3f} m/s | type={m.get('type','?')} | reason={m.get('reason','?')}")
        print(f"       fuel remaining: {m.get('fuel_remaining_kg', '?')} kg")
else:
    print(f"\n  No maneuvers were triggered.")
    print(f"  (TCA algorithm determined all threats are safe or cannot be avoided in time)")

# Show fuel
print(f"\n  FUEL STATUS:")
for sat in sorted(snap["satellites"], key=lambda s: s["fuel_kg"]):
    if sat["id"].startswith("SAT-TCA"):
        bar = int(sat["fuel_kg"] / 50 * 25)
        print(f"    {sat['id']:<15} {sat['fuel_kg']:.2f} kg [{'#'*bar}{'.'*(25-bar)}] {sat.get('status','?')}")

print(f"\n{'='*70}")
