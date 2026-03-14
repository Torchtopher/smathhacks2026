import L from "leaflet"
import { Marker, Tooltip, Polyline, CircleMarker } from "react-leaflet"
import MarkerClusterGroup from "react-leaflet-cluster"
import { TRASH_BG_CLASS, TRASH_COLOR } from "@/lib/colors"
import type { TrashPoint } from "@/types"

interface TrashLayerProps {
  trashPoints: TrashPoint[]
  timeHours: number
}

const trashIcon = L.divIcon({
  html: `<div class="${TRASH_BG_CLASS} w-3 h-3 rounded-full border-2 border-white"></div>`,
  className: "",
  iconSize: [12, 12],
  iconAnchor: [6, 6],
})

function clusterIcon(cluster: { getChildCount: () => number }) {
  const count = cluster.getChildCount()
  return L.divIcon({
    html: `<div class="w-8 h-8 rounded-full bg-red-500/80 text-white flex items-center justify-center text-sm font-semibold border-2 border-white">${count}</div>`,
    className: "",
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  })
}

function timeAgo(ts: number) {
  const mins = Math.round((Date.now() - ts) / 60000)
  if (mins < 60) return `${mins}m ago`
  return `${Math.round(mins / 60)}h ago`
}

export function TrashLayer({ trashPoints, timeHours }: TrashLayerProps) {
  return (
    <>
      <MarkerClusterGroup iconCreateFunction={clusterIcon} chunkedLoading>
        {trashPoints.map((tp) => (
          <Marker
            key={tp.id}
            position={[tp.lat, tp.lon]}
            icon={trashIcon}
          >
            <Tooltip>
              <div className="text-sm">
                <div className="font-semibold">Garbage</div>
                <div>{(tp.confidence * 100).toFixed(0)}% confidence</div>
                <div>{timeAgo(tp.detected_at)}</div>
              </div>
            </Tooltip>
          </Marker>
        ))}
      </MarkerClusterGroup>

      {timeHours > 0 &&
        trashPoints.map((tp) => {
          const visible = (tp.drift_path ?? []).filter(
            (d) => d.time_offset_hours <= timeHours
          )
          if (visible.length < 2) return null
          const last = visible[visible.length - 1]
          return (
            <span key={`drift-${tp.id}`}>
              <Polyline
                positions={visible.map((d) => [d.lat, d.lon])}
                pathOptions={{
                  color: TRASH_COLOR,
                  weight: 2,
                  dashArray: "6 4",
                  opacity: 0.6,
                }}
              />
              <CircleMarker
                center={[last.lat, last.lon]}
                radius={5}
                pathOptions={{
                  color: TRASH_COLOR,
                  fillColor: TRASH_COLOR,
                  fillOpacity: 0.4,
                  weight: 1,
                }}
              />
            </span>
          )
        })}
    </>
  )
}
