import { Moon, Sun } from "lucide-react";
import { useTheme } from "./theme-provider";

// Animated radar logo mark
function RadarLogo({ size = 22 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      className="text-primary"
    >
      {/* Outer ring */}
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.4" opacity="0.4" />
      {/* Middle ring */}
      <circle cx="12" cy="12" r="6" stroke="currentColor" strokeWidth="1.2" opacity="0.6" />
      {/* Inner ring */}
      <circle cx="12" cy="12" r="2.5" stroke="currentColor" strokeWidth="1.2" />
      {/* Center dot */}
      <circle cx="12" cy="12" r="1" fill="currentColor" />
      {/* Rotating sweep line */}
      <line
        x1="12"
        y1="12"
        x2="12"
        y2="2.5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        opacity="0.9"
        className="radar-sweep"
      />
      {/* Sweep fill (faded arc effect) */}
      <line
        x1="12"
        y1="12"
        x2="19"
        y2="5"
        stroke="currentColor"
        strokeWidth="1"
        strokeLinecap="round"
        opacity="0.3"
        className="radar-sweep"
        style={{ animationDelay: "-0.3s" }}
      />
    </svg>
  );
}

const PLATFORM_DOTS = [
  { label: "Zepto", color: "#7B2FF7" },
  { label: "Instamart", color: "#F97316" },
  { label: "BigBasket", color: "#65A30D" },
  { label: "Blinkit", color: "#E8B007" },
];

interface NavbarProps {
  /** Called when the user clicks the Cart Radar brand — typically resets the app to home state. */
  onLogoClick?: () => void;
}

export function Navbar({ onLogoClick }: NavbarProps) {
  const { theme, setTheme } = useTheme();

  return (
    <nav className="sticky top-0 z-50 w-full border-b border-border/50 bg-background/85 backdrop-blur-xl">
      <div className="mx-auto flex h-14 max-w-screen-xl items-center justify-between px-5">
        {/* Brand — clicking resets to home */}
        <button
          type="button"
          onClick={onLogoClick}
          className="flex items-center gap-2.5 rounded-md px-1 py-1 hover:opacity-80 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring cursor-pointer"
          aria-label="Cart Radar — go to home"
        >
          <RadarLogo size={24} />
          <div className="flex flex-col leading-none text-left">
            <span className="font-bold text-[15px] tracking-tight text-foreground">
              Cart Radar
            </span>
            <span className="hidden sm:block text-[10px] text-muted-foreground tracking-wide uppercase">
              Find it near you
            </span>
          </div>
        </button>

        {/* Center – platform dots (desktop) */}
        <div className="hidden md:flex items-center gap-4">
          {PLATFORM_DOTS.map((p) => (
            <span
              key={p.label}
              className="flex items-center gap-1.5 text-[12px] font-medium"
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
        <div className="flex items-center gap-2">
          <a
            href="https://github.com/Harsh-Gopal/CartRadar#-how-to-use"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:inline-flex items-center gap-1 text-[12px] text-muted-foreground hover:text-foreground transition-colors px-3 py-1.5 rounded-md hover:bg-muted"
          >
            How it works
          </a>
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-muted text-muted-foreground hover:text-foreground transition-all"
            title="Toggle theme"
          >
            {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
          </button>
        </div>
      </div>
    </nav>
  );
}
