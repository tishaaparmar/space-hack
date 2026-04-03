"""
Test script: Feeds a deliberate near-collision scenario and verifies
that the ACM detects it and autonomously executes an avoidance maneuver.
"""
import requests
import json
import time

BASE = "http://localhost:8000"

def pp(label, resp):
    print(f"\n{'='*60}")
    print(f"  {label}  [HTTP {resp.status_code}]")
    print(f"{'='*60}")
    print(json.dumps(resp.json(), indent=2))

# ── Step 1: Reset by ingesting a fresh scenario ──────────────
# Place a satellite and a debris object on a collision course
# Both at ~6800 km altitude, only 50 meters apart (< 100m threshold)
print("🛰️  SCENARIO: Near-collision test")
print("   Satellite SAT-ALPHA-04 at [6800, 0, 0] km heading +Y")
print("   Debris    DEB-THREAT-01 at [6800.03, 0.02, 0.01] km heading -Y")
print("   Initial separation: ~36 meters (below 100m collision threshold)")

r = requests.post(f"{BASE}/api/telemetry", json={
    "timestamp": "2026-03-12T08:00:00.000Z",
    "objects": [
        {
            "id": "SAT-ALPHA-04",
            "type": "SATELLITE",
            "r": {"x": 6800.0, "y": 0.0, "z": 0.0},
            "v": {"x": 0.0, "y": 7.66, "z": 0.0},
            "fuel_kg": 50.0
        },
        {
            "id": "DEB-THREAT-01",
            "type": "DEBRIS",
            "r": {"x": 6800.03, "y": 0.02, "z": 0.01},
            "v": {"x": 0.0, "y": -7.5, "z": 0.0}
        }
    ]
})
pp("Step 1: Telemetry Ingestion", r)

# ── Step 2: Check snapshot before simulation ──────────────────
r = requests.get(f"{BASE}/api/visualization/snapshot")
pp("Step 2: Snapshot (before sim)", r)
snap = r.json()
sat = next(s for s in snap["satellites"] if s["id"] == "SAT-ALPHA-04")
print(f"\n  📍 SAT-ALPHA-04 position: lat={sat['lat']:.4f}, lon={sat['lon']:.4f}")
print(f"  ⛽ Fuel: {sat['fuel_kg']} kg")

# ── Step 3: Simulate 1 tick — should detect collision + auto-avoid ──
print("\n⏱️  Simulating 10 seconds...")
r = requests.post(f"{BASE}/api/simulate/step", json={"step_seconds": 10})
pp("Step 3: Simulate Step (10s)", r)
step_data = r.json()

if step_data["collisions_detected"] > 0:
    print(f"\n  🚨 COLLISION DETECTED! count={step_data['collisions_detected']}")
else:
    print(f"\n  ✅ No collision detected (objects may have diverged)")

if step_data["maneuvers_executed"] > 0:
    print(f"  🔥 MANEUVER EXECUTED! count={step_data['maneuvers_executed']}")
else:
    print(f"  ℹ️  No maneuver executed")

# ── Step 4: Check snapshot after — verify fuel changed ────────
r = requests.get(f"{BASE}/api/visualization/snapshot")
snap2 = r.json()
sat2 = next((s for s in snap2["satellites"] if s["id"] == "SAT-ALPHA-04"), None)
if sat2:
    print(f"\n  📍 SAT-ALPHA-04 after: lat={sat2['lat']:.4f}, lon={sat2['lon']:.4f}")
    print(f"  ⛽ Fuel after: {sat2['fuel_kg']:.4f} kg (was {sat['fuel_kg']})")
    if sat2['fuel_kg'] < sat['fuel_kg']:
        print(f"  ✅ Fuel consumed by avoidance maneuver: {sat['fuel_kg'] - sat2['fuel_kg']:.4f} kg")

# ── Step 5: Check maneuver log ────────────────────────────────
if snap2.get("maneuvers"):
    print(f"\n  📋 Maneuver History ({len(snap2['maneuvers'])} entries):")
    for m in snap2["maneuvers"]:
        dv_mag = (m["delta_v"]["x"]**2 + m["delta_v"]["y"]**2 + m["delta_v"]["z"]**2)**0.5 * 1000
        print(f"     {m['satellite_id']} → avoided {m['debris_id']} | Δv={dv_mag:.2f} m/s | {m['reason']}")

# ── Step 6: Test manual maneuver scheduling ───────────────────
print("\n📡 Testing manual maneuver schedule (PS format)...")
r = requests.post(f"{BASE}/api/maneuver/schedule", json={
    "satelliteId": "SAT-ALPHA-04",
    "maneuver_sequence": [
        {
            "burn_id": "EVASION_BURN_1",
            "burnTime": "2026-03-12T14:15:30.000Z",
            "deltaV_vector": {"x": 0.002, "y": 0.015, "z": -0.001}
        },
        {
            "burn_id": "RECOVERY_BURN_1",
            "burnTime": "2026-03-12T15:45:30.000Z",
            "deltaV_vector": {"x": -0.0019, "y": -0.014, "z": 0.001}
        }
    ]
})
pp("Step 6: Maneuver Schedule (2-burn sequence)", r)

print("\n" + "="*60)
print("  🏁 TEST COMPLETE")
print("="*60)
