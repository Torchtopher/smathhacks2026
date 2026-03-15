import { Suspense, lazy, useCallback, useEffect, useRef, useState } from "react"
import { Routes, Route } from "react-router"
import { TopBar } from "@/components/top-bar"
import { MapView } from "@/components/map-view"
import { AddBoatDialog } from "@/components/add-boat-dialog"
import { BoatDetailSheet } from "@/components/boat-detail-sheet"
import { api } from "@/lib/api"
import type { BoatState, Detection } from "@/types"

const POLL_INTERVAL = 10_000

const AnalyticsPage = lazy(async () => {
  const module = await import("@/components/analytics-page")
  return { default: module.AnalyticsPage }
})

const AdminPage = lazy(async () => {
  const module = await import("@/components/admin-page")
  return { default: module.AdminPage }
})

type TrailPoint = [number, number]

function sameTrails(a: TrailPoint[] | null, b: TrailPoint[] | null) {
  if (a === b) return true
  if (!a || !b) return false
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i += 1) {
    if (a[i][0] !== b[i][0] || a[i][1] !== b[i][1]) return false
  }
  return true
}

function sameBoatImage(a: string | undefined, b: string | undefined) {
  return a === b
}

function sameBoats(a: BoatState[], b: BoatState[]) {
  if (a === b) return true
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i += 1) {
    const prev = a[i]
    const next = b[i]
    if (
      prev.boat_id !== next.boat_id ||
      prev.name !== next.name ||
      prev.weight_class !== next.weight_class ||
      prev.gps_lat !== next.gps_lat ||
      prev.gps_lon !== next.gps_lon ||
      prev.heading !== next.heading ||
      prev.timestamp !== next.timestamp ||
      prev.has_image !== next.has_image ||
      !sameBoatImage(prev.image, next.image)
    ) {
      return false
    }
  }
  return true
}

function sameDriftPath(
  a: Detection["drift_path"] | undefined,
  b: Detection["drift_path"] | undefined
) {
  const prev = a ?? []
  const next = b ?? []
  if (prev.length !== next.length) return false
  for (let i = 0; i < prev.length; i += 1) {
    if (
      prev[i].lat !== next[i].lat ||
      prev[i].lon !== next[i].lon ||
      prev[i].time_offset_hours !== next[i].time_offset_hours
    ) {
      return false
    }
  }
  return true
}

function mergeDetections(current: Detection[], incoming: Detection[]) {
  if (incoming.length === 0) return current

  const merged = new Map<string, Detection>()
  for (const detection of current) merged.set(detection.id, detection)

  let changed = false
  for (const detection of incoming) {
    const existing = merged.get(detection.id)
    if (!existing || !sameDetections([existing], [detection])) {
      merged.set(detection.id, detection)
      changed = true
    }
  }

  if (!changed) return current

  return [...merged.values()].sort((a, b) => b.detected_at - a.detected_at)
}

function sameDetections(a: Detection[], b: Detection[]) {
  if (a === b) return true
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i += 1) {
    const prev = a[i]
    const next = b[i]
    if (
      prev.id !== next.id ||
      prev.lat !== next.lat ||
      prev.lon !== next.lon ||
      prev.confidence !== next.confidence ||
      prev.detected_at !== next.detected_at ||
      prev.boat_id !== next.boat_id ||
      prev.label !== next.label ||
      !sameDriftPath(prev.drift_path, next.drift_path)
    ) {
      return false
    }
  }
  return true
}

function RouteFallback() {
  return <div className="flex-1 p-6 text-sm text-muted-foreground">Loading...</div>
}

