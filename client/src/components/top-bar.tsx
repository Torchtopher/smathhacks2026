import { Button } from "@/components/ui/button"
import { Waves } from "lucide-react"

interface TopBarProps {
  onAddBoat: () => void
}

export function TopBar({ onAddBoat }: TopBarProps) {
  return (
    <div className="flex items-center justify-between px-4 py-3 bg-card border-b border-border">
      <div className="flex items-center gap-2 text-foreground">
        <Waves className="h-6 w-6 text-primary" />
        <span className="text-lg font-semibold">OceanSight</span>
      </div>
      <Button onClick={onAddBoat}>Add Your Boat</Button>
    </div>
  )
}
