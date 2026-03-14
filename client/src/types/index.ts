export interface BoatState {
  boat_id: string
  name: string
  weight_class: "light" | "heavy"
  gps_lat: number
  gps_lon: number
  heading: number
  timestamp: number
  image?: string
  api_key?: string
}
