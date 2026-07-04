"use client";

import { useState } from "react";
import {
  Database,
  Filter,
  Layers,
  Radar,
  Sparkles,
} from "lucide-react";

import { StatCard } from "@/components/dashboard/stat-card";
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

import { formatVolume } from "@/lib/format";
import type { IngestResponse } from "@/lib/types";

type DialogKind = "universe" | "markets" | "sync" | null;

export function OverviewGrid({ result }: { result: IngestResponse | null }) {
  const [openDialog, setOpenDialog] = useState<DialogKind>(null);

  const p1 = result?.phase_1;
  const p2 = result?.phase_2;
  const p3 = result?.phase_3;
  const db = result?.db_load;

  const passRate = p1
    ? (p1.series_passing_volume_filter / p1.total_series_fetched) * 100
    : null;

  return (
    <section className="space-y-3">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          label="Series Universe"
          value={p1 ? p1.total_series_fetched.toLocaleString() : "—"}
          description={
            p1 ? `${p1.series_passing_volume_filter.toLocaleString()} passed volume filter` : undefined
          }
          icon={<Radar className="size-3.5" />}
          accent="neutral"
          loading={!result}
          onClick={result ? () => setOpenDialog("universe") : undefined}
        />
        <StatCard
          label="Series Scored"
          value={p2 ? p2.series_scored.toLocaleString() : "—"}
          description={p2 ? `${p2.series_skipped_no_open_markets} skipped (no open markets)` : undefined}
          icon={<Sparkles className="size-3.5" />}
          accent="primary"
          loading={!result}
        />
        <StatCard
          label="Markets Collected"
          value={p3 ? p3.total_markets.toLocaleString() : "—"}
          description={p3 ? `across ${p3.series_count} top-K series` : undefined}
          icon={<Layers className="size-3.5" />}
          accent="neutral"
          loading={!result}
          onClick={p3 ? () => setOpenDialog("markets") : undefined}
        />
        <StatCard
          label="Supabase Sync"
          value={db ? db.markets_upserted.toLocaleString() : "—"}
          description={db ? `${db.rankings_inserted} rankings · run ${db.run_id.slice(0, 8)}` : undefined}
          icon={<Database className="size-3.5" />}
          accent="positive"
          loading={!result}
          onClick={db ? () => setOpenDialog("sync") : undefined}
        />
      </div>

      {/* Universe detail */}
      <Dialog open={openDialog === "universe"} onOpenChange={(o) => !o && setOpenDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-h3 flex items-center gap-2">
              <Filter className="size-4" />
              Series Universe — Phase 1
            </DialogTitle>
            <DialogDescription className="text-body">
              All active Kalshi series, filtered by minimum lifetime volume.
            </DialogDescription>
          </DialogHeader>
          {p1 && (
            <div className="grid grid-cols-2 gap-3 pt-2">
              <DetailStat label="Total fetched" value={p1.total_series_fetched.toLocaleString()} />
              <DetailStat label="Min volume threshold" value={formatVolume(p1.min_volume)} />
              <DetailStat label="Passed filter" value={p1.series_passing_volume_filter.toLocaleString()} />
              <DetailStat label="Pass rate" value={passRate !== null ? `${passRate.toFixed(1)}%` : "—"} />
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Markets breakdown */}
      <Dialog open={openDialog === "markets"} onOpenChange={(o) => !o && setOpenDialog(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-h3 flex items-center gap-2">
              <Layers className="size-4" />
              Markets Collected — Phase 3
            </DialogTitle>
            <DialogDescription className="text-body">
              Per-series market counts cached from the Phase 2 volatility scan.
            </DialogDescription>
          </DialogHeader>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Series</TableHead>
                <TableHead className="text-right">Markets</TableHead>
                <TableHead className="text-right">24h Vol</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {p2?.ranked_series.map((s) => (
                <TableRow key={s.ticker}>
                  <TableCell className="text-body">{s.ticker}</TableCell>
                  <TableCell className="text-right metric">{s.open_market_count}</TableCell>
                  <TableCell className="text-right metric">{formatVolume(s.total_vol24)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </DialogContent>
      </Dialog>

      {/* Supabase sync detail */}
      <Dialog open={openDialog === "sync"} onOpenChange={(o) => !o && setOpenDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-h3 flex items-center gap-2">
              <Database className="size-4" />
              Supabase Sync
            </DialogTitle>
            <DialogDescription className="text-body">
              Rows upserted into Postgres for this ingestion run.
            </DialogDescription>
          </DialogHeader>
          {db && (
            <div className="grid grid-cols-2 gap-3 pt-2">
              <DetailStat label="Run ID" value={db.run_id} mono small />
              <DetailStat label="Series upserted" value={db.series_upserted.toLocaleString()} />
              <DetailStat label="Markets upserted" value={db.markets_upserted.toLocaleString()} />
              <DetailStat label="Rankings inserted" value={db.rankings_inserted.toLocaleString()} />
              <DetailStat label="Candlesticks upserted" value={db.candlesticks_upserted.toLocaleString()} />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </section>
  );
}

function DetailStat({
  label,
  value,
  mono,
  small,
}: {
  label: string;
  value: string;
  mono?: boolean;
  small?: boolean;
}) {
  return (
    <div className="rounded-lg border border-border/60 bg-muted/30 px-3 py-2">
      <div className="label-micro">{label}</div>
      <div className={mono ? (small ? "metric-sm break-all" : "metric") : "text-body-lg"}>
        {value}
      </div>
    </div>
  );
}
