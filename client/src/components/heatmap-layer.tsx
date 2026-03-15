import { useEffect } from "react"
import { useMap } from "react-leaflet"
import L from "leaflet"
import "leaflet.heat"
import type { Detection } from "@/types"

interface HeatmapLayerProps {
  detections: Detection[]
}

export function HeatmapLayer({ detections }: HeatmapLayerProps) {
  const map = useMap()

  useEffect(() => {
    if (detections.length === 0) return

    const points: [number, number, number][] = detections.map((d) => [
      d.lat,
      d.lon,
      d.confidence,
    ])

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const heat = (L as any).heatLayer(points, {
      radius: 25,
      blur: 15,
      maxZoom: 17,
      max: 1.0,
      gradient: {
        0.2: "#0000ff",
        0.4: "#00ffff",
        0.6: "#00ff00",
        0.8: "#ffff00",
        1.0: "#ff0000",
      },
    }) as L.Layer

    heat.addTo(map)

    // Fit bounds to detection locations
    const bounds = L.latLngBounds(detections.map((d) => [d.lat, d.lon]))
    map.fitBounds(bounds, { padding: [30, 30] })

    return () => {
      map.removeLayer(heat)
    }
  }, [map, detections])

  return null
}
