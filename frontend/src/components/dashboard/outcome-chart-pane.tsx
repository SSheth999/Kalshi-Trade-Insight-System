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

import { cn } from "@/lib/utils";
import { getMarketCandlesticks } from "@/lib/api";
import { formatCents } from "@/lib/format";
import { useMarketChartSocket } from "@/hooks/use-market-chart-socket";

const PERIOD_SECONDS = 60;

type Candle = {
  time: UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
};

export function OutcomeChartPane({
  ticker,
  outcomeLabel,
  displayLabel,
  active,
  enableLive,
  height,
  snapshotPrice,
}: {
  ticker: string;
  outcomeLabel: string;
  displayLabel: string;
  active?: boolean;
  enableLive: boolean;
  height: number;
  snapshotPrice?: number | null;
}) {
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const lastCandleRef = useRef<Candle | null>(null);
  const prevPriceRef = useRef<number | null>(null);

  const [containerEl, setContainerEl] = useState<HTMLDivElement | null>(null);
  const containerCallbackRef = useCallback((el: HTMLDivElement | null) => {
    setContainerEl(el);
  }, []);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastPrice, setLastPrice] = useState<number | null>(snapshotPrice ?? null);
  const [priceUp, setPriceUp] = useState<boolean | null>(null);

  const { state: socketState, lastTick } = useMarketChartSocket(enableLive ? ticker : null);

  useEffect(() => {
    if (!containerEl) return;

    const chart = createChart(containerEl, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "rgba(230, 230, 230, 0.75)",
        fontFamily: "'JetBrains Mono', ui-monospace, monospace",
        fontSize: 10,
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

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      lastCandleRef.current = null;
      prevPriceRef.current = null;
    };
  }, [containerEl]);

  useEffect(() => {
    let activeRequest = true;

    async function load() {
      setLoading(true);
      setError(null);
      lastCandleRef.current = null;
      prevPriceRef.current = snapshotPrice ?? null;
      setLastPrice(snapshotPrice ?? null);
      setPriceUp(null);

      try {
        const res = await getMarketCandlesticks(ticker, {
          periodInterval: 1,
          lookbackMinutes: 240,
        });
        if (!activeRequest) return;

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

        seriesRef.current?.setData(candles);
        chartRef.current?.timeScale().fitContent();

        const last = candles[candles.length - 1] ?? null;
        lastCandleRef.current = last;
        if (last) {
          prevPriceRef.current = last.close;
          setLastPrice(last.close);
        }
      } catch (err) {
        if (activeRequest) setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (activeRequest) setLoading(false);
      }
    }

    load();
    return () => {
      activeRequest = false;
    };
  }, [ticker, snapshotPrice]);

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

  const isLive = enableLive && socketState === "open";

  return (
    <div
      className={cn(
        "flex flex-col rounded-md border border-border/60 bg-black/10",
        active && "ring-1 ring-primary/50"
      )}
    >
      <div className="flex items-center justify-between gap-2 border-b border-border/40 px-3 py-2">
        <div className="min-w-0">
          <p className="text-body truncate font-medium">{displayLabel}</p>
          <p className="metric-sm text-muted-foreground truncate">{outcomeLabel}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span
            className={cn(
              "metric",
              priceUp === true && "text-positive",
              priceUp === false && "text-negative"
            )}
          >
            {formatCents(lastPrice)}
          </span>
          {enableLive && (
            <span
              className={cn(
                "label-micro flex items-center gap-1",
                isLive ? "text-positive" : "text-muted-foreground/50"
              )}
            >
              <span
                className={cn(
                  "size-1.5 rounded-full",
                  isLive ? "bg-positive" : "bg-muted-foreground/40"
                )}
              />
              {isLive ? "Live" : "Hist"}
            </span>
          )}
        </div>
      </div>

      <div className="relative w-full" style={{ height }}>
        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center gap-2 bg-card/60 text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" />
          </div>
        )}
        {error && (
          <div className="absolute inset-0 z-10 flex items-center justify-center px-2 text-center text-small text-red-400">
            {error}
          </div>
        )}
        <div ref={containerCallbackRef} className="h-full w-full" />
      </div>
    </div>
  );
}
