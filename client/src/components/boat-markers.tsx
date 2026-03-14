import { Marker, Tooltip, Polyline } from "react-leaflet"
import L from "leaflet"
import { renderToStaticMarkup } from "react-dom/server"
import { Sailboat, Ship } from "lucide-react"
import type { BoatState } from "@/types"
import { Badge } from "@/components/ui/badge"

interface BoatMarkersProps {
  boats: BoatState[]
  selectedBoatId: string | null
  onBoatClick: (boat: BoatState) => void
  dark: boolean
}

function boatIcon(weightClass: BoatState["weight_class"], dark: boolean) {
  const IconComponent = weightClass === "light" ? Sailboat : Ship
  const size = weightClass === "light" ? 28 : 34
  const color = dark ? "white" : "var(--primary)"
  const svg = renderToStaticMarkup(
    <span style={{ color }}>
      <IconComponent size={size} color="currentColor" />
    </span>
  )

  return L.divIcon({
    className: "",
    html: svg,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
}

export function BoatMarkers({ boats, selectedBoatId, onBoatClick, dark }: BoatMarkersProps) {
  return (
    <>
      {boats.map((boat) => (
        <span key={boat.boat_id}>
          {boat.trail && boat.boat_id === selectedBoatId && (
            <Polyline
              positions={boat.trail}
              pathOptions={{ color: "#56aad1", weight: 2, opacity: 0.6 }}
            />
          )}
          <Marker
            position={[boat.gps_lat, boat.gps_lon]}
            icon={boatIcon(boat.weight_class, dark)}
            eventHandlers={{ click: () => onBoatClick(boat) }}
          >
            <Tooltip>
              <div className="space-y-1 text-sm">
                <div className="font-semibold text-base">{boat.name}</div>
                <div>
                  <Badge variant="secondary" className="text-xs">
                    {boat.weight_class}
                  </Badge>
                </div>
                <div className="text-muted-foreground">
                  {boat.gps_lat.toFixed(4)}, {boat.gps_lon.toFixed(4)}
                </div>
                <div className="text-muted-foreground">Heading: {boat.heading}°</div>
              </div>
            </Tooltip>
          </Marker>
        </span>
      ))}
    </>
  )
}
