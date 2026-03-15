import { useState, useEffect, useRef } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Slider } from "@/components/ui/slider"

interface DriftControlsProps {
  value: number
  onChange: (hours: number) => void
}

const MAX_HOURS = 168

function formatLabel(hours: number): string {
  if (hours === 0) return "Now"
  const days = Math.floor(hours / 24)
  const remaining = hours % 24
  if (days === 0) return `+${remaining}h`
  if (remaining === 0) return `+${days}d`
  return `+${days}d ${remaining}h`
}

export function TimeSlider({ value, onChange }: DriftControlsProps) {
  // Local state for responsive slider, debounced commit to parent
  const [local, setLocal] = useState(value)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  // Sync if parent value changes externally
  useEffect(() => { setLocal(value) }, [value])

  useEffect(() => {
    return () => {
      clearTimeout(timer.current)
    }
  }, [])

  function handleChange(v: number) {
    setLocal(v)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => onChange(v), 150)
  }

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-[1000]">
      <Card className="bg-card/80 backdrop-blur-sm">
        <CardContent className="px-6 space-y-2">
          <div className="flex items-center justify-between text-sm font-medium">
            <span>Drift Prediction</span>
            <span className="text-muted-foreground">{formatLabel(local)}</span>
          </div>
          <Slider
            min={0}
            max={MAX_HOURS}
            step={1}
            value={[local]}
            onValueChange={([v]) => handleChange(v)}
            className="w-56"
          />
        </CardContent>
      </Card>
    </div>
  )
}
