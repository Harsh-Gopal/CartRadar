import { HugeiconsIcon } from "@hugeicons/react"
import {
  ComputerIcon,
  Moon02Icon,
  Sun01Icon,
} from "@hugeicons/core-free-icons"

import { Button } from "@/components/ui/button"
import { useTheme } from "@/components/theme-provider"

// system → light → dark → system. The button shows the current choice and its
// label says what a tap does next, so it's clear without a dropdown.
const ORDER = ["system", "light", "dark"] as const
const META = {
  system: { icon: ComputerIcon, label: "System theme" },
  light: { icon: Sun01Icon, label: "Light theme" },
  dark: { icon: Moon02Icon, label: "Dark theme" },
} as const

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const current = META[theme]
  const next = ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length]

  return (
    <Button
      variant="ghost"
      size="icon-sm"
      className="text-muted-foreground"
      aria-label={`${current.label} — switch to ${next}`}
      title={`${current.label} (press D to toggle)`}
      onClick={() => setTheme(next)}
    >
      <HugeiconsIcon icon={current.icon} />
    </Button>
  )
}
