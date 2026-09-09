import {
  Alert,
  AlertTitle,
  AlertDescription,
} from "@/components/ui/alert"
import { AlertTriangle, Box, MapPinOff } from "lucide-react"

export interface ZeptoResult {
  platform: string
  product: {
    id: string
    name: string
    image: string
    url: string
  }
  location: {
    lat: number
    lng: number
  }
  serviceability: {
    status: "SERVICEABLE" | "NOT_SERVICEABLE" | "UNKNOWN"
    reason?: string
  }
  availability: {
    status: "IN_STOCK" | "OUT_OF_STOCK" | "NOT_LISTED" | "UNKNOWN"
    verified: boolean
  }
}

export function ZeptoResultCard({ result }: { result: ZeptoResult }) {
  const sStatus = result.serviceability.status
  const aStatus = result.availability.status
  
  if (sStatus === "UNKNOWN" || aStatus === "UNKNOWN") {
    const isWaf = result.serviceability.reason === "ACCESS_BLOCKED_OR_CHALLENGED"
    return (
      <Alert variant="destructive" className="mb-6 bg-red-50/50 dark:bg-red-950/20 border-red-200 dark:border-red-900/50">
        <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
        <AlertTitle className="text-red-800 dark:text-red-300 font-semibold ml-2">
          {isWaf ? "Zepto verification unavailable" : "Unable to verify Zepto availability"}
        </AlertTitle>
        <AlertDescription className="text-red-700/80 dark:text-red-400/80 mt-2 ml-2 leading-relaxed">
          {isWaf 
            ? "Zepto could not be independently verified from this environment due to WAF restrictions." 
            : "Cart Radar encountered a network error while trying to query Zepto."}
          <br />
          <span className="font-medium">Note:</span> This does not mean the location is unserviceable.
        </AlertDescription>
      </Alert>
    )
  }

  if (sStatus === "NOT_SERVICEABLE") {
    return (
      <Alert className="mb-6 border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
        <MapPinOff className="h-5 w-5 text-slate-500" />
        <AlertTitle className="ml-2 font-medium text-slate-700 dark:text-slate-300">
          Zepto doesn't deliver to this location
        </AlertTitle>
        <AlertDescription className="ml-2 mt-1 text-slate-500 dark:text-slate-400">
          Zepto's systems confirmed this exact spot is outside their active delivery zones.
        </AlertDescription>
      </Alert>
    )
  }
  
  // Serviceable!
  const isStock = aStatus === "IN_STOCK"
  return (
    <Alert className={`mb-6 ${isStock ? "border-green-200 bg-green-50/50 dark:border-green-900/50 dark:bg-green-950/20" : "border-amber-200 bg-amber-50/50 dark:border-amber-900/50 dark:bg-amber-950/20"}`}>
      <Box className={`h-5 w-5 ${isStock ? "text-green-600 dark:text-green-400" : "text-amber-600 dark:text-amber-400"}`} />
      <AlertTitle className={`ml-2 font-semibold ${isStock ? "text-green-800 dark:text-green-300" : "text-amber-800 dark:text-amber-300"}`}>
        {isStock ? "✓ In stock at Zepto" : aStatus === "OUT_OF_STOCK" ? "Out of stock at Zepto" : "Not listed at Zepto"}
      </AlertTitle>
      <div className="flex items-center gap-4 mt-3 ml-2">
        {result.product.image && (
          <img src={result.product.image} className="w-12 h-12 rounded object-contain bg-white p-1 border shadow-sm" />
        )}
        <div className="flex flex-col gap-1">
          <span className="font-medium">{result.product.name}</span>
          <a href={result.product.url} target="_blank" rel="noreferrer" className="text-xs text-blue-600 hover:underline">
            View on Zepto ↗
          </a>
        </div>
      </div>
    </Alert>
  )
}
