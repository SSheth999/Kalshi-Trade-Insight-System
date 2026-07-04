"use client";

import { useState } from "react";
import { Loader2, PlayCircle, Settings2 } from "lucide-react";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { runIngest } from "@/lib/api";
import { formatDuration } from "@/lib/format";
import type { IngestResponse } from "@/lib/types";

export function PipelineControls({
  onCompleted,
}: {
  onCompleted: (result: IngestResponse) => void;
}) {
  const [through, setThrough] = useState("3");
  const [topK, setTopK] = useState("6");
  const [persistDb, setPersistDb] = useState(true);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);

  async function handleRun() {
    setLoading(true);
    try {
      const res = await runIngest({
        through: Number(through),
        top_k: Number(topK),
        persist_db: persistDb,
      });
      onCompleted(res);
      setOpen(false);
      toast.success(`Ingestion complete (through phase ${res.through})`, {
        description: `${formatDuration(res.duration_seconds)} · ${
          res.phase_2?.ranked_series.length ?? 0
        } series ranked`,
      });
    } catch (err) {
      toast.error("Ingestion failed", {
        description: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        className={cn(buttonVariants({ variant: "outline", size: "sm" }), "gap-2")}
      >
        <Settings2 className="size-3.5" />
        <span className="text-small">Re-run pipeline</span>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72 space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="pc-through" className="label-micro">
            Run through
          </Label>
          <Select value={through} onValueChange={(v) => v && setThrough(v)}>
            <SelectTrigger id="pc-through" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1">Phase 1 — Discover</SelectItem>
              <SelectItem value="2">Phase 2 — Score</SelectItem>
              <SelectItem value="3">Phase 3 — Collect</SelectItem>
              <SelectItem value="4">Phase 4 — History</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="pc-topk" className="label-micro">
            Top K series
          </Label>
          <Input
            id="pc-topk"
            type="number"
            min={1}
            value={topK}
            onChange={(e) => setTopK(e.target.value)}
          />
        </div>

        <div className="flex items-center justify-between">
          <Label htmlFor="pc-persist" className="label-micro">
            Persist to Supabase
          </Label>
          <Switch id="pc-persist" checked={persistDb} onCheckedChange={setPersistDb} />
        </div>

        <Button onClick={handleRun} disabled={loading} className="w-full gap-2">
          {loading ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <PlayCircle className="size-4" />
          )}
          {loading ? "Running…" : "Run ingest"}
        </Button>
      </PopoverContent>
    </Popover>
  );
}
