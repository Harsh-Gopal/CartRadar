import { useCallback, useEffect, useRef, useState } from "react"

import {
  tokenQuery,
  type HomeResult,
  type SearchSummary,
  type StoreResult,
} from "@/lib/api"

export interface SearchState {
  phase: "idle" | "searching" | "done" | "error"
  home: HomeResult | null
  results: StoreResult[]
  discovery: { probed: number; failed: number; total: number } | null
  totalStores: number
  summary: SearchSummary | null
  notice: string | null
  error: string | null
  platform: string | null
}

const INITIAL: SearchState = {
  phase: "idle",
  home: null,
  results: [],
  discovery: null,
  totalStores: 0,
  summary: null,
  notice: null,
  error: null,
  platform: null,
}

export interface SearchParams {
  pvid: string
  platform: string
  lat: number
  lng: number
  radiusKm: number
  force?: boolean
}

export function useSearch() {
  const [state, setState] = useState<SearchState>(INITIAL)
  const sourceRef = useRef<EventSource | null>(null)

  const stop = useCallback(() => {
    sourceRef.current?.close()
    sourceRef.current = null
  }, [])

  const cancel = useCallback(() => {
    stop()
    setState((s) => (s.phase === "searching" ? { ...s, phase: "done" } : s))
  }, [stop])

  const reset = useCallback(() => {
    stop()
    setState(INITIAL)
  }, [stop])

  useEffect(() => stop, [stop])

  const start = useCallback(
    ({ pvid, platform, lat, lng, radiusKm, force }: SearchParams) => {
      stop()
      setState({ ...INITIAL, phase: "searching", platform })
      const qs = new URLSearchParams({
        pvid,
        platform,
        lat: String(lat),
        lng: String(lng),
        radius_km: String(radiusKm),
        force: force ? "true" : "false",
      })
      const source = new EventSource(`/api/search?${qs}${tokenQuery()}`)
      sourceRef.current = source
      source.onmessage = (msg) => {
        const event = JSON.parse(msg.data)
        switch (event.type) {
          case "home_result":
            setState((s) => ({ ...s, home: event }))
            break
          case "discovery_start":
            setState((s) => ({
              ...s,
              discovery: { probed: 0, failed: 0, total: event.points_to_probe },
            }))
            break
          case "discovery_progress":
            setState((s) => ({
              ...s,
              discovery: {
                probed: event.probed,
                failed: event.failed,
                total: event.total,
              },
            }))
            break
          case "checking":
            setState((s) => ({ ...s, totalStores: event.total_stores }))
            break
          case "store_result":
            setState((s) => ({
              ...s,
              totalStores: Math.max(s.totalStores, s.results.length + 1),
              results: [...s.results, event],
            }))
            break
          case "notice":
            setState((s) => ({ ...s, notice: event.message }))
            break
          case "done":
            source.close()
            setState((s) => ({ ...s, phase: "done", summary: event.summary }))
            break
          case "error":
            source.close()
            setState((s) => ({ ...s, phase: "error", error: event.message }))
            break
        }
      }
      source.onerror = () => {
        source.close()
        setState((s) =>
          s.phase === "searching"
            ? {
                ...s,
                phase: "error",
                error: "Connection to the server was lost.",
              }
            : s
        )
      }
    },
    [stop]
  )

  return { state, start, stop, cancel, reset }
}
