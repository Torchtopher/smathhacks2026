import { useMemo } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { LABEL_BG_CLASSES, LABEL_DISPLAY_NAMES } from "@/lib/colors"
import type { Detection } from "@/types"

interface StatsOverlayProps {
  boatCount: number
  detections: Detection[]
  hoveredLabel: string | null
  onHoverLabel: (label: string | null) => void
}

export function StatsOverlay({ boatCount, detections, hoveredLabel, onHoverLabel }: StatsOverlayProps) {

  const labelCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const tp of detections) {
      const label = tp.label
      counts[label] = (counts[label] || 0) + 1
    }
    return counts
  }, [detections])

  const labels = Object.keys(labelCounts).sort()

  return (
    <div className="absolute bottom-4 left-4 z-[1000]">
      <Card className="bg-card/80 backdrop-blur-sm w-56">
        <CardContent className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Active Boats</span>
            <span className="font-semibold">{boatCount}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Total Detected</span>
            <span className="font-semibold">{detections.length}</span>
          </div>
          {labels.length > 0 && (
            <div className="space-y-1 pt-1 border-t border-border">
              {labels.map((label) => (
                <div
                  key={label}
                  className="flex items-center justify-between text-sm transition-opacity duration-150"
                  style={{
                    opacity: hoveredLabel === null || hoveredLabel === label ? 1 : 0.3,
                  }}
                  onMouseEnter={() => onHoverLabel(label)}
                  onMouseLeave={() => onHoverLabel(null)}
                >
                  <span className="flex items-center gap-2">
                    <span className={`inline-block w-2.5 h-2.5 rounded-full ${LABEL_BG_CLASSES[label] ?? "bg-gray-500"}`} />
                    <span className="text-muted-foreground">{LABEL_DISPLAY_NAMES[label] ?? label}</span>
                  </span>
                  <span className="font-semibold">{labelCounts[label]}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
