import { useMemo } from "react"
import {
  PieChart, Pie, Cell,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { BoatState, TrashPoint } from "@/types"

interface AnalyticsPageProps {
  boats: BoatState[]
  trashPoints: TrashPoint[]
}

export function AnalyticsPage({ boats, trashPoints }: AnalyticsPageProps) {
  const totalDetections = trashPoints.length
  const avgConfidence = useMemo(
    () =>
      trashPoints.length
        ? trashPoints.reduce((s, t) => s + t.confidence, 0) / trashPoints.length
        : 0,
    [trashPoints],
  )
  const mostCommonType = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const t of trashPoints) {
      counts[t.class_name] = (counts[t.class_name] || 0) + 1
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—"
  }, [trashPoints])

  const classDistribution = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const t of trashPoints) {
      counts[t.class_name] = (counts[t.class_name] || 0) + 1
    }
    return Object.entries(counts).map(([name, value]) => ({ name, value }))
  }, [trashPoints])

  const donutConfig: ChartConfig = {
    bottle: { label: "Bottle", color: "var(--chart-1)" },
    "plastic-bag": { label: "Plastic Bag", color: "var(--chart-2)" },
    cup: { label: "Cup", color: "var(--chart-3)" },
    "fishing-line": { label: "Fishing Line", color: "var(--chart-4)" },
    styrofoam: { label: "Styrofoam", color: "var(--chart-5)" },
  }

  const perBoat = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const t of trashPoints) counts[t.boat_id] = (counts[t.boat_id] || 0) + 1
    return boats.map((b) => ({
      name: b.name,
      detections: counts[b.boat_id] || 0,
    }))
  }, [boats, trashPoints])

  const perBoatConfig: ChartConfig = {
    detections: { label: "Detections", color: "var(--chart-1)" },
  }

  const confidenceBuckets = useMemo(() => {
    const buckets = [
      { range: "70-75%", min: 0.7, max: 0.75, count: 0 },
      { range: "75-80%", min: 0.75, max: 0.8, count: 0 },
      { range: "80-85%", min: 0.8, max: 0.85, count: 0 },
      { range: "85-90%", min: 0.85, max: 0.9, count: 0 },
      { range: "90-95%", min: 0.9, max: 0.95, count: 0 },
    ]
    for (const t of trashPoints) {
      for (const b of buckets) {
        if (t.confidence >= b.min && t.confidence < b.max) {
          b.count++
          break
        }
      }
      if (t.confidence >= 0.95) buckets[buckets.length - 1].count++
    }
    return buckets.map((b) => ({ range: b.range, count: b.count }))
  }, [trashPoints])

  const confidenceConfig: ChartConfig = {
    count: { label: "Count", color: "var(--chart-2)" },
  }

  const byWeightClass = useMemo(() => {
    const map: Record<string, { light: number; heavy: number }> = {}
    const boatWeight: Record<string, "light" | "heavy"> = {}
    for (const b of boats) boatWeight[b.boat_id] = b.weight_class
    for (const t of trashPoints) {
      if (!map[t.class_name]) map[t.class_name] = { light: 0, heavy: 0 }
      const w = boatWeight[t.boat_id] || "light"
      map[t.class_name][w]++
    }
    return Object.entries(map).map(([name, v]) => ({
      name,
      light: v.light,
      heavy: v.heavy,
    }))
  }, [boats, trashPoints])

  const weightConfig: ChartConfig = {
    light: { label: "Light", color: "var(--chart-1)" },
    heavy: { label: "Heavy", color: "var(--chart-4)" },
  }

  return (
    <div className="overflow-y-auto flex-1 p-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-6xl mx-auto">
        <div className="md:col-span-2 grid grid-cols-2 md:grid-cols-4 gap-4">
          <SummaryCard title="Total Detections" value={totalDetections} />
          <SummaryCard title="Avg Confidence" value={`${(avgConfidence * 100).toFixed(1)}%`} />
          <SummaryCard title="Most Common Type" value={mostCommonType} />
          <SummaryCard title="Active Boats" value={boats.length} />
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Trash Type Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ChartContainer config={donutConfig} className="mx-auto aspect-square max-h-[300px]">
              <PieChart>
                <ChartTooltip content={<ChartTooltipContent nameKey="name" hideLabel />} />
                <Pie
                  data={classDistribution}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={60}
                  strokeWidth={2}
                >
                  {classDistribution.map((d) => (
                    <Cell
                      key={d.name}
                      fill={`var(--color-${d.name.replace(/\s+/g, "-").toLowerCase()})`}
                    />
                  ))}
                </Pie>
              </PieChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Detections per Boat</CardTitle>
          </CardHeader>
          <CardContent>
            <ChartContainer config={perBoatConfig} className="max-h-[300px]">
              <BarChart data={perBoat}>
                <CartesianGrid />
                <XAxis dataKey="name" />
                <YAxis />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="detections" fill="var(--color-detections)" />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Confidence Score Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ChartContainer config={confidenceConfig} className="max-h-[300px]">
              <BarChart data={confidenceBuckets}>
                <CartesianGrid />
                <XAxis dataKey="range" />
                <YAxis />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="count" fill="var(--color-count)" />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Detections by Weight Class</CardTitle>
          </CardHeader>
          <CardContent>
            <ChartContainer config={weightConfig}>
              <BarChart data={byWeightClass}>
                <CartesianGrid />
                <XAxis dataKey="name" />
                <YAxis />
                <ChartTooltip content={<ChartTooltipContent />} />
                <ChartLegend content={<ChartLegendContent />} />
                <Bar dataKey="light" fill="var(--color-light)" />
                <Bar dataKey="heavy" fill="var(--color-heavy)" />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function SummaryCard({ title, value }: { title: string; value: string | number }) {
  return (
    <Card>
      <CardContent>
        <p className="text-sm text-muted-foreground">{title}</p>
        <p className="text-2xl font-bold">{value}</p>
      </CardContent>
    </Card>
  )
}
