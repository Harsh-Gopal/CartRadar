/**
 * useWatchConsole — safe SSE hook for the live backend console.
 *
 * Design principles:
 * - Only one SSEconnection per watch ID (dedup guard via ref)
 * - Exponential backoff reconnect on error (1s → 2s → 4s → max 30s)
 * - Proper cleanup on unmount / watch ID change
 * - No React state for the SSE connection itself (avoids double-connect in StrictMode)
 * - Keepalive pings from server are silently dropped (they are SSE comment lines)
 */

import { useEffect, useRef, useState, useCallback } from "react"

const BASE = import.meta.env.VITE_API_URL || ""
const MAX_BACKOFF_MS = 30_000
const MAX_BUFFER = 500

export type ConsoleLevel = "info" | "warn" | "error" | "success" | "debug"

export interface ConsoleEntry {
  ts: number     // unix timestamp from server
  level: ConsoleLevel
  msg: string
  [key: string]: unknown
}

export type ConnectionStatus = "connecting" | "connected" | "reconnecting" | "disconnected"

export function useWatchConsole(watchId: string | null) {
  const [entries, setEntries] = useState<ConsoleEntry[]>([])
  const [status, setStatus] = useState<ConnectionStatus>("disconnected")

  const esRef = useRef<EventSource | null>(null)
  const backoffRef = useRef(1000)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const activeWatchIdRef = useRef<string | null>(null)

  const addEntry = useCallback((entry: ConsoleEntry) => {
    setEntries((prev) => {
      const next = [...prev, entry]
      return next.length > MAX_BUFFER ? next.slice(next.length - MAX_BUFFER) : next
    })
  }, [])

  const clearEntries = useCallback(() => setEntries([]), [])

  const connect = useCallback(
    (id: string) => {
      // Prevent duplicate connections
      if (esRef.current && activeWatchIdRef.current === id) return

      // Close any existing connection
      if (esRef.current) {
        esRef.current.close()
        esRef.current = null
      }

      activeWatchIdRef.current = id
      setStatus("connecting")

      const url = `${BASE}/api/watches/${id}/console`
      const es = new EventSource(url)
      esRef.current = es

      es.onmessage = (e) => {
        // Reset backoff on successful message
        backoffRef.current = 1000

        // Skip keepalive ping comments (they arrive as empty data or "ping")
        if (!e.data || e.data === "ping") return

        try {
          const entry = JSON.parse(e.data) as ConsoleEntry
          addEntry(entry)
          setStatus("connected")
        } catch {
          // Malformed event — ignore
        }
      }

      es.onopen = () => {
        backoffRef.current = 1000
        setStatus("connected")
      }

      es.onerror = () => {
        es.close()
        esRef.current = null

        if (activeWatchIdRef.current !== id) return // stale

        setStatus("reconnecting")

        // Exponential backoff reconnect
        const delay = Math.min(backoffRef.current, MAX_BACKOFF_MS)
        backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF_MS)

        reconnectTimerRef.current = setTimeout(() => {
          if (activeWatchIdRef.current === id) {
            connect(id)
          }
        }, delay)
      }
    },
    [addEntry],
  )

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
    activeWatchIdRef.current = null
    setStatus("disconnected")
  }, [])

  useEffect(() => {
    if (!watchId) {
      disconnect()
      return
    }

    // Reset entries when switching watches
    if (activeWatchIdRef.current !== watchId) {
      clearEntries()
    }

    connect(watchId)

    return () => {
      // On unmount or watchId change — disconnect
      disconnect()
    }
  }, [watchId, connect, disconnect, clearEntries])

  return { entries, status, clearEntries }
}
