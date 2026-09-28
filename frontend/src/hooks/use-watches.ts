/**
 * useWatches — fetches and manages the list of all watches.
 * Lightweight polling every 60s — no SSE for the watch list itself.
 * SSE is reserved for per-watch console streams.
 */

import { useState, useEffect, useCallback, useRef } from "react"
import { listWatches, type Watch } from "@/lib/watches-api"

const POLL_INTERVAL_MS = 60_000 // 60 seconds

export type WatchListState = {
  watches: Watch[]
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
}

export function useWatches(): WatchListState {
  const [watches, setWatches] = useState<Watch[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const pollerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const refresh = useCallback(async () => {
    try {
      const data = await listWatches()
      setWatches(data)
      setError(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load watches")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    // Initial load
    refresh()

    // Lightweight background poll
    pollerRef.current = setInterval(refresh, POLL_INTERVAL_MS)

    return () => {
      if (pollerRef.current) clearInterval(pollerRef.current)
    }
  }, [refresh])

  return { watches, loading, error, refresh }
}
