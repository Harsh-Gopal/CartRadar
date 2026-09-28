/**
 * My Watches page — lists all active/paused watches with status, actions.
 * Never hangs on loading: shows skeleton → data or error.
 */

import { useState } from "react"
import { HugeiconsIcon } from "@hugeicons/react"
import {
  Add01Icon,
  RefreshIcon,
  PauseIcon,
  PlayIcon,
  Delete02Icon,
  CheckmarkCircle02Icon,
  Cancel01Icon,
  ClockIcon,
  Search01Icon,
} from "@hugeicons/core-free-icons"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import { useWatches } from "@/hooks/use-watches"
import { updateWatch, deleteWatch, scanNow, type Watch } from "@/lib/watches-api"
import { PLATFORM_LABELS, PLATFORM_COLORS } from "@/lib/api"

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatRelative(iso: string | null): string {
  if (!iso) return "Never"
  const diff = Date.now() - new Date(iso).getTime()
  const min = Math.floor(diff / 60_000)
  if (min < 1) return "Just now"
  if (min < 60) return `${min}m ago`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}h ago`
  return `${Math.floor(hr / 24)}d ago`
}

function formatNextScan(iso: string | null): string {
  if (!iso) return "—"
  const diff = new Date(iso).getTime() - Date.now()
  if (diff <= 0) return "Imminent"
  const min = Math.ceil(diff / 60_000)
  if (min < 60) return `in ${min}m`
  return `in ${Math.floor(min / 60)}h ${min % 60}m`
}

// ── WatchCard ─────────────────────────────────────────────────────────────────

interface WatchCardProps {
  watch: Watch
  onSelect: (id: string) => void
  onRefresh: () => void
}

function WatchCard({ watch, onSelect, onRefresh }: WatchCardProps) {
  const [pausing, setPausing] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [confirming, setConfirming] = useState(false)

  const handleToggle = async () => {
    setPausing(true)
    try {
      const newStatus = watch.status === "active" ? "paused" : "active"
      await updateWatch(watch.id, { status: newStatus })
      toast.success(`Watch ${newStatus === "active" ? "resumed" : "paused"}`)
      onRefresh()
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to update watch")
    } finally {
      setPausing(false)
    }
  }

  const handleScanNow = async () => {
    setScanning(true)
    try {
      const result = await scanNow(watch.id)
      toast.success(
        result.event?.criteria_met
          ? "✅ Scan complete — deal criteria met!"
          : "Scan complete — no qualifying results",
      )
      onRefresh()
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Scan failed")
    } finally {
      setScanning(false)
    }
  }

  const handleDelete = async () => {
    if (!confirming) {
      setConfirming(true)
      setTimeout(() => setConfirming(false), 3000)
      return
    }
    try {
      await deleteWatch(watch.id)
      toast.success("Watch deleted")
      onRefresh()
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Failed to delete watch")
    }
  }

  const platformColor = PLATFORM_COLORS[watch.platform] || "#888"
  const platformLabel = PLATFORM_LABELS[watch.platform] || watch.platform

  return (
    <Card
      className="cursor-pointer transition-shadow hover:shadow-md"
      onClick={() => onSelect(watch.id)}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge
                style={{ backgroundColor: platformColor, color: "#fff" }}
                className="shrink-0 text-xs"
              >
                {platformLabel}
              </Badge>
              <Badge
                variant={watch.status === "active" ? "default" : "secondary"}
                className="text-xs"
              >
                {watch.status === "active" ? "Active" : "Paused"}
              </Badge>
              {watch.found_count > 0 && (
                <Badge variant="outline" className="text-xs text-green-600 border-green-300">
                  {watch.found_count} deal{watch.found_count !== 1 ? "s" : ""} found
                </Badge>
              )}
            </div>
            <CardTitle className="mt-1.5 text-sm font-semibold truncate">{watch.name}</CardTitle>
            {watch.product_name && (
              <p className="text-xs text-muted-foreground truncate">{watch.product_name}</p>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        {/* Stats row */}
        <div className="flex gap-4 text-xs text-muted-foreground mb-3">
          <span title="Last scan">⏱ {formatRelative(watch.last_scan_at)}</span>
          <span title="Next scan">
            <HugeiconsIcon icon={ClockIcon} className="inline size-3 mr-0.5" />
            {formatNextScan(watch.next_scan_at)}
          </span>
          <span title="Scan count">📊 {watch.scan_count} scans</span>
          <span title="Interval">🔁 {watch.interval_minutes}min</span>
        </div>

        {/* Criteria chips */}
        <div className="flex gap-1.5 flex-wrap mb-3">
          {watch.in_stock_only && (
            <span className="px-1.5 py-0.5 rounded bg-muted text-xs">In stock only</span>
          )}
          {watch.max_price != null && (
            <span className="px-1.5 py-0.5 rounded bg-muted text-xs">≤ ₹{watch.max_price}</span>
          )}
          {watch.min_discount_pct != null && (
            <span className="px-1.5 py-0.5 rounded bg-muted text-xs">≥{watch.min_discount_pct}% off</span>
          )}
          <span className="px-1.5 py-0.5 rounded bg-muted text-xs">{watch.radius_km}km</span>
        </div>

        {/* Actions */}
        <div
          className="flex items-center gap-2"
          onClick={(e) => e.stopPropagation()} // prevent card click when clicking buttons
        >
          <Button
            size="sm"
            variant="outline"
            onClick={handleToggle}
            disabled={pausing}
            className="flex-1 text-xs"
          >
            {pausing ? (
              <Spinner className="size-3" />
            ) : watch.status === "active" ? (
              <>
                <HugeiconsIcon icon={PauseIcon} className="size-3 mr-1" /> Pause
              </>
            ) : (
              <>
                <HugeiconsIcon icon={PlayIcon} className="size-3 mr-1" /> Resume
              </>
            )}
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={handleScanNow}
            disabled={scanning}
            title="Trigger immediate scan"
          >
            {scanning ? <Spinner className="size-3" /> : <HugeiconsIcon icon={Search01Icon} className="size-3" />}
          </Button>

          <Button
            size="sm"
            variant={confirming ? "destructive" : "ghost"}
            onClick={handleDelete}
            title={confirming ? "Click again to confirm delete" : "Delete watch"}
          >
            {confirming ? (
              <HugeiconsIcon icon={CheckmarkCircle02Icon} className="size-3" />
            ) : (
              <HugeiconsIcon icon={Delete02Icon} className="size-3" />
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

interface MyWatchesProps {
  onCreateWatch: () => void
  onSelectWatch: (id: string) => void
}

export function MyWatches({ onCreateWatch, onSelectWatch }: MyWatchesProps) {
  const { watches, loading, error, refresh } = useWatches()

  if (loading) {
    return (
      <div className="p-4 space-y-3 max-w-xl mx-auto">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-40 rounded-xl" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 max-w-xl mx-auto">
        <Card className="border-destructive">
          <CardContent className="pt-6 text-center">
            <HugeiconsIcon icon={Cancel01Icon} className="size-8 text-destructive mx-auto mb-2" />
            <p className="font-medium text-destructive">{error}</p>
            <Button className="mt-3" variant="outline" onClick={refresh}>
              <HugeiconsIcon icon={RefreshIcon} className="size-4 mr-1" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-4 max-w-xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold">My Watches</h2>
        <div className="flex gap-2">
          <Button size="sm" variant="ghost" onClick={refresh}>
            <HugeiconsIcon icon={RefreshIcon} className="size-4" />
          </Button>
          <Button size="sm" onClick={onCreateWatch}>
            <HugeiconsIcon icon={Add01Icon} className="size-4 mr-1" />
            New Watch
          </Button>
        </div>
      </div>

      {watches.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <div className="text-4xl mb-3">📡</div>
          <p className="font-medium">No watches yet</p>
          <p className="text-sm mt-1">Create a watch to monitor a product for deals.</p>
          <Button className="mt-4" onClick={onCreateWatch}>
            <HugeiconsIcon icon={Add01Icon} className="size-4 mr-1" />
            Create your first watch
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {watches.map((w) => (
            <WatchCard
              key={w.id}
              watch={w}
              onSelect={onSelectWatch}
              onRefresh={refresh}
            />
          ))}
        </div>
      )}
    </div>
  )
}
