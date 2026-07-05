import { cn } from "@/lib/utils"
import { PLATFORM_COLORS, PLATFORM_LABELS } from "@/lib/api"

interface PlatformBadgeProps {
  platform: string
  size?: "sm" | "md" | "lg"
  className?: string
}

export function PlatformBadge({
  platform,
  size = "sm",
  className,
}: PlatformBadgeProps) {
  const color = PLATFORM_COLORS[platform] ?? "#888"
  const label = PLATFORM_LABELS[platform] ?? platform

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full font-medium",
        size === "sm" && "px-2 py-0.5 text-[10px]",
        size === "md" && "px-2.5 py-0.5 text-xs",
        size === "lg" && "px-3 py-1 text-sm",
        className
      )}
      style={{
        backgroundColor: `${color}18`,
        color,
        border: `1px solid ${color}30`,
      }}
    >
      <span
        className="size-2 rounded-full"
        style={{ backgroundColor: color }}
      />
      {label}
    </span>
  )
}

export function PlatformDot({
  platform,
  className,
}: {
  platform: string
  className?: string
}) {
  const color = PLATFORM_COLORS[platform] ?? "#888"
  return (
    <span
      className={cn("inline-block size-2.5 rounded-full", className)}
      style={{ backgroundColor: color }}
      title={PLATFORM_LABELS[platform] ?? platform}
    />
  )
}
