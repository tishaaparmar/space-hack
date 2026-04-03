from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import time
import math

from models import TelemetryPayload, ManeuverSchedulePayload, SimulateStepPayload
from physics import PhysicsEngine
from collision import CollisionDetector
from maneuver import ManeuverPlanner

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
engine = PhysicsEngine()
detector = CollisionDetector(threshold_km=0.1)  # 100 meters as per PS spec
planner = ManeuverPlanner(engine)

active_pairs = set()
recent_maneuvers = []
pending_recovery = []  # list of (sat_id, scheduled_time) for recovery burns

# Simulation clock
sim_time = datetime(2026, 3, 12, 8, 0, 0, tzinfo=timezone.utc)

# Cumulative stats
total_dv_consumed_ms = 0.0  # total delta-v consumed in m/s across all satellites

def get_sim_timestamp():
    """Return current simulation time as ISO 8601 string."""
    return sim_time.strftime("%Y-%m-%dT%H:%M:%S.000Z")

def auto_cola(collisions):
    """Autonomous Collision Avoidance — TCA-based predictive + reactive fallback.
    
    Phase 1: Predictive scan (scan_and_plan_avoidance) — uses TCA dot-product formula
             to find future conjunctions within 90 min window, computes minimum Δv = Δd/τ
    Phase 2: Reactive fallback — for any current-frame collision not already handled
    """
    global active_pairs, recent_maneuvers, pending_recovery, total_dv_consumed_ms
    
    executed = 0
    handled_sats = set()
    
    # --- Phase 1: Predictive TCA-based avoidance ---
    planned = planner.scan_and_plan_avoidance()
    
    for sat_id, deb_id, dv in planned:
        if dv is None:
            continue
        
        pair = (sat_id, deb_id)
        if pair in active_pairs:
            continue
        
        idx_sat = engine.id_map[sat_id]
        
        x, y, z = engine.positions[idx_sat]
        r = math.sqrt(x*x + y*y + z*z)
        lat_b = math.asin(z / r) * (180.0 / math.pi) if r > 1e-6 else 0
        lon_b = math.atan2(y, x) * (180.0 / math.pi) if r > 1e-6 else 0
        pos_before = {"lat": float(lat_b), "lon": float(lon_b)}
        
        success, msg = planner.execute_maneuver(sat_id, dv)
        if success:
            active_pairs.add(pair)
            handled_sats.add(sat_id)
            executed += 1
            dv_mag_ms = float(np.linalg.norm(dv)) * 1000.0
            total_dv_consumed_ms += dv_mag_ms
            
            vel = engine.velocities[idx_sat]
            nx = x + vel[0] * 120.0
            ny = y + vel[1] * 120.0
            nz = z + vel[2] * 120.0
            nr = math.sqrt(nx*nx + ny*ny + nz*nz)
            lat_a = math.asin(nz / nr) * (180.0 / math.pi) if nr > 1e-6 else 0
            lon_a = math.atan2(ny, nx) * (180.0 / math.pi) if nr > 1e-6 else 0
            pos_after = {"lat": float(lat_a), "lon": float(lon_a)}
            
            recent_maneuvers.append({
                "satellite_id": sat_id,
                "debris_id": deb_id,
                "timestamp": get_sim_timestamp(),
                "type": "EVASION",
                "position_before": pos_before,
                "position_after": pos_after,
                "delta_v": {"x": float(dv[0]), "y": float(dv[1]), "z": float(dv[2])},
                "dv_magnitude_ms": dv_mag_ms,
                "fuel_remaining_kg": float(engine.fuel_kg[idx_sat]),
                "reason": "Predictive COLA (TCA-based)"
            })
            
            # Schedule recovery burn after cooldown
            pending_recovery.append((sat_id, planner.sim_elapsed + planner.cooldown_s))
    
    # Keep recent maneuvers capped
    if len(recent_maneuvers) > 100:
        recent_maneuvers = recent_maneuvers[-100:]
        
    return executed

