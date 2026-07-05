/** Max concurrent live chart WebSocket feeds per event dialog (rate-limit guard). */
export const LIVE_CHART_MAX = 8;

export function parseOutcomeLabel(ticker: string, eventTicker: string | null): string {
  if (eventTicker && ticker.startsWith(`${eventTicker}-`)) {
    return ticker.slice(eventTicker.length + 1);
  }
  const parts = ticker.split("-");
  return parts[parts.length - 1] ?? ticker;
}

/** Common sports / market abbreviations for human-readable pane titles. */
const OUTCOME_ALIASES: Record<string, string> = {
  TB: "Tampa Bay",
  HOU: "Houston",
  BAL: "Baltimore",
  CIN: "Cincinnati",
  CLE: "Cleveland",
  CWS: "Chicago WS",
  NYY: "New York Y",
  NYM: "New York M",
  LAD: "LA Dodgers",
  LAA: "LA Angels",
  SF: "San Francisco",
  SD: "San Diego",
  DEN: "Denver",
  NYK: "New York",
  LAL: "LA Lakers",
  BOS: "Boston",
  MIA: "Miami",
  CHI: "Chicago",
  PHI: "Philadelphia",
  TOR: "Toronto",
  YES: "Yes",
  NO: "No",
};

export function formatOutcomeLabel(label: string): string {
  const upper = label.toUpperCase();
  return OUTCOME_ALIASES[upper] ?? label;
}

export function chartPaneHeight(outcomeCount: number): number {
  if (outcomeCount <= 2) return 300;
  if (outcomeCount <= 4) return 260;
  return 200;
}

export function liveChartTickers(
  outcomes: { ticker: string }[],
  clickedTicker: string | null
): Set<string> {
  const ordered = clickedTicker
    ? [
        ...outcomes.filter((o) => o.ticker === clickedTicker),
        ...outcomes.filter((o) => o.ticker !== clickedTicker),
      ]
    : outcomes;

  const live = new Set(ordered.slice(0, LIVE_CHART_MAX).map((o) => o.ticker));
  if (clickedTicker) live.add(clickedTicker);
  return live;
}
