export interface RankedSeriesSummary {
  ticker: string;
  title: string;
  score: number;
  open_market_count: number;
  max_1d_move: number;
  avg_spread: number;
  total_vol24: number;
}

export interface Phase1Summary {
  min_volume: number;
  total_series_fetched: number;
  series_passing_volume_filter: number;
}

export interface Phase2Summary {
  top_k: number;
  series_scored: number;
  series_skipped_no_open_markets: number;
  markets_cached: number;
  ranked_series: RankedSeriesSummary[];
}

export interface Phase3Summary {
  top_k: number;
  series_count: number;
  total_markets: number;
}

export interface SeriesHistorySummary {
  series_ticker: string;
  market_count: number;
  candlestick_count: number;
}

export interface Phase4Summary {
  lookback_days: number;
  period_interval: number;
  max_markets_per_series: number;
  markets_fetched: number;
  candlestick_count: number;
  markets_failed_count: number;
  series: SeriesHistorySummary[];
}

export interface DbLoadSummary {
  run_id: string;
  series_upserted: number;
  markets_upserted: number;
  rankings_inserted: number;
  candlesticks_upserted: number;
}

export interface IngestRequest {
  through: number;
  min_volume?: number | null;
  top_k?: number | null;
  max_series_to_score?: number | null;
  concurrency?: number | null;
  lookback_days?: number | null;
  period_interval?: 1 | 60 | 1440 | null;
  max_markets_per_series?: number | null;
  candlestick_concurrency?: number | null;
  persist?: boolean;
  persist_db?: boolean;
}
export interface IngestResponse {
  status: "completed";
  through: number;
  duration_seconds: number;
  phase_1: Phase1Summary;
  phase_2: Phase2Summary | null;
  phase_3: Phase3Summary | null;
  phase_4: Phase4Summary | null;
  artifacts: string[];
  db_load: DbLoadSummary | null;
}

export interface LatestIngestResponse {
  status: "pending" | "running" | "ready" | "error";
  result: IngestResponse | null;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface MarketRow {
  ticker: string;
  event_ticker: string | null;
  title: string | null;
  status: string | null;
  yes_bid_dollars: number | null;
  yes_ask_dollars: number | null;
  last_price_dollars: number | null;
  previous_price_dollars: number | null;
  volume_24h_fp: number | null;
  open_interest_fp: number | null;
  close_time: string | null;
}

export interface SeriesMarketsResponse {
  series_ticker: string;
  market_count: number;
  markets: MarketRow[];
}

export interface WatcherStatus {
  running: boolean;
  poll_interval_seconds: number | null;
  top_k: number | null;
  poll_count: number;
  connected_clients: number;
}

export interface WatcherStartRequest {
  poll_interval_seconds: number;
  top_k: number;
}

export interface MarketTick {
  ticker: string;
  series_ticker: string;
  last_price_dollars: number | null;
  yes_bid_dollars: number | null;
  yes_ask_dollars: number | null;
  volume_24h_fp: number | null;
  open_interest_fp: number | null;
  price_delta: number | null;
}

export interface WatcherSnapshot {
  event: "snapshot";
  poll_count: number;
  tickers: MarketTick[];
}

export interface CandlestickPoint {
  time: number;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
}

export interface CandlesticksResponse {
  ticker: string;
  period_interval: number;
  candles: CandlestickPoint[];
}

export interface MarketChartTick {
  event: "tick";
  ticker: string;
  time: number;
  price: number | null;
  yes_bid: number | null;
  yes_ask: number | null;
}

export interface EventOutcomeRow extends MarketRow {
  outcome_label: string;
}

export interface EventMarketsResponse {
  event_ticker: string;
  title: string | null;
  series_ticker: string | null;
  outcome_count: number;
  outcomes: EventOutcomeRow[];
}
