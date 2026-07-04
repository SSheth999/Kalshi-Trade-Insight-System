"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { WS_URL } from "@/lib/api";
import type { MarketTick, WatcherSnapshot } from "@/lib/types";

export type SocketState = "connecting" | "open" | "closed";

export function useWatcherSocket() {
  const [state, setState] = useState<SocketState>("closed");
  const [pollCount, setPollCount] = useState(0);
  const [tickers, setTickers] = useState<MarketTick[]>([]);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldRunRef = useRef(false);
  const connectRef = useRef<() => void>(() => {});


  const connect = useCallback(() => {
    if (socketRef.current) return;
    setState("connecting");
    const ws = new WebSocket(`${WS_URL}/api/v1/watcher/ws`);
    socketRef.current = ws;

    ws.onopen = () => setState("open");

    ws.onmessage = (event) => {
      try {
        const data: WatcherSnapshot = JSON.parse(event.data);
        if (data.event === "snapshot") {
          setPollCount(data.poll_count);
          setTickers(data.tickers);
        }
      } catch {
        // ignore malformed frames (e.g. pong)
      }
    };

    ws.onclose = () => {
      setState("closed");
      socketRef.current = null;
      if (shouldRunRef.current) {
        reconnectTimer.current = setTimeout(() => connectRef.current(), 3000);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  // Keep a stable ref to the latest `connect` so the reconnect timer
  // (scheduled from inside a socket callback) never closes over a stale value.
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const disconnect = useCallback(() => {
    shouldRunRef.current = false;
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    socketRef.current?.close();
    socketRef.current = null;
    setState("closed");
  }, []);

  useEffect(() => {
    shouldRunRef.current = true;
    connect();
    return () => {
      shouldRunRef.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      socketRef.current?.close();
    };
  }, [connect]);

  return { state, pollCount, tickers, disconnect, reconnect: connect };
}
