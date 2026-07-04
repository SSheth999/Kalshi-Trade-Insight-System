"use client";

import { useState } from "react";
import { Flame, TrendingUp, Layers } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { SeriesMarketsDialog } from "@/components/dashboard/series-markets-dialog";
import { cn } from "@/lib/utils";
import { formatPercent, formatVolume } from "@/lib/format";
import type { RankedSeriesSummary } from "@/lib/types";

export function SeriesGrid({ series }: { series: RankedSeriesSummary[] }) {
  const [selected, setSelected] = useState<RankedSeriesSummary | null>(null);

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-h3 flex items-center gap-2">
            <Flame className="size-4 text-orange-500" />
            Top Volatile Series
          </h2>
          <p className="text-small text-muted-foreground">
            Ranked by composite score — click a card to inspect its markets
          </p>
        </div>
      </div>

      {series.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border/60 py-14 text-center text-small text-muted-foreground">
          Waiting on the pipeline to score series…
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {series.map((s, i) => (
            <SeriesCard
              key={s.ticker}
              rank={i + 1}
              series={s}
              onClick={() => setSelected(s)}
            />
          ))}
        </div>
      )}

      <SeriesMarketsDialog
        series={selected}
        open={selected !== null}
        onOpenChange={(open) => !open && setSelected(null)}
      />
    </section>
  );
}

function SeriesCard({
  rank,
  series,
  onClick,
}: {
  rank: number;
  series: RankedSeriesSummary;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "group relative flex flex-col gap-3 overflow-hidden rounded-xl border border-border/60 bg-card p-4 text-left transition-all",
        "hover:border-border hover:bg-accent/40 active:scale-[0.99]"
      )}
    >
      <div className="pointer-events-none absolute -right-8 -top-8 size-28 rounded-full bg-orange-500/0 opacity-0 blur-2xl transition-opacity duration-300 group-hover:bg-orange-500/15 group-hover:opacity-100" />

      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="label-micro text-muted-foreground/70">#{rank}</span>
          <span className="metric-sm text-muted-foreground">{series.ticker}</span>
        </div>
        <Badge variant="secondary" className="metric-sm gap-1">
          <TrendingUp className="size-3" />
          {series.score.toFixed(2)}
        </Badge>
      </div>

      <h3 className="text-h3 leading-tight line-clamp-2">{series.title}</h3>

      <div className="mt-1 grid grid-cols-3 gap-2 border-t border-border/60 pt-3">
        <Stat label="Markets" value={series.open_market_count.toLocaleString()} icon={<Layers className="size-3" />} />
        <Stat label="Max 1d" value={formatPercent(series.max_1d_move)} />
        <Stat label="24h Vol" value={formatVolume(series.total_vol24)} />
      </div>
    </button>
  );
}

function Stat({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="label-micro flex items-center gap-1 text-muted-foreground/70">
        {icon}
        {label}
      </span>
      <span className="metric-sm">{value}</span>
    </div>
  );
}
