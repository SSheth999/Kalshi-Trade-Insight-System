"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { WS_URL } from "@/lib/api";
import type { MarketChartTick } from "@/lib/types";

export type SocketState = "connecting" | "open" | "closed";

/**
 * Subscribes to the dedicated per-market live feed (/markets/{ticker}/ws),
 * which polls Kalshi independently of the top-K watcher basket at a fast
 * (~2s) interval for as long as this hook is mounted.
 */
export function useMarketChartSocket(ticker: string | null) {
  const [state, setState] = useState<SocketState>("closed");
  const [lastTick, setLastTick] = useState<MarketChartTick | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldRunRef = useRef(false);
  const connectRef = useRef<() => void>(() => {});

  const connect = useCallback(() => {
    if (!ticker || socketRef.current) return;
    setState("connecting");
    const ws = new WebSocket(`${WS_URL}/api/v1/markets/${encodeURIComponent(ticker)}/ws`);
    socketRef.current = ws;

    ws.onopen = () => setState("open");

    ws.onmessage = (event) => {
      try {
        const data: MarketChartTick = JSON.parse(event.data);
        if (data.event === "tick") setLastTick(data);
      } catch {
        // ignore malformed frames (e.g. pong)
      }
    };

    ws.onclose = () => {
      setState("closed");
      socketRef.current = null;
      if (shouldRunRef.current) {
        reconnectTimer.current = setTimeout(() => connectRef.current(), 2000);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [ticker]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    if (!ticker) return;

    function start() {
      shouldRunRef.current = true;
      setLastTick(null);
      connect();
    }
    start();

    return () => {
      shouldRunRef.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      socketRef.current?.close();
      socketRef.current = null;
      setState("closed");
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker]);

  return { state, lastTick };
}
