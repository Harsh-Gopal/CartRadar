import { formatPrice, getPlatformFromId } from "./results-list"
import { type StoreResult } from "@/lib/api"
import { PlatformBadge } from "./platform-badge"

interface PriceSummaryProps {
  results: StoreResult[]
}

export function PriceSummary({ results }: PriceSummaryProps) {
  const inStock = results.filter((r) => r.status === "in_stock" && r.price != null)
  
  if (inStock.length === 0) return null

  const prices = inStock.map((r) => r.price!)
  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const avg = prices.reduce((a, b) => a + b, 0) / prices.length
  
  const bestPlatforms = Array.from(new Set(inStock.filter(r => r.price === min).map(r => getPlatformFromId(r.store.id))))

  return (
    <div className="flex items-center justify-between gap-4 rounded-xl bg-gradient-to-br from-card to-muted/20 border border-black/5 dark:border-white/5 px-4 py-3 shadow-sm mb-4 animate-in fade-in slide-in-from-bottom-2">
      <div className="flex flex-col gap-0.5">
        <span className="text-sm font-medium">Price Summary</span>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>Lowest <strong className="text-foreground">₹{formatPrice(min)}</strong></span>
          <span>·</span>
          <span>Highest ₹{formatPrice(max)}</span>
          <span>·</span>
          <span>Avg ₹{formatPrice(avg)}</span>
        </div>
      </div>
      
      {bestPlatforms.length > 0 && (
        <div className="flex flex-col items-end gap-1">
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Best on</span>
          <div className="flex gap-1">
            {bestPlatforms.map((p) => (
              <PlatformBadge key={p} platform={p} size="sm" />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
