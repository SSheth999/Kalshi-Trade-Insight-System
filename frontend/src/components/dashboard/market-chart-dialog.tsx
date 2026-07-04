"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  createChart,
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { Loader2 } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { getMarketCandlesticks } from "@/lib/api";
import { formatCents } from "@/lib/format";
import { useMarketChartSocket } from "@/hooks/use-market-chart-socket";

const PERIOD_SECONDS = 60; // backbone is fetched at period_interval=1 (minute) candles

type Candle = {
  time: UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
};

export function MarketChartDialog({
  ticker,
  title,
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
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const lastCandleRef = useRef<Candle | null>(null);
  const prevPriceRef = useRef<number | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastPrice, setLastPrice] = useState<number | null>(null);
  const [priceUp, setPriceUp] = useState<boolean | null>(null);
  // State (not a plain ref) so the chart-creation effect reliably re-runs the
  // moment the Dialog's portal actually mounts this node — Base UI mounts the
  // Popup's children asynchronously relative to the `open` prop changing, so a
  // ref alone can still be null on the render where our effect first fires.
  const [containerEl, setContainerEl] = useState<HTMLDivElement | null>(null);
  const containerCallbackRef = useCallback((el: HTMLDivElement | null) => {
    setContainerEl(el);
  }, []);

  const { state: socketState, lastTick } = useMarketChartSocket(open ? ticker : null);

  // Create the chart instance once per dialog-open cycle.
  useEffect(() => {
    // #region agent log
    fetch('http://127.0.0.1:7841/ingest/feae3149-bbc6-44e6-8ff9-a6d0a8dcd600',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'67399a'},body:JSON.stringify({sessionId:'67399a',location:'market-chart-dialog.tsx:65-guard',message:'chart effect fired, checking guard',data:{open,hasContainerEl:!!containerEl},hypothesisId:'H6_ref_null_at_effect_time',runId:'post-fix',timestamp:Date.now()})}).catch(()=>{});
    // #endregion agent log
    if (!open || !containerEl) return;
    const container = containerEl;

    // #region agent log
    fetch('http://127.0.0.1:7841/ingest/feae3149-bbc6-44e6-8ff9-a6d0a8dcd600',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'67399a'},body:JSON.stringify({sessionId:'67399a',location:'market-chart-dialog.tsx:66',message:'chart effect start, container size',data:{clientWidth:container.clientWidth,clientHeight:container.clientHeight},hypothesisId:'H2_container_size',runId:'post-fix',timestamp:Date.now()})}).catch(()=>{});
    // #endregion agent log

    try {
      const chart = createChart(container, {
        layout: {
          background: { type: ColorType.Solid, color: "transparent" },
          textColor: "rgba(230, 230, 230, 0.75)",
          fontFamily: "'JetBrains Mono', ui-monospace, monospace",
          fontSize: 11,
          panes: { separatorColor: "rgba(255,255,255,0.08)" },
        },
        grid: {
          vertLines: { color: "rgba(255,255,255,0.055)" },
          horzLines: { color: "rgba(255,255,255,0.055)" },
        },
        crosshair: {
          mode: CrosshairMode.Normal,
          vertLine: { color: "rgba(255,255,255,0.25)", labelBackgroundColor: "#27272a" },
          horzLine: { color: "rgba(255,255,255,0.25)", labelBackgroundColor: "#27272a" },
        },
        rightPriceScale: {
          borderColor: "rgba(255,255,255,0.1)",
          scaleMargins: { top: 0.12, bottom: 0.12 },
        },
        timeScale: {
          borderColor: "rgba(255,255,255,0.1)",
          timeVisible: true,
          secondsVisible: false,
        },
        autoSize: true,
      });

      const series = chart.addSeries(CandlestickSeries, {
        upColor: "#4ade80",
        downColor: "#f87171",
        borderUpColor: "#4ade80",
        borderDownColor: "#f87171",
        wickUpColor: "#4ade80",
        wickDownColor: "#f87171",
        priceFormat: {
          type: "custom",
          formatter: (p: number) => `${Math.round(p * 100)}¢`,
          minMove: 0.01,
        },
      });

      chartRef.current = chart;
      seriesRef.current = series;

      // #region agent log
      fetch('http://127.0.0.1:7841/ingest/feae3149-bbc6-44e6-8ff9-a6d0a8dcd600',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'67399a'},body:JSON.stringify({sessionId:'67399a',location:'market-chart-dialog.tsx:117',message:'chart+series created OK',data:{hasChart:!!chartRef.current,hasSeries:!!seriesRef.current},hypothesisId:'H1_exception',runId:'post-fix',timestamp:Date.now()})}).catch(()=>{});
      // #endregion agent log
    } catch (err) {
      // #region agent log
      fetch('http://127.0.0.1:7841/ingest/feae3149-bbc6-44e6-8ff9-a6d0a8dcd600',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'67399a'},body:JSON.stringify({sessionId:'67399a',location:'market-chart-dialog.tsx:catch',message:'chart creation THREW',data:{errMessage:err instanceof Error?err.message:String(err),errStack:err instanceof Error?err.stack:undefined},hypothesisId:'H1_exception',runId:'post-fix',timestamp:Date.now()})}).catch(()=>{});
      // #endregion agent log
    }

    return () => {
      chartRef.current?.remove();
      chartRef.current = null;
      seriesRef.current = null;
      lastCandleRef.current = null;
      prevPriceRef.current = null;
    };
  }, [open, containerEl]);

  // Seed with historical candles whenever a new market is opened.
  useEffect(() => {
    if (!open || !ticker) return;
    let active = true;

    async function load() {
      setLoading(true);
      setError(null);
      setLastPrice(null);
      setPriceUp(null);

      try {
        const res = await getMarketCandlesticks(ticker!, {
          periodInterval: 1,
          lookbackMinutes: 240,
        });
        if (!active) return;
        const candles: Candle[] = res.candles
          .filter(
            (c) => c.open !== null && c.high !== null && c.low !== null && c.close !== null
          )
          .map((c) => ({
            time: c.time as UTCTimestamp,
            open: c.open as number,
            high: c.high as number,
            low: c.low as number,
            close: c.close as number,
          }));

        // #region agent log
        fetch('http://127.0.0.1:7841/ingest/feae3149-bbc6-44e6-8ff9-a6d0a8dcd600',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'67399a'},body:JSON.stringify({sessionId:'67399a',location:'market-chart-dialog.tsx:load',message:'candles fetched+filtered',data:{rawCount:res.candles.length,filteredCount:candles.length,hasSeriesRef:!!seriesRef.current,firstTime:candles[0]?.time,lastTime:candles[candles.length-1]?.time},hypothesisId:'H4_data,H3_series_null',runId:'post-fix',timestamp:Date.now()})}).catch(()=>{});
        // #endregion agent log

        try {
          seriesRef.current?.setData(candles);
          chartRef.current?.timeScale().fitContent();
          // #region agent log
          fetch('http://127.0.0.1:7841/ingest/feae3149-bbc6-44e6-8ff9-a6d0a8dcd600',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'67399a'},body:JSON.stringify({sessionId:'67399a',location:'market-chart-dialog.tsx:setData',message:'setData call completed without throwing',data:{},hypothesisId:'H5_setdata_throw',runId:'post-fix',timestamp:Date.now()})}).catch(()=>{});
          // #endregion agent log
        } catch (setDataErr) {
          // #region agent log
          fetch('http://127.0.0.1:7841/ingest/feae3149-bbc6-44e6-8ff9-a6d0a8dcd600',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'67399a'},body:JSON.stringify({sessionId:'67399a',location:'market-chart-dialog.tsx:setData-catch',message:'setData THREW',data:{errMessage:setDataErr instanceof Error?setDataErr.message:String(setDataErr)},hypothesisId:'H5_setdata_throw',runId:'post-fix',timestamp:Date.now()})}).catch(()=>{});
          // #endregion agent log
        }

        const last = candles[candles.length - 1] ?? null;
        lastCandleRef.current = last;
        if (last) {
          prevPriceRef.current = last.close;
          setLastPrice(last.close);
        }
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

  // Append/merge each live tick into the in-progress candle.
  useEffect(() => {
    if (!lastTick || lastTick.price === null || !seriesRef.current) return;
    const price = lastTick.price;
    const prev = prevPriceRef.current;

    setPriceUp(prev === null ? null : price > prev ? true : price < prev ? false : null);
    setLastPrice(price);
    prevPriceRef.current = price;

    const bucket = (Math.floor(lastTick.time / PERIOD_SECONDS) * PERIOD_SECONDS) as UTCTimestamp;
    const prevCandle = lastCandleRef.current;

    const next: Candle =
      prevCandle && prevCandle.time === bucket
        ? {
            time: bucket,
            open: prevCandle.open,
            high: Math.max(prevCandle.high, price),
            low: Math.min(prevCandle.low, price),
            close: price,
          }
        : { time: bucket, open: price, high: price, low: price, close: price };

    lastCandleRef.current = next;
    seriesRef.current.update(next);
  }, [lastTick]);

  const isLive = socketState === "open";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <div className="flex flex-wrap items-center gap-2">
            <DialogTitle className="text-h3">{title ?? ticker}</DialogTitle>
            {seriesTicker && (
              <Badge variant="secondary" className="metric-sm">
                {seriesTicker}
              </Badge>
            )}
            <span
              className={cn(
                "label-micro ml-auto flex items-center gap-1.5",
                isLive ? "text-positive" : "text-muted-foreground/60"
              )}
            >
              <span className="relative flex size-1.5">
                <span
                  className={cn(
                    "absolute inline-flex size-full rounded-full",
                    isLive && "animate-ping bg-positive/60"
                  )}
                />
                <span
                  className={cn(
                    "relative inline-flex size-1.5 rounded-full",
                    isLive ? "bg-positive" : "bg-muted-foreground/50"
                  )}
                />
              </span>
              {isLive ? "Live" : socketState === "connecting" ? "Connecting…" : "Offline"}
            </span>
          </div>
          <DialogDescription className="metric-sm text-muted-foreground">
            {ticker}
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-baseline gap-3">
          <span
            className={cn(
              "metric-xl",
              priceUp === true && "text-positive",
              priceUp === false && "text-negative"
            )}
          >
            {formatCents(lastPrice)}
          </span>
          <span className="label-micro text-muted-foreground/70">last</span>
          {lastTick && (
            <>
              <span className="metric text-muted-foreground ml-4">
                {formatCents(lastTick.yes_bid)}
              </span>
              <span className="label-micro text-muted-foreground/70">bid</span>
              <span className="metric text-muted-foreground ml-2">
                {formatCents(lastTick.yes_ask)}
              </span>
              <span className="label-micro text-muted-foreground/70">ask</span>
            </>
          )}
        </div>

        <div className="relative h-[380px] w-full overflow-hidden rounded-md border border-border/60 bg-black/10">
          {loading && (
            <div className="absolute inset-0 z-10 flex items-center justify-center gap-2 bg-card/60 text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              <span className="text-small">Loading history…</span>
            </div>
          )}
          {error && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-card/80 text-small text-red-400">
              {error}
            </div>
          )}
          <div ref={containerCallbackRef} className="h-full w-full" />
        </div>

        <p className="label-micro text-muted-foreground/50">
          1-min candles · last 4h history · live tail polled ~2s
        </p>
      </DialogContent>
    </Dialog>
  );
}
