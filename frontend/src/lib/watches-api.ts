/**
 * Worth-It watches API client.
 * Reuses the same base URL and token pattern from lib/api.ts.
 */

import { getToken } from "./api"

const BASE = import.meta.env.VITE_API_URL || ""

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Watch {
  id: string
  name: string
  platform: string
  product_id: string
  product_url: string
  product_name: string | null
  product_image: string | null
  lat: number
  lng: number
  radius_km: number
  in_stock_only: boolean
  max_price: number | null
  min_discount_pct: number | null
  interval_minutes: 5 | 15 | 30
  status: "active" | "paused"
  created_at: string
  last_scan_at: string | null
  next_scan_at: string | null
  scan_count: number
  found_count: number
  telegram_chat_id: string | null
  notify_browser: boolean
}

export interface WatchEvent {
  id: string
  watch_id: string
  scanned_at: string
  found_in_stock: boolean
  price: number | null
  mrp: number | null
  discount_pct: number | null
  store_id: string | null
  store_name: string | null
  store_lat: number | null
  store_lng: number | null
  distance_km: number | null
  criteria_met: boolean
  alerted_telegram: boolean
  alerted_browser: boolean
  notes: string
}

export interface CreateWatchPayload {
  name: string
  product_url: string
  lat: number
  lng: number
  radius_km: number
  interval_minutes: 5 | 15 | 30
  in_stock_only: boolean
  max_price?: number | null
  min_discount_pct?: number | null
  telegram_chat_id?: string | null
  notify_browser: boolean
}

export interface UpdateWatchPayload {
  status?: "active" | "paused"
  name?: string
  interval_minutes?: 5 | 15 | 30
  max_price?: number | null
  min_discount_pct?: number | null
  in_stock_only?: boolean
  radius_km?: number
  telegram_chat_id?: string | null
  notify_browser?: boolean
}

export interface ResolvedUrl {
  platform: string
  product_id: string
  product_url: string
  product_name: string | null
  product_image: string | null
}

export interface TelegramStatus {
  configured: boolean
  has_chat_id: boolean
  chat_id: string | null
}

// ── HTTP helper ───────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs = 10000,
): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  const headers = new Headers(options.headers)
  const token = getToken()
  if (token) headers.set("X-App-Token", token)
  if (options.body && typeof options.body === "string") {
    headers.set("Content-Type", "application/json")
  }

  try {
    const res = await fetch(`${BASE}${path}`, {
      ...options,
      headers,
      signal: controller.signal,
    })

    if (!res.ok) {
      let detail = `HTTP ${res.status}`
      try {
        detail = (await res.json()).detail ?? detail
      } catch {
        /* non-JSON */
      }
      throw new Error(detail)
    }
    return res.json() as Promise<T>
  } catch (e: unknown) {
    if (e instanceof Error && e.name === "AbortError") {
      throw new Error("Request timed out. The backend may be starting up.")
    }
    throw e
  } finally {
    clearTimeout(timer)
  }
}

// ── Watches CRUD ──────────────────────────────────────────────────────────────

export async function listWatches(): Promise<Watch[]> {
  const data = await apiFetch<{ watches: Watch[] }>("/api/watches")
  return data.watches
}

export async function getWatch(id: string): Promise<{ watch: Watch; events: WatchEvent[] }> {
  return apiFetch(`/api/watches/${id}`)
}

export async function createWatch(payload: CreateWatchPayload): Promise<Watch> {
  return apiFetch("/api/watches", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export async function updateWatch(id: string, payload: UpdateWatchPayload): Promise<Watch> {
  return apiFetch(`/api/watches/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  })
}

export async function deleteWatch(id: string): Promise<void> {
  await apiFetch(`/api/watches/${id}`, { method: "DELETE" })
}

export async function scanNow(id: string): Promise<{ status: string; event: WatchEvent | null }> {
  return apiFetch(`/api/watches/${id}/scan-now`, { method: "POST" }, 90000) // 90s timeout for full scan
}

export async function getWatchEvents(id: string, limit = 50): Promise<WatchEvent[]> {
  const data = await apiFetch<{ events: WatchEvent[] }>(`/api/watches/${id}/events?limit=${limit}`)
  return data.events
}

// ── URL resolution ────────────────────────────────────────────────────────────

export async function resolveProductUrl(
  url: string,
  lat?: number,
  lng?: number,
): Promise<ResolvedUrl> {
  return apiFetch("/api/watches/resolve-url", {
    method: "POST",
    body: JSON.stringify({ url, lat, lng }),
  })
}

// ── Telegram ──────────────────────────────────────────────────────────────────

export async function getTelegramStatus(): Promise<TelegramStatus> {
  return apiFetch("/api/telegram/status")
}

export async function configureTelegram(
  bot_token: string,
  chat_id: string,
): Promise<{ status: string; bot_username: string; bot_name: string }> {
  return apiFetch("/api/telegram/configure", {
    method: "POST",
    body: JSON.stringify({ bot_token, chat_id }),
  })
}

export async function testTelegram(chat_id?: string): Promise<{ status: string }> {
  return apiFetch("/api/telegram/test", {
    method: "POST",
    body: JSON.stringify({ chat_id }),
  })
}

export async function clearTelegramConfig(): Promise<void> {
  await apiFetch("/api/telegram/configure", { method: "DELETE" })
}
