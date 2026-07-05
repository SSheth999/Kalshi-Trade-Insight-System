"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { OutcomeChartPane } from "@/components/dashboard/outcome-chart-pane";
import { cn } from "@/lib/utils";
import { getMarketEvent } from "@/lib/api";
import {
  chartPaneHeight,
  formatOutcomeLabel,
  liveChartTickers,
  LIVE_CHART_MAX,
} from "@/lib/market-labels";
import type { EventMarketsResponse } from "@/lib/types";

export function MarketChartDialog({
  ticker,
  seriesTicker,
  open,
  onOpenChange,
}: {
  ticker: string | null;
  title?: string | null;
  seriesTicker?: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [event, setEvent] = useState<EventMarketsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !ticker) return;
    let active = true;

    async function load() {
      setLoading(true);
      setError(null);
      setEvent(null);
      try {
        const res = await getMarketEvent(ticker!);
        if (active) setEvent(res);
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
  }, [open, ticker]);

  const orderedOutcomes = useMemo(() => {
    if (!event || !ticker) return [];
    const clicked = event.outcomes.filter((o) => o.ticker === ticker);
    const rest = event.outcomes.filter((o) => o.ticker !== ticker);
    return [...clicked, ...rest];
  }, [event, ticker]);
  const liveSet = useMemo(
    () => liveChartTickers(orderedOutcomes, ticker),
    [orderedOutcomes, ticker]
  );

  const paneHeight = chartPaneHeight(event?.outcome_count ?? 1);
  const isWide = (event?.outcome_count ?? 1) > 2;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={cn(isWide ? "max-w-6xl" : "max-w-4xl")}>
        <DialogHeader>
          <div className="flex flex-wrap items-center gap-2">
            <DialogTitle className="text-h3">
              {event?.title ?? ticker}
            </DialogTitle>
            {(event?.series_ticker ?? seriesTicker) && (
              <Badge variant="secondary" className="metric-sm">
                {event?.series_ticker ?? seriesTicker}
              </Badge>
            )}
            {event && event.outcome_count > 1 && (
              <Badge variant="outline" className="metric-sm">
                {event.outcome_count} outcomes
              </Badge>
            )}
          </div>
          <DialogDescription className="metric-sm text-muted-foreground">
            {event?.event_ticker ?? ticker}
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center gap-2 py-24 text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            <span className="text-small">Loading event markets…</span>
          </div>
        ) : error ? (
          <div className="py-16 text-center text-small text-red-400">{error}</div>
        ) : event ? (
          <>
            <div
              className={cn(
                "grid gap-3",
                event.outcome_count === 1 ? "grid-cols-1" : "grid-cols-1 sm:grid-cols-2",
                event.outcome_count > 4 && "max-h-[65vh] overflow-y-auto pr-1"
              )}
            >
              {orderedOutcomes.map((outcome) => (
                <OutcomeChartPane
                  key={outcome.ticker}
                  ticker={outcome.ticker}
                  outcomeLabel={outcome.outcome_label}
                  displayLabel={formatOutcomeLabel(outcome.outcome_label)}
                  active={outcome.ticker === ticker}
                  enableLive={liveSet.has(outcome.ticker)}
                  height={paneHeight}
                  snapshotPrice={outcome.last_price_dollars}
                />
              ))}
            </div>

            <p className="label-micro text-muted-foreground/50">
              1-min candles · last 4h history
              {event.outcome_count > LIVE_CHART_MAX
                ? ` · live on top ${LIVE_CHART_MAX} outcomes (incl. selected)`
                : " · live tail polled ~2s"}
            </p>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
