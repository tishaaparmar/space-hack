"""
simulate_data3.py — EXTREME STRESS TEST
Same scale: 50 sats + 10,000 debris
BUT injects 25 guaranteed collision threats across 5 different geometry types:
  1. Head-on (retrograde debris)        — closing speed ~14 km/s
  2. Coplanar catch-up (same as v2)     — closing speed ~20-30 m/s
  3. Cross-track intercept              — oblique approach at ~500 m/s
  4. Fuel-critical satellites           — low fuel + collision forces EOL decision
  5. Blackout-zone conjunctions         — TCA occurs far from ground stations

Goal: Hammer every COLA branch of your ACM:
  - Basic evasion
  - RTN-frame retrograde burn (head-on)
  - Cross-track plane-change avoidance
  - EOL graveyard maneuver trigger
  - Pre-emptive uplink before comm blackout
"""

import requests
import random
import uuid
import math
import numpy as np

# ── Ground stations from the PS (lat/lon in degrees) ──────────────────────────
GROUND_STATIONS = [
    {"name": "ISTRAC_Bengaluru",    "lat":  13.0333,  "lon":  77.5167},
    {"name": "Svalbard",            "lat":  78.2297,  "lon":  15.4077},
    {"name": "Goldstone",           "lat":  35.4266,  "lon": -116.890},
    {"name": "Punta_Arenas",        "lat": -53.1500,  "lon":  -70.917},
    {"name": "IIT_Delhi",           "lat":  28.5450,  "lon":  77.1926},
    {"name": "McMurdo",             "lat": -77.8463,  "lon": 166.668},
]

RE = 6378.137  # km

def ecef_from_latlon(lat_deg, lon_deg):
    """Approximate ECEF for ground station (on Earth surface)."""
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    x = RE * math.cos(lat) * math.cos(lon)
    y = RE * math.cos(lat) * math.sin(lon)
    z = RE * math.sin(lat)
    return np.array([x, y, z])

def has_ground_contact(pos_km):
    """Check if satellite has line-of-sight to ANY ground station (naive check)."""
    for gs in GROUND_STATIONS:
        gs_pos = ecef_from_latlon(gs["lat"], gs["lon"])
        to_sat = pos_km - gs_pos
        dot = np.dot(gs_pos / np.linalg.norm(gs_pos), to_sat / np.linalg.norm(to_sat))
        # elevation angle approximation: dot > sin(5°) ≈ 0.087
        if dot > 0.087:
            return True
    return False


# ── Helpers ───────────────────────────────────────────────────────────────────

def random_unit():
    v = np.array([random.gauss(0, 1) for _ in range(3)])
    return v / np.linalg.norm(v)

def circular_velocity(r_km):
    mu = 398600.4418
    return math.sqrt(mu / r_km)

def make_circular_velocity_vec(pos):
    """Return a circular-orbit velocity vector perpendicular to pos."""
    r_hat = pos / np.linalg.norm(pos)
    up = np.array([0.0, 0.0, 1.0])
    if abs(np.dot(r_hat, up)) > 0.99:
        up = np.array([1.0, 0.0, 0.0])
    t_hat = np.cross(r_hat, up)
    t_hat /= np.linalg.norm(t_hat)
    v_mag = circular_velocity(np.linalg.norm(pos))
    return t_hat * v_mag

def generate_random_satellite(idx):
    r_mag = random.uniform(6600, 7200)
    pos = random_unit() * r_mag
    vel = make_circular_velocity_vec(pos)
    return {
        "id": f"SAT-{idx:03d}-{str(uuid.uuid4())[:6].upper()}",
        "type": "SATELLITE",
        "r": {"x": float(pos[0]), "y": float(pos[1]), "z": float(pos[2])},
        "v": {"x": float(vel[0]), "y": float(vel[1]), "z": float(vel[2])},
        "fuel_kg": 50.0,
    }

def generate_random_debris():
    r_mag = random.uniform(6500, 7300)
    pos = random_unit() * r_mag
    vel = make_circular_velocity_vec(pos)
    # Add small random perturbation so it's not perfectly circular
    vel += np.array([random.uniform(-0.05, 0.05) for _ in range(3)])
    return {
        "id": f"DEB-{str(uuid.uuid4())[:8].upper()}",
        "type": "DEBRIS",
        "r": {"x": float(pos[0]), "y": float(pos[1]), "z": float(pos[2])},
        "v": {"x": float(vel[0]), "y": float(vel[1]), "z": float(vel[2])},
    }

