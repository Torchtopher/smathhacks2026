import { Card, CardContent } from "@/components/ui/card"
import { TRASH_BG } from "@/lib/colors"
import type { TrashPoint } from "@/types"

interface StatsOverlayProps {
  boatCount: number
  trashPoints: TrashPoint[]
}

export function StatsOverlay({ boatCount, trashPoints }: StatsOverlayProps) {
  const byType = trashPoints.reduce<Record<string, number>>((acc, tp) => {
    acc[tp.class_name] = (acc[tp.class_name] || 0) + 1
    return acc
  }, {})

  return (
    <div className="absolute bottom-4 left-4 z-[1000]">
      <Card className="bg-card/80 backdrop-blur-sm w-56">
        <CardContent className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Active Boats</span>
            <span className="font-semibold">{boatCount}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Trash Detected</span>
            <span className="font-semibold">{trashPoints.length}</span>
          </div>
          <div className="border-t pt-2 space-y-1.5">
            <div className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              By Type
            </div>
            {Object.entries(byType).map(([name, count]) => (
              <div key={name} className="flex items-center gap-2 text-sm">
                <span
                  className={`inline-block w-2.5 h-2.5 rounded-full ${TRASH_BG[name as TrashPoint["class_name"]]}`}
                />
                <span className="capitalize flex-1">{name}</span>
                <span className="font-medium">{count}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
