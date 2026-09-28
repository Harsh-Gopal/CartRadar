/**
 * CreateWatch — multi-step watch creation form.
 * Step 1: Paste product URL → resolve preview
 * Step 2: Configure deal criteria + interval + notifications
 * Step 3: Confirm and create
 *
 * Never hangs: every async call has timeout + error state.
 */

import { useState, useCallback } from "react"
import { HugeiconsIcon } from "@hugeicons/react"
import {
  ArrowLeft01Icon,
  Link01Icon,
  CheckmarkCircle02Icon,
  Cancel01Icon,
  LocationUpdate01Icon,
} from "@hugeicons/core-free-icons"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"
import { LocationSearch } from "@/components/location-search"
import { resolveProductUrl, createWatch, type ResolvedUrl, type CreateWatchPayload } from "@/lib/watches-api"
import { PLATFORM_LABELS, PLATFORM_COLORS, type GeocodeResponse } from "@/lib/api"

const INTERVALS: Array<{ value: 5 | 15 | 30; label: string }> = [
  { value: 5, label: "Every 5 minutes" },
  { value: 15, label: "Every 15 minutes (recommended)" },
  { value: 30, label: "Every 30 minutes" },
]

interface Props {
  onBack: () => void
  onCreated: (watchId: string) => void
  initialLat?: number
  initialLng?: number
}

