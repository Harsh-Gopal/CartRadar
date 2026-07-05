import { Zap } from "lucide-react";

const PLATFORMS = [
  { name: "Zepto", color: "#7C3AED" },
  { name: "Instamart", color: "#F97316" },
  { name: "BigBasket", color: "#65A30D" },
  { name: "Blinkit", color: "#EAB308" },
];

export function HeroSection() {
  return (
    <div className="flex flex-col items-center justify-center pt-16 pb-12 px-4 text-center">
      {/* Icon badge */}
      <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-border/60 bg-card px-4 py-2 text-sm text-muted-foreground shadow-sm">
        <Zap size={14} className="text-primary" />
        <span>Real-time stock across 4 platforms</span>
      </div>

      {/* Heading */}
      <h1 className="max-w-2xl text-[2.6rem] sm:text-5xl font-semibold tracking-tight text-foreground leading-[1.1]">
        Find it in stock,{" "}
        <span className="text-muted-foreground font-normal">wherever it is</span>
      </h1>

      {/* Subtitle */}
      <p className="mt-4 max-w-lg text-base text-muted-foreground leading-relaxed">
        Paste any product link and we'll sweep nearby stores on Zepto, Instamart,
        BigBasket, and Blinkit — showing you exactly where it's available.
      </p>

      {/* Platform pills */}
      <div className="mt-8 flex flex-wrap justify-center gap-2">
        {PLATFORMS.map((p) => (
          <span
            key={p.name}
            className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium border"
            style={{
              backgroundColor: `${p.color}14`,
              borderColor: `${p.color}30`,
              color: p.color,
            }}
          >
            <span
              className="size-1.5 rounded-full"
              style={{ backgroundColor: p.color }}
            />
            {p.name}
          </span>
        ))}
      </div>
    </div>
  );
}
