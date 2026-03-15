import { useCallback, useEffect, useState } from "react"
import { Routes, Route } from "react-router"
import { TopBar } from "@/components/top-bar"
import { MapView } from "@/components/map-view"
import { AnalyticsPage } from "@/components/analytics-page"
import { AdminPage } from "@/components/admin-page"
import { AddBoatDialog } from "@/components/add-boat-dialog"
import { BoatDetailSheet } from "@/components/boat-detail-sheet"
import { api } from "@/lib/api"
import type { BoatState, TrashPoint } from "@/types"

const POLL_INTERVAL = 5_000

function App() {
  const [boats, setBoats] = useState<BoatState[]>([])
  const [trashPoints, setTrashPoints] = useState<TrashPoint[]>([])
  const [timeHours, setTimeHours] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedBoat, setSelectedBoat] = useState<BoatState | null>(null)
  const [connected, setConnected] = useState<boolean | null>(null)
  const [dark, setDark] = useState(
    () => document.documentElement.classList.contains("dark")
  )

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark)
  }, [dark])

  const fetchData = useCallback(async () => {
    try {
      const [b, t, h] = await Promise.all([api.getBoats(), api.getTrash(), api.getBoatHistory()])
      const trails = new Map<string, [number, number][]>()
      for (const p of h.points) {
        let arr = trails.get(p.boat_id)
        if (!arr) { arr = []; trails.set(p.boat_id, arr) }
        arr.push([p.gps_lat, p.gps_lon])
      }
      setBoats(b.map(boat => ({ ...boat, trail: trails.get(boat.boat_id) })))
      setTrashPoints(t)
      setConnected(true)
    } catch (err) {
      console.error("Failed to fetch data:", err)
      setConnected(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const id = setInterval(fetchData, POLL_INTERVAL)
    return () => clearInterval(id)
  }, [fetchData])

  return (
    <div className="flex flex-col h-screen">
      <TopBar onAddBoat={() => setDialogOpen(true)} dark={dark} onToggleDark={() => setDark(!dark)} connected={connected} />
      <Routes>
        <Route path="/" element={
          <MapView
            boats={boats}
            selectedBoatId={selectedBoat?.boat_id ?? null}
            onBoatClick={setSelectedBoat}
            trashPoints={trashPoints}
            timeHours={timeHours}
            onTimeChange={setTimeHours}
            dark={dark}
          />
        } />
        <Route path="/analytics" element={
          <AnalyticsPage boats={boats} trashPoints={trashPoints} />
        } />
        <Route path="/admin" element={
          <AdminPage onDataChanged={fetchData} />
        } />
      </Routes>
      <AddBoatDialog open={dialogOpen} onOpenChange={setDialogOpen} />
      <BoatDetailSheet boat={selectedBoat} onOpenChange={(open) => { if (!open) setSelectedBoat(null) }} />
    </div>
  )
}

export default App