function App() {
  const [boats, setBoats] = useState<BoatState[]>([])
  const [detections, setDetections] = useState<Detection[]>([])
  const [selectedBoatTrail, setSelectedBoatTrail] = useState<TrailPoint[] | null>(null)
  const [selectedBoatImage, setSelectedBoatImage] = useState<string | undefined>(undefined)
  const [showBoats, setShowBoats] = useState(true)
  const [showDetections, setShowDetections] = useState(true)
  const [timeHours, setTimeHours] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedBoatId, setSelectedBoatId] = useState<string | null>(null)
  const [connected, setConnected] = useState<boolean | null>(null)
  const [dark, setDark] = useState(
    () => document.documentElement.classList.contains("dark")
  )
  const latestDetectionTimestampRef = useRef<number | null>(null)
  const selectedBoatBase = selectedBoatId
    ? boats.find((boat) => boat.boat_id === selectedBoatId) ?? null
    : null
  const selectedBoat = selectedBoatBase
    ? {
      ...selectedBoatBase,
      trail: selectedBoatTrail ?? undefined,
      image: selectedBoatImage,
    }
    : null

  const handleBoatClick = useCallback((boat: BoatState) => {
    setSelectedBoatTrail(null)
    setSelectedBoatImage(undefined)
    setSelectedBoatId(boat.boat_id)
  }, [])

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark)
  }, [dark])

  const fetchLiveData = useCallback(async () => {
    try {
      const includeDrift = timeHours > 0
      const [nextBoats, nextDetections] = await Promise.all([
        api.getBoats(),
        api.getDetections(
          latestDetectionTimestampRef.current === null || includeDrift
            ? { includeDrift }
            : { includeDrift, since: latestDetectionTimestampRef.current }
        ),
      ])

      setBoats((current) => (sameBoats(current, nextBoats) ? current : nextBoats))
      setDetections((current) => {
        const merged = latestDetectionTimestampRef.current === null || includeDrift
          ? nextDetections
          : mergeDetections(current, nextDetections)
        return sameDetections(current, merged) ? current : merged
      })
      const newest = nextDetections[0]?.detected_at
      if (newest !== undefined) {
        latestDetectionTimestampRef.current = latestDetectionTimestampRef.current === null
          ? newest
          : Math.max(latestDetectionTimestampRef.current, newest)
      }

      setConnected(true)
    } catch (err) {
      console.error("Failed to fetch data:", err)
      setConnected(false)
    }
  }, [timeHours])

  useEffect(() => {
    latestDetectionTimestampRef.current = null
  }, [timeHours])

  const fetchSelectedBoatHistory = useCallback(async (boatId: string) => {
    try {
      const history = await api.getBoatHistory(boatId)
      const trail = history.points.map((point) => [point.gps_lat, point.gps_lon] as TrailPoint)
      setSelectedBoatTrail((current) => (sameTrails(current, trail) ? current : trail))
    } catch (err) {
      console.error(`Failed to fetch history for boat ${boatId}:`, err)
    }
  }, [])

  const fetchSelectedBoatImage = useCallback(async (boatId: string) => {
    try {
      const image = await api.getBoatImage(boatId)
      setSelectedBoatImage((current) => (current === image ? current : image))
    } catch (err) {
      console.error(`Failed to fetch image for boat ${boatId}:`, err)
      setSelectedBoatImage(undefined)
    }
  }, [])

  useEffect(() => {
    fetchLiveData()
    const id = setInterval(fetchLiveData, POLL_INTERVAL)
    return () => clearInterval(id)
  }, [fetchLiveData])

  useEffect(() => {
    if (!selectedBoatId) {
      setSelectedBoatTrail(null)
      setSelectedBoatImage(undefined)
      return
    }

    void fetchSelectedBoatHistory(selectedBoatId)
    if (selectedBoatBase?.has_image) {
      void fetchSelectedBoatImage(selectedBoatId)
    } else {
      setSelectedBoatImage(undefined)
    }
    const id = setInterval(() => {
      void fetchSelectedBoatHistory(selectedBoatId)
    }, POLL_INTERVAL)
    return () => clearInterval(id)
  }, [fetchSelectedBoatHistory, fetchSelectedBoatImage, selectedBoatBase?.has_image, selectedBoatId])

  return (
    <div className="flex flex-col h-screen">
      <TopBar onAddBoat={() => setDialogOpen(true)} dark={dark} onToggleDark={() => setDark(!dark)} connected={connected} />
      <Routes>
        <Route path="/" element={
          <MapView
            boats={boats}
            selectedBoatId={selectedBoatId}
            selectedBoatTrail={selectedBoatTrail}
            onBoatClick={handleBoatClick}
            detections={detections}
            showBoats={showBoats}
            showDetections={showDetections}
            onToggleBoats={() => setShowBoats((value) => !value)}
            onToggleDetections={() => setShowDetections((value) => !value)}
            timeHours={timeHours}
            onTimeChange={setTimeHours}
            dark={dark}
          />
        } />
        <Route path="/analytics" element={
          <Suspense fallback={<RouteFallback />}>
            <AnalyticsPage boats={boats} detections={detections} />
          </Suspense>
        } />
        <Route path="/admin" element={
          <Suspense fallback={<RouteFallback />}>
            <AdminPage onDataChanged={fetchLiveData} />
          </Suspense>
        } />
      </Routes>
      <AddBoatDialog open={dialogOpen} onOpenChange={setDialogOpen} />
      <BoatDetailSheet
        boat={selectedBoat}
        onOpenChange={(open) => {
          if (!open) setSelectedBoatId(null)
        }}
      />
    </div>
  )
}

export default App
