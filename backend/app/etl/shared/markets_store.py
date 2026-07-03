"""In-memory store for open markets fetched during Phase 2 scoring."""


class MarketsStore:
    def __init__(self) -> None:
        self._by_series: dict[str, list] = {}

    def put(self, series_ticker: str, markets: list) -> None:
        self._by_series[series_ticker] = markets

    def get(self, series_ticker: str) -> list:
        return self._by_series.get(series_ticker, [])

    def series_tickers(self) -> list[str]:
        return list(self._by_series.keys())

    def __len__(self) -> int:
        return len(self._by_series)