def tca_stats(s_pos, s_vel, d_pos, d_vel):
    """Returns (tca_seconds, miss_distance_km)."""
    r_rel = s_pos - d_pos
    v_rel = s_vel - d_vel
    v_rel_sq = np.dot(v_rel, v_rel)
    if v_rel_sq < 1e-12:
        return 0.0, np.linalg.norm(r_rel)
    tca = -np.dot(r_rel, v_rel) / v_rel_sq
    r_tca = r_rel + v_rel * tca
    return tca, np.linalg.norm(r_tca)


# ── Threat generators ─────────────────────────────────────────────────────────

def inject_catchup_threats(sat_list, n=6):
    """Type 1: Same-plane debris just ahead, slow closing speed (original v2 style)."""
    threats = []
    targets = random.sample(sat_list, min(n, len(sat_list)))
    for i, sat in enumerate(targets):
        s_pos = np.array([sat["r"]["x"], sat["r"]["y"], sat["r"]["z"]])
        s_vel = np.array([sat["v"]["x"], sat["v"]["y"], sat["v"]["z"]])
        v_hat = s_vel / np.linalg.norm(s_vel)
        r_hat = s_pos / np.linalg.norm(s_pos)
        c_hat = np.cross(v_hat, r_hat); c_hat /= np.linalg.norm(c_hat)

        offset_km = random.uniform(3.0, 8.0)
        closing_speed = random.uniform(0.015, 0.035)  # km/s (15-35 m/s)
        cross_track_m = random.uniform(20, 70)        # 20-70 m cross-track

        d_pos = s_pos + v_hat * offset_km + c_hat * (cross_track_m / 1000.0)
        d_vel = s_vel - v_hat * closing_speed

        tca, miss = tca_stats(s_pos, s_vel, d_pos, d_vel)
        deb_id = f"DEB-CTUP-{i+1:03d}"
        print(f"  [CATCHUP]  {deb_id} -> {sat['id']}: "
              f"ahead={offset_km:.1f}km, closing={closing_speed*1000:.0f}m/s, "
              f"TCA={tca:.0f}s, miss={miss*1000:.0f}m")
        threats.append({
            "id": deb_id, "type": "DEBRIS",
            "r": {"x": float(d_pos[0]), "y": float(d_pos[1]), "z": float(d_pos[2])},
            "v": {"x": float(d_vel[0]), "y": float(d_vel[1]), "z": float(d_vel[2])},
        })
    return threats


def inject_headon_threats(sat_list, n=5):
    """
    Type 2: RETROGRADE debris on nearly same orbit — head-on at ~14 km/s closing speed.
    Most dangerous real-world scenario.
    """
    threats = []
    targets = random.sample(sat_list, min(n, len(sat_list)))
    for i, sat in enumerate(targets):
        s_pos = np.array([sat["r"]["x"], sat["r"]["y"], sat["r"]["z"]])
        s_vel = np.array([sat["v"]["x"], sat["v"]["y"], sat["v"]["z"]])
        v_hat = s_vel / np.linalg.norm(s_vel)
        r_hat = s_pos / np.linalg.norm(s_pos)
        c_hat = np.cross(v_hat, r_hat); c_hat /= np.linalg.norm(c_hat)

        # Debris is AHEAD at 1500-3000 km, moving RETROGRADE (opposite direction)
        # We need it far away because at 14 km/s closing speed, 60km takes only 4 seconds,
        # which means it would pass the satellite before the 120s simulation step even finishes!
        offset_km = random.uniform(1500.0, 3000.0)
        cross_m = random.uniform(10, 50)

        d_pos = s_pos + v_hat * offset_km + c_hat * (cross_m / 1000.0)
        # Retrograde: same speed magnitude, opposite transverse direction
        v_mag = np.linalg.norm(s_vel)
        d_vel = -s_vel + r_hat * random.uniform(-0.01, 0.01)  # slight radial wobble

        tca, miss = tca_stats(s_pos, s_vel, d_pos, d_vel)
        deb_id = f"DEB-HEAD-{i+1:03d}"
        print(f"  [HEAD-ON]  {deb_id} -> {sat['id']}: "
              f"ahead={offset_km:.1f}km, closing≈{v_mag*2:.2f}km/s, "
              f"TCA={tca:.0f}s, miss={miss*1000:.0f}m")
        threats.append({
            "id": deb_id, "type": "DEBRIS",
            "r": {"x": float(d_pos[0]), "y": float(d_pos[1]), "z": float(d_pos[2])},
            "v": {"x": float(d_vel[0]), "y": float(d_vel[1]), "z": float(d_vel[2])},
        })
    return threats


