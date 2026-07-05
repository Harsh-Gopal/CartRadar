import { Moon, Sun } from "lucide-react";
import { useTheme } from "./theme-provider";

// Simple SVG logo mark
function LogoMark({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="12" cy="12" r="4" fill="currentColor" opacity="0.2" />
      <circle cx="12" cy="12" r="1.5" fill="currentColor" />
      <line x1="12" y1="2" x2="12" y2="7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="12" y1="17" x2="12" y2="22" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="2" y1="12" x2="7" y2="12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="17" y1="12" x2="22" y2="12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

const PLATFORM_DOTS = [
  { label: "Zepto", color: "#7C3AED" },
  { label: "Instamart", color: "#F97316" },
  { label: "BigBasket", color: "#65A30D" },
  { label: "Blinkit", color: "#EAB308" },
];

export function Navbar() {
  const { theme, setTheme } = useTheme();

  return (
    <nav className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/90 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-screen-xl items-center justify-between px-5">
        {/* Brand */}
        <div className="flex items-center gap-2.5">
          <div className="text-primary">
            <LogoMark size={22} />
          </div>
          <span className="font-semibold text-[15px] tracking-tight">
            Cart Radar
          </span>
        </div>

        {/* Center – platform dots (desktop) */}
        <div className="hidden md:flex items-center gap-3">
          {PLATFORM_DOTS.map((p) => (
            <span
              key={p.label}
              className="flex items-center gap-1.5 text-[13px] font-medium"
              style={{ color: p.color }}
            >
              <span
                className="size-1.5 rounded-full"
                style={{ backgroundColor: p.color }}
              />
              {p.label}
            </span>
          ))}
        </div>

        {/* Right */}
        <div className="flex items-center gap-3">
          <a
            href="https://github.com"
            className="hidden sm:inline-flex text-[13px] text-muted-foreground hover:text-foreground transition-colors"
          >
            How it works
          </a>
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-muted text-muted-foreground transition-colors"
            title="Toggle theme"
          >
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
      </div>
    </nav>
  );
}
