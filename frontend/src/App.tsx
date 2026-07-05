import { useEffect, useMemo, useRef, useState } from "react"

import { HugeiconsIcon } from "@hugeicons/react"
import {
  Alert01Icon,
  CancelCircleIcon,
  CheckmarkCircle02Icon,
  LocationOffline01Icon,
  LockKeyIcon,
  MapPinIcon,
  PackageRemoveIcon,
  Refresh01Icon,
  Search01Icon,
  Link01Icon,
  Cancel01Icon,
  ArrowUpRight01Icon,
  Copy01Icon,
} from "@hugeicons/core-free-icons"
import { toast } from "sonner"


import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group"
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from "@/components/ui/item"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { Slider } from "@/components/ui/slider"
import { Toaster } from "@/components/ui/sonner"
import { Spinner } from "@/components/ui/spinner"

import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { LocationSearch } from "@/components/location-search"
import { PlatformBadge } from "@/components/platform-badge"

import { Navbar } from "@/components/navbar"
import { HeroSection } from "@/components/hero-section"
import { PriceSummary } from "@/components/price-summary"
import {
  ResultsList,
  ResultsSkeleton,
  STATUS_LABEL,
  STATUS_VARIANT,
  formatPrice,
  prettyStoreName,
} from "@/components/results-list"
import { ResultsMap } from "@/components/results-map"
import { useAddressDetails } from "@/lib/use-address"
import { useSearch } from "@/hooks/use-search"
import {
  detectPlatformFromUrl,
  getConfig,
  getToken,
  PLATFORM_LABELS,
  resolveLink,
  setToken,
  type AppConfig,
  type GeocodeResponse,
  type ResolveResponse,
  type StoreResult,
} from "@/lib/api"

interface RecentProduct {
  pvid: string
  platform: string
  name: string | null
  image_url: string | null
  link: string
}

function load<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null
  }
}

function save(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // storage full/blocked — persistence is best-effort
  }
}

