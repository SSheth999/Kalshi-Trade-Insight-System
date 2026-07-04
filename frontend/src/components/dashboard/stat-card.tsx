"use client";

import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  suffix,
  description,
  icon,
  accent = "neutral",
  onClick,
  loading = false,
}: {
  label: string;
  value: ReactNode;
  suffix?: string;
  description?: ReactNode;
  icon?: ReactNode;
  accent?: "neutral" | "primary" | "positive" | "negative";
  onClick?: () => void;
  loading?: boolean;
}) {
  const clickable = Boolean(onClick);
  const Comp = clickable ? "button" : "div";

  return (
    <Comp
      onClick={onClick}
      className={cn(
        "group relative flex flex-col gap-3 overflow-hidden rounded-xl border border-border/60 bg-card px-4 py-3.5 text-left transition-all",
        clickable &&
          "cursor-pointer hover:border-border hover:bg-accent/40 active:scale-[0.99]"
      )}
    >
      <div
        className={cn(
          "pointer-events-none absolute -right-6 -top-6 size-24 rounded-full opacity-0 blur-2xl transition-opacity duration-300 group-hover:opacity-100",
          accent === "primary" && "bg-primary/25",
          accent === "positive" && "bg-emerald-500/25",
          accent === "negative" && "bg-red-500/25",
          accent === "neutral" && "bg-foreground/10"
        )}
      />

      <div className="flex items-center justify-between">
        <span className="label-micro">{label}</span>
        <div className="flex items-center gap-1 text-muted-foreground">
          {icon}
          {clickable && (
            <ChevronRight className="size-3.5 -mr-1 opacity-0 transition-opacity group-hover:opacity-100" />
          )}
        </div>
      </div>

      <div className="flex items-baseline gap-1.5">
        {loading ? (
          <span className="metric-xl text-muted-foreground/40">···</span>
        ) : (
          <span className="metric-xl">{value}</span>
        )}
        {suffix && !loading && (
          <span className="metric text-muted-foreground">{suffix}</span>
        )}
      </div>

      {description && (
        <div className="text-small text-muted-foreground">{description}</div>
      )}
    </Comp>
  );
}