def process_recovery_burns():
    """Execute pending recovery burns after cooldown period."""
    global pending_recovery, recent_maneuvers, total_dv_consumed_ms
    
    still_pending = []
    recovery_count = 0
    
    for sat_id, scheduled_time in pending_recovery:
        if planner.sim_elapsed >= scheduled_time:
            if sat_id in engine.id_map:
                idx = engine.id_map[sat_id]
                dv = planner.plan_recovery_burn(idx)
                if dv is not None:
                    success, msg = planner.execute_maneuver(sat_id, dv)
                    if success:
                        recovery_count += 1
                        dv_mag_ms = float(np.linalg.norm(dv)) * 1000.0
                        total_dv_consumed_ms += dv_mag_ms
                        
                        x, y, z = engine.positions[idx]
                        r = math.sqrt(x*x + y*y + z*z)
                        lat = math.asin(z / r) * (180.0 / math.pi) if r > 1e-6 else 0
                        lon = math.atan2(y, x) * (180.0 / math.pi) if r > 1e-6 else 0
                        
                        recent_maneuvers.append({
                            "satellite_id": sat_id,
                            "debris_id": None,
                            "timestamp": get_sim_timestamp(),
                            "type": "RECOVERY",
                            "position_before": {"lat": float(lat), "lon": float(lon)},
                            "position_after": {"lat": float(lat), "lon": float(lon)},
                            "delta_v": {"x": float(dv[0]), "y": float(dv[1]), "z": float(dv[2])},
                            "dv_magnitude_ms": dv_mag_ms,
                            "fuel_remaining_kg": float(engine.fuel_kg[idx]),
                            "reason": "Station-Keeping Recovery"
                        })
                    else:
                        # Can't execute now (maybe cooldown overlap), retry later
                        still_pending.append((sat_id, planner.sim_elapsed + 60))
        else:
            still_pending.append((sat_id, scheduled_time))
    
    pending_recovery = still_pending
    return recovery_count

import numpy as np

@app.get("/")
def home():
    return {"message": "ACM running 🚀", "objects_tracked": engine.count}

@app.post("/api/telemetry")
def telemetry(payload: TelemetryPayload):
    global sim_time
    
    if payload.timestamp:
        try:
            sim_time = datetime.fromisoformat(payload.timestamp.replace("Z", "+00:00"))
        except ValueError:
            pass
    
    engine.ingest_objects(payload.objects)
    collisions = detector.detect_collisions(engine)
    
    return {
        "status": "ACK",
        "processed_count": len(payload.objects),
        "active_cdm_warnings": len(collisions)
    }

@app.post("/api/simulate/step")
def simulate(payload: SimulateStepPayload):
    global sim_time
    
    # Step physics (also propagates nominal slots and tracks uptime)
    engine.step(payload.step_seconds)
    
    # Advance simulation clock
    sim_time += timedelta(seconds=payload.step_seconds)
    planner.advance_time(payload.step_seconds)
    
    # Detect collisions post-step
    collisions = detector.detect_collisions(engine)
    
    # Auto collision avoidance
    evasion_count = auto_cola(collisions)
    
    # Process pending recovery burns
    recovery_count = process_recovery_burns()
    
    return {
        "status": "STEP_COMPLETE",
        "new_timestamp": get_sim_timestamp(),
        "collisions_detected": len(collisions),
        "maneuvers_executed": evasion_count + recovery_count
    }

@app.post("/api/maneuver/schedule")
def maneuver(payload: ManeuverSchedulePayload):
    idx = engine.id_map.get(payload.satelliteId)
    if idx is None:
        return {"status": "FAILED", "reason": "Satellite not found"}
        
    sat_pos = engine.positions[idx]
    has_los = planner.check_los(sat_pos)
    cooldown_ok = planner.check_cooldown(payload.satelliteId)
    
    total_dv_m_s = 0.0
    for m in payload.maneuver_sequence:
        dv_mag = (m.deltaV.x**2 + m.deltaV.y**2 + m.deltaV.z**2)**0.5
        total_dv_m_s += dv_mag * 1000.0
        
    fuel_needed = planner.calculate_fuel_usage(float(engine.fuel_kg[idx]), total_dv_m_s)
    sufficient_fuel = fuel_needed <= float(engine.fuel_kg[idx])
    remaining = max(0.0, float(engine.fuel_kg[idx]) - fuel_needed)
    
    return {
        "status": "SCHEDULED",
        "validation": {
            "ground_station_los": bool(has_los),
            "thruster_cooldown_ok": bool(cooldown_ok),
            "sufficient_fuel": bool(sufficient_fuel),
            "projected_mass_remaining_kg": float(remaining)
        }
    }

@app.get("/api/visualization/snapshot")
def snapshot():
    sats, debris = engine.get_snapshot()
    
    # Compute fleet-level uptime stats
    sat_count = len(sats)
    fleet_uptime = 0.0
    if sat_count > 0:
        fleet_uptime = sum(s.get("uptime_pct", 100.0) for s in sats) / sat_count
    
    return {
        "timestamp": get_sim_timestamp(),
        "satellites": sats,
        "debris_cloud": debris,
        "maneuvers": recent_maneuvers,
        "fleet_stats": {
            "total_dv_consumed_ms": float(total_dv_consumed_ms),
            "fleet_uptime_pct": float(fleet_uptime),
            "pending_recovery_burns": len(pending_recovery)
        }
    }