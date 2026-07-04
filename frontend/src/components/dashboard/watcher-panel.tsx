"use client";

import { useEffect, useState } from "react";
import { Loader2, Radio, Settings2, Square, Wifi, WifiOff } from "lucide-react";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

import { getWatcherStatus, startWatcher, stopWatcher } from "@/lib/api";
import type { WatcherStatus } from "@/lib/types";
import type { SocketState } from "@/hooks/use-watcher-socket";

export function WatcherPanel({
  socketState,
  pollCount,
}: {
  socketState: SocketState;
  pollCount: number;
}) {
  const [status, setStatus] = useState<WatcherStatus | null>(null);
  const [interval, setIntervalSeconds] = useState("20");
  const [topK, setTopK] = useState("15");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;

    async function poll() {
      try {
        const res = await getWatcherStatus();
        if (active) setStatus(res);
      } catch {
        // backend not reachable yet; ignore silently on poll
      }
    }

    poll();
    const id = setInterval(poll, 5000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  async function handleStart() {
    setBusy(true);
    try {
      const res = await startWatcher({
        poll_interval_seconds: Number(interval),
        top_k: Number(topK),
      });
      setStatus(res);
      toast.success("Watcher started", {
        description: `Polling every ${interval}s for top ${topK} markets`,
      });
    } catch (err) {
      toast.error("Failed to start watcher", {
        description: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleStop() {
    setBusy(true);
    try {
      const res = await stopWatcher();
      setStatus(res);
      toast.info("Watcher stopped");
    } catch (err) {
      toast.error("Failed to stop watcher", {
        description: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setBusy(false);
    }
  }

  const isRunning = status?.running ?? false;

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/60 bg-card px-4 py-3">
      <div className="flex items-center gap-3">
        <div className="relative flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Radio className="size-4" />
          {isRunning && (
            <span className="absolute -right-0.5 -top-0.5 flex size-2.5">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-500 opacity-75" />
              <span className="relative inline-flex size-2.5 rounded-full bg-emerald-500" />
            </span>
          )}
        </div>
        <div>
          <h2 className="text-h3 leading-none">Live Market Watcher</h2>
          <div className="mt-1 flex items-center gap-2 text-small text-muted-foreground">
            <span className="metric-sm">{isRunning ? "running" : "stopped"}</span>
            <span>·</span>
            <span className="metric-sm">poll #{pollCount}</span>
            <span>·</span>
            <span className="metric-sm">{status?.connected_clients ?? 0} clients</span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <SocketBadge state={socketState} />

        <Popover>
          <PopoverTrigger
            className={cn(buttonVariants({ variant: "outline", size: "sm" }), "gap-2")}
          >
            <Settings2 className="size-3.5" />
            <span className="text-small">Settings</span>
          </PopoverTrigger>
          <PopoverContent align="end" className="w-64 space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="poll_interval" className="label-micro">
                Poll interval (s)
              </Label>
              <Input
                id="poll_interval"
                type="number"
                min={5}
                value={interval}
                onChange={(e) => setIntervalSeconds(e.target.value)}
                disabled={isRunning}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="watcher_top_k" className="label-micro">
                Top K
              </Label>
              <Input
                id="watcher_top_k"
                type="number"
                min={1}
                value={topK}
                onChange={(e) => setTopK(e.target.value)}
                disabled={isRunning}
              />
            </div>
            {!isRunning ? (
              <Button onClick={handleStart} disabled={busy} className="w-full gap-2">
                {busy ? <Loader2 className="size-4 animate-spin" /> : <Radio className="size-4" />}
                Start watcher
              </Button>
            ) : (
              <Button
                onClick={handleStop}
                disabled={busy}
                variant="destructive"
                className="w-full gap-2"
              >
                {busy ? <Loader2 className="size-4 animate-spin" /> : <Square className="size-4" />}
                Stop watcher
              </Button>
            )}
          </PopoverContent>
        </Popover>
      </div>
    </div>
  );
}

function SocketBadge({ state }: { state: SocketState }) {
  if (state === "open") {
    return (
      <Badge className="gap-1.5 border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
        <Wifi className="size-3" />
        <span className="metric-sm">connected</span>
      </Badge>
    );
  }
  if (state === "connecting") {
    return (
      <Badge variant="secondary" className="gap-1.5">
        <Loader2 className="size-3 animate-spin" />
        <span className="metric-sm">connecting</span>
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="gap-1.5 text-muted-foreground">
      <WifiOff className="size-3" />
      <span className="metric-sm">disconnected</span>
    </Badge>
  );
}
