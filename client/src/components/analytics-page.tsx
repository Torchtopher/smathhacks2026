import { useMemo } from "react"
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Cell, Legend,
} from "recharts"
import { MapContainer, TileLayer } from "react-leaflet"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { HeatmapLayer } from "@/components/heatmap-layer"
import { LABEL_COLORS, LABEL_DISPLAY_NAMES } from "@/lib/colors"
import type { BoatState, Detection } from "@/types"
import "leaflet/dist/leaflet.css"

const BOAT_CHART_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
]

interface AnalyticsPageProps {
  boats: BoatState[]
  detections: Detection[]
}

function formatHour(ts: number): string {
  const d = new Date(ts * 1000)
  const month = d.toLocaleString("en-US", { month: "short" })
  const day = d.getDate()
  const hour = d.toLocaleString("en-US", { hour: "numeric", hour12: true })
  return `${month} ${day} ${hour}`
}

export function AnalyticsPage({ boats, detections }: AnalyticsPageProps) {
  const totalDetections = detections.length
  const avgConfidence = useMemo(
    () =>
      detections.length
        ? detections.reduce((s, t) => s + t.confidence, 0) / detections.length
        : 0,
    [detections],
  )

  const labelCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const t of detections) {
      const label = t.label
      counts[label] = (counts[label] || 0) + 1
    }
    return Object.entries(counts)
      .map(([label, count]) => ({
        label: LABEL_DISPLAY_NAMES[label] ?? label,
        rawLabel: label,
        count,
      }))
      .sort((a, b) => b.count - a.count)
  }, [detections])

  const perBoat = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const t of detections) counts[t.boat_id] = (counts[t.boat_id] || 0) + 1
    return boats.map((b) => ({
      name: b.name,
      detections: counts[b.boat_id] || 0,
    }))
  }, [boats, detections])

  const perBoatConfig: ChartConfig = {
    detections: { label: "Detections", color: "var(--chart-1)" },
  }

  const labelChartConfig: ChartConfig = {
    count: { label: "Count", color: "var(--chart-3)" },
  }

  const confidenceBuckets = useMemo(() => {
    const buckets = [
      { range: "70-75%", min: 0.7, max: 0.75, count: 0 },
      { range: "75-80%", min: 0.75, max: 0.8, count: 0 },
      { range: "80-85%", min: 0.8, max: 0.85, count: 0 },
      { range: "85-90%", min: 0.85, max: 0.9, count: 0 },
      { range: "90-95%", min: 0.9, max: 0.95, count: 0 },
    ]
    for (const t of detections) {
      for (const b of buckets) {
        if (t.confidence >= b.min && t.confidence < b.max) {
          b.count++
          break
        }
      }
      if (t.confidence >= 0.95) buckets[buckets.length - 1].count++
    }
    return buckets.map((b) => ({ range: b.range, count: b.count }))
  }, [detections])

  const confidenceConfig: ChartConfig = {
    count: { label: "Count", color: "var(--chart-2)" },
  }

  const perBoatStats = useMemo(() => {
    const byBoat: Record<string, { count: number; confidenceSum: number; latestDetectionAt: number | null }> = {}
    for (const t of detections) {
      const cur = byBoat[t.boat_id] ?? { count: 0, confidenceSum: 0, latestDetectionAt: null }
      cur.count += 1
      cur.confidenceSum += t.confidence
      cur.latestDetectionAt = cur.latestDetectionAt === null ? t.detected_at : Math.max(cur.latestDetectionAt, t.detected_at)
      byBoat[t.boat_id] = cur
    }
    return byBoat
  }, [detections])

  // Hourly bucketing for trend charts
  const { hourlyByLabel, hourlyByBoat, boatNames } = useMemo(() => {
    if (detections.length === 0) return { hourlyByLabel: [], hourlyByBoat: [], boatNames: [] }

    const times = detections.map((d) => d.detected_at)
    const minTime = Math.min(...times)
    const maxTime = Math.max(...times)

    const HOUR = 3600
    const startHour = Math.floor(minTime / HOUR) * HOUR
    const endHour = Math.floor(maxTime / HOUR) * HOUR

    // Build boat name lookup
    const boatNameMap: Record<string, string> = {}
    for (const b of boats) boatNameMap[b.boat_id] = b.name
    const uniqueBoatIds = [...new Set(detections.map((d) => d.boat_id))]
    const names = uniqueBoatIds.map((id) => boatNameMap[id] || id)

    // All unique labels
    const labels = [...new Set(detections.map((d) => d.label))]

    const byLabelArr: Record<string, number>[] = []
    const byBoatArr: Record<string, number>[] = []
    const hours: number[] = []

    for (let h = startHour; h <= endHour; h += HOUR) {
      hours.push(h)
      const labelBucket: Record<string, number> = {}
      const boatBucket: Record<string, number> = {}
      for (const l of labels) labelBucket[l] = 0
      for (const name of names) boatBucket[name] = 0
      byLabelArr.push(labelBucket)
      byBoatArr.push(boatBucket)
    }

    for (const d of detections) {
      const idx = Math.floor((d.detected_at - startHour) / HOUR)
      if (idx >= 0 && idx < hours.length) {
        byLabelArr[idx][d.label] = (byLabelArr[idx][d.label] || 0) + 1
        const bName = boatNameMap[d.boat_id] || d.boat_id
        byBoatArr[idx][bName] = (byBoatArr[idx][bName] || 0) + 1
      }
    }

    return {
      hourlyByLabel: hours.map((h, i) => ({
        hour: formatHour(h),
        ...byLabelArr[i],
      })),
      hourlyByBoat: hours.map((h, i) => ({
        hour: formatHour(h),
        ...byBoatArr[i],
      })),
      boatNames: names,
    }
  }, [detections, boats])

  const labels = useMemo(
    () => [...new Set(detections.map((d) => d.label))],
    [detections],
  )

  const detectionsPerHour = useMemo(() => {
    if (detections.length < 2) return 0
    const times = detections.map((d) => d.detected_at)
    const spanHours = (Math.max(...times) - Math.min(...times)) / 3600
    return spanHours > 0 ? detections.length / spanHours : 0
  }, [detections])

  const labelTrendConfig: ChartConfig = Object.fromEntries(
    labels.map((l) => [l, { label: LABEL_DISPLAY_NAMES[l] ?? l, color: LABEL_COLORS[l] ?? "#888" }]),
  )

  const boatTrendConfig: ChartConfig = Object.fromEntries(
    boatNames.map((name, i) => [name, { label: name, color: BOAT_CHART_COLORS[i % BOAT_CHART_COLORS.length] }]),
  )

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
    const rows = [...detections]
      .sort((a, b) => b.detected_at - a.detected_at)
      .map((t) => [
        t.id,
        t.boat_id,
        t.label,
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
        "label",
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
    const maxConfidence = detections.length
      ? Math.max(...detections.map((t) => t.confidence))
      : 0
    const latestDetectionAt = detections.length
      ? Math.max(...detections.map((t) => t.detected_at))
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
        <div className="md:col-span-2 grid grid-cols-2 md:grid-cols-4 gap-4">
          <SummaryCard title="Total Detections" value={totalDetections} />
          <SummaryCard title="Avg Confidence" value={`${(avgConfidence * 100).toFixed(1)}%`} />
          <SummaryCard title="Active Boats" value={boats.length} />
          <SummaryCard title="Detections/Hour" value={detectionsPerHour.toFixed(1)} />
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
            <CardTitle>Detections by Label</CardTitle>
          </CardHeader>
          <CardContent>
            <ChartContainer config={labelChartConfig} className="max-h-[300px]">
              <BarChart data={labelCounts}>
                <CartesianGrid />
                <XAxis dataKey="label" />
                <YAxis />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="count">
                  {labelCounts.map((entry) => (
                    <Cell
                      key={entry.rawLabel}
                      fill={LABEL_COLORS[entry.rawLabel] ?? LABEL_COLORS.trash}
                    />
                  ))}
                </Bar>
              </BarChart>
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

        {/* Detection Rate Over Time */}
        <Card>
            <CardHeader>
              <CardTitle>Detection Rate Over Time</CardTitle>
            </CardHeader>
            <CardContent>
              <ChartContainer config={labelTrendConfig} className="h-[300px]">
                <LineChart data={hourlyByLabel}>
                  <CartesianGrid />
                  <XAxis dataKey="hour" tick={{ fontSize: 12 }} interval="preserveStartEnd" />
                  <YAxis />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Legend />
                  {labels.map((label) => (
                    <Line
                      key={label}
                      type="monotone"
                      dataKey={label}
                      name={LABEL_DISPLAY_NAMES[label] ?? label}
                      stroke={LABEL_COLORS[label] ?? "#888"}
                      strokeWidth={2}
                      dot={false}
                    />
                  ))}
                </LineChart>
              </ChartContainer>
            </CardContent>
          </Card>

        {/* Detections per Hour by Boat */}
        <Card>
            <CardHeader>
              <CardTitle>Detections per Hour by Boat</CardTitle>
            </CardHeader>
            <CardContent>
              <ChartContainer config={boatTrendConfig} className="h-[300px]">
                <LineChart data={hourlyByBoat}>
                  <CartesianGrid />
                  <XAxis dataKey="hour" tick={{ fontSize: 12 }} interval="preserveStartEnd" />
                  <YAxis />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Legend />
                  {boatNames.map((name, i) => (
                    <Line
                      key={name}
                      type="monotone"
                      dataKey={name}
                      stroke={BOAT_CHART_COLORS[i % BOAT_CHART_COLORS.length]}
                      strokeWidth={2}
                      dot={false}
                    />
                  ))}
                </LineChart>
              </ChartContainer>
            </CardContent>
          </Card>

        {/* Detection Heatmap */}
        <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle>Detection Heatmap</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[400px] rounded-md overflow-hidden">
                <MapContainer
                  center={[39.8283, -98.5795]}
                  zoom={4}
                  className="w-full h-full"
                >
                  <TileLayer
                    url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                  />
                  <HeatmapLayer detections={detections} />
                </MapContainer>
              </div>
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
