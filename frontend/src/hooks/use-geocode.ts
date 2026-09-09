import { useState, useEffect } from "react"

export interface GeocodeResult {
  formatted_address: string
  short_address: string
  confidence: "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN"
  provider: string
}

export type GeocodeState = "IDLE" | "LOADING" | "SUCCESS" | "PARTIAL" | "FAILED" | "INVALID_COORDINATES"

export function useGeocode(lat: number | undefined, lng: number | undefined) {
  const [result, setResult] = useState<GeocodeResult | null>(null)
  const [state, setState] = useState<GeocodeState>("IDLE")

  useEffect(() => {
    if (lat === undefined || lng === undefined) {
      setState("IDLE")
      setResult(null)
      return
    }

    if (lat < -90 || lat > 90 || lng < -180 || lng > 180 || (lat === 0 && lng === 0)) {
      setState("INVALID_COORDINATES")
      setResult(null)
      return
    }

    let active = true
    setState("LOADING")

    async function fetchGeocode() {
      try {
        const token = localStorage.getItem("mf.token")
        const tokenStr = token ? `?token=${encodeURIComponent(token.replace(/"/g, ''))}` : ""
        const url = `/api/reverse_geocode${tokenStr}${tokenStr ? "&" : "?"}lat=${lat}&lng=${lng}`
        
        const res = await fetch(url)
        if (!active) return

        if (!res.ok) {
          setState("FAILED")
          setResult(null)
          return
        }

        const data: GeocodeResult = await res.json()
        if (!active) return

        setResult(data)
        if (data.confidence === "HIGH") {
          setState("SUCCESS")
        } else if (data.confidence === "MEDIUM" || data.confidence === "LOW") {
          setState("PARTIAL")
        } else {
          setState("FAILED")
        }
      } catch (err) {
        if (!active) return
        setState("FAILED")
        setResult(null)
      }
    }

    fetchGeocode()

    return () => {
      active = false
    }
  }, [lat, lng])

  return { result, state }
}
