import { MapContainer, TileLayer } from "react-leaflet"
import { BoatMarkers } from "@/components/boat-markers"
import type { BoatState } from "@/types"
import "leaflet/dist/leaflet.css"

interface MapViewProps {
  boats: BoatState[]
  onBoatClick: (boat: BoatState) => void
}

export function MapView({ boats, onBoatClick }: MapViewProps) {
  return (
    <MapContainer
      center={[44.2, -68.8]}
      zoom={10}
      className="flex-1 w-full"
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      <BoatMarkers boats={boats} onBoatClick={onBoatClick} />
    </MapContainer>
  )
}
