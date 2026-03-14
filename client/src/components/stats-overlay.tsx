import { Card, CardContent } from "@/components/ui/card"
import type { TrashPoint } from "@/types"

interface StatsOverlayProps {
  boatCount: number
  trashPoints: TrashPoint[]
}

export function StatsOverlay({ boatCount, trashPoints }: StatsOverlayProps) {
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
        </CardContent>
      </Card>
    </div>
  )
}