export function CreateWatch({ onBack, onCreated, initialLat, initialLng }: Props) {
  // URL step
  const [url, setUrl] = useState("")
  const [resolving, setResolving] = useState(false)
  const [resolveError, setResolveError] = useState("")
  const [resolved, setResolved] = useState<ResolvedUrl | null>(null)

  // Location
  const [location, setLocation] = useState<GeocodeResponse | null>(
    initialLat && initialLng ? { lat: initialLat, lng: initialLng, label: "Current location" } : null
  )

  // Config
  const [name, setName] = useState("")
  const [interval, setInterval] = useState<5 | 15 | 30>(15)
  const [inStockOnly, setInStockOnly] = useState(true)
  const [maxPrice, setMaxPrice] = useState("")
  const [minDiscount, setMinDiscount] = useState("")
  const [radiusKm, setRadiusKm] = useState("10")
  const [telegramChatId, setTelegramChatId] = useState("")
  const [notifyBrowser, setNotifyBrowser] = useState(true)

  // Submit
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState("")

  const handleResolve = useCallback(async () => {
    if (!url.trim()) return
    setResolving(true)
    setResolveError("")
    setResolved(null)
    try {
      const result = await resolveProductUrl(url.trim(), location?.lat, location?.lng)
      setResolved(result)
      if (!name) {
        setName(result.product_name || `Watch ${result.platform}/${result.product_id.slice(0, 8)}`)
      }
    } catch (e: unknown) {
      setResolveError(e instanceof Error ? e.message : "Failed to resolve URL")
    } finally {
      setResolving(false)
    }
  }, [url, location, name])

  const handleCreate = useCallback(async () => {
    if (!resolved || !location) return
    setCreating(true)
    setCreateError("")
    try {
      const payload: CreateWatchPayload = {
        name: name.trim() || `Watch ${resolved.platform}/${resolved.product_id.slice(0, 8)}`,
        product_url: resolved.product_url,
        lat: location.lat,
        lng: location.lng,
        radius_km: parseFloat(radiusKm) || 10,
        interval_minutes: interval,
        in_stock_only: inStockOnly,
        max_price: maxPrice ? parseFloat(maxPrice) : null,
        min_discount_pct: minDiscount ? parseFloat(minDiscount) : null,
        telegram_chat_id: telegramChatId.trim() || null,
        notify_browser: notifyBrowser,
      }
      const watch = await createWatch(payload)
      toast.success("Watch created! First scan will run at the scheduled interval.")
      onCreated(watch.id)
    } catch (e: unknown) {
      setCreateError(e instanceof Error ? e.message : "Failed to create watch")
    } finally {
      setCreating(false)
    }
  }, [resolved, location, name, radiusKm, interval, inStockOnly, maxPrice, minDiscount, telegramChatId, notifyBrowser, onCreated])

  const platformColor = resolved ? (PLATFORM_COLORS[resolved.platform] || "#888") : "#888"
  const platformLabel = resolved ? (PLATFORM_LABELS[resolved.platform] || resolved.platform) : ""

  return (
    <div className="p-4 max-w-xl mx-auto">
      <div className="flex items-center gap-2 mb-4">
        <Button variant="ghost" size="sm" onClick={onBack}>
          <HugeiconsIcon icon={ArrowLeft01Icon} className="size-4" />
        </Button>
        <h2 className="text-lg font-bold">New Watch</h2>
      </div>

      {/* Step 1: URL */}
      <Card className="mb-4">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-1.5">
            <HugeiconsIcon icon={Link01Icon} className="size-4" />
            Product URL
          </CardTitle>
          <CardDescription className="text-xs">
            Paste a product link from Zepto, Instamart, BigBasket, Blinkit, etc.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Input
              value={url}
              onChange={(e) => { setUrl(e.target.value); setResolved(null); setResolveError("") }}
              placeholder="https://www.swiggy.com/instamart/item/..."
              className="flex-1 text-sm"
              onKeyDown={(e) => e.key === "Enter" && handleResolve()}
            />
            <Button onClick={handleResolve} disabled={resolving || !url.trim()}>
              {resolving ? <Spinner className="size-4" /> : "Resolve"}
            </Button>
          </div>

          {resolveError && (
            <div className="flex items-center gap-1.5 text-destructive text-sm">
              <HugeiconsIcon icon={Cancel01Icon} className="size-4 shrink-0" />
              {resolveError}
            </div>
          )}

          {resolved && (
            <div className="rounded-lg border bg-muted/40 p-3 flex gap-3">
              {resolved.product_image && (
                <img
                  src={resolved.product_image}
                  alt=""
                  className="size-12 rounded object-cover shrink-0"
                />
              )}
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span
                    className="text-xs px-1.5 py-0.5 rounded text-white font-medium"
                    style={{ backgroundColor: platformColor }}
                  >
                    {platformLabel}
                  </span>
                  <HugeiconsIcon icon={CheckmarkCircle02Icon} className="size-4 text-green-500" />
                </div>
                <p className="text-sm font-medium truncate">
                  {resolved.product_name || `Product ${resolved.product_id}`}
                </p>
                <p className="text-xs text-muted-foreground font-mono">{resolved.product_id}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Step 2: Location */}
      <Card className="mb-4">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-1.5">
            <HugeiconsIcon icon={LocationUpdate01Icon} className="size-4" />
            Location
          </CardTitle>
          <CardDescription className="text-xs">
            Search area to check for availability
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <LocationSearch
            onCoords={(coords) => setLocation(coords)}
            coords={location}
            placeholder="Search a locality, area, or pincode..."
          />
          {location && (
            <p className="text-xs text-muted-foreground">
              📍 {location.label} ({location.lat.toFixed(4)}, {location.lng.toFixed(4)})
            </p>
          )}

          <div className="flex items-center gap-2">
            <Label className="text-xs shrink-0">Radius</Label>
            <Input
              type="number"
              value={radiusKm}
              onChange={(e) => setRadiusKm(e.target.value)}
              min={1}
              max={30}
              className="w-24 text-sm"
            />
            <span className="text-xs text-muted-foreground">km (1–30)</span>
          </div>
        </CardContent>
      </Card>

      {/* Step 3: Config */}
      <Card className="mb-4">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Watch Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <Label className="text-xs mb-1 block">Watch name</Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Amul Milk deal tracker"
              className="text-sm"
            />
          </div>

          <div>
            <Label className="text-xs mb-1 block">Scan interval</Label>
            <div className="flex gap-2">
              {INTERVALS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setInterval(opt.value)}
                  className={`flex-1 py-1.5 px-2 rounded-md border text-xs font-medium transition-colors ${
                    interval === opt.value
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-input bg-background hover:bg-muted"
                  }`}
                >
                  {opt.value}m
                </button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {INTERVALS.find((o) => o.value === interval)?.label}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="in-stock"
              checked={inStockOnly}
              onChange={(e) => setInStockOnly(e.target.checked)}
              className="rounded"
            />
            <Label htmlFor="in-stock" className="text-xs cursor-pointer">
              Only alert when in stock
            </Label>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label className="text-xs mb-1 block">Max price (₹)</Label>
              <Input
                type="number"
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value)}
                placeholder="e.g. 299"
                className="text-sm"
              />
            </div>
            <div>
              <Label className="text-xs mb-1 block">Min discount (%)</Label>
              <Input
                type="number"
                value={minDiscount}
                onChange={(e) => setMinDiscount(e.target.value)}
                placeholder="e.g. 20"
                className="text-sm"
              />
            </div>
          </div>

          <details className="text-xs">
            <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
              Notifications (optional)
            </summary>
            <div className="mt-2 space-y-2 pl-2 border-l">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="notify-browser"
                  checked={notifyBrowser}
                  onChange={(e) => setNotifyBrowser(e.target.checked)}
                />
                <Label htmlFor="notify-browser" className="cursor-pointer">
                  Browser notifications
                </Label>
              </div>
              <div>
                <Label className="mb-1 block">Telegram Chat ID (override)</Label>
                <Input
                  value={telegramChatId}
                  onChange={(e) => setTelegramChatId(e.target.value)}
                  placeholder="Leave blank to use global Telegram config"
                  className="text-xs"
                />
              </div>
            </div>
          </details>
        </CardContent>
      </Card>

      {createError && (
        <div className="rounded-lg border border-destructive bg-destructive/10 p-3 mb-3 text-sm text-destructive flex items-center gap-2">
          <HugeiconsIcon icon={Cancel01Icon} className="size-4 shrink-0" />
          {createError}
        </div>
      )}

      <Button
        className="w-full h-11"
        disabled={!resolved || !location || creating}
        onClick={handleCreate}
      >
        {creating ? (
          <>
            <Spinner className="size-4 mr-2" />
            Creating watch...
          </>
        ) : (
          "Create Watch"
        )}
      </Button>

      {(!resolved || !location) && !creating && (
        <p className="text-xs text-muted-foreground text-center mt-2">
          {!resolved ? "Resolve a product URL first" : "Set a location to continue"}
        </p>
      )}
    </div>
  )
}
