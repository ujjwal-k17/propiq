/**
 * ProjectMap — Mapbox GL JS interactive map for the project detail page.
 *
 * Features:
 * - Project pin with branded marker
 * - Nearby POIs: metro stations, employment hubs, schools, hospitals
 * - Popups on marker click (name + distance)
 * - Layer toggle buttons per POI category
 * - Geocoding fallback when project has no lat/lng
 * - Graceful no-token / no-data fallback UI
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { MapPin, Train, Briefcase, GraduationCap, Cross } from 'lucide-react'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface POI {
  id: string
  name: string
  category: 'metro' | 'employment' | 'school' | 'hospital'
  longitude: number
  latitude: number
  distance_km?: number
}

export interface ProjectMapProps {
  projectId: string
  projectName: string
  city: string
  micromarket?: string | null
  latitude?: number | null
  longitude?: number | null
  /** Height class for the map container, e.g. "h-80" or "h-96". Default: "h-80" */
  heightClass?: string
}

// ─── Constants ────────────────────────────────────────────────────────────────

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string | undefined

const CATEGORY_CONFIG = {
  metro: {
    color: '#3B82F6',       // blue-500
    bg: '#DBEAFE',          // blue-100
    label: 'Metro Stations',
    icon: '🚇',
  },
  employment: {
    color: '#8B5CF6',       // violet-500
    bg: '#EDE9FE',          // violet-100
    label: 'Employment Hubs',
    icon: '🏢',
  },
  school: {
    color: '#10B981',       // emerald-500
    bg: '#D1FAE5',          // emerald-100
    label: 'Schools',
    icon: '🎓',
  },
  hospital: {
    color: '#EF4444',       // red-500
    bg: '#FEE2E2',          // red-100
    label: 'Hospitals',
    icon: '🏥',
  },
} as const

type Category = keyof typeof CATEGORY_CONFIG

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Haversine distance in km between two lat/lng points. */
function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLng = ((lng2 - lng1) * Math.PI) / 180
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLng / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

/**
 * Use Mapbox Geocoding API to resolve a city + micromarket string to lat/lng.
 * Returns null if the token is absent or the API fails.
 */
async function geocodeLocation(query: string, token: string): Promise<[number, number] | null> {
  try {
    const encoded = encodeURIComponent(`${query}, India`)
    const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encoded}.json?access_token=${token}&country=in&limit=1`
    const res = await fetch(url)
    if (!res.ok) return null
    const data = await res.json() as { features?: Array<{ center: [number, number] }> }
    const center = data.features?.[0]?.center
    return center ?? null
  } catch {
    return null
  }
}

/**
 * Use Mapbox Geocoding to find nearby places of a given type.
 * Returns up to `limit` results near the given coordinates.
 */
async function fetchNearbyPOIs(
  lng: number,
  lat: number,
  types: string,
  token: string,
  limit = 5,
): Promise<Array<{ name: string; lng: number; lat: number }>> {
  try {
    const url =
      `https://api.mapbox.com/geocoding/v5/mapbox.places/${types}.json` +
      `?proximity=${lng},${lat}&access_token=${token}&limit=${limit}&country=in`
    const res = await fetch(url)
    if (!res.ok) return []
    const data = await res.json() as {
      features?: Array<{ text: string; center: [number, number] }>
    }
    return (data.features ?? []).map((f) => ({
      name: f.text,
      lng: f.center[0],
      lat: f.center[1],
    }))
  } catch {
    return []
  }
}

/** Build an SVG data-URI marker for a given color and emoji label. */
function makeMarkerEl(color: string, bg: string, emoji: string): HTMLElement {
  const el = document.createElement('div')
  el.style.cssText = `
    width: 36px; height: 36px;
    background: ${bg};
    border: 2.5px solid ${color};
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px;
    cursor: pointer;
    box-shadow: 0 2px 6px rgba(0,0,0,0.25);
    transition: transform 0.15s ease;
  `
  el.textContent = emoji
  el.onmouseenter = () => { el.style.transform = 'scale(1.2)' }
  el.onmouseleave = () => { el.style.transform = 'scale(1)' }
  return el
}

