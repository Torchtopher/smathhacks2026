import { useMemo } from "react"
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
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

  const perBoatStats = useMemo(() => {
    const byBoat: Record<string, { count: number; confidenceSum: number; latestDetectionAt: number | null }> = {}
    for (const t of trashPoints) {
      const cur = byBoat[t.boat_id] ?? { count: 0, confidenceSum: 0, latestDetectionAt: null }
      cur.count += 1
      cur.confidenceSum += t.confidence
      cur.latestDetectionAt = cur.latestDetectionAt === null ? t.detected_at : Math.max(cur.latestDetectionAt, t.detected_at)
      byBoat[t.boat_id] = cur
    }
    return byBoat
  }, [trashPoints])

  function csvEscape(value: unknown): string {
    if (value === null || value === undefined) return ""
    const str = String(value)
    if (/[",\n]/.test(str)) return `"${str.replace(/"/g, '""')}"`
    return str
  }

  function downloadCsv(filename: string, headers: string[], rows: Array<Array<unknown>>) {
    const lines = [
      headers.map(csvEscape).join(","),
      ...rows.map((r) => r.map(csvEscape).join(",")),
    ]
    const csv = `${lines.join("\n")}\n`
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  function exportDetectionsCsv() {
    const rows = [...trashPoints]
      .sort((a, b) => b.detected_at - a.detected_at)
      .map((t) => [
        t.id,
        t.boat_id,
        t.confidence,
        t.detected_at,
        new Date(t.detected_at * 1000).toISOString(),
        t.lat,
        t.lon,
        (t.drift_path ?? []).length,
        JSON.stringify(t.drift_path ?? []),
      ])
    downloadCsv(
      `hackathon_detections_${Date.now()}.csv`,
      [
        "detection_id",
        "boat_id",
        "confidence",
        "detected_at_unix_s",
        "detected_at_iso",
        "lat",
        "lon",
        "drift_points",
        "drift_path_json",
      ],
      rows,
    )
  }

  function exportFleetSummaryCsv() {
    const rows = boats.map((b) => {
      const stats = perBoatStats[b.boat_id] ?? { count: 0, confidenceSum: 0, latestDetectionAt: null as number | null }
      const avg = stats.count ? stats.confidenceSum / stats.count : 0
      return [
        b.boat_id,
        b.name,
        b.weight_class,
        b.gps_lat,
        b.gps_lon,
        b.heading,
        b.timestamp,
        new Date(b.timestamp * 1000).toISOString(),
        stats.count,
        avg,
        stats.latestDetectionAt ?? "",
        stats.latestDetectionAt ? new Date(stats.latestDetectionAt * 1000).toISOString() : "",
      ]
    })
    downloadCsv(
      `hackathon_fleet_summary_${Date.now()}.csv`,
      [
        "boat_id",
        "name",
        "weight_class",
        "gps_lat",
        "gps_lon",
        "heading_deg",
        "last_state_unix_s",
        "last_state_iso",
        "detections_count",
        "avg_detection_confidence",
        "last_detection_unix_s",
        "last_detection_iso",
      ],
      rows,
    )
  }

  function exportPitchSnapshotCsv() {
    const maxConfidence = trashPoints.length
      ? Math.max(...trashPoints.map((t) => t.confidence))
      : 0
    const latestDetectionAt = trashPoints.length
      ? Math.max(...trashPoints.map((t) => t.detected_at))
      : null
    const rows = [[
      new Date().toISOString(),
      boats.length,
      totalDetections,
      Number((avgConfidence * 100).toFixed(2)),
      Number((maxConfidence * 100).toFixed(2)),
      latestDetectionAt ?? "",
      latestDetectionAt ? new Date(latestDetectionAt * 1000).toISOString() : "",
    ]]
    downloadCsv(
      `hackathon_pitch_snapshot_${Date.now()}.csv`,
      [
        "exported_at_iso",
        "active_boats",
        "total_detections",
        "avg_confidence_percent",
        "max_confidence_percent",
        "latest_detection_unix_s",
        "latest_detection_iso",
      ],
      rows,
    )
  }

  return (
    <div className="overflow-y-auto flex-1 p-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-6xl mx-auto">
        <div className="md:col-span-2 grid grid-cols-2 md:grid-cols-3 gap-4">
          <SummaryCard title="Total Detections" value={totalDetections} />
          <SummaryCard title="Avg Confidence" value={`${(avgConfidence * 100).toFixed(1)}%`} />
          <SummaryCard title="Active Boats" value={boats.length} />
        </div>

        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Hackathon CSV Exports</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              <Button onClick={exportDetectionsCsv}>Export Detections CSV</Button>
              <Button variant="secondary" onClick={exportFleetSummaryCsv}>Export Fleet Summary CSV</Button>
              <Button variant="outline" onClick={exportPitchSnapshotCsv}>Export Pitch Snapshot CSV</Button>
            </div>
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
