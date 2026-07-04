"use client";

import { useEffect, useState } from "react";
import { LineChart, CircleCheck, CircleX, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { checkHealth } from "@/lib/api";
import type { LatestIngestResponse } from "@/lib/types";

export function DashboardHeader({
  latest,
}: {
  latest: LatestIngestResponse | null;
}) {
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;
    async function poll() {
      try {
        await checkHealth();
        if (mounted) setHealthy(true);
      } catch {
        if (mounted) setHealthy(false);
      }
    }
    poll();
    const id = setInterval(poll, 10000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border/60 pb-6">
      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <LineChart className="size-5" />
        </div>
        <div>
          <h1 className="text-h2">Kalshi Trade Insight System</h1>
          <p className="text-small text-muted-foreground">
            ETL pipeline monitoring &amp; live market watcher
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <PipelineStatusBadge latest={latest} />
        <Badge
          variant="outline"
          className={
            healthy
              ? "gap-1.5 border-emerald-500/40 text-emerald-600 dark:text-emerald-400"
              : "gap-1.5 border-red-500/40 text-red-600 dark:text-red-400"
          }
        >
          {healthy ? (
            <CircleCheck className="size-3.5" />
          ) : (
            <CircleX className="size-3.5" />
          )}
          <span className="metric-sm">
            API {healthy === null ? "checking…" : healthy ? "online" : "offline"}
          </span>
        </Badge>
      </div>
    </header>
  );
}

function PipelineStatusBadge({ latest }: { latest: LatestIngestResponse | null }) {
  if (!latest || latest.status === "pending" || latest.status === "running") {
    return (
      <Badge variant="secondary" className="gap-1.5">
        <Loader2 className="size-3 animate-spin" />
        <span className="metric-sm">ingesting…</span>
      </Badge>
    );
  }
  if (latest.status === "error") {
    return (
      <Badge variant="outline" className="gap-1.5 border-red-500/40 text-red-600 dark:text-red-400">
        <CircleX className="size-3.5" />
        <span className="metric-sm">ingest failed</span>
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="gap-1.5 border-emerald-500/40 text-emerald-600 dark:text-emerald-400">
      <CircleCheck className="size-3.5" />
      <span className="metric-sm">
        synced {latest.result ? `${latest.result.duration_seconds.toFixed(1)}s` : ""}
      </span>
    </Badge>
  );
}
