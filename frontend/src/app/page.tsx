"use client";

import { DashboardHeader } from "@/components/dashboard/dashboard-header";
import { OverviewGrid } from "@/components/dashboard/overview-grid";
import { PipelineControls } from "@/components/dashboard/pipeline-controls";
import { SeriesGrid } from "@/components/dashboard/series-grid";
import { WatcherPanel } from "@/components/dashboard/watcher-panel";
import { LiveTickerTable } from "@/components/dashboard/live-ticker-table";
import { useLatestIngest } from "@/hooks/use-latest-ingest";
import { useWatcherSocket } from "@/hooks/use-watcher-socket";
import { formatDuration } from "@/lib/format";

export default function DashboardPage() {
  const { data: latest, refetch } = useLatestIngest();
  const { state, pollCount, tickers } = useWatcherSocket();

  const result = latest?.result ?? null;
  const rankedSeries = result?.phase_2?.ranked_series ?? [];

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-6 py-10">
        <DashboardHeader latest={latest} />

        <section className="space-y-3">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <h2 className="text-h3">Pipeline Overview</h2>
              <p className="text-small text-muted-foreground">
                {result
                  ? `Last run completed in ${formatDuration(result.duration_seconds)}`
                  : "Running the initial ingestion — this can take up to ~20s…"}
              </p>
            </div>
            <PipelineControls
              onCompleted={() => {
                refetch();
              }}
            />
          </div>
          <OverviewGrid result={result} />
        </section>

        <SeriesGrid series={rankedSeries} />

        <section className="space-y-3">
          <WatcherPanel socketState={state} pollCount={pollCount} />
          <LiveTickerTable tickers={tickers} />
        </section>
      </div>
    </div>
  );
}
