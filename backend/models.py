from pydantic import BaseModel, Field


class DetectionInput(BaseModel):
    class_name: str
    confidence: float
    bbox: list[float] = Field(min_length=4, max_length=4)


class BoatReport(BaseModel):
    boat_id: str
    timestamp: float
    gps_lat: float
    gps_lon: float
    heading: float
    detections: list[DetectionInput] = Field(default_factory=list)


class DetectionSaved(BaseModel):
    id: str
    boat_id: str
    class_name: str
    confidence: float
    detected_at: float
    bbox: list[float]
    projected_lat: float
    projected_lon: float


class BoatStateResponse(BaseModel):
    boat_id: str
    gps_lat: float
    gps_lon: float
    heading: float
    timestamp: float


class BoatPositionPointResponse(BaseModel):
    boat_id: str
    gps_lat: float
    gps_lon: float
    heading: float
    timestamp: float


class TrashPointResponse(BaseModel):
    id: str
    lat: float
    lon: float
    class_name: str
    confidence: float
    detected_at: float
    boat_id: str