function looksResolvable(text: string): boolean {
  return (
    /\/pvid\/[0-9a-fA-F-]{36}/.test(text) ||
    ((/zepto|swiggy|bigbasket|blinkit|instamart/i.test(text) ||
      detectPlatformFromUrl(text) !== null) &&
      /https?:\/\//.test(text))
  )
}

const RADIUS_PRESETS = [5, 10, 20, 30]

function AddressSection({ lat, lng }: { lat: number; lng: number }) {
  const { details, loading } = useAddressDetails(lat, lng)

  if (loading) {
    return <div className="text-xs text-muted-foreground animate-pulse mt-2 p-3 bg-muted/30 rounded-lg border">Finding precise address...</div>
  }

  if (!details) return null

  return (
    <div className="mt-2 space-y-2 bg-muted/30 rounded-lg p-3 border">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold text-foreground/80">Location Address</p>
          <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2" title={details.address}>
            {details.address}
          </p>
        </div>
        <Button 
          variant="ghost" 
          size="icon" 
          className="h-6 w-6 shrink-0" 
          onClick={() => {
            navigator.clipboard.writeText(details.address)
            toast.success("Address copied")
          }}
          title="Copy Address"
        >
          <HugeiconsIcon icon={Copy01Icon} className="w-3.5 h-3.5" />
        </Button>
      </div>

      {details.suggestions && details.suggestions.length > 0 && (
        <div className="pt-1 border-t border-border/50 mt-2">
          <p className="text-[11px] font-semibold text-foreground/80">Nearby Landmarks (for delivery reference)</p>
          <ul className="text-[11px] text-muted-foreground list-disc pl-4 mt-1 space-y-0.5">
            {details.suggestions.map((s: string, i: number) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function StepBadge({ n, done }: { n: number; done?: boolean }) {
  return (
    <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium text-muted-foreground tabular-nums">
      {done ? (
        <HugeiconsIcon icon={CheckmarkCircle02Icon} className="text-primary" />
      ) : (
        n
      )}
    </span>
  )
}

export function App() {
  const [linkText, setLinkText] = useState("")
  const [resolving, setResolving] = useState(false)
  const [resolveError, setResolveError] = useState<string | null>(null)
  const [resolved, setResolved] = useState<ResolveResponse | null>(null)
  const resolvedFor = useRef<string | null>(null)

  const [recent, setRecent] = useState<RecentProduct[]>(
    () => load("mf.recent") ?? []
  )
  const [coords, setCoordsState] = useState<GeocodeResponse | null>(() =>
    load("mf.coords")
  )
  const [radiusKm, setRadiusState] = useState<number>(
    () => load("mf.radius") ?? 5
  )

  const [onlyInStock, setOnlyInStock] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<StoreResult | null>(null)
  const [view, setView] = useState<"map" | "list">("map")
  const [lastRunKey, setLastRunKey] = useState<string | null>(null)

  const [appConfig, setAppConfig] = useState<AppConfig | null>(null)
  const [hasToken, setHasToken] = useState(() => !!getToken())
  const [tokenInput, setTokenInput] = useState("")

  // Learn the instance's radius cap and whether it's token-gated.
  useEffect(() => {
    getConfig()
      .then((cfg) => {
        setAppConfig(cfg)
        setRadiusState((r) => {
          const clamped = Math.min(r, cfg.max_radius_km)
          if (clamped !== r) save("mf.radius", clamped)
          return clamped
        })
      })
      .catch(() => {
        // Best-effort: fall back to defaults if /api/config is unreachable.
      })
  }, [])

  const maxRadius = appConfig?.max_radius_km ?? 50
  const locked = (appConfig?.auth_required ?? false) && !hasToken

  function unlock() {
    const value = tokenInput.trim()
    if (!value) return
    setToken(value)
    setHasToken(true)
    setTokenInput("")
  }

  const { state, start, cancel, reset } = useSearch()
  const autoRan = useRef(false)
  const [helpValue, setHelpValue] = useState("")
  const helpRef = useRef<HTMLDivElement>(null)

  const setCoords = (c: GeocodeResponse | null) => {
    setCoordsState(c)
    if (c) save("mf.coords", c)
  }
  const setRadius = (km: number) => {
    setRadiusState(km)
    save("mf.radius", km)
  }

  async function doResolve(text: string) {
    setResolving(true)
    setResolveError(null)
    try {
      const result = await resolveLink(text, coords)
      setResolved(result)
      resolvedFor.current = text
      setRecent((prev) => {
        const next: RecentProduct[] = [
          {
            pvid: result.pvid,
            platform: result.platform,
            name: result.product?.name ?? null,
            image_url: result.product?.image_url ?? null,
            link: text,
          },
          ...prev.filter((p) => p.pvid !== result.pvid),
        ].slice(0, 4)
        save("mf.recent", next)
        return next
      })
    } catch (e) {
      setResolved(null)
      setResolveError(
        e instanceof Error ? e.message : "Couldn't read that link."
      )
    } finally {
      setResolving(false)
    }
  }

  // Auto-resolve as soon as the pasted text looks like a Zepto link.
  useEffect(() => {
    const text = linkText.trim()
    if (
      !text ||
      resolving ||
      resolvedFor.current === text ||
      !looksResolvable(text)
    )
      return
    const timer = setTimeout(() => doResolve(text), 350)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [linkText, resolving])

  const searchKey =
    resolved && coords
      ? `${resolved.pvid}|${coords.lat.toFixed(4)},${coords.lng.toFixed(4)}|${radiusKm}`
      : null

  function startSearch(km: number, force: boolean) {
    if (!resolved || !coords) return
    setLastRunKey(
      `${resolved.pvid}|${coords.lat.toFixed(4)},${coords.lng.toFixed(4)}|${km}`
    )
    setSelectedId(null)
    setDetail(null)
    setOnlyInStock(false)
    start({
      pvid: resolved.pvid,
      platform: resolved.platform,
      lat: coords.lat,
      lng: coords.lng,
      radiusKm: km,
      force,
    })
  }

  const runSearch = (force: boolean) => startSearch(radiusKm, force)

  // Kick off the first search automatically once product + location are known.
  useEffect(() => {
    if (searchKey && !autoRan.current && state.phase === "idle") {
      autoRan.current = true
      runSearch(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchKey, state.phase])

  const sortedResults = useMemo(
    () =>
      [...state.results].sort(
        (a, b) =>
          (a.status === "in_stock" ? 0 : 1) -
            (b.status === "in_stock" ? 0 : 1) || a.distance_km - b.distance_km
      ),
    [state.results]
  )

  const inStock = useMemo(
    () => sortedResults.filter((r) => r.status === "in_stock"),
    [sortedResults]
  )
  const cheapestId = useMemo(() => {
    let best: { id: string; price: number } | null = null
    for (const r of inStock) {
      if (r.price != null && (best === null || r.price < best.price)) {
        best = { id: r.store.id, price: r.price }
      }
    }
    return inStock.length > 1 ? (best?.id ?? null) : null
  }, [inStock])

  const visibleResults = onlyInStock ? inStock : sortedResults

  const searching = state.phase === "searching"
  const probing =
    searching &&
    state.discovery !== null &&
    state.discovery.probed < state.discovery.total
  const homeInStock = state.home?.product?.status === "in_stock"
  const homeOnlySearch =
    state.phase === "done" && homeInStock && state.results.length === 0
  const paramsChanged =
    lastRunKey !== null && searchKey !== null && searchKey !== lastRunKey
  const showResults =
    coords && (searching || state.phase === "done") && !homeOnlySearch
  const pendingRows = searching
    ? Math.max(
        0,
        Math.min(
          state.totalStores > 0 ? state.totalStores - state.results.length : 3,
          6
        )
      )
    : 0
  const nextRadius = RADIUS_PRESETS.find(
    (km) => km > radiusKm && km <= maxRadius
  )

  // Result toasts on phase transitions (cancelled searches end without a
  // summary, so they stay quiet).
  const prevPhase = useRef(state.phase)
  useEffect(() => {
    if (prevPhase.current === state.phase) return
    prevPhase.current = state.phase
    if (state.phase === "done" && state.summary) {
      if (state.summary.in_stock > 0) {
        toast.success(
          `In stock at ${state.summary.in_stock} ${
            state.summary.in_stock === 1 ? "store" : "stores"
          } nearby`
        )
      } else if (homeInStock) {
        toast.success("It's in stock at your own store")
      } else if (state.summary.stores > 0) {
        toast(
          `Sold out at all ${state.summary.stores} stores within ${radiusKm} km`
        )
      }
    } else if (state.phase === "error" && state.error) {
      toast.error(state.error)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.phase])

  function handleSelect(result: StoreResult) {
    setSelectedId(result.store.id)
    setDetail(result)
  }

  // Brand click → fresh start: drop the product and any results, keep the
  // saved location and recents, scroll back up to step 1.
  function resetToStart() {
    reset()
    setLinkText("")
    setResolved(null)
    resolvedFor.current = null
    setResolveError(null)
    setLastRunKey(null)
    setSelectedId(null)
    setDetail(null)
    setOnlyInStock(false)
    setHelpValue("")
    autoRan.current = false
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  function showOnMap() {
    setView("map")
    setDetail(null)
  }

  const product = resolved?.product ?? null
  const platformName = resolved?.platform ?? "zepto"
  const platformLabel = PLATFORM_LABELS[platformName] ?? platformName
  const homePrice = state.home?.product?.price ?? null

  const statusText = probing
    ? `Mapping ${platformLabel} stores in this area…`
    : state.totalStores > 0
      ? `Checking stock at ${state.results.length}/${state.totalStores} stores…`
      : `Checking on ${platformLabel}…`

  const searchPincode = coords?.label?.match(/\b\d{6}\b/)?.[0] || null;

  return (
    <div className="min-h-screen bg-[#f9fafb] dark:bg-background flex flex-col font-sans selection:bg-primary/20">
      <Navbar />

      <main className="flex-1 w-full max-w-screen-2xl mx-auto flex flex-col">
        {locked ? (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <HugeiconsIcon
                  icon={LockKeyIcon}
                  className="text-muted-foreground"
                />
                Private instance
              </CardTitle>
              <CardDescription>
                Open the invite link you were given (it carries the access
                token), or paste the token below.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Field>
                <FieldLabel htmlFor="token">Access token</FieldLabel>
                <InputGroup>
                  <InputGroupInput
                    id="token"
                    placeholder="Paste access token"
                    value={tokenInput}
                    onChange={(e) => setTokenInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && unlock()}
                  />
                  <InputGroupAddon align="inline-end">
                    <InputGroupButton
                      onClick={unlock}
                      disabled={!tokenInput.trim()}
                    >
                      Unlock
                    </InputGroupButton>
                  </InputGroupAddon>
                </InputGroup>
              </Field>
            </CardContent>
          </Card>
        ) : (
          <>
            {!resolved && !linkText && <HeroSection />}
            
            <div className={`w-full flex flex-col lg:flex-row gap-6 p-4 md:p-6 lg:p-8 ${!resolved && !linkText ? 'max-w-3xl mx-auto' : ''}`}>
              
              {/* Left Column - Search & Controls */}
              <div className={`flex flex-col gap-6 w-full ${resolved || linkText ? 'lg:w-[480px] xl:w-[560px] shrink-0' : 'w-full'}`}>
                
                {/* Step 1 — product */}
            <Card className="animate-in fade-in-0 slide-in-from-bottom-1">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <StepBadge n={1} done={!!resolved} />
                  Product
                </CardTitle>
                {!resolved && (
                  <CardDescription>
                    Paste a link from Zepto, Instamart, BigBasket, or Blinkit
                    — it loads automatically.
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <Field data-invalid={resolveError ? true : undefined}>
                  <InputGroup className="rounded-full overflow-hidden shadow-sm">
                    <InputGroupAddon align="inline-start">
                      <HugeiconsIcon icon={Link01Icon} className="text-muted-foreground" />
                    </InputGroupAddon>
                    <InputGroupInput
                      id="link"
                      placeholder="Paste a product link from Zepto, Instamart, BigBasket, Blinkit…"
                      value={linkText}
                      aria-invalid={resolveError ? true : undefined}
                      onChange={(e) => setLinkText(e.target.value)}
                      onKeyDown={(e) =>
                        e.key === "Enter" &&
                        looksResolvable(linkText) &&
                        doResolve(linkText.trim())
                      }
                      className="px-2"
                    />
                    <InputGroupAddon align="inline-end" className="gap-1">
                      {linkText && !resolving && (
                        <InputGroupButton
                          aria-label="Clear input"
                          size="icon-sm"
                          onClick={() => {
                            setLinkText("")
                            resetToStart()
                          }}
                        >
                          <HugeiconsIcon icon={Cancel01Icon} />
                        </InputGroupButton>
                      )}
                      {resolving ? (
                        <Spinner />
                      ) : resolved ? (
                        <HugeiconsIcon
                          icon={CheckmarkCircle02Icon}
                          className="text-primary"
                        />
                      ) : (
                        <HugeiconsIcon
                          icon={Search01Icon}
                          className="text-muted-foreground"
                        />
                      )}
                    </InputGroupAddon>
                  </InputGroup>
                  {resolveError && (
                    <FieldDescription className="text-destructive">
                      {resolveError}
                    </FieldDescription>
                  )}
                </Field>

                {recent.length > 0 && !resolved && (
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs text-muted-foreground">
                      Recent:
                    </span>
                    {recent.map((r) => (
                      <button
                        type="button"
                        key={r.pvid}
                        onClick={() => setLinkText(r.link)}
                        className="flex min-h-8 items-center gap-2 rounded-full border bg-card py-1 pr-3 pl-1 text-xs transition-colors hover:bg-muted/50"
                      >
                        {r.image_url && (
                          <img
                            src={r.image_url}
                            alt=""
                            className="size-6 rounded-full border object-cover"
                          />
                        )}
                        <span className="max-w-36 truncate">
                          {r.name ?? "Product"}
                        </span>
                      </button>
                    ))}
                  </div>
                )}

                {product && (
                  <>
                    <Separator />
                    <div className="flex items-center gap-2 animate-in fade-in-0 slide-in-from-bottom-1">
                      <PlatformBadge platform={platformName} size="md" />
                    </div>
                    <Item
                      size="sm"
                      className="px-0 animate-in fade-in-0 slide-in-from-bottom-1"
                    >
                      {product.image_url && (
                        <img
                          src={product.image_url}
                          alt=""
                          className="size-16 shrink-0 rounded-lg border object-cover"
                        />
                      )}
                      <ItemContent>
                        <ItemTitle>
                          <span className="line-clamp-2">{product.name}</span>
                        </ItemTitle>
                        {product.brand && (
                          <ItemDescription>{product.brand}</ItemDescription>
                        )}
                      </ItemContent>
                      {product.price != null && (
                        <ItemActions className="flex-col items-end gap-0">
                          <span className="font-semibold text-lg tabular-nums">
                            ₹{formatPrice(product.price)}
                          </span>
                          {product.mrp != null &&
                            product.mrp > product.price && (
                              <div className="flex items-center gap-1.5 mt-0.5">
                                <Badge variant="secondary" className="h-5 px-1 text-[10px] bg-green-100 text-green-700 hover:bg-green-100 border-none">
                                  {Math.round(((product.mrp - product.price) / product.mrp) * 100)}% OFF
                                </Badge>
                                <s className="text-xs text-muted-foreground tabular-nums">
                                  ₹{formatPrice(product.mrp)}
                                </s>
                              </div>
                            )}
                        </ItemActions>
                      )}
                    </Item>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Step 2 — location & radius */}
            {resolved && (
              <Card className="animate-in fade-in-0 slide-in-from-bottom-1">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <StepBadge n={2} done={!!coords} />
                    Where to look
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <FieldGroup>
                    <LocationSearch coords={coords} onCoords={setCoords} />
                    <Field>
                      <div className="flex items-center justify-between">
                        <FieldLabel htmlFor="radius">Search radius</FieldLabel>
                        <span className="text-sm font-medium tabular-nums">
                          {radiusKm} km
                        </span>
                      </div>
                      <Slider
                        id="radius"
                        min={1}
                        max={maxRadius}
                        step={1}
                        value={[radiusKm]}
                        onValueChange={(v: number[]) => setRadius(v[0])}
                      />
                      <ToggleGroup
                        type="single"
                        variant="outline"
                        className="w-full"
                        value={String(radiusKm)}
                        onValueChange={(v: string) => v && setRadius(Number(v))}
                      >
                        {RADIUS_PRESETS.filter((km) => km <= maxRadius).map(
                          (km) => (
                            <ToggleGroupItem
                              key={km}
                              value={String(km)}
                              className="flex-1"
                            >
                              {km} km
                            </ToggleGroupItem>
                          )
                        )}
                      </ToggleGroup>
                    </Field>
                  </FieldGroup>
                </CardContent>
              </Card>
            )}

            {state.error && (
              <Alert variant="destructive">
                <HugeiconsIcon icon={CancelCircleIcon} />
                <AlertTitle>Search failed</AlertTitle>
                <AlertDescription>{state.error}</AlertDescription>
              </Alert>
            )}

            {state.notice && (
              <Alert className="animate-in fade-in-0">
                <HugeiconsIcon icon={Alert01Icon} />
                <AlertTitle>Heads up</AlertTitle>
                <AlertDescription>{state.notice}</AlertDescription>
              </Alert>
            )}

            {state.home && (
              <Alert className="animate-in fade-in-0 slide-in-from-bottom-1">
                <HugeiconsIcon
                  icon={
                    homeInStock
                      ? CheckmarkCircle02Icon
                      : state.home.serviceable
                        ? PackageRemoveIcon
                        : LocationOffline01Icon
                  }
                />
                <AlertTitle>
                  {homeInStock
                    ? "In stock at your location 🎉"
                    : state.home.serviceable
                      ? "Not available at your location"
                      : `${platformLabel} doesn't deliver to this exact spot`}
                </AlertTitle>
                <div className="flex items-start justify-between gap-4 mt-2">
                  <AlertDescription>
                    {state.home.serviceable ? (
                      <div className="flex flex-col gap-1">
                        <span>Your store: {prettyStoreName(state.home.store_name)}</span>
                        <span className="text-xs">
                          {state.home.eta_minutes != null &&
                            `~${state.home.eta_minutes} min delivery`}
                          {homeInStock && state.home.product?.price != null && (
                            <> · ₹{formatPrice(state.home.product.price)}</>
                          )}
                        </span>
                      </div>
                    ) : (
                      "Checking stores in the area instead."
                    )}
                  </AlertDescription>
                  
                  {homeInStock && resolved && (
                    <a
                      href={resolved.link ?? "#"}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="shrink-0 flex items-center gap-1 text-xs font-medium text-primary bg-primary/10 hover:bg-primary/20 px-2 py-1 rounded-md transition-colors"
                    >
                      Open in App
                      <HugeiconsIcon icon={ArrowUpRight01Icon} className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </Alert>
            )}

            {homeOnlySearch && (
              <Button variant="outline" onClick={() => runSearch(true)}>
                <HugeiconsIcon icon={Search01Icon} data-icon="inline-start" />
                Search nearby stores anyway
              </Button>
            )}

            {/* Results Area */}
            {showResults && (
              <>
                <div className="flex flex-col gap-2 mt-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium">
                      {sortedResults.length > 0 ? (
                        <>
                          In stock at {inStock.length} of {sortedResults.length} stores
                          {searching && " — still checking…"}
                        </>
                      ) : (
                        statusText
                      )}
                    </p>
                    {sortedResults.length > 0 && (
                      <ToggleGroup
                        type="single"
                        variant="outline"
                        size="sm"
                        value={onlyInStock ? "in" : "all"}
                        onValueChange={(v: string) => v && setOnlyInStock(v === "in")}
                      >
                        <ToggleGroupItem value="all">All</ToggleGroupItem>
                        <ToggleGroupItem value="in">In stock</ToggleGroupItem>
                      </ToggleGroup>
                    )}
                  </div>
                  
                  {/* Search Progress */}
                  {probing && state.discovery && (
                    <div className="mt-2 flex flex-col gap-1.5 animate-in fade-in slide-in-from-top-1">
                      <div className="h-1 w-full bg-muted overflow-hidden rounded-full">
                        <div 
                          className="h-full bg-primary transition-all duration-300 ease-out" 
                          style={{ width: `${(state.discovery.probed / Math.max(1, state.discovery.total)) * 100}%` }}
                        />
                      </div>
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>{statusText}</span>
                        <span className="tabular-nums">{state.discovery.probed}/{state.discovery.total} stores</span>
                      </div>
                    </div>
                  )}
                  
                  {inStock.length > 0 && (
                    <p className="text-xs text-muted-foreground mt-2">
                      Guest prices — the actual app may show different prices
                      for logged-in or subscription users.
                    </p>
                  )}
                  
                  {/* Results List */}
                  <div className="mt-4 flex flex-col gap-3">
                    {visibleResults.length > 0 && <PriceSummary results={visibleResults} />}
                    {visibleResults.length > 0 && (
                      <ResultsList
                        results={visibleResults}
                        selectedId={selectedId}
                        cheapestId={cheapestId}
                        searchPincode={searchPincode}
                        onSelect={handleSelect}
                      />
                    )}
                    {pendingRows > 0 && <ResultsSkeleton rows={pendingRows} />}
                    {!searching && sortedResults.length > 0 && visibleResults.length === 0 && (
                      <p className="px-4 py-3 text-sm text-muted-foreground bg-muted rounded-xl">
                        No stores match the filter.
                      </p>
                    )}
                  </div>
                </div>
              </>
            )}

            {state.phase === "done" &&
              state.summary &&
              !homeOnlySearch &&
              inStock.length === 0 && (
                <Empty>
                  <EmptyHeader>
                    <EmptyMedia variant="icon">
                      <HugeiconsIcon icon={PackageRemoveIcon} />
                    </EmptyMedia>
                    <EmptyTitle>Not available nearby</EmptyTitle>
                    <EmptyDescription>
                      None of the {state.summary.stores} stores within{" "}
                      {radiusKm} km have this in stock right now.
                    </EmptyDescription>
                  </EmptyHeader>
                  {nextRadius && (
                    <EmptyContent>
                      <Button
                        variant="outline"
                        onClick={() => {
                          setRadius(nextRadius)
                          startSearch(nextRadius, false)
                        }}
                      >
                        <HugeiconsIcon
                          icon={Search01Icon}
                          data-icon="inline-start"
                        />
                        Widen to {nextRadius} km and search again
                      </Button>
                    </EmptyContent>
                  )}
                </Empty>
              )}

            <Accordion
              type="single"
              collapsible
              ref={helpRef}
              value={helpValue}
              onValueChange={setHelpValue}
              className="mt-auto scroll-mt-24"
            >
              <AccordionItem value="how">
                <AccordionTrigger className="text-sm">
                  How does this work?
                </AccordionTrigger>
                <AccordionContent className="flex flex-col gap-2 text-sm text-muted-foreground">
                  <p>
                    Paste a product link from Zepto, Instamart, or
                    BigBasket. The app auto-detects which platform it's from
                    and checks availability at nearby dark stores (for Zepto)
                    or at your pincode (for other platforms).
                  </p>
                  <p>
                    Stock and prices are checked live against each platform's
                    own internal data — the same data their apps see.
                  </p>
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="price">
                <AccordionTrigger className="text-sm">
                  Why does the price differ from my app?
                </AccordionTrigger>
                <AccordionContent className="text-sm text-muted-foreground">
                  This tool checks as a guest. Platforms apply campaign and
                  subscription discounts in their apps that the public catalog
                  doesn't expose, so prices here may be slightly higher. The
                  relative comparison between stores still holds.
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="slow">
                <AccordionTrigger className="text-sm">
                  Why is the first search in an area slow?
                </AccordionTrigger>
                <AccordionContent className="text-sm text-muted-foreground">
                  Discovering the stores in a new area means sweeping the whole
                  circle once. Mapped areas are remembered, so every later
                  search there only runs the live stock checks and finishes in
                  seconds.
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="limited">
                <AccordionTrigger className="text-sm">
                  What does "Limited Distribution" mean?
                </AccordionTrigger>
                <AccordionContent className="text-sm text-muted-foreground">
                  When a product shows as Limited Distribution, it means the platform 
                  specifically doesn't allocate this item uniformly across all their local hubs. 
                  Some areas won't carry it at all depending on their internal fulfillment routing.
                </AccordionContent>
              </AccordionItem>
            </Accordion>
            
              </div> {/* End Left Column */}

              {/* Right Column - Sticky Map */}
              {(resolved || linkText) && (
                <div className="hidden lg:block flex-1 w-full lg:sticky lg:top-24 lg:h-[calc(100vh-8rem)]">
                  <div className="w-full h-full rounded-2xl overflow-hidden border bg-card shadow-sm relative">
                    {showResults && coords ? (
                      <ResultsMap
                        lat={coords.lat}
                        lng={coords.lng}
                        radiusKm={radiusKm}
                        results={visibleResults}
                        homeStatus={state.home?.product?.status ?? null}
                        homePrice={homePrice}
                        selectedId={selectedId}
                        searchPincode={searchPincode}
                        onSelect={handleSelect}
                        className="w-full h-full absolute inset-0"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center bg-muted/30 text-muted-foreground">
                        {resolved ? "Ready to search map" : "Map will appear here"}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div> {/* End Two-Column Layout */}
          </>
        )}
      </main>

      {/* Store detail bottom sheet */}
      <Drawer
        open={!!detail}
        onOpenChange={(open) => {
          if (!open) setDetail(null)
        }}
      >
        <DrawerContent>
          {detail && (
            <>
              <DrawerHeader>
                <DrawerTitle>{prettyStoreName(detail.store.name)}</DrawerTitle>
                <DrawerDescription>
                  {[detail.store.city, `${detail.distance_km} km away`]
                    .filter(Boolean)
                    .join(" · ")}
                </DrawerDescription>
              </DrawerHeader>
              <div className="flex flex-col gap-3 overflow-y-auto px-4">
                <Item variant="outline" size="sm">
                  {product?.image_url && (
                    <img
                      src={product.image_url}
                      alt=""
                      className="size-12 shrink-0 rounded-lg border object-cover"
                    />
                  )}
                  <ItemContent>
                    <ItemTitle>
                      <span className="line-clamp-2">{product?.name}</span>
                    </ItemTitle>
                    {detail.status === "in_stock" && (
                      <ItemDescription>
                        {STATUS_LABEL[detail.status]}
                        {detail.store.id === cheapestId &&
                          " · cheapest nearby"}
                      </ItemDescription>
                    )}
                  </ItemContent>
                  <ItemActions className="flex-col items-end gap-0">
                    {detail.status === "in_stock" && detail.price != null ? (
                      <>
                        <span className="font-semibold tabular-nums">
                          ₹{formatPrice(detail.price)}
                        </span>
                        {detail.mrp != null && detail.mrp > detail.price && (
                          <s className="text-xs text-muted-foreground tabular-nums">
                            ₹{formatPrice(detail.mrp)}
                          </s>
                        )}
                      </>
                    ) : (
                      <Badge variant={STATUS_VARIANT[detail.status]}>
                        {STATUS_LABEL[detail.status]}
                      </Badge>
                    )}
                  </ItemActions>
                </Item>
                {detail.status === "in_stock" &&
                  detail.price != null &&
                  homePrice != null &&
                  (detail.price !== homePrice ? (
                    <p className="text-sm text-muted-foreground">
                      ₹{formatPrice(Math.abs(detail.price - homePrice))}{" "}
                      {detail.price < homePrice ? "cheaper" : "more expensive"}{" "}
                      than at your store.
                    </p>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      Same price as your store.
                    </p>
                  ))}
                {detail.status === "in_stock" && detail.price != null && (
                  <p className="text-xs text-muted-foreground">
                    Guest price — {platformLabel}'s app may show a lower price, especially
                    for premium members.
                  </p>
                )}
                <p className="text-xs text-muted-foreground">
                  To order from here, set a {platformLabel} delivery address in this area
                  — stock belongs to the store, not the app.
                </p>
                
                <AddressSection lat={detail.store.lat} lng={detail.store.lng} />
              </div>
              <DrawerFooter>
                {view === "list" && (
                  <Button variant="outline" onClick={showOnMap}>
                    <HugeiconsIcon icon={MapPinIcon} data-icon="inline-start" />
                    Show on map
                  </Button>
                )}
                <DrawerClose asChild>
                  <Button variant="ghost">Close</Button>
                </DrawerClose>
              </DrawerFooter>
            </>
          )}
        </DrawerContent>
      </Drawer>

      {/* Sticky action bar — primary control always within thumb reach */}
      {resolved && !locked && (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t bg-background/80 backdrop-blur">
          <div className="mx-auto flex w-full max-w-xl flex-col gap-2 p-3 px-[max(0.75rem,env(safe-area-inset-left),env(safe-area-inset-right))] pb-[max(0.75rem,env(safe-area-inset-bottom))]">
            {searching && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Spinner />
                <span className="flex-1 truncate">{statusText}</span>
                {probing && state.discovery && (
                  <span className="tabular-nums">
                    {state.discovery.probed}/{state.discovery.total}
                  </span>
                )}
              </div>
            )}
            {probing && state.discovery && (
              <Progress
                className="h-1"
                value={
                  (state.discovery.probed /
                    Math.max(1, state.discovery.total)) *
                  100
                }
              />
            )}
            {searching ? (
              <Button
                variant="outline"
                className="h-11 w-full"
                onClick={cancel}
              >
                <HugeiconsIcon
                  icon={CancelCircleIcon}
                  data-icon="inline-start"
                />
                Cancel search
              </Button>
            ) : lastRunKey === null ? (
              <Button
                className="h-11 w-full"
                onClick={() => runSearch(false)}
                disabled={!searchKey}
              >
                <HugeiconsIcon icon={Search01Icon} data-icon="inline-start" />
                Check availability
              </Button>
            ) : paramsChanged ? (
              <Button className="h-11 w-full" onClick={() => runSearch(false)}>
                <HugeiconsIcon icon={Search01Icon} data-icon="inline-start" />
                Update results
              </Button>
            ) : (
              <Button
                variant="outline"
                className="h-11 w-full"
                onClick={() => runSearch(false)}
              >
                <HugeiconsIcon icon={Refresh01Icon} data-icon="inline-start" />
                Re-check stock
              </Button>
            )}
            {probing && (
              <p className="text-center text-xs text-muted-foreground">
                First search in a new area takes a while — it's instant once
                mapped.
              </p>
            )}
          </div>
        </div>
      )}
      {/* End sticky bottom bar */}

      <Toaster
        position="top-center"
        mobileOffset={{ top: "max(16px, env(safe-area-inset-top))" }}
      />
    </div>
  )
}

export default App
