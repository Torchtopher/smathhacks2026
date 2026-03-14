import { useEffect, useState } from "react"
import { Routes, Route } from "react-router"
import { TopBar } from "@/components/top-bar"
import { MapView } from "@/components/map-view"
import { AnalyticsPage } from "@/components/analytics-page"
import { AddBoatDialog } from "@/components/add-boat-dialog"
import { BoatDetailSheet } from "@/components/boat-detail-sheet"
import { demoBoats, demoTrash } from "@/lib/mock-data"
import type { BoatState, TrashPoint } from "@/types"

function App() {
  const [boats, setBoats] = useState<BoatState[]>(demoBoats)
  const [trashPoints] = useState<TrashPoint[]>(demoTrash)
  const [timeHours, setTimeHours] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedBoat, setSelectedBoat] = useState<BoatState | null>(null)
  const [dark, setDark] = useState(
    () => document.documentElement.classList.contains("dark")
  )

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark)
  }, [dark])

  function addBoat(boat: BoatState) {
    setBoats((prev) => [...prev, boat])
  }

  return (
    <div className="flex flex-col h-screen">
      <TopBar onAddBoat={() => setDialogOpen(true)} dark={dark} onToggleDark={() => setDark(!dark)} />
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
      </Routes>
      <AddBoatDialog open={dialogOpen} onOpenChange={setDialogOpen} onAdd={addBoat} />
      <BoatDetailSheet boat={selectedBoat} onOpenChange={(open) => { if (!open) setSelectedBoat(null) }} />
    </div>
  )
}

export default App
