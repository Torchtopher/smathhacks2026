import { Card, CardContent } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"

interface LayerTogglesProps {
  showBoats: boolean
  showDetections: boolean
  onToggleBoats: () => void
  onToggleDetections: () => void
}

export function LayerToggles({ showBoats, showDetections, onToggleBoats, onToggleDetections }: LayerTogglesProps) {
  return (
    <div className="absolute top-4 right-4 z-[1000]">
      <Card className="bg-card/80 backdrop-blur-sm">
        <CardContent className="space-y-2">
          <Label htmlFor="toggle-boats" className="cursor-pointer justify-between gap-3 text-sm text-foreground">
            <span className="text-muted-foreground">Boats</span>
            <Checkbox
              id="toggle-boats"
              checked={showBoats}
              onCheckedChange={onToggleBoats}
            />
          </Label>
          <Label htmlFor="toggle-detections" className="cursor-pointer justify-between gap-3 text-sm text-foreground">
            <span className="text-muted-foreground">Detections</span>
            <Checkbox
              id="toggle-detections"
              checked={showDetections}
              onCheckedChange={onToggleDetections}
            />
          </Label>
        </CardContent>
      </Card>
    </div>
  )
}
