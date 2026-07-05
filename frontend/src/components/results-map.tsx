import { useEffect } from "react"

import L from "leaflet"
import { Circle, CircleMarker, MapContainer, Popup, Tooltip, TileLayer, useMap } from "react-leaflet"
import "leaflet/dist/leaflet.css"

import { cn } from "@/lib/utils"
import { useTheme } from "@/components/theme-provider"
import { STATUS_LABEL, getPlatformFromId } from "@/components/results-list"
import type { StoreResult } from "@/lib/api"
import { usePincode } from "@/lib/use-pincode"

// Carto basemaps track the app theme: Positron (light) / Dark Matter (dark).
// Cleaner than default OSM tiles and they actually have a dark variant.
const TILE_URL = {
  light: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
  dark: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
} as const
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'

const PLATFORM_COLORS: Record<string, string> = {
  zepto: "#8B5CF6",
  swiggy: "#FF6B35",
  bigbasket: "#84C225",
  blinkit: "#F5C913",
  default: "#16a34a",
}

const OUT_OF_STOCK_COLOR = "#9ca3af"
const NOT_CARRIED_COLOR = "#d1d5db"
const ERROR_COLOR = "#f87171"

function getColor(status: StoreResult["status"], platform?: string): string {
  if (status === "in_stock") return PLATFORM_COLORS[platform || "default"] || PLATFORM_COLORS.default
  if (status === "out_of_stock") return OUT_OF_STOCK_COLOR
  if (status === "not_carried") return NOT_CARRIED_COLOR
  return ERROR_COLOR
}

function FitToRadius({ lat, lng, radiusKm }: { lat: number; lng: number; radiusKm: number }) {
  const map = useMap()
  useEffect(() => {
    map.fitBounds(L.latLng(lat, lng).toBounds(radiusKm * 2000))
  }, [map, lat, lng, radiusKm])
  return null
}

function FlyToSelected({ results, selectedId }: { results: StoreResult[]; selectedId: string | null }) {
  const map = useMap()
  useEffect(() => {
    const r = results.find((x) => x.store.id === selectedId)
    if (r) {
      map.flyTo([r.store.lat, r.store.lng], Math.max(map.getZoom(), 13), { duration: 0.6 })
    }
  }, [map, results, selectedId])
  return null
}

function StoreMarker({ r, selectedId, searchPincode, onSelect }: { r: StoreResult; selectedId: string | null; searchPincode?: string | null; onSelect: (r: StoreResult) => void }) {
  const storePincode = usePincode(r.store.lat, r.store.lng, r.store.city)
  
  return (
    <CircleMarker
      center={[r.store.lat, r.store.lng]}
      radius={r.store.id === selectedId ? 12 : 9}
      pathOptions={{
        color: r.store.id === selectedId ? "#6d28d9" : "#ffffff",
        weight: 2,
        fillColor: getColor(r.status, getPlatformFromId(r.store.id)),
        fillOpacity: 0.95,
      }}
      eventHandlers={{ click: () => onSelect(r) }}
    >
      {r.store.city && <Tooltip>{r.store.city}</Tooltip>}
      <Popup className="rounded-xl overflow-hidden shadow-sm">
        <div className="flex flex-col gap-1 p-1">
          <span className="font-semibold text-sm">{r.store.name ?? "Store"} {r.store.city ? `(${r.store.city})` : ""}</span>
          {(storePincode || searchPincode) && (
            <span className="text-xs font-medium text-primary/70">
              Pincode: {storePincode || searchPincode}
            </span>
          )}
          <div className="flex items-center justify-between gap-4 mt-1">
            <span className="text-xs text-muted-foreground">{r.distance_km} km away</span>
            <span className="font-medium text-primary">
              {r.status === "in_stock" ? `₹${r.price}` : STATUS_LABEL[r.status]}
            </span>
          </div>
        </div>
      </Popup>
    </CircleMarker>
  )
}

interface ResultsMapProps {
  lat: number
  lng: number
  radiusKm: number
  results: StoreResult[]
  // Stock at the user's own location (incl. via the backup store) — so the
  // "Your location" marker can match the banner instead of looking unavailable.
  homeStatus: StoreResult["status"] | null
  homePrice: number | null
  selectedId: string | null
  searchPincode?: string | null
  onSelect: (result: StoreResult) => void
  className?: string
}

export function ResultsMap({ lat, lng, radiusKm, results, homeStatus, homePrice, selectedId, searchPincode, onSelect, className }: ResultsMapProps) {
  const { resolvedTheme } = useTheme()
  return (
    <MapContainer
      center={[lat, lng]}
      zoom={12}
      className={cn("z-0 w-full", className || "h-72")}
      scrollWheelZoom={false}
    >
      <TileLayer
        key={resolvedTheme}
        attribution={TILE_ATTRIBUTION}
        url={TILE_URL[resolvedTheme]}
      />
      <FitToRadius lat={lat} lng={lng} radiusKm={radiusKm} />
      <FlyToSelected results={results} selectedId={selectedId} />
      <Circle
        center={[lat, lng]}
        radius={radiusKm * 1000}
        pathOptions={{ color: "#7c3aed", weight: 1, fillOpacity: 0.04 }}
      />
      <CircleMarker
        center={[lat, lng]}
        radius={8}
        pathOptions={{
          // Purple ring keeps it identifiable as "you"; fill reflects stock at
          // your location (green when in stock, incl. via the backup store).
          color: "#6d28d9",
          weight: 3,
          fillColor: homeStatus ? getColor(homeStatus, "default") : "#1A73E8",
          fillOpacity: 1,
        }}
      >
        <Popup>
          <span className="font-medium">Your location</span>
          {homeStatus && (
            <>
              <br />
              {homeStatus === "in_stock"
                ? `In stock — ₹${homePrice}`
                : STATUS_LABEL[homeStatus]}
            </>
          )}
        </Popup>
      </CircleMarker>
      {results.map((r) => (
        <StoreMarker
          key={r.store.id}
          r={r}
          selectedId={selectedId}
          searchPincode={searchPincode}
          onSelect={onSelect}
        />
      ))}
    </MapContainer>
  )
}
