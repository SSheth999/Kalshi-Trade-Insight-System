"use client";

import { useState } from "react";
import { ArrowDown, ArrowUp, Minus, Activity } from "lucide-react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import { MarketChartDialog } from "@/components/dashboard/market-chart-dialog";
import { cn } from "@/lib/utils";
import { formatCents, formatVolume } from "@/lib/format";
import type { MarketTick } from "@/lib/types";

export function LiveTickerTable({ tickers }: { tickers: MarketTick[] }) {
  const [chartTicker, setChartTicker] = useState<MarketTick | null>(null);
  const [chartOpen, setChartOpen] = useState(false);

  return (
    <div className="rounded-xl border border-border/60 bg-card">
      <div className="flex items-center gap-2 border-b border-border/60 px-4 py-3">
        <Activity className="size-4 text-primary" />
        <span className="text-h3">Live Ticks</span>
        <span className="label-micro ml-auto text-muted-foreground/70">
          {tickers.length} markets
        </span>
      </div>

      {tickers.length === 0 ? (
        <p className="py-14 text-center text-small text-muted-foreground">
          No data yet — the watcher streams a snapshot on every poll.
        </p>
      ) : (
        <div className="max-h-[440px] overflow-auto">
          <Table>
            <TableHeader className="sticky top-0 z-10 bg-card">
              <TableRow>
                <TableHead>Market</TableHead>
                <TableHead className="text-right">Last</TableHead>
                <TableHead className="text-right">Δ</TableHead>
                <TableHead className="text-right">Bid</TableHead>
                <TableHead className="text-right">Ask</TableHead>
                <TableHead className="text-right">24h Vol</TableHead>
                <TableHead className="text-right">OI</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tickers.map((t) => (
                <TableRow
                  key={t.ticker}
                  className="cursor-pointer transition-colors hover:bg-muted/40"
                  onClick={() => {
                    setChartTicker(t);
                    setChartOpen(true);
                  }}
                >
                  <TableCell>
                    <div className="max-w-[220px] truncate text-body">{t.ticker}</div>
                    <div className="label-micro text-muted-foreground/70">
                      {t.series_ticker}
                    </div>
                  </TableCell>
                  <TableCell className="text-right metric">
                    {formatCents(t.last_price_dollars)}
                  </TableCell>
                  <TableCell className="text-right">
                    <DeltaBadge delta={t.price_delta} />
                  </TableCell>
                  <TableCell className="text-right metric text-muted-foreground">
                    {formatCents(t.yes_bid_dollars)}
                  </TableCell>
                  <TableCell className="text-right metric text-muted-foreground">
                    {formatCents(t.yes_ask_dollars)}
                  </TableCell>
                  <TableCell className="text-right metric">
                    {formatVolume(t.volume_24h_fp)}
                  </TableCell>
                  <TableCell className="text-right metric">
                    {formatVolume(t.open_interest_fp)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <MarketChartDialog
        ticker={chartTicker?.ticker ?? null}
        title={chartTicker?.ticker}
        seriesTicker={chartTicker?.series_ticker}
        open={chartOpen}
        onOpenChange={setChartOpen}
      />
    </div>
  );
}

function DeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null || delta === undefined) {
    return <Minus className="ml-auto size-3.5 text-muted-foreground" />;
  }
  const up = delta > 0;
  const flat = delta === 0;
  return (
    <span
      className={cn(
        "metric inline-flex items-center justify-end gap-0.5",
        flat && "text-muted-foreground",
        !flat && up && "text-positive",
        !flat && !up && "text-negative"
      )}
    >
      {!flat && (up ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />)}
      {formatCents(Math.abs(delta))}
    </span>
  );
}
