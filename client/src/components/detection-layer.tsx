import { memo, useMemo } from "react"
import L from "leaflet"
import { Marker, Tooltip, Polyline, CircleMarker } from "react-leaflet"
import MarkerClusterGroup from "react-leaflet-cluster"
import { LABEL_BG_CLASSES, LABEL_COLORS, LABEL_DISPLAY_NAMES } from "@/lib/colors"
import type { Detection } from "@/types"

interface DetectionLayerProps {
  detections: Detection[]
  timeHours: number
}

interface VisibleDriftPath {
  id: string
  label: string
  points: [number, number][]
}

function getLabelIcon(label: string) {
  const bg = LABEL_BG_CLASSES[label] ?? "bg-red-500"
  return L.divIcon({
    html: `<div class="${bg} w-3 h-3 rounded-full border-2 border-white"></div>`,
    className: "",
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  })
}

const iconCache: Record<string, L.DivIcon> = {}
function getCachedIcon(label: string) {
  if (!iconCache[label]) iconCache[label] = getLabelIcon(label)
  return iconCache[label]
}

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
  const mins = Math.round((Date.now() - ts * 1000) / 60000)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.round(hours / 24)}d ago`
}

function ageOpacity(detectedAt: number): number {
  const ageHours = (Date.now() - detectedAt * 1000) / 3600000
  return Math.max(0.3, 1 - (ageHours / 24) * 0.7)
}

const DetectionMarker = memo(function DetectionMarker({ tp }: { tp: Detection }) {
  return (
    <Marker
      position={[tp.lat, tp.lon]}
      icon={getCachedIcon(tp.label)}
      opacity={ageOpacity(tp.detected_at)}
    >
      <Tooltip>
        <div className="text-sm">
          <div className="font-semibold">{LABEL_DISPLAY_NAMES[tp.label] ?? tp.label}</div>
          <div>{(tp.confidence * 100).toFixed(0)}% confidence</div>
          <div>{timeAgo(tp.detected_at)}</div>
        </div>
      </Tooltip>
    </Marker>
  )
})

const DriftPath = memo(function DriftPath({ path }: { path: VisibleDriftPath }) {
  const last = path.points[path.points.length - 1]
  const color = LABEL_COLORS[path.label] ?? LABEL_COLORS.trash
  return (
    <>
      <Polyline
        positions={path.points}
        pathOptions={{
          color,
          weight: 2,
          dashArray: "6 4",
          opacity: 0.6,
        }}
      />
      <CircleMarker
        center={[last[0], last[1]]}
        radius={5}
        pathOptions={{
          color,
          fillColor: color,
          fillOpacity: 0.4,
          weight: 1,
        }}
      />
    </>
  )
})

export const DetectionLayer = memo(function DetectionLayer({ detections, timeHours }: DetectionLayerProps) {
  const visibleDriftPaths = useMemo(() => {
    if (timeHours <= 0) return [] as VisibleDriftPath[]

    return detections.flatMap((tp) => {
      const visible = (tp.drift_path ?? [])
        .filter((point) => point.time_offset_hours <= timeHours)
        .map((point) => [point.lat, point.lon] as [number, number])

      return visible.length < 2
        ? []
        : [{ id: tp.id, label: tp.label, points: visible }]
    })
  }, [detections, timeHours])

  return (
    <>
      <MarkerClusterGroup iconCreateFunction={clusterIcon} chunkedLoading maxClusterRadius={40} disableClusteringAtZoom={18}>
        {detections.map((tp) => (
          <DetectionMarker key={tp.id} tp={tp} />
        ))}
      </MarkerClusterGroup>

      {visibleDriftPaths.map((path) => (
        <DriftPath key={`drift-${path.id}`} path={path} />
      ))}
    </>
  )
})
