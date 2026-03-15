import { memo } from "react"
import { Marker, Tooltip, Polyline } from "react-leaflet"
import L from "leaflet"
import { renderToStaticMarkup } from "react-dom/server"
import { Ship } from "lucide-react"
import type { BoatState } from "@/types"
import { Badge } from "@/components/ui/badge"

interface BoatMarkersProps {
  boats: BoatState[]
  selectedBoatId: string | null
  selectedBoatTrail: [number, number][] | null
  onBoatClick: (boat: BoatState) => void
  dark: boolean
}

const sizeByWeight = { light: 24, medium: 30, heavy: 36 } as const

// Cache icons by weight+dark key so renderToStaticMarkup runs only once per combo
const iconCache = new Map<string, L.DivIcon>()

function getBoatIcon(weightClass: BoatState["weight_class"], dark: boolean) {
  const key = `${weightClass}-${dark}`
  let icon = iconCache.get(key)
  if (!icon) {
    const size = sizeByWeight[weightClass]
    const color = dark ? "white" : "var(--primary)"
    const svg = renderToStaticMarkup(
      <span style={{ color }}>
        <Ship size={size} color="currentColor" />
      </span>
    )
    icon = L.divIcon({
      className: "",
      html: svg,
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
    })
    iconCache.set(key, icon)
  }
  return icon
}

const BoatMarker = memo(function BoatMarker({
  boat,
  isSelected,
  selectedBoatTrail,
  onBoatClick,
  dark,
}: {
  boat: BoatState
  isSelected: boolean
  selectedBoatTrail: [number, number][] | null
  onBoatClick: (boat: BoatState) => void
  dark: boolean
}) {
  const icon = getBoatIcon(boat.weight_class, dark)

  return (
    <>
      {selectedBoatTrail && isSelected && (
        <Polyline
          positions={selectedBoatTrail}
          pathOptions={{ color: "#56aad1", weight: 2, opacity: 0.6 }}
        />
      )}
      <Marker
        position={[boat.gps_lat, boat.gps_lon]}
        icon={icon}
        zIndexOffset={1000}
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
    </>
  )
})

export const BoatMarkers = memo(function BoatMarkers({
  boats,
  selectedBoatId,
  selectedBoatTrail,
  onBoatClick,
  dark,
}: BoatMarkersProps) {
  return (
    <>
      {boats.map((boat) => (
        <BoatMarker
          key={boat.boat_id}
          boat={boat}
          isSelected={boat.boat_id === selectedBoatId}
          selectedBoatTrail={selectedBoatTrail}
          onBoatClick={onBoatClick}
          dark={dark}
        />
      ))}
    </>
  )
})
