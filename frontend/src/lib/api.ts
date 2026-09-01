export interface ProductInfo {
  status: "in_stock" | "out_of_stock" | "not_carried" | "error" | "unknown"
  name: string | null
  brand: string | null
  image_url: string | null
  price: number | null
  mrp: number | null
  available_quantity: number | null
}

export interface ResolveResponse {
  pvid: string
  platform: string
  display_name: string
  product: ProductInfo | null
  link?: string
}

export interface GeocodeResponse {
  lat: number
  lng: number
  label: string
}

export interface PlaceSuggestion {
  place_id: string
  description: string
  main_text: string
  secondary_text: string
}

export interface HomeResult {
  serviceable: boolean
  store_name: string | null
  city: string | null
  eta_minutes: number | null
  product: ProductInfo | null
  platform?: string
}

export interface StoreResult {
  store: {
    id: string
    name: string | null
    city: string | null
    lat: number
    lng: number
    platform?: string
  }
  distance_km: number
  status: ProductInfo["status"]
  price: number | null
  mrp: number | null
  platform?: string
  verified?: boolean
}

export interface SearchSummary {
  in_stock: number
  out_of_stock: number
  not_carried: number
  error: number
  stores: number
}

export interface AppConfig {
  auth_required: boolean
  max_radius_km: number
  enabled_platforms: string[]
}

export interface PlatformInfo {
  name: string
  display_name: string
  supports_sweep: boolean
  supports_geocoding: boolean
}

/** Real-time serviceability response from /api/serviceability */
export interface PlatformServiceability {
  source: "live" | "timeout" | "error" | "skipped"
  is_open: boolean | null     // true = platform delivering there right now
  serviceable?: boolean
  store_name?: string | null
  city?: string | null
  eta_minutes?: number | null
}

// -- access token ----------------------------------------------------------

const TOKEN_KEY = "mf_token"

function initToken(): string | null {
  const url = new URL(window.location.href)
  const fromUrl = url.searchParams.get("token")
  if (fromUrl) {
    localStorage.setItem(TOKEN_KEY, fromUrl)
    url.searchParams.delete("token")
    window.history.replaceState({}, "", url.pathname + url.search + url.hash)
    return fromUrl
  }
  return localStorage.getItem(TOKEN_KEY)
}

let token = initToken()

export function getToken(): string | null {
  return token
}

export function setToken(value: string): void {
  token = value.trim() || null
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export function tokenQuery(): string {
  return token ? `&token=${encodeURIComponent(token)}` : ""
}

export function getConfig() {
  return request<AppConfig>("/api/config")
}

/** Check real-time delivery availability at coordinates for all platforms. */
export function getServiceability(lat: number, lng: number) {
  return request<Record<string, PlatformServiceability>>(
    `/api/serviceability?lat=${lat}&lng=${lng}`
  )
}

/** Fire-and-forget: wake up Render from sleep before user performs a search. */
export function pingBackend(): void {
  const baseUrl = import.meta.env.VITE_API_URL || ""
  fetch(`${baseUrl}/api/ping`).catch(() => { /* ignore — best-effort */ })
}

async function request<T>(input: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (token) headers.set("X-App-Token", token)
  
  // Use VITE_API_URL if defined (useful for separate frontend/backend deployments)
  const baseUrl = import.meta.env.VITE_API_URL || ""
  const url = input.startsWith("/") ? `${baseUrl}${input}` : input
  
  const res = await fetch(url, { ...init, headers })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      // non-JSON error body
    }
    // Make common errors user-friendly
    if (res.status === 502 || res.status === 503) {
      throw new Error(
        detail.startsWith("HTTP")
          ? "The platform returned an error — it may be temporarily unavailable. Try again in a moment."
          : detail
      )
    }
    if (res.status === 429) {
      throw new Error("Too many requests — please wait a moment before trying again.")
    }
    throw new Error(detail)
  }
  return res.json()
}

export function resolveLink(
  url: string,
  coords?: { lat: number; lng: number } | null
) {
  return request<ResolveResponse>("/api/resolve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, lat: coords?.lat, lng: coords?.lng }),
  })
}

export function geocode(q: string) {
  return request<GeocodeResponse>(`/api/geocode?q=${encodeURIComponent(q)}`)
}

export function suggestPlaces(q: string, signal?: AbortSignal) {
  return request<{ suggestions: PlaceSuggestion[] }>(
    `/api/suggest?q=${encodeURIComponent(q)}`,
    { signal }
  )
}

export function placeDetails(placeId: string, label: string) {
  return request<GeocodeResponse>(
    `/api/place?place_id=${encodeURIComponent(placeId)}&label=${encodeURIComponent(label)}`
  )
}

export function getPlatforms() {
  return request<{ platforms: PlatformInfo[] }>("/api/platforms")
}

// -- platform helpers -------------------------------------------------------

export const PLATFORM_COLORS: Record<string, string> = {
  zepto: "#7B2FF7",        // Zepto purple
  swiggy: "#FC8019",       // Swiggy orange
  bigbasket: "#84C225",    // BigBasket green
  blinkit: "#F5C913",      // Blinkit yellow
  bbnow: "#C4162A",        // Tata Neu / BB Now red
  flipkart: "#2874F0",     // Flipkart blue
  flipkart_minutes: "#2874F0",
}

export const PLATFORM_LABELS: Record<string, string> = {
  zepto: "Zepto",
  swiggy: "Instamart",
  bigbasket: "BigBasket",
  blinkit: "Blinkit",
  bbnow: "BB Now",
  flipkart: "Flipkart",
  flipkart_minutes: "Flipkart Minutes",
}

export function detectPlatformFromUrl(url: string): string | null {
  const lower = url.toLowerCase()
  if (lower.includes("zepto.com") || lower.includes("zeptonow.com")) return "zepto"
  // instamart.in is Swiggy's dedicated share/deep-link domain for Instamart
  if (lower.includes("swiggy.com") || lower.includes("instamart.in")) return "swiggy"
  if (lower.includes("bbnow.bigbasket.com")) return "bbnow"
  if (lower.includes("bigbasket.com") || lower.includes("bb.com")) return "bigbasket"
  if (lower.includes("blinkit.com") || lower.includes("grofers.com")) return "blinkit"
  
  if (lower.includes("flipkart.com")) {
    try {
      const parsedUrl = new URL(url)
      const marketplace = parsedUrl.searchParams.get("marketplace")
      if (marketplace && marketplace.toUpperCase() === "HYPERLOCAL") {
        return "flipkart_minutes"
      }
      return "flipkart"
    } catch {
      return "flipkart"
    }
  }

  // Zepto pvid pattern
  if (/\/pvid\/[0-9a-f-]{36}/i.test(lower)) return "zepto"
  return null
}
