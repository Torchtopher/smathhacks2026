import { useEffect, useState } from "react"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Ship, Navigation, MapPin } from "lucide-react"
import type { BoatState } from "@/types"

interface BoatDetailSheetProps {
  boat: BoatState | null
  onOpenChange: (open: boolean) => void
}

export function BoatDetailSheet({ boat, onOpenChange }: BoatDetailSheetProps) {
  const [imageOpen, setImageOpen] = useState(false)

  useEffect(() => {
    if (!boat) setImageOpen(false)
  }, [boat])

  return (
    <Sheet open={!!boat} onOpenChange={onOpenChange}>
      <SheetContent side="right">
        {boat && (
          <>
            <SheetHeader>
              <div className="flex items-center gap-2">
                <Ship className="h-5 w-5 text-primary" />
                <SheetTitle>{boat.name}</SheetTitle>
              </div>
              <SheetDescription>Boat details and position</SheetDescription>
            </SheetHeader>
            <div className="space-y-4 px-4">
              {boat.image && (
                <div className="overflow-hidden rounded-lg">
                  <button
                    type="button"
                    className="w-full text-left"
                    onClick={() => setImageOpen(true)}
                  >
                    <img
                      src={boat.image}
                      alt={`Latest image from ${boat.name}`}
                      className="w-full h-48 object-cover cursor-zoom-in"
                    />
                    <div className="mt-1 text-xs text-muted-foreground">Click image to open fullscreen</div>
                  </button>
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
            <Dialog open={imageOpen} onOpenChange={setImageOpen}>
              <DialogContent className="w-[98vw] h-[96vh] max-w-[98vw] sm:max-w-[98vw] p-3 gap-3">
                <DialogHeader>
                  <DialogTitle>{boat.name} - Latest Image</DialogTitle>
                </DialogHeader>
                {boat.image && (
                  <div className="flex-1 min-h-0 overflow-hidden rounded-md bg-black/80">
                    <img
                      src={boat.image}
                      alt={`Latest image for ${boat.name}`}
                      className="w-full h-full object-contain"
                    />
                  </div>
                )}
              </DialogContent>
            </Dialog>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
