import type {
  CandlesticksResponse,
  IngestRequest,
  IngestResponse,
  LatestIngestResponse,
  SeriesMarketsResponse,
  WatcherStartRequest,
  WatcherStatus,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export function checkHealth(): Promise<{ status: string }> {
  return request("/health");
}

export function runIngest(body: IngestRequest): Promise<IngestResponse> {
  return request("/api/v1/pipeline/ingest", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getLatestIngest(): Promise<LatestIngestResponse> {
  return request("/api/v1/pipeline/latest");
}

export function getSeriesMarkets(
  ticker: string,
  limit = 50
): Promise<SeriesMarketsResponse> {
  return request(
    `/api/v1/series/${encodeURIComponent(ticker)}/markets?limit=${limit}`
  );
}

export function getWatcherStatus(): Promise<WatcherStatus> {
  return request("/api/v1/watcher/status");
}

export function startWatcher(body: WatcherStartRequest): Promise<WatcherStatus> {
  return request("/api/v1/watcher/start", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function stopWatcher(): Promise<WatcherStatus> {
  return request("/api/v1/watcher/stop", { method: "POST" });
}

export function getMarketCandlesticks(
  ticker: string,
  opts: { periodInterval?: 1 | 60 | 1440; lookbackMinutes?: number } = {}
): Promise<CandlesticksResponse> {
  const { periodInterval = 1, lookbackMinutes = 240 } = opts;
  return request(
    `/api/v1/markets/${encodeURIComponent(ticker)}/candlesticks?period_interval=${periodInterval}&lookback_minutes=${lookbackMinutes}`
  );
}
