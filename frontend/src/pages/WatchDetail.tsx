/**
 * WatchDetail — monitoring dashboard for a single watch.
 * Shows: watch config, status, scan history, live console, actions.
 * Every async op has loading/error/success states — no permanent spinners.
 */

import { useState, useEffect, useRef, useCallback } from "react"
import { HugeiconsIcon } from "@hugeicons/react"
import {
  ArrowLeft01Icon,
  RefreshIcon,
  PauseIcon,
  PlayIcon,
  Delete02Icon,
  Search01Icon,
  CheckmarkCircle02Icon,
  Cancel01Icon,
  TerminalIcon,
  DatabaseIcon,
} from "@hugeicons/core-free-icons"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { useWatchConsole } from "@/hooks/use-watch-console"
import {
  getWatch,
  updateWatch,
  deleteWatch,
  scanNow,
  type Watch,
  type WatchEvent,
} from "@/lib/watches-api"
import { PLATFORM_LABELS, PLATFORM_COLORS } from "@/lib/api"

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(ts: string | null): string {
  if (!ts) return "Never"
  const d = new Date(ts)
  return d.toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" })
}

function relativeTime(iso: string | null): string {
  if (!iso) return "Never"
  const diff = Date.now() - new Date(iso).getTime()
  const min = Math.floor(diff / 60_000)
  if (min < 1) return "Just now"
  if (min < 60) return `${min}m ago`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}h ago`
  return `${Math.floor(hr / 24)}d ago`
}

function nextScan(iso: string | null): string {
  if (!iso) return "—"
  const diff = new Date(iso).getTime() - Date.now()
  if (diff <= 0) return "Imminent"
  const min = Math.ceil(diff / 60_000)
  return `in ${min}m`
}

// ── Console line colors ───────────────────────────────────────────────────────

const LEVEL_CLASS: Record<string, string> = {
  info: "text-muted-foreground",
  debug: "text-muted-foreground opacity-60",
  warn: "text-yellow-500",
  error: "text-red-500",
  success: "text-green-500",
}

// ── EventCard ─────────────────────────────────────────────────────────────────

function EventCard({ event }: { event: WatchEvent }) {
  return (
    <div
      className={`rounded-lg border p-3 text-sm ${
        event.criteria_met
          ? "border-green-300 bg-green-50 dark:bg-green-950/30"
          : "border-border bg-muted/30"
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="text-xs text-muted-foreground">{fmt(event.scanned_at)}</span>
        {event.criteria_met ? (
          <Badge className="text-xs bg-green-600 text-white">Deal found!</Badge>
        ) : event.found_in_stock ? (
          <Badge variant="secondary" className="text-xs">In stock</Badge>
        ) : (
          <Badge variant="outline" className="text-xs text-muted-foreground">No stock</Badge>
        )}
      </div>
      {event.price != null && (
        <div className="flex items-baseline gap-2">
          <span className="font-bold">₹{event.price.toFixed(0)}</span>
          {event.mrp != null && event.mrp > event.price && (
            <span className="line-through text-muted-foreground text-xs">₹{event.mrp.toFixed(0)}</span>
          )}
          {event.discount_pct != null && event.discount_pct > 0 && (
            <span className="text-green-600 text-xs font-medium">{event.discount_pct.toFixed(0)}% off</span>
          )}
        </div>
      )}
      {event.store_name && (
        <div className="text-xs text-muted-foreground mt-0.5">
          📍 {event.store_name}
          {event.distance_km != null && ` · ${event.distance_km.toFixed(1)}km`}
        </div>
      )}
      {event.notes && (
        <div className="text-xs text-muted-foreground mt-0.5 italic">{event.notes}</div>
      )}
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

interface WatchDetailProps {
  watchId: string
  onBack: () => void
  onDelete: () => void
}

export function WatchDetail({ watchId, onBack, onDelete }: WatchDetailProps) {
  const [watch, setWatch] = useState<Watch | null>(null)
  const [events, setEvents] = useState<WatchEvent[]>([])
  const [loadState, setLoadState] = useState<"loading" | "ok" | "error">("loading")
  const [loadError, setLoadError] = useState("")
  const [scanning, setScanning] = useState(false)
  const [toggling, setToggling] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const consoleBottomRef = useRef<HTMLDivElement>(null)
  const { entries: consoleLogs, status: consoleStatus, clearEntries } = useWatchConsole(watchId)

  // Load watch data
  const load = useCallback(async () => {
    try {
      const data = await getWatch(watchId)
      setWatch(data.watch)
      setEvents(data.events)
      setLoadState("ok")
    } catch (e: unknown) {
      setLoadError(e instanceof Error ? e.message : "Failed to load watch")
      setLoadState("error")
    }
  }, [watchId])

  useEffect(() => {
    load()
  }, [load])

  // Auto-scroll console to bottom
  useEffect(() => {
    consoleBottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [consoleLogs.length])

  if (loadState === "loading") {
    return (
      <div className="p-4 space-y-3 max-w-xl mx-auto">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-32 rounded-xl" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
    )
  }

  if (loadState === "error") {
    return (
      <div className="p-4 max-w-xl mx-auto">
        <Button variant="ghost" onClick={onBack} className="mb-3">
          <HugeiconsIcon icon={ArrowLeft01Icon} className="size-4 mr-1" /> Back
        </Button>
        <Card className="border-destructive">
          <CardContent className="pt-6 text-center">
            <HugeiconsIcon icon={Cancel01Icon} className="size-8 text-destructive mx-auto mb-2" />
            <p className="font-medium text-destructive">{loadError}</p>
            <Button className="mt-3" variant="outline" onClick={load}>Retry</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!watch) return null

  const platformColor = PLATFORM_COLORS[watch.platform] || "#888"
  const platformLabel = PLATFORM_LABELS[watch.platform] || watch.platform

  const handleToggle = async () => {
    setToggling(true)
    try {
      const newStatus = watch.status === "active" ? "paused" : "active"
      const updated = await updateWatch(watch.id, { status: newStatus })
      setWatch(updated)
      toast.success(`Watch ${newStatus}`)
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Update failed")
    } finally {
      setToggling(false)
    }
  }

  const handleScanNow = async () => {
    setScanning(true)
    try {
      const result = await scanNow(watch.id)
      if (result.event?.criteria_met) {
        toast.success("🎉 Deal criteria met! Check scan history.")
      } else {
        toast.info("Scan complete — no qualifying deals found")
      }
      await load()
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Scan failed")
    } finally {
      setScanning(false)
    }
  }

  const handleDelete = async () => {
    if (!confirmDelete) {
      setConfirmDelete(true)
      setTimeout(() => setConfirmDelete(false), 3000)
      return
    }
    try {
      await deleteWatch(watch.id)
      toast.success("Watch deleted")
      onDelete()
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Delete failed")
    }
  }

  return (
    <div className="p-4 max-w-xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <Button variant="ghost" size="sm" onClick={onBack}>
          <HugeiconsIcon icon={ArrowLeft01Icon} className="size-4" />
        </Button>
        <h2 className="text-lg font-bold flex-1 truncate">{watch.name}</h2>
        <Button variant="ghost" size="sm" onClick={load}>
          <HugeiconsIcon icon={RefreshIcon} className="size-4" />
        </Button>
      </div>

      {/* Status card */}
      <Card className="mb-4">
        <CardContent className="pt-4 pb-3">
          <div className="flex items-center gap-2 flex-wrap mb-3">
            <Badge style={{ backgroundColor: platformColor, color: "#fff" }} className="text-xs">
              {platformLabel}
            </Badge>
            <Badge variant={watch.status === "active" ? "default" : "secondary"} className="text-xs">
              {watch.status === "active" ? "🟢 Active" : "⏸ Paused"}
            </Badge>
          </div>

          {watch.product_name && (
            <p className="font-medium mb-1">{watch.product_name}</p>
          )}
          <a
            href={watch.product_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-primary underline break-all"
            onClick={(e) => e.stopPropagation()}
          >
            {watch.product_url}
          </a>

          {/* Stats grid */}
          <div className="grid grid-cols-2 gap-2 mt-3 text-xs text-muted-foreground">
            <div>
              <span className="block font-medium text-foreground">Last scan</span>
              {relativeTime(watch.last_scan_at)}
              {watch.last_scan_at && (
                <span className="block opacity-70">{fmt(watch.last_scan_at)}</span>
              )}
            </div>
            <div>
              <span className="block font-medium text-foreground">Next scan</span>
              {nextScan(watch.next_scan_at)}
            </div>
            <div>
              <span className="block font-medium text-foreground">Total scans</span>
              {watch.scan_count}
            </div>
            <div>
              <span className="block font-medium text-foreground">Deals found</span>
              <span className={watch.found_count > 0 ? "text-green-600 font-bold" : ""}>
                {watch.found_count}
              </span>
            </div>
          </div>

          {/* Config chips */}
          <div className="flex gap-1.5 flex-wrap mt-3">
            <span className="px-1.5 py-0.5 rounded bg-muted text-xs">🔁 {watch.interval_minutes}min</span>
            <span className="px-1.5 py-0.5 rounded bg-muted text-xs">📍 {watch.radius_km}km</span>
            {watch.in_stock_only && (
              <span className="px-1.5 py-0.5 rounded bg-muted text-xs">In stock only</span>
            )}
            {watch.max_price != null && (
              <span className="px-1.5 py-0.5 rounded bg-muted text-xs">≤ ₹{watch.max_price}</span>
            )}
            {watch.min_discount_pct != null && (
              <span className="px-1.5 py-0.5 rounded bg-muted text-xs">≥{watch.min_discount_pct}% off</span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Action buttons */}
      <div className="flex gap-2 mb-4">
        <Button
          variant="outline"
          onClick={handleToggle}
          disabled={toggling}
          className="flex-1"
        >
          {toggling ? (
            <Spinner className="size-4 mr-1" />
          ) : watch.status === "active" ? (
            <>
              <HugeiconsIcon icon={PauseIcon} className="size-4 mr-1" /> Pause
            </>
          ) : (
            <>
              <HugeiconsIcon icon={PlayIcon} className="size-4 mr-1" /> Resume
            </>
          )}
        </Button>

        <Button
          variant="outline"
          onClick={handleScanNow}
          disabled={scanning}
          className="flex-1"
        >
          {scanning ? (
            <>
              <Spinner className="size-4 mr-1" /> Scanning...
            </>
          ) : (
            <>
              <HugeiconsIcon icon={Search01Icon} className="size-4 mr-1" /> Scan now
            </>
          )}
        </Button>

        <Button
          variant={confirmDelete ? "destructive" : "ghost"}
          onClick={handleDelete}
          title={confirmDelete ? "Click again to confirm" : "Delete watch"}
        >
          {confirmDelete ? (
            <HugeiconsIcon icon={CheckmarkCircle02Icon} className="size-4" />
          ) : (
            <HugeiconsIcon icon={Delete02Icon} className="size-4" />
          )}
        </Button>
      </div>

      {/* Tabs: History + Console */}
      <Tabs defaultValue="history">
        <TabsList className="w-full mb-3">
          <TabsTrigger value="history" className="flex-1">
            <HugeiconsIcon icon={DatabaseIcon} className="size-4 mr-1" />
            Scan History ({events.length})
          </TabsTrigger>
          <TabsTrigger value="console" className="flex-1">
            <HugeiconsIcon icon={TerminalIcon} className="size-4 mr-1" />
            Live Console
            {consoleStatus === "connected" && (
              <span className="ml-1 size-2 rounded-full bg-green-500 inline-block" />
            )}
            {consoleStatus === "reconnecting" && (
              <span className="ml-1 size-2 rounded-full bg-yellow-500 inline-block animate-pulse" />
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="history">
          {events.length === 0 ? (
            <div className="text-center py-10 text-muted-foreground text-sm">
              No scan history yet. Press "Scan now" or wait for the next scheduled scan.
            </div>
          ) : (
            <div className="space-y-2">
              {events.map((e) => (
                <EventCard key={e.id} event={e} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="console">
          <div className="flex items-center justify-between mb-2 text-xs text-muted-foreground">
            <span>
              {consoleStatus === "connected" && "● Connected"}
              {consoleStatus === "connecting" && "⏳ Connecting..."}
              {consoleStatus === "reconnecting" && "↺ Reconnecting..."}
              {consoleStatus === "disconnected" && "○ Disconnected"}
            </span>
            <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={clearEntries}>
              Clear
            </Button>
          </div>

          <div className="rounded-lg border bg-black/90 text-xs font-mono p-3 h-80 overflow-y-auto">
            {consoleLogs.length === 0 ? (
              <div className="text-muted-foreground text-center py-8">
                Waiting for scan activity...
                <br />
                Press "Scan now" to see live output.
              </div>
            ) : (
              consoleLogs.map((entry, i) => (
                <div key={i} className={`leading-5 ${LEVEL_CLASS[entry.level] || "text-muted-foreground"}`}>
                  <span className="opacity-50 mr-1.5 select-none">
                    {new Date(entry.ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                  </span>
                  {entry.msg}
                </div>
              ))
            )}
            <div ref={consoleBottomRef} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
