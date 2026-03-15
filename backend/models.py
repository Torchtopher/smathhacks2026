from pydantic import BaseModel, Field


class DetectionInput(BaseModel):
    confidence: float
    bbox: list[float] = Field(min_length=4, max_length=4)


class BoatReport(BaseModel):
    boat_id: str
    timestamp: float
    gps_lat: float
    gps_lon: float
    heading: float
    image: str = ""


class BoatRegisterInput(BaseModel):
    name: str
    weight_class: str


class BoatRegisterResponse(BaseModel):
    boat_id: str
    name: str
    weight_class: str


class BoatAdminCreateInput(BaseModel):
    boat_id: str | None = None
    name: str
    weight_class: str


class BoatAdminUpdateInput(BaseModel):
    name: str | None = None
    weight_class: str | None = None


class BoatAdminResponse(BaseModel):
    boat_id: str
    name: str
    weight_class: str
    created_at: float
    last_reported_at: float | None = None


class BoatAdminDeleteResponse(BaseModel):
    boat_id: str
    deleted_boat_rows: int
    deleted_state_rows: int
    deleted_position_rows: int
    deleted_detection_rows: int


class DriftPoint(BaseModel):
    lat: float
    lon: float
    time_offset_hours: float


class DetectionSaved(BaseModel):
    id: str
    boat_id: str
    confidence: float
    detected_at: float
    bbox: list[float]
    projected_lat: float
    projected_lon: float
    drift_path: list[DriftPoint] = Field(default_factory=list)


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
    confidence: float
    detected_at: float
    boat_id: str
    drift_path: list[DriftPoint] = Field(default_factory=list)
