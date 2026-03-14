export interface BoatState {
  boat_id: string
  name: string
  weight_class: "light" | "heavy"
  gps_lat: number
  gps_lon: number
  heading: number
  timestamp: number
  trail?: [number, number][]
  image?: string
  api_key?: string
}

export interface DriftPoint {
  lat: number
  lon: number
  time_offset_hours: number
}

export interface TrashPoint {
  id: string
  lat: number
  lon: number
  class_name: "bottle" | "plastic bag" | "cup" | "fishing line" | "styrofoam"
  confidence: number
  detected_at: number
  boat_id: string
  drift_path?: DriftPoint[]
}
