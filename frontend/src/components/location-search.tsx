import { useEffect, useRef, useState } from "react"

import { HugeiconsIcon } from "@hugeicons/react"
import { Gps01Icon, MapPinIcon } from "@hugeicons/core-free-icons"

import { Field, FieldDescription, FieldLabel } from "@/components/ui/field"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group"
import { Spinner } from "@/components/ui/spinner"
import { cn } from "@/lib/utils"
import { placeDetails, suggestPlaces, type GeocodeResponse, type PlaceSuggestion } from "@/lib/api"

interface LocationSearchProps {
  coords: GeocodeResponse | null
  onCoords: (coords: GeocodeResponse | null) => void
}

export function LocationSearch({ coords, onCoords }: LocationSearchProps) {
  const [query, setQuery] = useState(coords?.label ?? "")
  const [suggestions, setSuggestions] = useState<PlaceSuggestion[]>([])
  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const skipNextFetch = useRef(false)

  useEffect(() => {
    if (skipNextFetch.current) {
      skipNextFetch.current = false
      return
    }
    const q = query.trim()
    if (q.length < 2) {
      setSuggestions([])
      setOpen(false)
      return
    }
    const timer = setTimeout(async () => {
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      try {
        const { suggestions } = await suggestPlaces(q, controller.signal)
        setSuggestions(suggestions)
        setHighlight(0)
        setOpen(suggestions.length > 0)
      } catch {
        // aborted or transient — keep whatever is shown
      }
    }, 250)
    return () => clearTimeout(timer)
  }, [query])

  async function select(s: PlaceSuggestion) {
    skipNextFetch.current = true
    setQuery(s.description)
    setOpen(false)
    setBusy(true)
    setError(null)
    try {
      onCoords(await placeDetails(s.place_id, s.description))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't locate that place.")
      onCoords(null)
    } finally {
      setBusy(false)
    }
  }

  function useGps() {
    if (!navigator.geolocation) {
      setError("Geolocation isn't supported here — search for your area instead.")
      return
    }
    setBusy(true)
    setError(null)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        skipNextFetch.current = true
        setQuery("Current location (GPS)")
        setOpen(false)
        onCoords({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          label: "Current location (GPS)",
        })
        setBusy(false)
      },
      () => {
        setError("Location access denied — search for your area instead.")
        setBusy(false)
      },
      { enableHighAccuracy: true, timeout: 10_000 }
    )
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open || suggestions.length === 0) return
    if (e.key === "ArrowDown") {
      e.preventDefault()
      setHighlight((h) => (h + 1) % suggestions.length)
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setHighlight((h) => (h - 1 + suggestions.length) % suggestions.length)
    } else if (e.key === "Enter") {
      e.preventDefault()
      select(suggestions[highlight])
    } else if (e.key === "Escape") {
      setOpen(false)
    }
  }

  return (
    <Field data-invalid={error ? true : undefined}>
      <FieldLabel htmlFor="loc">Your location</FieldLabel>
      <div className="relative">
        <InputGroup>
          <InputGroupAddon>
            <HugeiconsIcon icon={MapPinIcon} />
          </InputGroupAddon>
          <InputGroupInput
            id="loc"
            placeholder="Search area, locality or pincode…"
            value={query}
            aria-invalid={error ? true : undefined}
            autoComplete="off"
            onChange={(e) => {
              setQuery(e.target.value)
              onCoords(null)
              setError(null)
            }}
            onFocus={() => suggestions.length > 0 && setOpen(true)}
            onBlur={() => setOpen(false)}
            onKeyDown={onKeyDown}
          />
          <InputGroupAddon align="inline-end">
            {busy ? (
              <Spinner />
            ) : (
              <InputGroupButton
                aria-label="Use my current location"
                size="icon-sm"
                onClick={useGps}
              >
                <HugeiconsIcon icon={Gps01Icon} />
              </InputGroupButton>
            )}
          </InputGroupAddon>
        </InputGroup>
        {open && suggestions.length > 0 && (
          <div
            role="listbox"
            className="absolute inset-x-0 top-full z-20 mt-1 max-h-72 overflow-y-auto overscroll-contain rounded-md border bg-popover text-popover-foreground shadow-md animate-in fade-in-0 slide-in-from-top-1"
          >
            {suggestions.map((s, i) => (
              <button
                type="button"
                role="option"
                aria-selected={i === highlight}
                key={s.place_id}
                onMouseDown={(e) => {
                  e.preventDefault()
                  select(s)
                }}
                onMouseEnter={() => setHighlight(i)}
                className={cn(
                  "flex min-h-11 w-full flex-col items-start justify-center gap-0.5 px-3 py-2 text-left text-sm",
                  i === highlight && "bg-accent text-accent-foreground"
                )}
              >
                <span className="font-medium">{s.main_text}</span>
                {s.secondary_text && (
                  <span className="text-xs text-muted-foreground">{s.secondary_text}</span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>
      {error ? (
        <FieldDescription className="text-destructive">{error}</FieldDescription>
      ) : coords ? (
        <FieldDescription>Searching around: {coords.label}</FieldDescription>
      ) : (
        <FieldDescription>Pick a suggestion or tap the GPS button.</FieldDescription>
      )}
    </Field>
  )
}