def inject_crosstrack_threats(sat_list, n=5):
    """
    Type 3: Debris approaching from normal (out-of-plane) direction.
    Tests the N-component burn in RTN frame.
    """
    threats = []
    targets = random.sample(sat_list, min(n, len(sat_list)))
    for i, sat in enumerate(targets):
        s_pos = np.array([sat["r"]["x"], sat["r"]["y"], sat["r"]["z"]])
        s_vel = np.array([sat["v"]["x"], sat["v"]["y"], sat["v"]["z"]])
        v_hat = s_vel / np.linalg.norm(s_vel)
        r_hat = s_pos / np.linalg.norm(s_pos)
        n_hat = np.cross(r_hat, v_hat); n_hat /= np.linalg.norm(n_hat)  # normal to orbital plane

        # Place debris 10-25 km above/below the orbital plane (smaller so linear projection holds better)
        normal_offset = random.choice([-1, 1]) * random.uniform(10.0, 25.0)
        along_track_offset = random.uniform(-5.0, 5.0)   # roughly same position in orbit

        d_pos = s_pos + n_hat * normal_offset + v_hat * along_track_offset

        # Velocity: similar prograde speed but with a strong normal component
        # that will bring it to near-zero normal offset at TCA
        normal_closing = -normal_offset / random.uniform(100, 300)  # close within 100-300s
        d_vel = s_vel + n_hat * normal_closing + v_hat * random.uniform(-0.02, 0.02)

        tca, miss = tca_stats(s_pos, s_vel, d_pos, d_vel)
        deb_id = f"DEB-CRST-{i+1:03d}"
        print(f"  [CROSS-TK] {deb_id} -> {sat['id']}: "
              f"normal_off={normal_offset:.1f}km, n_close={normal_closing*1000:.0f}m/s, "
              f"TCA={tca:.0f}s, miss={miss*1000:.0f}m")
        threats.append({
            "id": deb_id, "type": "DEBRIS",
            "r": {"x": float(d_pos[0]), "y": float(d_pos[1]), "z": float(d_pos[2])},
            "v": {"x": float(d_vel[0]), "y": float(d_vel[1]), "z": float(d_vel[2])},
        })
    return threats


def inject_fuellow_threats(sat_list, n=4):
    """
    Type 4: Targets satellites and also sets their fuel critically low (4-6 kg).
    Forces ACM to decide between collision avoidance and EOL graveyard maneuver.
    """
    threats = []
    targets = random.sample(sat_list, min(n, len(sat_list)))
    for i, sat in enumerate(targets):
        # Drop fuel to critical level
        sat["fuel_kg"] = random.uniform(3.0, 6.0)

        s_pos = np.array([sat["r"]["x"], sat["r"]["y"], sat["r"]["z"]])
        s_vel = np.array([sat["v"]["x"], sat["v"]["y"], sat["v"]["z"]])
        v_hat = s_vel / np.linalg.norm(s_vel)
        r_hat = s_pos / np.linalg.norm(s_pos)
        c_hat = np.cross(v_hat, r_hat); c_hat /= np.linalg.norm(c_hat)

        offset_km = random.uniform(2.0, 5.0)
        closing_speed = random.uniform(0.01, 0.025)
        cross_m = random.uniform(30, 60)

        d_pos = s_pos + v_hat * offset_km + c_hat * (cross_m / 1000.0)
        d_vel = s_vel - v_hat * closing_speed

        tca, miss = tca_stats(s_pos, s_vel, d_pos, d_vel)
        deb_id = f"DEB-FUEL-{i+1:03d}"
        print(f"  [FUEL-LO]  {deb_id} -> {sat['id']} (fuel={sat['fuel_kg']:.1f}kg): "
              f"TCA={tca:.0f}s, miss={miss*1000:.0f}m ← EOL trigger!")
        threats.append({
            "id": deb_id, "type": "DEBRIS",
            "r": {"x": float(d_pos[0]), "y": float(d_pos[1]), "z": float(d_pos[2])},
            "v": {"x": float(d_vel[0]), "y": float(d_vel[1]), "z": float(d_vel[2])},
        })
    return threats


