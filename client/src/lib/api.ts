import type { BoatState, TrashPoint } from "@/types"

const BASE = import.meta.env.VITE_BACKEND_URL || ""

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} failed (${res.status})`)
  return res.json()
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`POST ${path} failed (${res.status})`)
  return res.json()
}

export const api = {
  async getBoats(): Promise<BoatState[]> {
    const data = await get<{
      boats: {
        boat_id: string
        gps_lat: number
        gps_lon: number
        heading: number
        timestamp: number
        name: string
        weight_class: string
      }[]
    }>("/api/boats")
    return data.boats.map((b) => ({
      boat_id: b.boat_id,
      name: b.name,
      weight_class: b.weight_class as BoatState["weight_class"],
      gps_lat: b.gps_lat,
      gps_lon: b.gps_lon,
      heading: b.heading,
      timestamp: b.timestamp,
    }))
  },

  async getTrash(driftDays = 7): Promise<TrashPoint[]> {
    const days = Math.max(1, Math.min(7, Math.floor(driftDays)))
    const data = await get<{
      trash_points: {
        id: string
        lat: number
        lon: number
        class_name: string
        confidence: number
        detected_at: number
        boat_id: string
        drift_path?: {
          lat: number
          lon: number
          time_offset_hours: number
        }[]
      }[]
    }>(`/api/trash?drift_days=${days}`)
    return data.trash_points.map((t) => ({
      id: t.id,
      lat: t.lat,
      lon: t.lon,
      class_name: t.class_name as TrashPoint["class_name"],
      confidence: t.confidence,
      detected_at: t.detected_at,
      boat_id: t.boat_id,
      drift_path: t.drift_path ?? [],
    }))
  },

  async getStats() {
    return get<{
      total_trash_detected: number
      active_boats: number
      last_detection_time: number | null
      trash_by_class: Record<string, number>
    }>("/api/stats")
  },

  async getBoatHistory(boatId?: string) {
    const params = boatId ? `?boat_id=${encodeURIComponent(boatId)}` : ""
    return get<{
      minutes: number
      points: {
        boat_id: string
        gps_lat: number
        gps_lon: number
        heading: number
        timestamp: number
      }[]
    }>(`/api/boats/history${params}`)
  },

  async registerBoat(name: string, weightClass: string) {
    return post<{
      boat_id: string
      name: string
      weight_class: string
      api_key: string
    }>("/api/boats/register", { name, weight_class: weightClass })
  },
}
