import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
import { Badge } from "@/components/ui/badge"
import { Sailboat, Ship, Navigation, MapPin } from "lucide-react"
import type { BoatState } from "@/types"

interface BoatDetailSheetProps {
  boat: BoatState | null
  onOpenChange: (open: boolean) => void
}

export function BoatDetailSheet({ boat, onOpenChange }: BoatDetailSheetProps) {
  return (
    <Sheet open={!!boat} onOpenChange={onOpenChange}>
      <SheetContent side="right">
        {boat && (
          <>
            <SheetHeader>
              <div className="flex items-center gap-2">
                {boat.weight_class === "light" ? (
                  <Sailboat className="h-5 w-5 text-primary" />
                ) : (
                  <Ship className="h-5 w-5 text-primary" />
                )}
                <SheetTitle>{boat.name}</SheetTitle>
              </div>
              <SheetDescription>Boat details and position</SheetDescription>
            </SheetHeader>
            <div className="space-y-4 px-4">
              {boat.image && (
                <div className="overflow-hidden rounded-lg">
                  <img
                    src={boat.image}
                    alt={`Latest sighting from ${boat.name}`}
                    className="w-full h-48 object-cover"
                  />
                </div>
              )}
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Class</span>
                <Badge>{boat.weight_class}</Badge>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <span>{boat.gps_lat.toFixed(4)}, {boat.gps_lon.toFixed(4)}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Navigation className="h-4 w-4 text-muted-foreground" />
                <span>Heading: {boat.heading}°</span>
              </div>
              <div className="text-xs text-muted-foreground">
                Last updated: {new Date(boat.timestamp).toLocaleString()}
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
