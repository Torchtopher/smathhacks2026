import { MapContainer, TileLayer } from "react-leaflet"
import { BoatMarkers } from "@/components/boat-markers"
import { TrashLayer } from "@/components/trash-layer"
import { StatsOverlay } from "@/components/stats-overlay"
import { TimeSlider } from "@/components/time-slider"
import type { BoatState, TrashPoint } from "@/types"
import "leaflet/dist/leaflet.css"

const TILE_DARK = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
const TILE_LIGHT = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"

interface MapViewProps {
  boats: BoatState[]
  selectedBoatId: string | null
  onBoatClick: (boat: BoatState) => void
  trashPoints: TrashPoint[]
  timeHours: number
  onTimeChange: (hours: number) => void
  dark: boolean
}

export function MapView({
  boats,
  selectedBoatId,
  onBoatClick,
  trashPoints,
  timeHours,
  onTimeChange,
  dark,
}: MapViewProps) {
  return (
    <div className="relative flex-1">
      <MapContainer
        center={[35.0, -55.0]}
        zoom={10}
        className="absolute inset-0 w-full h-full"
      >
        <TileLayer
          key={dark ? "dark" : "light"}
          url={dark ? TILE_DARK : TILE_LIGHT}
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        />
        <BoatMarkers boats={boats} selectedBoatId={selectedBoatId} onBoatClick={onBoatClick} dark={dark} />
        <TrashLayer trashPoints={trashPoints} timeHours={timeHours} />
      </MapContainer>
      <StatsOverlay boatCount={boats.length} trashPoints={trashPoints} />
      <TimeSlider value={timeHours} onChange={onTimeChange} />
    </div>
  )
}
