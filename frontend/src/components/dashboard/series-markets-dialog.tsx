"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

import { MarketChartDialog } from "@/components/dashboard/market-chart-dialog";
import { getSeriesMarkets } from "@/lib/api";
import { formatCents, formatVolume } from "@/lib/format";
import type { MarketRow, RankedSeriesSummary } from "@/lib/types";

export function SeriesMarketsDialog({
  series,
  open,
  onOpenChange,
}: {
  series: RankedSeriesSummary | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [markets, setMarkets] = useState<MarketRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chartMarket, setChartMarket] = useState<MarketRow | null>(null);
  const [chartOpen, setChartOpen] = useState(false);

  useEffect(() => {
    if (!open || !series) return;
    let active = true;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await getSeriesMarkets(series!.ticker, 50);
        if (active) setMarkets(res.markets);
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (active) setLoading(false);
      }
    }

    load();
    return () => {
      active = false;
    };
  }, [open, series]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <DialogTitle className="text-h3">{series?.title}</DialogTitle>
            <Badge variant="secondary" className="metric-sm">
              {series?.ticker}
            </Badge>
          </div>
          <DialogDescription className="text-body">
            Top markets by 24h volume · score{" "}
            <span className="metric-sm">{series?.score.toFixed(2)}</span>
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[60vh] overflow-auto rounded-md border border-border/60">
          {loading ? (
            <div className="flex items-center justify-center gap-2 py-16 text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              <span className="text-small">Loading markets…</span>
            </div>
          ) : error ? (
            <div className="py-16 text-center text-small text-red-500">
              {error}
            </div>
          ) : (
            <Table>
              <TableHeader className="sticky top-0 bg-card">
                <TableRow>
                  <TableHead>Market</TableHead>
                  <TableHead className="text-right">Last</TableHead>
                  <TableHead className="text-right">Bid</TableHead>
                  <TableHead className="text-right">Ask</TableHead>
                  <TableHead className="text-right">24h Vol</TableHead>
                  <TableHead className="text-right">OI</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {markets.map((m) => (
                  <TableRow
                    key={m.ticker}
                    className="cursor-pointer transition-colors hover:bg-muted/40"
                    onClick={() => {
                      setChartMarket(m);
                      setChartOpen(true);
                    }}
                  >
                    <TableCell>
                      <div className="max-w-[260px] truncate text-body">
                        {m.title ?? m.ticker}
                      </div>
                      <div className="metric-sm text-muted-foreground">
                        {m.event_ticker ?? m.ticker}
                        {(m.outcome_count ?? 1) > 1 && (
                          <span className="ml-1.5 text-muted-foreground/60">
                            · {m.outcome_count} outcomes
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right metric">
                      {formatCents(m.last_price_dollars)}
                    </TableCell>
                    <TableCell className="text-right metric text-muted-foreground">
                      {formatCents(m.yes_bid_dollars)}
                    </TableCell>
                    <TableCell className="text-right metric text-muted-foreground">
                      {formatCents(m.yes_ask_dollars)}
                    </TableCell>
                    <TableCell className="text-right metric">
                      {formatVolume(m.volume_24h_fp)}
                    </TableCell>
                    <TableCell className="text-right metric">
                      {formatVolume(m.open_interest_fp)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </DialogContent>

      <MarketChartDialog
        ticker={chartMarket?.ticker ?? null}
        title={chartMarket?.title}
        seriesTicker={series?.ticker}
        open={chartOpen}
        onOpenChange={setChartOpen}
      />
    </Dialog>
  );
}
