import type { BoatState, DriftPoint } from "@/types"

// Make a fake data points
function generateTrail(lat: number, lon: number, heading: number): [number, number][] {
  const rad = (heading * Math.PI) / 180
  const points: [number, number][] = []
  for (let i = 8; i >= 1; i--) {
    // Points trail behind the boat (opposite of heading)
    const jitter = (Math.random() - 0.5) * 0.005
    points.push([
      lat - Math.cos(rad) * i * 0.008 + jitter,
      lon - Math.sin(rad) * i * 0.008 + jitter,
    ])
  }
  points.push([lat, lon])
  return points
}

function generateDriftPath(lat: number, lon: number): DriftPoint[] {
  const hours = [0, 4, 8, 12, 18, 24]
  let curLat = lat
  let curLon = lon
  return hours.map((h) => {
    const point: DriftPoint = { lat: curLat, lon: curLon, time_offset_hours: h }
    // drift SE with jitter
    curLat += -0.005 + (Math.random() - 0.5) * 0.003
    curLon += 0.006 + (Math.random() - 0.5) * 0.003
    return point
  })
}

export const demoBoats: BoatState[] = [
  {
    boat_id: "boat-001",
    name: "Sea Wanderer",
    weight_class: "light",
    gps_lat: 44.27,
    gps_lon: -68.78,
    heading: 45,
    timestamp: Date.now(),
    image: "/demo-sighting.jpg",
    trail: generateTrail(44.27, -68.78, 45),
  },
  {
    boat_id: "boat-002",
    name: "Lobster King",
    weight_class: "heavy",
    gps_lat: 44.15,
    gps_lon: -68.65,
    heading: 120,
    timestamp: Date.now(),
    image: "/demo-sighting.jpg",
    trail: generateTrail(44.15, -68.65, 120),
  },
  {
    boat_id: "boat-003",
    name: "Tide Runner",
    weight_class: "light",
    gps_lat: 44.32,
    gps_lon: -68.92,
    heading: 200,
    timestamp: Date.now(),
    image: "/demo-sighting.jpg",
    trail: generateTrail(44.32, -68.92, 200),
  },
  {
    boat_id: "boat-004",
    name: "Atlantic Scout",
    weight_class: "heavy",
    gps_lat: 44.1,
    gps_lon: -68.55,
    heading: 310,
    timestamp: Date.now(),
    image: "/demo-sighting.jpg",
    trail: generateTrail(44.1, -68.55, 310),
  },
  {
    boat_id: "boat-005",
    name: "Harbor Breeze",
    weight_class: "light",
    gps_lat: 44.38,
    gps_lon: -68.72,
    heading: 85,
    timestamp: Date.now(),
    image: "/demo-sighting.jpg",
    trail: generateTrail(44.38, -68.72, 85),
  },
  {
    boat_id: "boat-006",
    name: "Deep Current",
    weight_class: "heavy",
    gps_lat: 44.22,
    gps_lon: -68.88,
    heading: 160,
    timestamp: Date.now(),
    image: "/demo-sighting.jpg",
    trail: generateTrail(44.22, -68.88, 160),
  },
]

export const demoDetections = demoBoats.flatMap((boat, _bi) =>
  Array.from({ length: 3 }, (_, i) => {
    const offsetLat = (Math.random() - 0.5) * 0.04
    const offsetLon = (Math.random() - 0.5) * 0.04
    const lat = boat.gps_lat + offsetLat
    const lon = boat.gps_lon + offsetLon
    return {
      id: `det-${boat.boat_id}-${i}`,
      lat,
      lon,
      confidence: 0.7 + Math.random() * 0.25,
      detected_at: Date.now() - Math.random() * 3600000,
      boat_id: boat.boat_id,
      drift_path: generateDriftPath(lat, lon),
    }
  })
)
