from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import time

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
detector = CollisionDetector(threshold_km=100.0)
planner = ManeuverPlanner(engine)

active_pairs = set()
recent_maneuvers = []

def auto_cola(collisions):
    """Autonomous Collision Avoidance with deduplication"""
    global active_pairs, recent_maneuvers
    
    current_pairs = set()
    executed = 0
    
    for c in collisions:
        sat_id = c["satellite"]
        deb_id = c["debris"]
        pair = (sat_id, deb_id)
        current_pairs.add(pair)
        
        if pair not in active_pairs:
            if sat_id in engine.id_map and deb_id in engine.id_map:
                idx_sat = engine.id_map[sat_id]
                idx_deb = engine.id_map[deb_id]
                
                import math
                x, y, z = engine.positions[idx_sat]
                r = math.sqrt(x*x + y*y + z*z)
                lat_b = math.asin(z / r) * (180.0 / math.pi) if r > 1e-6 else 0
                lon_b = math.atan2(y, x) * (180.0 / math.pi) if r > 1e-6 else 0
                pos_before = {"lat": float(lat_b), "lon": float(lon_b)}
                
                dv = planner.plan_directional_avoidance(idx_sat, idx_deb)
                success, msg = planner.execute_maneuver(sat_id, dv)
                if success:
                    active_pairs.add(pair)
                    executed += 1
                    
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
                        "timestamp": int(time.time()),
                        "position_before": pos_before,
                        "position_after": pos_after,
                        "delta_v": {"x": float(dv[0]), "y": float(dv[1]), "z": float(dv[2])},
                        "reason": "Collision Avoidance"
                    })
                    
    # Clean up resolved collisions
    active_pairs = active_pairs.intersection(current_pairs)
    
    # Keep only the latest 50 maneuvers to avoid memory leak
    if len(recent_maneuvers) > 50:
        recent_maneuvers = recent_maneuvers[-50:]
        
    return executed

@app.get("/")
def home():
    return {"message": "ACM running 🚀", "objects_tracked": engine.count}

@app.post("/api/telemetry")
def telemetry(payload: TelemetryPayload):
    engine.ingest_objects(payload.objects)
    
    # Check immediate collisions
    collisions = detector.detect_collisions(engine)
    
    return {
        "status": "ACK",
        "processed_count": len(payload.objects),
        "active_cdm_warnings": len(collisions)
    }

@app.post("/api/simulate/step")
def simulate(payload: SimulateStepPayload):
    # Step physics
    engine.step(payload.step_seconds)
    
    # Detect collisions post-step
    collisions = detector.detect_collisions(engine)
    
    # Auto avoid
    maneuvers_executed = auto_cola(collisions)
    
    return {
        "status": "STEP_COMPLETE",
        "new_timestamp": int(time.time()),
        "collisions_detected": len(collisions),
        "maneuvers_executed": maneuvers_executed
    }

@app.post("/api/maneuver/schedule")
def maneuver(payload: ManeuverSchedulePayload):
    # Validate scheduled maneuvers
    idx = engine.id_map.get(payload.satelliteId)
    if idx is None:
        return {"status": "FAILED", "reason": "Satellite not found"}
        
    sat_pos = engine.positions[idx]
    has_los = planner.check_los(sat_pos)
    
    # Check fuel assuming sequence
    total_dv_m_s = 0.0
    for m in payload.maneuver_sequence:
        dv_mag = (m.deltaV.x**2 + m.deltaV.y**2 + m.deltaV.z**2)**0.5
        total_dv_m_s += dv_mag * 1000.0 # Assuming input is km/s
        
    fuel_needed = planner.calculate_fuel_usage(engine.fuel_kg[idx], total_dv_m_s)
    sufficient_fuel = fuel_needed <= engine.fuel_kg[idx]
    remaining = max(0.0, engine.fuel_kg[idx] - fuel_needed)
    
    # For now, we execute immediately if possible as a demo of the scheduling endpoint
    # A real scheduler would queue this.
    return {
        "status": "SCHEDULED",
        "validation": {
            "ground_station_los": has_los,
            "sufficient_fuel": sufficient_fuel,
            "projected_mass_remaining_kg": remaining
        }
    }

@app.get("/api/visualization/snapshot")
def snapshot():
    sats, debris = engine.get_snapshot()
    return {
        "timestamp": int(time.time()),
        "satellites": sats,
        "debris_cloud": debris,
        "maneuvers": recent_maneuvers
    }