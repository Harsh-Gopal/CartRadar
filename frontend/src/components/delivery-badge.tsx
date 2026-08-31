/**
 * DeliveryBadge — shows real-time delivery availability for a platform.
 *
 * Uses /api/serviceability (actual platform API) when coordinates are available.
 * Falls back to showing nothing if the check hasn't completed yet.
 *
 * Usage:
 *   <DeliveryBadge platform="blinkit" serviceability={serviceability?.blinkit} />
 */
import type { PlatformServiceability } from "@/lib/api"

interface DeliveryBadgeProps {
  platform: string
  serviceability?: PlatformServiceability | null
  loading?: boolean
  className?: string
}

const STATUS_STYLES = {
  open: "bg-green-500/15 text-green-600 dark:text-green-400 border-green-500/30",
  closed: "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/30",
  unknown: "bg-muted/60 text-muted-foreground border-border",
  checking: "bg-muted/60 text-muted-foreground border-border",
}

export function DeliveryBadge({ serviceability, loading, className }: DeliveryBadgeProps) {
  if (loading) {
    return (
      <span className={`inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded border ${STATUS_STYLES.checking} ${className ?? ""}`}>
        <span className="w-1.5 h-1.5 rounded-full bg-current opacity-40 animate-pulse" />
        Checking delivery…
      </span>
    )
  }

  if (!serviceability) return null

  const { is_open, source, eta_minutes, city } = serviceability

  if (source === "skipped" || source === "error" || source === "timeout") return null

  let styleKey: keyof typeof STATUS_STYLES
  let label: string

  if (is_open === null) {
    return null // don't show if unknown
  } else if (is_open) {
    styleKey = "open"
    label = eta_minutes ? `Delivering · ~${eta_minutes} min` : `Delivering now${city ? ` in ${city}` : ""}`
  } else {
    styleKey = "closed"
    label = "Not delivering here"
  }

  return (
    <span
      className={`inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded border ${STATUS_STYLES[styleKey]} ${className ?? ""}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full bg-current ${is_open ? "animate-pulse" : "opacity-50"}`} />
      {label}
    </span>
  )
}

/**
 * DeliveryWarningBanner — shown when platform is definitively NOT delivering.
 * Uses real-time serviceability data from /api/serviceability.
 */
interface DeliveryWarningProps {
  platform: string
  platformLabel: string
  serviceability?: PlatformServiceability | null
}

export function DeliveryWarningBanner({ platformLabel, serviceability }: DeliveryWarningProps) {
  if (!serviceability) return null
  if (serviceability.is_open !== false) return null
  if (serviceability.source !== "live") return null

  return (
    <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2.5 text-xs text-amber-700 dark:text-amber-400">
      <span className="text-base leading-none mt-0.5">⚠️</span>
      <span>
        <strong>{platformLabel}</strong> is currently not delivering to your selected location.
        Stock may still be visible but no order can be placed right now.
      </span>
    </div>
  )
}