def inject_blackout_threats(sat_list, n=5):
    """
    Type 5: Threat satellites that are currently IN a communication blackout zone
    (over ocean / polar region — no ground station LOS).
    Forces ACM to pre-schedule the uplink before coverage loss.
    """
    threats = []
    attempts = 0
    blackout_sats = []

    # Find satellites that are already in blackout
    for sat in sat_list:
        pos = np.array([sat["r"]["x"], sat["r"]["y"], sat["r"]["z"]])
        if not has_ground_contact(pos):
            blackout_sats.append(sat)
        if len(blackout_sats) >= n:
            break

    if len(blackout_sats) < n:
        # Fill remainder with random sats regardless of coverage
        extras = [s for s in sat_list if s not in blackout_sats]
        blackout_sats += random.sample(extras, min(n - len(blackout_sats), len(extras)))

    targets = blackout_sats[:n]
    for i, sat in enumerate(targets):
        s_pos = np.array([sat["r"]["x"], sat["r"]["y"], sat["r"]["z"]])
        s_vel = np.array([sat["v"]["x"], sat["v"]["y"], sat["v"]["z"]])
        v_hat = s_vel / np.linalg.norm(s_vel)
        r_hat = s_pos / np.linalg.norm(s_pos)
        c_hat = np.cross(v_hat, r_hat); c_hat /= np.linalg.norm(c_hat)

        offset_km = random.uniform(5.0, 15.0)
        closing_speed = random.uniform(0.02, 0.04)
        cross_m = random.uniform(20, 55)

        d_pos = s_pos + v_hat * offset_km + c_hat * (cross_m / 1000.0)
        d_vel = s_vel - v_hat * closing_speed

        tca, miss = tca_stats(s_pos, s_vel, d_pos, d_vel)
        in_blackout = not has_ground_contact(s_pos)
        deb_id = f"DEB-BLKT-{i+1:03d}"
        print(f"  [BLACKOUT] {deb_id} -> {sat['id']}: "
              f"blackout={in_blackout}, TCA={tca:.0f}s, miss={miss*1000:.0f}m")
        threats.append({
            "id": deb_id, "type": "DEBRIS",
            "r": {"x": float(d_pos[0]), "y": float(d_pos[1]), "z": float(d_pos[2])},
            "v": {"x": float(d_vel[0]), "y": float(d_vel[1]), "z": float(d_vel[2])},
        })
    return threats


# ── Main ──────────────────────────────────────────────────────────────────────

def generate_telemetry(num_sats=50, num_debris=10000):
    objects = []
    sat_list = []

    print(f"Generating {num_sats} satellites...")
    for i in range(num_sats):
        sat = generate_random_satellite(i + 1)
        objects.append(sat)
        sat_list.append(sat)

    total_threats = 25  # 6+5+5+4+5
    safe_debris_count = num_debris - total_threats

    print(f"Generating {safe_debris_count} safe background debris...")
    for _ in range(safe_debris_count):
        objects.append(generate_random_debris())

    # Inject all 5 threat types
    print("\n─── Injecting Threat Type 1: CATCH-UP (6) ───")
    objects += inject_catchup_threats(sat_list, n=6)

    print("\n─── Injecting Threat Type 2: HEAD-ON RETROGRADE (5) ───")
    objects += inject_headon_threats(sat_list, n=5)

    print("\n─── Injecting Threat Type 3: CROSS-TRACK (5) ───")
    objects += inject_crosstrack_threats(sat_list, n=5)

    print("\n─── Injecting Threat Type 4: FUEL-CRITICAL SAT (4) ───")
    objects += inject_fuellow_threats(sat_list, n=4)

    print("\n─── Injecting Threat Type 5: BLACKOUT ZONE (5) ───")
    objects += inject_blackout_threats(sat_list, n=5)

    print(f"\nTotal objects: {len(objects)} "
          f"({num_sats} sats + {safe_debris_count} safe debris + {total_threats} threats)")
    return objects


def main():
    random.seed(3033)
    np.random.seed(3033)

    print("=" * 60)
    print(" simulate_data3.py — EXTREME STRESS TEST")
    print(" 50 sats | 10,000 debris | 25 collision threats")
    print(" 5 geometry types to stress-test all COLA branches")
    print("=" * 60 + "\n")

    data = generate_telemetry(50, 10000)

    payload = {
        "timestamp": "2026-03-12T08:00:00.000Z",
        "objects": data,
    }

    print(f"\nSending {len(data)} objects to backend at http://127.0.0.1:8000 ...")
    try:
        res = requests.post(
            "http://127.0.0.1:8000/api/telemetry",
            json=payload,
            timeout=60,
        )
        print("Status:", res.status_code)
        print("Response:", res.json())
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to backend. Is it running on port 8000?")
    except Exception as e:
        print("ERROR:", e)

    print("\n" + "=" * 60)
    print("Done! Open http://localhost:3000 and click RUN SIMULATION.")
    print("Expected: maneuvers within first 1-3 steps across all 5 threat types.")
    print("Watch for:")
    print("  • CATCHUP → prograde retrograde burn (T-axis)")
    print("  • HEAD-ON → large retrograde / radial burn (R+T axis)")
    print("  • CROSS-TRACK → normal burn (N-axis, fuel expensive)")
    print("  • FUEL-CRITICAL → EOL graveyard orbit schedule")
    print("  • BLACKOUT → pre-emptive uplink before LOS loss")
    print("=" * 60)


if __name__ == "__main__":
    main()
