from pydantic import BaseModel
from typing import List, Literal, Optional

class Vector3D(BaseModel):
    x: float
    y: float
    z: float

class SpaceObject(BaseModel):
    id: str
    type: Literal["SATELLITE", "DEBRIS"]
    r: Vector3D
    v: Vector3D
    mass_kg: Optional[float] = 500.0  # Dry mass
    fuel_kg: Optional[float] = 50.0   # Fuel

class TelemetryPayload(BaseModel):
    objects: List[SpaceObject]

class ManeuverCommand(BaseModel):
    burnTime: float  # UNIX timestamp or relative seconds
    deltaV: Vector3D

class ManeuverSchedulePayload(BaseModel):
    satelliteId: str
    maneuver_sequence: List[ManeuverCommand]

class SimulateStepPayload(BaseModel):
    step_seconds: float = 1.0

