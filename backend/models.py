from pydantic import BaseModel, Field, ConfigDict
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
    timestamp: Optional[str] = None  # ISO 8601 timestamp from grader
    objects: List[SpaceObject]

class ManeuverCommand(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    burn_id: Optional[str] = None  # Unique burn identifier
    burnTime: str  # ISO 8601 timestamp
    deltaV: Vector3D = Field(alias="deltaV_vector")  # Accepts "deltaV_vector" from grader

class ManeuverSchedulePayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    satelliteId: str
    maneuver_sequence: List[ManeuverCommand]

class SimulateStepPayload(BaseModel):
    step_seconds: float = 1.0
