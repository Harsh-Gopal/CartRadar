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
  error: "Check failed",
}

export const STATUS_VARIANT: Record<
  StoreResult["status"],
  "default" | "secondary" | "outline" | "destructive"
> = {
  in_stock: "default",
  out_of_stock: "secondary",
  not_carried: "outline",
  error: "destructive",
}

export function prettyStoreName(name: string | null): string {
  // Store names come prefixed with an internal city code, e.g. "BLR-HSR Layout New".
  return (name ?? "Zepto store").replace(/^[A-Z]{2,5}[- ]\s*/, "")
}

export function formatPrice(price: number): string {
  return price % 1 === 0 ? price.toFixed(0) : price.toFixed(2)
}

export function getPlatformFromId(id: string): string {
  if (id.startsWith("bb_") || id.startsWith("bb-")) return "bigbasket"
  if (id.startsWith("blinkit_")) return "blinkit"
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

function StoreListItem({ r, selectedId, cheapestId, searchPincode, onSelect }: { r: StoreResult; selectedId: string | null; cheapestId: string | null; searchPincode?: string | null; onSelect: (r: StoreResult) => void }) {
  const storePincode = usePincode(r.store.lat, r.store.lng, r.store.city)
  
  return (
    <Item asChild size="sm">
      <button
        type="button"
        id={`store-${r.store.id}`}
        onClick={() => onSelect(r)}
        title={r.store.city || undefined}
        className={cn(
          "w-full text-left transition-colors animate-in fade-in-0 slide-in-from-bottom-1 hover:bg-muted/50",
          r.store.id === selectedId && "bg-muted"
        )}
      >
        <ItemContent>
          <ItemTitle className="flex items-center gap-1.5">
            <PlatformBadge platform={getPlatformFromId(r.store.id)} size="sm" />
            <span>{prettyStoreName(r.store.name)}</span>
            {r.store.id === cheapestId && (
              <Badge variant="outline" className="ml-1 text-[10px] uppercase tracking-wider text-amber-600 border-amber-200 bg-amber-50">Cheapest</Badge>
            )}
          </ItemTitle>
          <ItemDescription>
            {r.store.city ? `${r.store.city} · ` : ""}
            {(storePincode || searchPincode) ? (
              <span className="text-primary/70 font-medium">
                {storePincode || searchPincode} ·{" "}
              </span>
            ) : ""}
            {r.distance_km} km away
          </ItemDescription>
        </ItemContent>
        <ItemActions className="flex-col items-end gap-1">
          {r.status === "in_stock" && r.price != null ? (
            <span className="text-sm font-semibold tabular-nums text-primary">
              ₹{formatPrice(r.price)}
            </span>
          ) : (
            <span className="text-sm font-medium opacity-0">₹0</span> // spacer
          )}
          {r.status === "in_stock" ? (
            <Badge variant="secondary" className="bg-green-100 text-green-700 hover:bg-green-100 border-none font-medium h-5">
              IN STOCK
            </Badge>
          ) : (
            <Badge variant={STATUS_VARIANT[r.status]} className="h-5">
              {STATUS_LABEL[r.status]}
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
