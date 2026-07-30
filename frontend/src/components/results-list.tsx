import { Fragment } from "react"

import { Badge } from "@/components/ui/badge"
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemSeparator,
  ItemTitle,
} from "@/components/ui/item"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import type { StoreResult } from "@/lib/api"
import { PlatformBadge } from "./platform-badge"
import { usePincode } from "@/lib/use-pincode"

export const STATUS_LABEL: Record<StoreResult["status"], string> = {
  in_stock: "In stock",
  out_of_stock: "Out of stock",
  not_carried: "Limited Distribution",
  error: "Unavailable",
}

export const STATUS_VARIANT: Record<
  StoreResult["status"],
  "default" | "secondary" | "outline" | "destructive"
> = {
  in_stock: "default",
  out_of_stock: "secondary",
  not_carried: "outline",
  error: "outline",  // Changed from destructive to outline (less alarming)
}

export function prettyStoreName(name: string | null): string {
  return (name ?? "Store").replace(/^[A-Z]{2,5}[- ]\s*/, "")
}

export function formatPrice(price: number): string {
  return price % 1 === 0 ? price.toFixed(0) : price.toFixed(2)
}

export function getPlatformFromId(id: string): string {
  if (id.startsWith("bb_") || id.startsWith("bb-")) return "bigbasket"
  if (id.startsWith("blinkit_")) return "blinkit"
  if (id.startsWith("swiggy_")) return "swiggy"
  if (/^\d+$/.test(id)) return "swiggy"
  return "zepto"
}

interface ResultsListProps {
  results: StoreResult[]
  selectedId: string | null
  cheapestId: string | null
  searchPincode?: string | null
  onSelect: (result: StoreResult) => void
}

function StoreListItem({
  r,
  selectedId,
  cheapestId,
  searchPincode,
  onSelect,
}: {
  r: StoreResult
  selectedId: string | null
  cheapestId: string | null
  searchPincode?: string | null
  onSelect: (r: StoreResult) => void
}) {
  const storePincode = usePincode(r.store.lat, r.store.lng, r.store.city)
  // Remove pincode already embedded in city string to avoid "City, 110092 · 110092" duplicates
  const cityDisplay = r.store.city
    ? r.store.city.replace(/[,\s]*(\d{6})[,\s]*/g, "").trim().replace(/[,·]+$/, "").trim()
    : null
  // Only show pincode badge if we actually have one
  const displayPincode = storePincode || searchPincode || null

  return (
    <Item asChild size="sm">
      <button
        type="button"
        id={`store-${r.store.id}`}
        onClick={() => onSelect(r)}
        title={r.store.city || undefined}
        className={cn(
          "w-full text-left transition-colors animate-in fade-in-0 slide-in-from-bottom-1 hover:bg-muted/50",
          r.store.id === selectedId && "bg-muted/70 ring-1 ring-primary/20"
        )}
      >
        <ItemContent>
          <ItemTitle className="flex items-center gap-1.5 flex-wrap">
            <PlatformBadge platform={getPlatformFromId(r.store.id)} size="sm" />
            <span>{prettyStoreName(r.store.name)}</span>
            {r.store.id === cheapestId && (
              <Badge
                variant="outline"
                className="ml-1 text-[10px] uppercase tracking-wider text-amber-600 border-amber-200 bg-amber-50 dark:bg-amber-950/30 dark:text-amber-400 dark:border-amber-800"
              >
                Cheapest
              </Badge>
            )}
          </ItemTitle>
          <ItemDescription>
            {cityDisplay ? `${cityDisplay} · ` : ""}
            {displayPincode ? (
              <span className="text-primary/70 font-medium">
                {displayPincode} ·{" "}
              </span>
            ) : (
              ""
            )}
            {r.distance_km === 0 ? "at your location" : `${r.distance_km} km away`}
          </ItemDescription>
        </ItemContent>
        <ItemActions className="flex-col items-end gap-1 shrink-0">
          {r.status === "in_stock" && r.price != null ? (
            <span className="text-sm font-semibold tabular-nums text-primary">
              ₹{formatPrice(r.price)}
            </span>
          ) : (
            <span className="text-sm font-medium opacity-0">₹0</span>
          )}
          {r.status === "in_stock" ? (
            <Badge className="badge-in-stock h-5 text-[10px] font-semibold">
              IN STOCK
            </Badge>
          ) : r.status === "out_of_stock" ? (
            <Badge variant="secondary" className="h-5 text-[10px]">
              Out of stock
            </Badge>
          ) : r.status === "not_carried" ? (
            <Badge variant="outline" className="h-5 text-[10px] text-muted-foreground">
              Limited
            </Badge>
          ) : (
            // error status — show as muted "Unavailable" not alarming red
            <Badge variant="outline" className="h-5 text-[10px] text-muted-foreground badge-unavailable">
              Unavailable
            </Badge>
          )}
        </ItemActions>
      </button>
    </Item>
  )
}

export function ResultsList({
  results,
  selectedId,
  cheapestId,
  searchPincode,
  onSelect,
}: ResultsListProps) {
  return (
    <ItemGroup>
      {results.map((r, i) => (
        <Fragment key={r.store.id}>
          {i > 0 && <ItemSeparator />}
          <StoreListItem
            r={r}
            selectedId={selectedId}
            cheapestId={cheapestId}
            searchPincode={searchPincode}
            onSelect={onSelect}
          />
        </Fragment>
      ))}
    </ItemGroup>
  )
}

export function ResultsSkeleton({ rows }: { rows: number }) {
  return (
    <ItemGroup>
      {Array.from({ length: rows }).map((_, i) => (
        <Fragment key={i}>
          {i > 0 && <ItemSeparator />}
          <Item size="sm">
            <ItemContent className="gap-1.5">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3 w-24" />
            </ItemContent>
            <ItemActions>
              <Skeleton className="h-5 w-20 rounded-full" />
            </ItemActions>
          </Item>
        </Fragment>
      ))}
    </ItemGroup>
  )
}
