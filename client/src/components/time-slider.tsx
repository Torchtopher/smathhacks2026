import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

interface DriftControlsProps {
  value: number
  onChange: (hours: number) => void
}

const STEPS = [
  { hours: 0, label: "Now" },
  { hours: 4, label: "+4h" },
  { hours: 8, label: "+8h" },
  { hours: 12, label: "+12h" },
  { hours: 18, label: "+18h" },
  { hours: 24, label: "+24h" },
]

export function TimeSlider({ value, onChange }: DriftControlsProps) {
  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-[1000]">
      <Card className="bg-card/80 backdrop-blur-sm">
        <CardContent className="px-6 space-y-2">
          <div className="text-sm font-medium text-center">
            Drift Prediction
          </div>
          <div className="flex gap-1">
            {STEPS.map(({ hours, label }) => (
              <Button
                key={hours}
                variant={value === hours ? "default" : "outline"}
                size="sm"
                onClick={() => onChange(hours)}
              >
                {label}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
