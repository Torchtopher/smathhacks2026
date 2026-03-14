import { Marker, Tooltip } from "react-leaflet"
import L from "leaflet"
import { renderToStaticMarkup } from "react-dom/server"
import { Sailboat, Ship } from "lucide-react"
import type { BoatState } from "@/types"
import { Badge } from "@/components/ui/badge"

interface BoatMarkersProps {
  boats: BoatState[]
  onBoatClick: (boat: BoatState) => void
}

function boatIcon(weightClass: BoatState["weight_class"]) {
  const IconComponent = weightClass === "light" ? Sailboat : Ship
  const size = weightClass === "light" ? 28 : 34
  const svg = renderToStaticMarkup(<IconComponent size={size} color="white" />)

  return L.divIcon({
    className: "",
    html: svg,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
}

export function BoatMarkers({ boats, onBoatClick }: BoatMarkersProps) {
  return (
    <>
      {boats.map((boat) => (
        <Marker
          key={boat.boat_id}
          position={[boat.gps_lat, boat.gps_lon]}
          icon={boatIcon(boat.weight_class)}
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
      ))}
    </>
  )
}
