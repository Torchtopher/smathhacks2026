import { useState } from "react"
import { TopBar } from "@/components/top-bar"
import { MapView } from "@/components/map-view"
import { AddBoatDialog } from "@/components/add-boat-dialog"
import { BoatDetailSheet } from "@/components/boat-detail-sheet"
import { demoBoats } from "@/lib/mock-data"
import type { BoatState } from "@/types"

function App() {
  const [boats, setBoats] = useState<BoatState[]>(demoBoats)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedBoat, setSelectedBoat] = useState<BoatState | null>(null)

  function addBoat(boat: BoatState) {
    setBoats((prev) => [...prev, boat])
  }

  return (
    <div className="flex flex-col h-screen">
      <TopBar onAddBoat={() => setDialogOpen(true)} />
      <MapView boats={boats} onBoatClick={setSelectedBoat} />
      <AddBoatDialog open={dialogOpen} onOpenChange={setDialogOpen} onAdd={addBoat} />
      <BoatDetailSheet boat={selectedBoat} onOpenChange={(open) => { if (!open) setSelectedBoat(null) }} />
    </div>
  )
}

export default App
