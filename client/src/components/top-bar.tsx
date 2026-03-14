import { NavLink } from "react-router"
import { Button } from "@/components/ui/button"
import { Waves, Sun, Moon } from "lucide-react"

interface TopBarProps {
  onAddBoat: () => void
  dark: boolean
  onToggleDark: () => void
}

export function TopBar({ onAddBoat, dark, onToggleDark }: TopBarProps) {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
      isActive
        ? "bg-primary text-primary-foreground"
        : "text-muted-foreground hover:text-foreground"
    }`

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-card border-border">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 text-foreground">
          <Waves className="h-6 w-6 text-primary dark:text-white" />
          <span className="text-lg font-semibold">OceanSight</span>
        </div>
        <nav className="flex items-center gap-1">
          <NavLink to="/" end className={linkClass}>Map</NavLink>
          <NavLink to="/analytics" className={linkClass}>Analytics</NavLink>
        </nav>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={onToggleDark}>
          {dark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </Button>
        <Button onClick={onAddBoat}>Add Your Boat</Button>
      </div>
    </div>
  )
}
