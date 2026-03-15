import { useState, useMemo } from "react"
import { MapContainer, TileLayer, ScaleControl } from "react-leaflet"
import { BoatMarkers } from "@/components/boat-markers"
import { DetectionLayer } from "@/components/detection-layer"
import { StatsOverlay } from "@/components/stats-overlay"
import { TimeSlider } from "@/components/time-slider"
import type { BoatState, Detection } from "@/types"
import "leaflet/dist/leaflet.css"

const TILE_DARK = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
const TILE_LIGHT = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"

interface MapViewProps {
  boats: BoatState[]
  selectedBoatId: string | null
  onBoatClick: (boat: BoatState) => void
  detections: Detection[]
  timeHours: number
  onTimeChange: (hours: number) => void
  dark: boolean
}

export function MapView({
  boats,
  selectedBoatId,
  onBoatClick,
  detections,
  timeHours,
  onTimeChange,
  dark,
}: MapViewProps) {
  const [hoveredLabel, setHoveredLabel] = useState<string | null>(null)

  const filteredDetections = useMemo(
    () => hoveredLabel ? detections.filter((d) => d.label === hoveredLabel) : detections,
    [detections, hoveredLabel]
  )

  return (
    <div className="relative flex-1">
      <MapContainer
        center={[39.8283, -98.5795]}
        zoom={4}
        className="absolute inset-0 w-full h-full"
      >
        <TileLayer
          key={dark ? "dark" : "light"}
          url={dark ? TILE_DARK : TILE_LIGHT}
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        />
        <ScaleControl position="bottomright" />
        <BoatMarkers boats={boats} selectedBoatId={selectedBoatId} onBoatClick={onBoatClick} dark={dark} />
        <DetectionLayer detections={filteredDetections} timeHours={timeHours} />
      </MapContainer>
      <StatsOverlay boatCount={boats.length} detections={detections} hoveredLabel={hoveredLabel} onHoverLabel={setHoveredLabel} />
      <TimeSlider value={timeHours} onChange={onTimeChange} />
    </div>
  )
}
