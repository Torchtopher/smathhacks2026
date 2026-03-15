import type { BoatState, Detection } from "@/types"

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${path}`)
  if (!res.ok) throw new Error(`GET ${path} failed (${res.status})`)
  return res.json()
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`POST ${path} failed (${res.status})`)
  return res.json()
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`PUT ${path} failed (${res.status})`)
  return res.json()
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${path}`, {
    method: "DELETE",
  })
  if (!res.ok) throw new Error(`DELETE ${path} failed (${res.status})`)
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
        has_image?: boolean
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
      has_image: b.has_image ?? false,
    }))
  },

  async getBoatImage(boatId: string): Promise<string | undefined> {
    const data = await get<{
      boat_id: string
      image: string | null
    }>(`/api/boats/${encodeURIComponent(boatId)}/image`)
    return data.image ?? undefined
  },

  async getDetections(options?: { includeDrift?: boolean; since?: number; limit?: number }): Promise<Detection[]> {
    const params = new URLSearchParams()
    if (options?.includeDrift) params.set("include_drift", "true")
    if (options?.since !== undefined) params.set("since", String(options.since))
    if (options?.limit !== undefined) params.set("limit", String(options.limit))
    const data = await get<{
      detections: {
        id: string
        lat: number
        lon: number
        confidence: number
        detected_at: number
        boat_id: string
        label: string
        drift_path?: {
          lat: number
          lon: number
          time_offset_hours: number
        }[]
        }[]
    }>(`/api/detections${params.size ? `?${params.toString()}` : ""}`)
    return data.detections.map((t) => ({
      id: t.id,
      lat: t.lat,
      lon: t.lon,
      confidence: t.confidence,
      detected_at: t.detected_at,
      boat_id: t.boat_id,
      label: t.label,
      drift_path: t.drift_path ?? [],
    }))
  },

  async getStats() {
    return get<{
      total_detections: number
      active_boats: number
      last_detection_time: number | null
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
    }>("/api/boats/register", { name, weight_class: weightClass })
  },

  async getAdminBoats() {
    return get<{
      boats: {
        boat_id: string
        name: string
        weight_class: string
        created_at: number
        last_reported_at: number | null
      }[]
    }>("/api/admin/boats")
  },

  async createAdminBoat(input: { boat_id?: string; name: string; weight_class: string }) {
    return post<{
      boat_id: string
      name: string
      weight_class: string
      created_at: number
      last_reported_at: number | null
    }>("/api/admin/boats", input)
  },

  async updateAdminBoat(
    boatId: string,
    input: { name?: string; weight_class?: string }
  ) {
    return put<{
      boat_id: string
      name: string
      weight_class: string
      created_at: number
      last_reported_at: number | null
    }>(`/api/admin/boats/${encodeURIComponent(boatId)}`, input)
  },

  async deleteAdminBoat(boatId: string, purgeData = true) {
    return del<{
      boat_id: string
      deleted_boat_rows: number
      deleted_state_rows: number
      deleted_position_rows: number
      deleted_detection_rows: number
    }>(`/api/admin/boats/${encodeURIComponent(boatId)}?purge_data=${purgeData ? "true" : "false"}`)
  },
}
