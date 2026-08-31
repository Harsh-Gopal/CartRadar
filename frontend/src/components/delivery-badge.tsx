/**
 * DeliveryBadge — shows whether a platform is currently delivering.
 *
 * Usage:
 *   <DeliveryBadge platform="blinkit" city="Kharar" />
 *
 * Fetches /api/delivery-hours?city=<city> once and caches per session.
 */
import { useEffect, useState } from "react"
import { getDeliveryHours, type DeliveryStatus } from "@/lib/api"

// Module-level cache so the fetch isn't repeated on re-renders.
const _cache: Record<string, Record<string, DeliveryStatus>> = {}

function usePlatformDelivery(platform: string, city?: string | null) {
  const cacheKey = city ? city.toLowerCase() : "__no_city__"
  const [status, setStatus] = useState<DeliveryStatus | null>(
    () => _cache[cacheKey]?.[platform] ?? null
  )

  useEffect(() => {
    if (_cache[cacheKey]?.[platform]) {
      setStatus(_cache[cacheKey][platform])
      return
    }
    getDeliveryHours(city ?? undefined)
      .then((all) => {
        _cache[cacheKey] = all
        setStatus(all[platform] ?? null)
      })
      .catch(() => {/* best-effort */})
  }, [platform, cacheKey, city])

  return status
}

interface DeliveryBadgeProps {
  platform: string
  city?: string | null
  className?: string
}

const STATUS_STYLES = {
  open: "bg-green-500/15 text-green-600 dark:text-green-400 border-green-500/30",
  closed: "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/30",
  always: "bg-primary/10 text-primary border-primary/20",
  unknown: "bg-muted text-muted-foreground border-border",
}

export function DeliveryBadge({ platform, city, className }: DeliveryBadgeProps) {
  const status = usePlatformDelivery(platform, city)
  if (!status) return null

  let styleKey: keyof typeof STATUS_STYLES
  let label: string

  if (status.is_open === null) {
    styleKey = "unknown"
    label = "Hours unknown"
  } else if (status.always_open) {
    styleKey = "always"
    label = "Delivers 24×7"
  } else if (status.is_open) {
    styleKey = "open"
    label = `Open until ${status.closes_at} IST`
  } else {
    styleKey = "closed"
    label = status.opens_at ? `Opens at ${status.opens_at} IST` : "Currently closed"
  }

  return (
    <span
      title={status.notes}
      className={`inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded border ${STATUS_STYLES[styleKey]} ${className ?? ""}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${
        styleKey === "always" || styleKey === "open"
          ? "bg-current animate-pulse"
          : "bg-current opacity-50"
      }`} />
      {label}
    </span>
  )
}

/**
 * DeliveryWarningBanner — full-width warning when searching during closed hours.
 * Only shown when the platform is definitively closed (not unknown or always-open).
 */
interface DeliveryWarningProps {
  platform: string
  city?: string | null
}

export function DeliveryWarningBanner({ platform, city }: DeliveryWarningProps) {
  const status = usePlatformDelivery(platform, city)

  if (!status || status.is_open !== false || status.always_open) return null

  return (
    <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2.5 text-xs text-amber-700 dark:text-amber-400">
      <span className="text-base leading-none mt-0.5">⚠️</span>
      <span>
        <strong>{status.label}</strong> is not delivering right now.
        {status.opens_at && (
          <> Delivery restarts at <strong>{status.opens_at} IST</strong>.</>
        )}{" "}
        Results may show available stock but no order can be placed.
        <br />
        <span className="opacity-70">{status.notes}</span>
      </span>
    </div>
  )
}