/** Build the branded project pin element. */
function makeProjectPinEl(): HTMLElement {
  const el = document.createElement('div')
  el.style.cssText = `
    width: 44px; height: 44px;
    background: linear-gradient(135deg, #1E3A8A, #0EA5E9);
    border: 3px solid white;
    border-radius: 50% 50% 50% 0;
    transform: rotate(-45deg);
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.35);
    cursor: pointer;
  `
  const inner = document.createElement('div')
  inner.style.cssText = `
    transform: rotate(45deg);
    font-size: 18px;
    line-height: 1;
  `
  inner.textContent = '🏗'
  el.appendChild(inner)
  return el
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ProjectMap({
  projectName,
  city,
  micromarket,
  latitude,
  longitude,
  heightClass = 'h-80',
}: ProjectMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)
  const markersRef = useRef<Record<string, mapboxgl.Marker[]>>({
    metro: [],
    employment: [],
    school: [],
    hospital: [],
  })

  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [visibleLayers, setVisibleLayers] = useState<Record<Category, boolean>>({
    metro: true,
    employment: true,
    school: true,
    hospital: true,
  })
  const [pois, setPois] = useState<POI[]>([])

  // ── Resolved coordinates (may come from props or geocoding) ──────────────────
  const [resolvedCoords, setResolvedCoords] = useState<[number, number] | null>(
    latitude && longitude ? [longitude, latitude] : null,
  )

  // ── Geocode if no coords provided ────────────────────────────────────────────
  useEffect(() => {
    if (resolvedCoords) return
    if (!MAPBOX_TOKEN) {
      setError('Map token not configured')
      setIsLoading(false)
      return
    }
    const query = micromarket ? `${micromarket}, ${city}` : city
    geocodeLocation(query, MAPBOX_TOKEN).then((coords) => {
      if (coords) {
        setResolvedCoords(coords)
      } else {
        setError('Could not locate project on map')
        setIsLoading(false)
      }
    })
  }, [city, micromarket, resolvedCoords])

  // ── Fetch nearby POIs once we have coordinates ───────────────────────────────
  useEffect(() => {
    if (!resolvedCoords || !MAPBOX_TOKEN) return
    const [lng, lat] = resolvedCoords

    const poiSearches: Array<{ category: Category; mapboxType: string }> = [
      { category: 'metro', mapboxType: 'metro station' },
      { category: 'employment', mapboxType: 'office park' },
      { category: 'school', mapboxType: 'school' },
      { category: 'hospital', mapboxType: 'hospital' },
    ]

    Promise.all(
      poiSearches.map(async ({ category, mapboxType }) => {
        const results = await fetchNearbyPOIs(lng, lat, mapboxType, MAPBOX_TOKEN!, 5)
        return results.map((r, i): POI => ({
          id: `${category}-${i}`,
          name: r.name,
          category,
          longitude: r.lng,
          latitude: r.lat,
          distance_km: parseFloat(haversineKm(lat, lng, r.lat, r.lng).toFixed(1)),
        }))
      }),
    ).then((groups) => setPois(groups.flat()))
  }, [resolvedCoords])

  // ── Initialise map ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!resolvedCoords || !containerRef.current || mapRef.current) return
    if (!MAPBOX_TOKEN) {
      setError('Map token not configured')
      setIsLoading(false)
      return
    }

    mapboxgl.accessToken = MAPBOX_TOKEN
    const [lng, lat] = resolvedCoords

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center: [lng, lat],
      zoom: 13,
      attributionControl: false,
    })

    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'bottom-right')
    map.addControl(new mapboxgl.AttributionControl({ compact: true }), 'bottom-left')

    // Project pin
    const pin = makeProjectPinEl()
    const popup = new mapboxgl.Popup({ offset: 28, closeButton: false })
      .setHTML(`<strong class="text-sm">${projectName}</strong><br/><span class="text-xs text-slate-500">${micromarket ?? city}</span>`)
    new mapboxgl.Marker({ element: pin, anchor: 'bottom' })
      .setLngLat([lng, lat])
      .setPopup(popup)
      .addTo(map)

    map.on('load', () => setIsLoading(false))
    map.on('error', () => {
      setError('Map failed to load')
      setIsLoading(false)
    })

    mapRef.current = map

    return () => {
      map.remove()
      mapRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resolvedCoords])

  // ── Add / update POI markers whenever pois or visibility changes ──────────────
  useEffect(() => {
    const map = mapRef.current
    if (!map || pois.length === 0) return

    // Remove all existing POI markers
    for (const category of Object.keys(markersRef.current) as Category[]) {
      markersRef.current[category].forEach((m) => m.remove())
      markersRef.current[category] = []
    }

    // Re-add visible markers
    pois.forEach((poi) => {
      if (!visibleLayers[poi.category]) return
      const cfg = CATEGORY_CONFIG[poi.category]
      const el = makeMarkerEl(cfg.color, cfg.bg, cfg.icon)

      const popup = new mapboxgl.Popup({ offset: 20, closeButton: false, maxWidth: '200px' })
        .setHTML(
          `<strong class="text-xs font-semibold">${poi.name}</strong>` +
          (poi.distance_km != null
            ? `<br/><span class="text-xs text-slate-400">${poi.distance_km} km away</span>`
            : ''),
        )

      const marker = new mapboxgl.Marker({ element: el })
        .setLngLat([poi.longitude, poi.latitude])
        .setPopup(popup)
        .addTo(map)

      markersRef.current[poi.category].push(marker)
    })
  }, [pois, visibleLayers])

  const toggleLayer = useCallback((cat: Category) => {
    setVisibleLayers((prev) => ({ ...prev, [cat]: !prev[cat] }))
  }, [])

  // ── No token fallback ─────────────────────────────────────────────────────────
  if (!MAPBOX_TOKEN) {
    return (
      <div className={`${heightClass} bg-slate-50 rounded-2xl border border-slate-100 flex flex-col items-center justify-center gap-3 text-slate-400`}>
        <MapPin size={32} className="text-slate-300" />
        <p className="text-sm font-medium">Map unavailable</p>
        <p className="text-xs text-slate-400">Set VITE_MAPBOX_TOKEN to enable the map</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-card overflow-hidden">
      {/* Layer toggles */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-100 flex-wrap">
        <span className="text-xs font-semibold text-slate-500 mr-1">Show:</span>
        {(Object.entries(CATEGORY_CONFIG) as Array<[Category, typeof CATEGORY_CONFIG[Category]]>).map(([cat, cfg]) => (
          <button
            key={cat}
            onClick={() => toggleLayer(cat)}
            className={`
              flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border transition-all
              ${visibleLayers[cat]
                ? 'text-white border-transparent'
                : 'bg-white text-slate-500 border-slate-200 hover:border-slate-300'
              }
            `}
            style={visibleLayers[cat] ? { background: cfg.color, borderColor: cfg.color } : undefined}
          >
            <span>{cfg.icon}</span>
            {cfg.label}
          </button>
        ))}
      </div>

      {/* Map container */}
      <div className="relative">
        <div ref={containerRef} className={heightClass} />

        {/* Loading overlay */}
        {isLoading && (
          <div className="absolute inset-0 bg-slate-100 flex items-center justify-center">
            <div className="flex flex-col items-center gap-2 text-slate-400">
              <div className="w-8 h-8 border-2 border-propiq-blue border-t-transparent rounded-full animate-spin" />
              <p className="text-xs">Loading map…</p>
            </div>
          </div>
        )}

        {/* Error overlay */}
        {error && (
          <div className="absolute inset-0 bg-slate-50 flex flex-col items-center justify-center gap-2 text-slate-400">
            <MapPin size={28} className="text-slate-300" />
            <p className="text-sm font-medium">{error}</p>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="px-4 py-2 border-t border-slate-100 flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <span className="text-base">🏗</span>
          <span>{projectName}</span>
        </div>
        {pois.length === 0 && !isLoading && (
          <span className="text-xs text-slate-400 italic">No nearby POI data available</span>
        )}
        {pois.length > 0 && (
          <span className="text-xs text-slate-400">{pois.length} nearby places loaded</span>
        )}
      </div>
    </div>
  )
}

// Unused icon imports are referenced below to avoid TS "unused" warnings when
// the icons are only used in JSX fallback comments above.
void MapPin; void Train; void Briefcase; void GraduationCap; void Cross
