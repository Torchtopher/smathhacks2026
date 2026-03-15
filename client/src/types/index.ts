export const WEIGHT_CLASSES = ["light", "medium", "heavy"] as const
export type WeightClass = (typeof WEIGHT_CLASSES)[number]

export interface BoatState {
  boat_id: string
  name: string
  weight_class: WeightClass
  gps_lat: number
  gps_lon: number
  heading: number
  timestamp: number
  trail?: [number, number][]
  image?: string

}

export interface DriftPoint {
  lat: number
  lon: number
  time_offset_hours: number
}

export interface Detection {
  id: string
  lat: number
  lon: number
  confidence: number
  detected_at: number
  boat_id: string
  drift_path?: DriftPoint[]
  label: string
}
