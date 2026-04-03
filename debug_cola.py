"""Debug: MUST be run on fresh backend. Seeds data and tests COLA step by step."""
import requests, json, sys

BASE = "http://localhost:8000"

# Check if backend is clean
r = requests.get(f"{BASE}/")
d = r.json()
if d.get("objects_tracked", 0) > 0:
    print(f"WARNING: Backend already has {d['objects_tracked']} objects!")
    print("Please restart the backend first: Ctrl+C, then 'uvicorn main:app --reload'")
    sys.exit(1)

# Step 1: Seed data
print("=== Seeding simulate_data3.py ===")
import simulate_data3
simulate_data3.main()

# Step 2: Run steps one at a time
print("\n=== Running simulation steps ===")
for i in range(10):
    r = requests.post(f"{BASE}/api/simulate/step", json={"step_seconds": 120})
    s = r.json()
    tag = ""
    if s["maneuvers_executed"] > 0:
        tag = f" << {s['maneuvers_executed']} MANEUVER(S)!"
    if s["collisions_detected"] > 0:
        tag += f" << {s['collisions_detected']} COLLISION(S)!"
    print(f"  Step {i+1}: t={s['new_timestamp']} | col={s['collisions_detected']} | man={s['maneuvers_executed']}{tag}")

# Step 3: Check all maneuvers
r = requests.get(f"{BASE}/api/visualization/snapshot")
snap = r.json()
maneuvers = snap.get("maneuvers", [])
stats = snap.get("fleet_stats", {})

print(f"\n=== RESULTS ===")
print(f"Total maneuvers: {len(maneuvers)}")
print(f"Total Dv consumed: {stats.get('total_dv_consumed_ms', 0):.3f} m/s")
print(f"Fleet uptime: {stats.get('fleet_uptime_pct', 0):.1f}%")
print(f"Pending recovery burns: {stats.get('pending_recovery_burns', 0)}")

if maneuvers:
    print(f"\nManeuver details:")
    for m in maneuvers:
        dv = m.get("dv_magnitude_ms", 0)
        print(f"  {m.get('type','?'):8s} | {m['satellite_id']:<20s} vs {str(m.get('debris_id','N/A')):<15s} | dv={dv:.3f}m/s | fuel={m.get('fuel_remaining_kg',0):.1f}kg")
else:
    print("\nNo maneuvers! Investigating why...")
    # Check if threats exist
    threats = [d for d in snap["debris_cloud"] if "THR" in d[0]]
    print(f"  Threat debris in system: {len(threats)}")
    print(f"  Satellites: {len(snap['satellites'])}")
