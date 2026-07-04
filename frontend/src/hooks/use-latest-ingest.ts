"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { getLatestIngest } from "@/lib/api";
import type { LatestIngestResponse } from "@/lib/types";

const ACTIVE_POLL_MS = 2000;
const IDLE_POLL_MS = 30000;

export function useLatestIngest() {
  const [data, setData] = useState<LatestIngestResponse | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const kickRef = useRef<() => void>(() => {});

  useEffect(() => {
    let active = true;

    async function poll() {
      try {
        const res = await getLatestIngest();
        if (!active) return;
        setData(res);
        const delay =
          res.status === "pending" || res.status === "running"
            ? ACTIVE_POLL_MS
            : IDLE_POLL_MS;
        timerRef.current = setTimeout(poll, delay);
      } catch {
        if (active) timerRef.current = setTimeout(poll, ACTIVE_POLL_MS);
      }
    }

    kickRef.current = () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      poll();
    };

    poll();
    return () => {
      active = false;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const refetch = useCallback(() => {
    kickRef.current();
  }, []);

  return { data, refetch };
}
