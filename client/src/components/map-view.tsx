import { useState, useMemo, useEffect } from "react"
import { MapContainer, TileLayer, ScaleControl } from "react-leaflet"
import { BoatMarkers } from "@/components/boat-markers"
import { DetectionLayer } from "@/components/detection-layer"
import { LayerToggles } from "@/components/layer-toggles"
import { StatsOverlay } from "@/components/stats-overlay"
import { TimeSlider } from "@/components/time-slider"
import type { BoatState, Detection } from "@/types"
import "leaflet/dist/leaflet.css"

const TILE_DARK = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
const TILE_LIGHT = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"

interface MapViewProps {
  boats: BoatState[]
  selectedBoatId: string | null
  selectedBoatTrail: [number, number][] | null
  onBoatClick: (boat: BoatState) => void
  detections: Detection[]
  showBoats: boolean
  showDetections: boolean
  onToggleBoats: () => void
  onToggleDetections: () => void
  timeHours: number
  onTimeChange: (hours: number) => void
  dark: boolean
}

export function MapView({
  boats,
  selectedBoatId,
  selectedBoatTrail,
  onBoatClick,
  detections,
  showBoats,
  showDetections,
  onToggleBoats,
  onToggleDetections,
  timeHours,
  onTimeChange,
  dark,
}: MapViewProps) {
  const [hoveredLabel, setHoveredLabel] = useState<string | null>(null)
  const [activeHoveredLabel, setActiveHoveredLabel] = useState<string | null>(null)

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setActiveHoveredLabel(hoveredLabel)
    }, 60)

    return () => window.clearTimeout(timeout)
  }, [hoveredLabel])

  const filteredDetections = useMemo(
    () => activeHoveredLabel ? detections.filter((d) => d.label === activeHoveredLabel) : detections,
    [detections, activeHoveredLabel]
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
          {showBoats ? (
            <BoatMarkers
              boats={boats}
              selectedBoatId={selectedBoatId}
              selectedBoatTrail={selectedBoatTrail}
              onBoatClick={onBoatClick}
              dark={dark}
            />
          ) : null}
          {showDetections ? (
            <DetectionLayer detections={filteredDetections} timeHours={timeHours} />
          ) : null}
        </MapContainer>
      <LayerToggles showBoats={showBoats} showDetections={showDetections} onToggleBoats={onToggleBoats} onToggleDetections={onToggleDetections} />
      <StatsOverlay boatCount={boats.length} detections={detections} hoveredLabel={hoveredLabel} onHoverLabel={setHoveredLabel} />
      <TimeSlider value={timeHours} onChange={onTimeChange} />
    </div>
  )
}
